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
        self.api_base_url = 'https://m.land.naver.com/cluster/ajax/articleList'
        self.progress_manager = get_progress_manager()
        self.streamlit_filters = streamlit_filters or {}
        
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
            'lat': '37.5665',      # 기본 위도
            'lon': '126.9780',     # 기본 경도
            'btm': '37.4665',      # 남쪽 경계
            'lft': '126.8780',     # 서쪽 경계  
            'top': '37.6665',      # 북쪽 경계
            'rgt': '127.0780',     # 동쪽 경계
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
        
        # API 파라미터 구성 (완화된 조건으로 유지)
        request_params = self.base_api_params.copy()
        
        # 구별 좌표 정보 (기존 시스템과 동일)
        district_coords = {
            '강남구': {'lat': 37.517, 'lon': 127.047, 'btm': 37.4086766, 'lft': 126.9800521, 'top': 37.6251664, 'rgt': 127.1139479},
            '강서구': {'lat': 37.551, 'lon': 126.849, 'btm': 37.4516766, 'lft': 126.7820521, 'top': 37.6501664, 'rgt': 126.9159479},
            '영등포구': {'lat': 37.526, 'lon': 126.896, 'btm': 37.4266766, 'lft': 126.8290521, 'top': 37.6251664, 'rgt': 126.9629479},
            '구로구': {'lat': 37.495, 'lon': 126.887, 'btm': 37.3956766, 'lft': 126.8200521, 'top': 37.5941664, 'rgt': 126.9539479},
            '마포구': {'lat': 37.566, 'lon': 126.901, 'btm': 37.4666766, 'lft': 126.8340521, 'top': 37.6651664, 'rgt': 126.9679479}
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
    
    async def stealth_mass_collect(self, api_params: Dict[str, Any], district_name: str, max_pages: int = 20) -> List[Dict[str, Any]]:
        """🥷 스텔스 모드로 대량 수집"""
        print(f"            🥷 스텔스 API 수집 시작 (최대 {max_pages}페이지)")
        
        all_properties = []
        current_page = 1
        consecutive_failures = 0
        max_failures = 3
        
        # 페르소나 설정
        self.stealth_manager.set_persona(self.stealth_manager.get_random_persona())
        
        while current_page <= max_pages and consecutive_failures < max_failures:
            try:
                print(f"               📄 {current_page}페이지 (스텔스 모드)...", flush=True)
                
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
                response = session.get(self.api_base_url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 총 매물 수 확인 (첫 페이지에서)
                    if current_page == 1:
                        total_count = data.get('data', {}).get('totCnt', 0)
                        if total_count:
                            self._total_count = total_count
                            print(f"                  📊 총 {total_count}개 매물 확인됨", flush=True)
                            # 진행률 관리자에 총 개수 업데이트
                            self.progress_manager.update_page_progress(current_page, 0, total_count)
                        else:
                            self._total_count = None
                    
                    # 기존 시스템과 동일한 응답 처리
                    if 'body' in data and isinstance(data['body'], list):
                        articles = data['body']
                    else:
                        articles = data.get('data', {}).get('ARTICLE', [])
                    
                    if articles:
                        print(f"                  ✅ {len(articles)}개 원시 데이터", flush=True)
                        
                        # 매물 처리
                        processed_count = 0
                        for article in articles:
                            processed_property = self.process_api_property(article, district_name)
                            if processed_property:
                                all_properties.append(processed_property)
                                processed_count += 1
                        
                        print(f"                  ✅ {processed_count}개 처리 완료 (누적: {len(all_properties)}개)", flush=True)
                        consecutive_failures = 0
                        
                        # 진행률 업데이트
                        self.progress_manager.update_page_progress(current_page, processed_count)
                        
                        # 총 매물 수 도달 확인
                        if hasattr(self, '_total_count') and len(all_properties) >= self._total_count:
                            print(f"                  🎯 전체 매물 수집 완료: {len(all_properties)}/{self._total_count}개", flush=True)
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
                    consecutive_failures += 1
                    
                    # 연속 5페이지 HTTP 오류시 수집 종료
                    if consecutive_failures >= 5:
                        print(f"                  🛑 연속 {consecutive_failures}페이지 오류 → 수집 종료", flush=True)
                        break
                
                current_page += 1
                
            except Exception as e:
                print(f"                  ❌ {current_page}페이지 수집 오류: {e}", flush=True)
                consecutive_failures += 1
                current_page += 1
                
                # 오류 시 더 긴 대기
                error_wait = self.stealth_manager.get_human_wait_time(long_wait=True)
                await asyncio.sleep(error_wait)
        
        print(f"            ✅ {district_name} 신중한 수집 완료: {len(all_properties)}개", flush=True)
        print(f"            🎉 스텔스 수집 성공! ({len(all_properties)}개)", flush=True)
        
        return all_properties
    
    def process_api_property(self, prop, district_name: str) -> Optional[Dict[str, Any]]:
        """🏠 API 매물 데이터 처리 (기존 시스템과 동일)"""
        try:
            # 매물 링크 생성
            atcl_no = prop.get('atclNo', '') if isinstance(prop, dict) else ''
            naver_link = f'https://m.land.naver.com/article/info/{atcl_no}' if atcl_no else ''
            
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
            
            # 매물 타입
            rlet_tp_nm = prop.get('rletTpNm', '상가') if isinstance(prop, dict) else '상가'
            
            # 층수 정보 추출 (NoneType 오류 방지)
            floor_number = None
            if isinstance(flr_info, str) and flr_info.strip():
                try:
                    # "3/10층" 형태에서 현재 층수 추출
                    if '/' in flr_info:
                        current_floor_str = flr_info.split('/')[0].strip()
                        if current_floor_str.startswith('B') and len(current_floor_str) > 1:
                            # 지하층 처리 (B1 = -1)
                            basement_num = current_floor_str[1:]
                            if basement_num.isdigit():
                                floor_number = -int(basement_num)
                        elif current_floor_str.isdigit():
                            floor_number = int(current_floor_str)
                    elif flr_info.replace('층', '').strip().isdigit():
                        floor_number = int(flr_info.replace('층', '').strip())
                except (ValueError, IndexError, AttributeError) as e:
                    print(f"            ⚠️ 층수 파싱 실패: '{flr_info}' -> {e}")
                    floor_number = None
            
            return {
                'district': district_name,
                'property_type': rlet_tp_nm,
                'deposit': deposit,
                'monthly_rent': monthly_rent,
                'area_sqm': area_sqm,
                'area_pyeong': area_pyeong,
                'floor': floor,
                'floor_info': flr_info,
                'floor_number': floor_number,  # 추가!
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
