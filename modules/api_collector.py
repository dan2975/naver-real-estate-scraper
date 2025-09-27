#!/usr/bin/env python3
"""
🚀 APICollector - 네이버 부동산 API 수집
- 네이버 내부 API 호출
- 대량 매물 수집
- 페이지네이션 처리
- 스텔스 기능 통합
- 실시간 진행률 업데이트
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from .stealth_manager import StealthManager

# 진행률 관리자 임포트
try:
    from progress_manager import get_progress_manager
except ImportError:
    # 진행률 관리자가 없어도 동작하도록 더미 함수
    def get_progress_manager():
        class DummyProgressManager:
            def update_page_progress(self, *args, **kwargs): pass
            def add_error(self, *args, **kwargs): pass
        return DummyProgressManager()


class APICollector:
    """🚀 네이버 부동산 API를 통한 매물 수집 클래스"""
    
    def __init__(self, stealth_manager: StealthManager, streamlit_filters=None):
        self.stealth_manager = stealth_manager
        # 🔄 API URL 교체: HTTP 307 차단 회피
        self.api_urls = [
            'https://m.land.naver.com/cluster/ajax/articleList',  # 기존 URL
            'https://m.land.naver.com/ajax/articleList',          # 대안 URL 1
            'https://land.naver.com/api/articles',                # 대안 URL 2
            'https://new.land.naver.com/api/articles'             # 대안 URL 3
        ]
        self.current_api_index = 0
        self.api_url = self.api_urls[self.current_api_index]
        self.progress_manager = get_progress_manager()
        self.streamlit_filters = streamlit_filters or {}
        
        # 🎯 중복 감지 시스템
        self.collected_article_ids = set()  # 이미 수집된 article_no 저장
        self.duplicate_count = 0            # 중복 발견 카운터
        
        # 동적 API 파라미터 (Streamlit 필터 반영)
        self.base_api_params = self._build_api_params_from_filters()
    
    def _build_api_params_from_filters(self) -> Dict[str, Any]:
        """🎯 Streamlit 필터를 API 파라미터로 변환"""
        # 기본값 (조건.md 기준)
        default_filters = {
            'deposit_max': 2000,      # 보증금 최대 2000만원
            'monthly_rent_max': 130,  # 월세 최대 130만원  
            'area_min': 20           # 면적 최소 20평 (66㎡)
        }
        
        # Streamlit 필터가 있으면 우선 적용
        deposit_max = self.streamlit_filters.get('deposit_max', default_filters['deposit_max'])
        monthly_rent_max = self.streamlit_filters.get('monthly_rent_max', default_filters['monthly_rent_max']) 
        area_min_pyeong = self.streamlit_filters.get('area_min', default_filters['area_min'])
        area_min_sqm = int(area_min_pyeong * 3.3)  # 평을 ㎡로 변환
        
        print(f"            🎯 필터 적용됨 - 보증금≤{deposit_max}만원, 월세≤{monthly_rent_max}만원, 면적≥{area_min_pyeong}평")
        
        return {
            'rletTpCd': 'SG:SMS',  # 상가+사무실
            'tradTpCd': 'B2',      # 월세
            'z': '12',             # 줌 레벨
            'lat': '37.517',       # 강남구 중심 위도
            'lon': '127.047',      # 강남구 중심 경도
            'btm': '37.492',       # 강남구 남쪽 경계
            'lft': '127.012',      # 강남구 서쪽 경계  
            'top': '37.542',       # 강남구 북쪽 경계
            'rgt': '127.082',      # 강남구 동쪽 경계
            'wprcMax': str(deposit_max),      # 동적 보증금 최대
            'rprcMax': str(monthly_rent_max), # 동적 월세 최대
            'spcMin': str(area_min_sqm),      # 동적 면적 최소
            'page': '1',
            'showR0': '',
            'totCnt': '7689',
            'cortarNo': ''
        }
    
    async def collect_with_api_params(self, api_params: Dict[str, Any], district_name: str, max_pages: int = 20) -> List[Dict[str, Any]]:
        """🌐 API 파라미터로 대량 수집"""
        print(f"            🌐 API 파라미터 추출 완료, 대량 수집 시작...")
        
        # 🔧 지역별 API URL 리셋 (중요: 이전 지역에서 무효화된 URL 복구)
        self.current_api_index = 0
        self.api_url = self.api_urls[self.current_api_index]
        print(f"            🔄 {district_name} 전용 API URL 리셋: {self.api_url}")
        
        # API 파라미터 구성 (완화된 조건으로 유지)
        request_params = self.base_api_params.copy()
        
        # 🎯 브라우저에서 추출한 파라미터 우선 사용 (동기화 보장)
        if 'lat' in api_params and 'lon' in api_params:
            # 브라우저 상태 그대로 사용 (완벽한 동기화)
            print(f"            🎯 브라우저 상태 동기화: lat={api_params['lat']}, lon={api_params['lon']}")
            request_params.update({
                'lat': str(api_params['lat']),
                'lon': str(api_params['lon']),
                'zoom': str(api_params.get('zoom', 12))
            })
            
            # 브라우저 필터도 그대로 사용
            browser_filters = ['wprcMax', 'rprcMax', 'spcMin', 'flrMin', 'flrMax']
            for filter_key in browser_filters:
                if filter_key in api_params:
                    request_params[filter_key] = str(api_params[filter_key])
                    print(f"            🎯 브라우저 필터 동기화: {filter_key}={api_params[filter_key]}")
            
            # 브라우저 총 매물 수 저장
            if 'browser_total_count' in api_params:
                self._browser_total_count = api_params['browser_total_count']
                print(f"            🎯 브라우저 총 매물 수 설정: {self._browser_total_count}개")
                # 진행률 관리자에도 전달
                try:
                    self.progress_manager.set_district_browser_total(district_name, self._browser_total_count)
                except:
                    pass
        else:
            # 폴백: 기존 하드코딩 좌표 사용
            print(f"            ⚠️ 브라우저 파라미터 없음, 기본 좌표 사용")
            
        # 서울시 25개 구별 좌표 (인접 지역 10% 겹침 허용 - 매물 누락 최소화)
        district_coords = {
            # 강남 3구 (10-15% 겹침 허용으로 매물 누락 최소화)
            '강남구': {'lat': 37.516, 'lon': 127.055, 'btm': 37.485, 'lft': 127.030, 'top': 37.550, 'rgt': 127.085},
            '서초구': {'lat': 37.485, 'lon': 127.015, 'btm': 37.455, 'lft': 126.980, 'top': 37.515, 'rgt': 127.050},
            '송파구': {'lat': 37.515, 'lon': 127.115, 'btm': 37.485, 'lft': 127.090, 'top': 37.545, 'rgt': 127.145},
            
            # 강동 지역 (10% 겹침 허용)
            '강동구': {'lat': 37.545, 'lon': 127.135, 'btm': 37.520, 'lft': 127.115, 'top': 37.570, 'rgt': 127.155},
            '광진구': {'lat': 37.555, 'lon': 127.085, 'btm': 37.535, 'lft': 127.065, 'top': 37.575, 'rgt': 127.105},
            '성동구': {'lat': 37.560, 'lon': 127.045, 'btm': 37.540, 'lft': 127.025, 'top': 37.580, 'rgt': 127.065},
            
            # 동북 지역 (10% 겹침 허용)
            '동대문구': {'lat': 37.585, 'lon': 127.045, 'btm': 37.565, 'lft': 127.025, 'top': 37.605, 'rgt': 127.065},
            '중랑구': {'lat': 37.605, 'lon': 127.080, 'btm': 37.585, 'lft': 127.060, 'top': 37.625, 'rgt': 127.100},
            '성북구': {'lat': 37.595, 'lon': 127.015, 'btm': 37.575, 'lft': 126.995, 'top': 37.615, 'rgt': 127.035},
            '강북구': {'lat': 37.625, 'lon': 127.025, 'btm': 37.605, 'lft': 127.005, 'top': 37.645, 'rgt': 127.045},
            '도봉구': {'lat': 37.665, 'lon': 127.035, 'btm': 37.645, 'lft': 127.015, 'top': 37.685, 'rgt': 127.055},
            '노원구': {'lat': 37.645, 'lon': 127.075, 'btm': 37.615, 'lft': 127.055, 'top': 37.675, 'rgt': 127.095},
            
            # 서북 지역 (10% 겹침 허용)
            '은평구': {'lat': 37.605, 'lon': 126.925, 'btm': 37.585, 'lft': 126.905, 'top': 37.625, 'rgt': 126.945},
            '서대문구': {'lat': 37.575, 'lon': 126.945, 'btm': 37.555, 'lft': 126.925, 'top': 37.595, 'rgt': 126.965},
            '마포구': {'lat': 37.565, 'lon': 126.915, 'btm': 37.545, 'lft': 126.895, 'top': 37.585, 'rgt': 126.935},
            
            # 중심 지역 (10% 겹침 허용)
            '종로구': {'lat': 37.585, 'lon': 126.985, 'btm': 37.565, 'lft': 126.965, 'top': 37.605, 'rgt': 127.005},
            '중구': {'lat': 37.565, 'lon': 126.985, 'btm': 37.545, 'lft': 126.965, 'top': 37.585, 'rgt': 127.005},
            '용산구': {'lat': 37.535, 'lon': 126.975, 'btm': 37.515, 'lft': 126.955, 'top': 37.555, 'rgt': 126.995},
            
            # 서남 지역 (10% 겹침 허용)
            '강서구': {'lat': 37.565, 'lon': 126.825, 'btm': 37.545, 'lft': 126.805, 'top': 37.585, 'rgt': 126.845},
            '양천구': {'lat': 37.525, 'lon': 126.845, 'btm': 37.505, 'lft': 126.825, 'top': 37.545, 'rgt': 126.865},
            '구로구': {'lat': 37.485, 'lon': 126.865, 'btm': 37.465, 'lft': 126.845, 'top': 37.505, 'rgt': 126.885},
            '금천구': {'lat': 37.465, 'lon': 126.905, 'btm': 37.445, 'lft': 126.885, 'top': 37.485, 'rgt': 126.925},
            '영등포구': {'lat': 37.525, 'lon': 126.915, 'btm': 37.505, 'lft': 126.895, 'top': 37.545, 'rgt': 126.935},
            
            # 남부 지역 (10% 겹침 허용)
            '동작구': {'lat': 37.495, 'lon': 126.965, 'btm': 37.475, 'lft': 126.945, 'top': 37.515, 'rgt': 126.985},
            '관악구': {'lat': 37.475, 'lon': 126.945, 'btm': 37.455, 'lft': 126.925, 'top': 37.495, 'rgt': 126.965}
        }
        
        coords = district_coords.get(district_name, district_coords['강남구'])
        
        request_params.update({
            'lat': str(coords['lat']),
            'lon': str(coords['lon']),
            'btm': str(coords['btm']),
            'lft': str(coords['lft']),
            'top': str(coords['top']),
            'rgt': str(coords['rgt']),
            # 조건.md 준수 (엄격한 조건)
            'wprcMax': '2000',     # 보증금 최대 2000만원
            'rprcMax': '130',      # 월세 최대 130만원  
            'spcMin': '66'         # 면적 최소 66㎡ = 20평
        })
        
        return await self.stealth_mass_collect(request_params, district_name, max_pages)
    
    async def stealth_mass_collect(self, api_params: Dict[str, Any], district_name: str, max_pages: int = 500) -> List[Dict[str, Any]]:
        """🥷 스텔스 모드로 대량 수집"""
        print(f"            🥷 스텔스 API 수집 시작 (최대 {max_pages}페이지)")
        
        all_properties = []
        current_page = 1
        consecutive_failures = 0
        max_failures = 3
        
        # 페르소나 설정
        self.stealth_manager.set_persona(self.stealth_manager.get_random_persona())
        
        # 🚀 진정한 무제한 수집: API 완료 신호까지 수집 (안전장치 강화)
        # 1순위: API "more": false 완료 신호
        # 2순위: 연속 빈 응답 5회
        # 3순위: 시간 제한 (구별 60분 = 3600초)
        # 마지막: 극한 안전장치 (10,000페이지 = 200,000개)
        max_iterations = min(max_pages, 10000)  # 극한 안전장치: 10,000페이지
        max_time_seconds = 3600  # 구별 최대 60분
        empty_response_count = 0
        max_empty_responses = 5
        start_time = time.time()  # 시간 제한 체크용
        
        while current_page <= max_iterations and consecutive_failures < max_failures:
            # 🛡️ 다중 안전장치 체크
            try:
                # 1. 사용자 중지 요청
                if self.progress_manager.is_stop_requested():
                    print(f"                  🛑 수집 중지 요청 감지 → 중단 (페이지 {current_page})", flush=True)
                    break
                
                # 2. 시간 제한 체크 (구별 60분)
                elapsed_time = time.time() - start_time
                if elapsed_time > max_time_seconds:
                    print(f"                  ⏰ 시간 제한 도달 → 중단 ({elapsed_time/60:.1f}분, 페이지 {current_page})", flush=True)
                    break
                    
            except:
                pass
                
            try:
                print(f"               📄 {current_page}페이지 (스텔스 모드)...", flush=True)
                
                # 🛡️ HTTP 307 방지: 세션 재생성 (매 5페이지마다)
                if current_page % 5 == 1 or current_page == 1:
                    print(f"                  🔄 세션 재생성 (페이지 {current_page})", flush=True)
                    self.stealth_manager.create_stealth_session_pool()
                
                # 스텔스 세션 가져오기
                session = self.stealth_manager.get_stealth_session()
                
                # API 요청 파라미터
                params = api_params.copy()
                params['page'] = current_page
                
                # 첫 페이지가 아니면 대기
                if current_page > 1:
                    wait_time = self.stealth_manager.get_human_wait_time()
                    self.stealth_manager.wait_with_message(wait_time, f"({self.stealth_manager.current_persona} 패턴)")
                
                # API 호출
                response = session.get(self.api_url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 총 매물 수 확인 (첫 페이지에서)
                    if current_page == 1:
                        print(f"                  🔍 API 응답 구조 디버그:", flush=True)
                        print(f"                      data 키들: {list(data.keys()) if data else 'data is None'}", flush=True)
                        if data and 'data' in data:
                            print(f"                      data.data 키들: {list(data['data'].keys())}", flush=True)
                        
                        # 다양한 경로에서 totCnt 찾기
                        total_count = 0
                        if 'totCnt' in data:
                            total_count = data['totCnt']
                            print(f"                      totCnt 발견 (최상위): {total_count}", flush=True)
                        elif data.get('data', {}).get('totCnt'):
                            total_count = data['data']['totCnt']
                            print(f"                      totCnt 발견 (data.totCnt): {total_count}", flush=True)
                        elif 'body' in data and isinstance(data['body'], dict) and 'totCnt' in data['body']:
                            total_count = data['body']['totCnt']
                            print(f"                      totCnt 발견 (body.totCnt): {total_count}", flush=True)
                        else:
                            print(f"                      totCnt를 찾을 수 없음. 가능한 키들: {list(data.keys())}", flush=True)
                            # 샘플 응답 저장 (디버깅용)
                            import json
                            with open('debug_api_response.json', 'w', encoding='utf-8') as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                            print(f"                      샘플 응답 저장: debug_api_response.json", flush=True)
                        
                        if total_count:
                            self._total_count = total_count
                            print(f"                  📊 총 {total_count}개 매물 확인됨", flush=True)
                            # 진행률 관리자에 총 개수 업데이트 (안전 처리)
                            try:
                                self.progress_manager.update_page_progress(current_page, 0, total_count)
                            except:
                                pass
                        else:
                            # totCnt를 찾을 수 없으면 more 필드 기반 수집
                            self._total_count = None  # more 필드로 제어
                            print(f"                  ⚠️ totCnt를 찾을 수 없음 - 'more' 필드 기반 수집 모드", flush=True)
                    
                    # 기존 시스템과 동일한 응답 처리
                    if 'body' in data and isinstance(data['body'], list):
                        articles = data['body']
                    else:
                        articles = data.get('data', {}).get('ARTICLE', [])
                    
                    if articles:
                        print(f"                  ✅ {len(articles)}개 원시 데이터", flush=True)
                        
                        # 매물 처리 (안전한 처리)
                        processed_count = 0
                        for article in articles:
                            try:
                                processed_property = self.process_api_property(article, district_name)
                                if processed_property:
                                    all_properties.append(processed_property)
                                    processed_count += 1
                            except Exception as prop_error:
                                print(f"                     ⚠️ 매물 처리 오류 (건너뜀): {prop_error}", flush=True)
                                continue
                        
                        unique_count = len(self.collected_article_ids)
                        print(f"                  ✅ {processed_count}개 처리 완료 (누적: {len(all_properties)}개, 유니크: {unique_count}개)", flush=True)
                        if self.duplicate_count > 0:
                            print(f"                  📊 중복 통계: {self.duplicate_count}개 중복 감지됨", flush=True)
                        consecutive_failures = 0
                        
                        # 진행률 업데이트 (안전 처리)
                        try:
                            browser_total = getattr(self, '_browser_total_count', None)
                            self.progress_manager.update_page_progress(current_page, processed_count, browser_total)
                        except:
                            pass
                        
                        # 수집 종료 조건 확인
                        more_value = data.get('more', 'unknown')
                        unique_count = len(self.collected_article_ids)
                        
                        # 🎯 브라우저 감지 수 기준 종료 조건
                        browser_total = getattr(self, '_browser_total_count', None)
                        if browser_total and unique_count >= browser_total:
                            print(f"                  🎯 브라우저 정확한 매물 수 도달: {unique_count}/{browser_total}개", flush=True)
                            print(f"                  ✅ 브라우저-API 동기화 완료! (+{len(all_properties) - browser_total}개 차이)", flush=True)
                            break
                        
                        if hasattr(self, '_total_count'):
                            print(f"                  🔍 디버그: _total_count={self._total_count}, 현재={len(all_properties)}개, 유니크={unique_count}개, more={more_value}", flush=True)
                            if self._total_count is not None and len(all_properties) >= self._total_count:
                                print(f"                  🎯 전체 매물 수집 완료: {len(all_properties)}/{self._total_count}개", flush=True)
                                break
                        
                        # 'more' 필드로 종료 조건 확인 (API가 더 이상 데이터 없음을 알림)
                        if 'more' in data and not data['more']:
                            print(f"                  🎯 API 응답 완료: 더 이상 데이터 없음 (총 {len(all_properties)}개 수집)", flush=True)
                            break
                        
                        # 🛡️ 빈 응답 연속 감지 (안전장치 강화)
                        if not articles:
                            empty_response_count += 1
                            print(f"                  ⚠️ 빈 응답 감지 {empty_response_count}/{max_empty_responses}", flush=True)
                            if empty_response_count >= max_empty_responses:
                                print(f"                  🎯 연속 빈 응답 {empty_response_count}회: 수집 완료 (총 {len(all_properties)}개)", flush=True)
                                break
                        else:
                            # 매물이 있으면 빈 응답 카운터 리셋
                            empty_response_count = 0
                        
                        # 🎯 순수 브라우저 감지 시스템 (하드코딩 완전 제거)
                        if hasattr(self, '_browser_total_count') and self._browser_total_count:
                            # 정확히 브라우저 매물 수에 도달하거나 1-2개 차이 허용
                            if len(all_properties) >= self._browser_total_count:
                                actual_collected = len(all_properties)
                                target_count = self._browser_total_count
                                difference = actual_collected - target_count
                                
                                print(f"                  🎯 브라우저 정확한 매물 수 도달: {actual_collected}/{target_count}개", flush=True)
                                if difference == 0:
                                    print(f"                  ✅ 완벽한 브라우저-API 동기화 달성! (정확히 일치)", flush=True)
                                else:
                                    print(f"                  ✅ 브라우저-API 동기화 완료! ({difference:+d}개 차이)", flush=True)
                                break
                        else:
                            # 브라우저 매물 수를 감지하지 못한 경우에만 경고
                            if len(all_properties) >= 3000:  # 매우 높은 안전 제한
                                print(f"                  ⚠️ 브라우저 매물 수 감지 실패 - 안전 제한 도달: {len(all_properties)}개", flush=True)
                                print(f"                  🔧 브라우저 감지 로직 개선 필요", flush=True)
                                break
                        
                        # 강제 안전 제한 (비정상 상황 방지)
                        if len(all_properties) >= 2000:
                            print(f"                  ⚠️ 안전 제한 도달: 2000개 수집 완료 (more={more_value})", flush=True)
                            break
                        
                        # 5페이지마다 긴 휴식
                        if current_page % 5 == 0:
                            rest_time = self.stealth_manager.get_human_wait_time(long_wait=True)
                            print(f"                  😴 5페이지 수집 완료, {rest_time}초 휴식...", flush=True)
                            await asyncio.sleep(rest_time)
                    else:
                        print(f"                  ⚠️ {current_page}페이지: 매물 없음", flush=True)
                        consecutive_failures += 1
                        
                        # 연속 3페이지 매물 없으면 수집 종료
                        if consecutive_failures >= 3:
                            print(f"                  🛑 연속 {consecutive_failures}페이지 매물 없음 → 수집 종료", flush=True)
                            break
                else:
                    print(f"                  ❌ {current_page}페이지: HTTP {response.status_code}", flush=True)
                    
                    # 🛡️ HTTP 307 리다이렉트 특별 처리: API URL 교체
                    if response.status_code == 307:
                        print(f"                  🔄 HTTP 307 감지: API URL 교체 시도", flush=True)
                        if self.current_api_index < len(self.api_urls) - 1:
                            self.current_api_index += 1
                            self.api_url = self.api_urls[self.current_api_index]
                            print(f"                  🔄 새 API URL: {self.api_url}", flush=True)
                            self.stealth_manager.create_stealth_session_pool()
                            # 즉시 재시도 (페이지 증가 없이)
                            continue
                        else:
                            print(f"                  ❌ 모든 API URL 시도 완료: 수집 종료", flush=True)
                            break
                    
                    consecutive_failures += 1
                    
                    # 연속 5페이지 HTTP 오류시 수집 종료
                    if consecutive_failures >= 5:
                        print(f"                  🛑 연속 {consecutive_failures}페이지 오류 → 수집 종료", flush=True)
                        break
                
                current_page += 1
                
            except Exception as e:
                import traceback
                print(f"                  ❌ {current_page}페이지 수집 오류: {e}", flush=True)
                print(f"                  🔍 상세 오류: {traceback.format_exc()}", flush=True)
                consecutive_failures += 1
                current_page += 1
                
                # 오류 시 더 긴 대기
                error_wait = self.stealth_manager.get_human_wait_time(long_wait=True)
                await asyncio.sleep(error_wait)
        
        unique_count = len(self.collected_article_ids)
        print(f"            ✅ {district_name} 신중한 수집 완료: {len(all_properties)}개 (유니크: {unique_count}개)", flush=True)
        if self.duplicate_count > 0:
            print(f"            📊 최종 중복 통계: {self.duplicate_count}개 중복 제거됨", flush=True)
        print(f"            🎉 스텔스 수집 성공! (총 {len(all_properties)}개, 유니크 {unique_count}개)", flush=True)
        
        return all_properties
    
    def process_api_property(self, prop, district_name: str) -> Optional[Dict[str, Any]]:
        """🏠 API 매물 데이터 처리 (중복 감지 포함)"""
        try:
            # 🎯 중복 감지 및 필터링
            atcl_no = prop.get('atclNo', '') if isinstance(prop, dict) else ''
            if atcl_no and atcl_no in self.collected_article_ids:
                self.duplicate_count += 1
                print(f"                     🔄 중복 매물 감지 (건너뜀): {atcl_no} (총 중복: {self.duplicate_count}개)", flush=True)
                return None
            
            # 매물 링크 생성
            naver_link = f'https://m.land.naver.com/article/info/{atcl_no}' if atcl_no else ''
            
            # 🎯 중복 감지 Set에 추가
            if atcl_no:
                self.collected_article_ids.add(atcl_no)
            
            # 📍 좌표 정보 추출
            lat = float(prop.get('lat', 0)) if isinstance(prop, dict) and prop.get('lat') else 0
            lng = float(prop.get('lng', 0)) if isinstance(prop, dict) and prop.get('lng') else 0
            
            # 면적 정보 (㎡ → 평 변환)
            spc1 = float(prop.get('spc1', 0)) if isinstance(prop, dict) and prop.get('spc1', '').replace('.', '').isdigit() else 0
            spc2 = float(prop.get('spc2', 0)) if isinstance(prop, dict) and prop.get('spc2', '').replace('.', '').isdigit() else 0
            area_sqm = spc2 if spc2 > 0 else spc1
            area_pyeong = area_sqm / 3.305785 if area_sqm > 0 else 0
            
            # 층수 정보 파싱
            flr_info = prop.get('flrInfo', '') if isinstance(prop, dict) else ''
            floor = 0
            if '/' in flr_info:
                try:
                    floor_str = flr_info.split('/')[0].strip()
                    if 'B' in floor_str:
                        floor = -int(floor_str.replace('B', ''))
                    else:
                        floor = int(floor_str)
                except:
                    floor = 0
            
            # 가격 정보
            deposit = int(prop.get('prc', 0)) if isinstance(prop, dict) else 0
            monthly_rent = int(prop.get('rentPrc', 0)) if isinstance(prop, dict) else 0
            
            # 건물 정보
            bild_nm = prop.get('bildNm', '') if isinstance(prop, dict) else ''
            atcl_nm = prop.get('atclNm', '') if isinstance(prop, dict) else ''
            
            # 주소 정보
            road_addr = prop.get('roadAddr', '') if isinstance(prop, dict) else ''
            jibun_addr = prop.get('jibunAddr', '') if isinstance(prop, dict) else ''
            full_address = road_addr if road_addr else jibun_addr
            
            # 🛡️ 좌표 기반 서울 검증 (주소 정보가 비어있는 경우 대비)
            if lat and lng:
                # 서울 경계 확인
                seoul_boundary = {
                    'north': 37.701, 'south': 37.413,
                    'west': 126.764, 'east': 127.269
                }
                in_seoul_bounds = (
                    seoul_boundary['south'] <= lat <= seoul_boundary['north'] and
                    seoul_boundary['west'] <= lng <= seoul_boundary['east']
                )
                if not in_seoul_bounds:
                    print(f"                     ❌ 서울 경계 밖: {lat:.6f}, {lng:.6f}")
                    return None
                else:
                    print(f"                     ✅ 서울 경계 내: {lat:.6f}, {lng:.6f}")
            else:
                print(f"                     ⚠️ 좌표 정보 없음: lat={lat}, lng={lng}")
                # 좌표가 없으면 일단 통과 (보수적 접근)
            
            # 매물 타입
            rlet_tp_nm = prop.get('rletTpNm', '상가') if isinstance(prop, dict) else '상가'
            
            return {
                'district': district_name,
                'property_type': rlet_tp_nm,
                'deposit': deposit,
                'monthly_rent': monthly_rent,
                'area_sqm': area_sqm,
                'area_pyeong': area_pyeong,
                'floor': floor,
                'floor_info': flr_info,
                'building_name': bild_nm,
                'property_name': atcl_nm,
                'full_address': full_address,
                'road_address': road_addr,
                'jibun_address': jibun_addr,
                'naver_link': naver_link,
                'article_no': atcl_no,
                'raw_data': prop if isinstance(prop, dict) else str(prop)
            }
            
        except Exception as e:
            print(f"            ⚠️ 매물 처리 오류: {e}")
            return None
    
    def create_api_params_from_coords(self, district_name: str, lat: float, lon: float) -> Dict[str, Any]:
        """🗺️ 좌표로부터 API 파라미터 생성"""
        # 검색 영역 계산 (약 2km 반경)
        margin = 0.018  # 약 2km
        
        return {
            'lat': lat,
            'lon': lon,
            'btm': lat - margin,
            'lft': lon - margin,
            'top': lat + margin,
            'rgt': lon + margin,
            'district_name': district_name
        }
    
    def get_collection_stats(self, properties: List[Dict[str, Any]]) -> Dict[str, Any]:
        """📊 수집 통계 반환"""
        if not properties:
            return {}
        
        # 기본 통계
        total_count = len(properties)
        
        # 매물 타입별 분포
        property_types = {}
        for prop in properties:
            prop_type = prop.get('property_type', '기타')
            property_types[prop_type] = property_types.get(prop_type, 0) + 1
        
        # 가격 범위
        deposits = [p.get('deposit', 0) for p in properties if p.get('deposit', 0) > 0]
        rents = [p.get('monthly_rent', 0) for p in properties if p.get('monthly_rent', 0) > 0]
        areas = [p.get('area_pyeong', 0) for p in properties if p.get('area_pyeong', 0) > 0]
        
        return {
            'total_count': total_count,
            'property_types': property_types,
            'deposit_range': f"{min(deposits)}~{max(deposits)}만원" if deposits else "N/A",
            'rent_range': f"{min(rents)}~{max(rents)}만원" if rents else "N/A",
            'area_range': f"{min(areas)}~{max(areas)}평" if areas else "N/A",
            'has_links': sum(1 for p in properties if p.get('naver_link'))
        }
