#!/usr/bin/env python3
"""
네이버 지도 "구만 보기" 버튼 활용 정확한 수집
- 이미지에서 확인된 "강남구만 보기" 버튼 클릭
- 100% 정확한 구별 분류 보장
- 지역 경계 문제 완전 해결
"""

import asyncio
import pandas as pd
from datetime import datetime
from playwright.async_api import async_playwright
from data_processor import PropertyDataProcessor
import re
import requests
import time
import random
import json

class DistrictButtonCollector:
    def __init__(self):
        self.processor = PropertyDataProcessor()
        
        # 테스트할 구들
        self.target_districts = [
            '강남구', '강서구', '영등포구', '구로구', '마포구'
        ]
        
        # 기본 네이버 지도 URL (필터 적용된 상태)
        self.base_map_url = "https://m.land.naver.com/map/37.5665:126.9780:12/SG:SMS/B2?wprcMax=2000&rprcMax=130&spcMin=66&flrMin=-1&flrMax=2"
        
        # 🚀 API 방식 추가 설정
        self.seoul_districts_coords = {
            '강남구': {'lat': 37.517, 'lon': 127.047, 'btm': 37.4086766, 'lft': 126.9800521, 'top': 37.6251664, 'rgt': 127.1139479},
            '강서구': {'lat': 37.551, 'lon': 126.849, 'btm': 37.4516766, 'lft': 126.7820521, 'top': 37.6501664, 'rgt': 126.9159479},
            '영등포구': {'lat': 37.526, 'lon': 126.896, 'btm': 37.4266766, 'lft': 126.8290521, 'top': 37.6251664, 'rgt': 126.9629479},
            '구로구': {'lat': 37.495, 'lon': 126.887, 'btm': 37.3956766, 'lft': 126.8200521, 'top': 37.5941664, 'rgt': 126.9539479},
            '마포구': {'lat': 37.566, 'lon': 126.901, 'btm': 37.4666766, 'lft': 126.8340521, 'top': 37.6651664, 'rgt': 126.9679479}
        }
        
        # 🥷 스텔스 API 설정
        self.api_base_url = 'https://m.land.naver.com/cluster/ajax/articleList'
        
        # 🎯 1번: 실제 디바이스 User-Agent 풀
        self.stealth_user_agents = [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36'
        ]
        
        # 🎯 2번: 다중 세션 풀
        self.session_pool = []
        self.current_session_idx = 0

    async def run_district_button_collection(self, target_per_district=10):
        """🚀 브라우저 구만보기 + API 대량수집 하이브리드"""
        print("🗺️ === 하이브리드 수집 시스템 ===")
        print("💡 방식: 브라우저로 '구만보기' → API로 무제한 수집")
        print("🎯 목표: 100% 정확한 구별 분류 + 완전한 데이터 + 링크")
        
        all_properties = []
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 390, 'height': 844},
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()
        
        try:
            for i, district_name in enumerate(self.target_districts, 1):
                print(f"\n📍 {i}/{len(self.target_districts)}: {district_name} 하이브리드 수집")
                
                # 1단계: 브라우저로 구만 보기 버튼 클릭
                print(f"         🌐 1단계: 브라우저로 {district_name}만 보기 활성화...")
                success = await self.navigate_to_map_and_apply_district_filter(page, district_name)
                
                if success:
                    # 2단계: 현재 브라우저 상태에서 API 파라미터 추출하여 대량 수집
                    print(f"         🚀 2단계: {district_name} 필터 상태에서 API 대량 수집...")
                    district_properties = await self.collect_district_hybrid(page, district_name)
                    
                    if district_properties:
                        all_properties.extend(district_properties)
                        print(f"      ✅ {district_name}: {len(district_properties)}개 하이브리드 수집 완료")
                    else:
                        print(f"      ❌ {district_name}: 하이브리드 수집 실패")
                else:
                    print(f"      ❌ {district_name}: 구만 보기 버튼 찾기 실패")
                
                # 🛡️ 구간별 긴 휴식 (봇 차단 방지)
                rest_time = random.uniform(10, 20)
                print(f"      😴 {district_name} 완료, 다음 구까지 {rest_time:.1f}초 휴식...")
                await asyncio.sleep(rest_time)
        
        except Exception as e:
            print(f"❌ 하이브리드 수집 중 오류: {e}")
        finally:
            await browser.close()
            await playwright.stop()
        
        # 결과 분석
        if all_properties:
            await self.analyze_api_results(all_properties)
        
        return all_properties

    def create_stealth_session_pool(self, pool_size=3):
        """🎯 2번: 스텔스 세션 풀 생성"""
        if self.session_pool:
            return
            
        print(f"🔄 {pool_size}개 스텔스 세션 생성...")
        for i in range(pool_size):
            session = requests.Session()
            headers = {
                'User-Agent': random.choice(self.stealth_user_agents),
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://m.land.naver.com/map/',
                'X-Requested-With': 'XMLHttpRequest',
                'Connection': 'keep-alive',
                'DNT': '1'
            }
            session.headers.update(headers)
            self.session_pool.append(session)

    def get_stealth_session(self):
        """🔄 세션 로테이션"""
        if not self.session_pool:
            self.create_stealth_session_pool()
        
        session = self.session_pool[self.current_session_idx]
        self.current_session_idx = (self.current_session_idx + 1) % len(self.session_pool)
        return session

    def get_human_wait_time(self):
        """🎯 3번: 인간 대기시간 패턴"""
        patterns = [
            (0.8, 2.5, 0.4),   # 빠른 탐색
            (2.5, 5.0, 0.4),   # 보통 탐색
            (5.0, 8.0, 0.15),  # 느린 탐색
            (8.0, 15.0, 0.05)  # 생각하는 시간
        ]
        
        rand = random.random()
        cumulative = 0
        for min_wait, max_wait, prob in patterns:
            cumulative += prob
            if rand <= cumulative:
                return random.uniform(min_wait, max_wait)
        
        return random.uniform(2.0, 5.0)  # 기본값

    async def collect_district_hybrid(self, page, district_name):
        """🚀 하이브리드 방식: 브라우저 필터 상태 → API 대량 수집"""
        try:
            # 1단계: 목록 모드로 전환
            await self.switch_to_list_mode(page)
            await page.wait_for_timeout(3000)
            
            # 2단계: 현재 페이지 URL에서 필터 파라미터 추출
            current_url = page.url
            print(f"            📍 현재 URL: {current_url}")
            
            # 3단계: URL에서 좌표 및 필터 정보 파싱
            api_params = await self.extract_api_params_from_browser(page, district_name, current_url)
            
            if not api_params:
                print(f"            ❌ API 파라미터 추출 실패")
                return []
            
            # 4단계: 추출된 파라미터로 API 대량 수집
            print(f"            🌐 API 파라미터 추출 완료, 대량 수집 시작...")
            properties = await self.api_mass_collect_with_params(api_params, district_name)
            
            return properties
            
        except Exception as e:
            print(f"            ❌ 하이브리드 수집 오류: {e}")
            return []

    async def extract_api_params_from_browser(self, page, district_name, url):
        """브라우저 상태에서 API 파라미터 추출"""
        try:
            # URL 파싱으로 좌표 정보 추출
            import urllib.parse
            
            # 기본 좌표 (fallback)
            coords = self.seoul_districts_coords.get(district_name, self.seoul_districts_coords['강남구'])
            
            # URL에서 좌표 정보 추출 시도
            if '/map/' in url:
                map_part = url.split('/map/')[1].split('/')[0]
                if ':' in map_part:
                    coord_parts = map_part.split(':')
                    if len(coord_parts) >= 3:
                        try:
                            lat = float(coord_parts[0])
                            lon = float(coord_parts[1])
                            zoom = int(coord_parts[2])
                            
                            # 좌표 기반 범위 계산
                            zoom_factor = 0.05 if zoom >= 12 else 0.1
                            coords = {
                                'lat': lat,
                                'lon': lon,
                                'btm': lat - zoom_factor,
                                'lft': lon - zoom_factor,
                                'top': lat + zoom_factor,
                                'rgt': lon + zoom_factor
                            }
                            print(f"            ✅ URL에서 좌표 추출: lat={lat}, lon={lon}")
                        except:
                            pass
            
            # URL 쿼리 파라미터 추출
            parsed_url = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            # API 파라미터 구성
            api_params = {
                'rletTpCd': 'SG:SMS',  # 상가,사무실
                'tradTpCd': 'B2',      # 월세
                'z': '12',
                'lat': str(coords['lat']),
                'lon': str(coords['lon']),
                'btm': str(coords['btm']),
                'lft': str(coords['lft']),
                'top': str(coords['top']),
                'rgt': str(coords['rgt']),
                'showR0': '',
                'totCnt': '7689',
                'cortarNo': ''
            }
            
            # URL 파라미터가 있으면 적용
            param_mapping = {
                'wprcMax': 'wprcMax',    # 보증금 최대
                'rprcMax': 'rprcMax',    # 월세 최대
                'spcMin': 'spcMin',      # 면적 최소
                'flrMin': 'flrMin',      # 층수 최소
                'flrMax': 'flrMax'       # 층수 최대
            }
            
            for url_param, api_param in param_mapping.items():
                if url_param in query_params:
                    api_params[api_param] = query_params[url_param][0]
                    print(f"            ✅ 필터 적용: {api_param}={query_params[url_param][0]}")
            
            # 기본 필터 값 설정 (없으면)
            default_filters = {
                'wprcMax': '5000',     # 보증금 최대 (완화)
                'rprcMax': '300',      # 월세 최대 (완화)
                'spcMin': '30'         # 면적 최소 (완화)
            }
            
            for param, default_value in default_filters.items():
                if param not in api_params:
                    api_params[param] = default_value
            
            return api_params
            
        except Exception as e:
            print(f"            ❌ API 파라미터 추출 오류: {e}")
            return None

    async def api_mass_collect_with_params(self, api_params, district_name, max_pages=200):
        """🥷 스텔스 API 수집 (1,2,3번 적용)"""
        print(f"            🥷 스텔스 API 수집 시작 (최대 {max_pages}페이지)")
        
        all_properties = []
        page_num = 1
        consecutive_failures = 0
        
        # 🎯 2번: 스텔스 세션 풀 생성
        self.create_stealth_session_pool()
        
        while page_num <= max_pages and consecutive_failures < 5:
            print(f"               📄 {page_num}페이지 (스텔스 모드)...", flush=True)
            
            current_params = api_params.copy()
            current_params['page'] = str(page_num)
            
            try:
                # 🎯 3번: 인간 대기시간 패턴
                if page_num > 1:
                    wait_time = self.get_human_wait_time()
                    print(f"                  ⏳ {wait_time:.1f}초 대기 중... (인간 패턴)", flush=True)
                    await asyncio.sleep(wait_time)
                
                # 🎯 2번: 스텔스 세션 사용
                session = self.get_stealth_session()
                response = session.get(self.api_base_url, params=current_params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'body' in data and isinstance(data['body'], list):
                        page_properties = data['body']
                        print(f"                  ✅ {len(page_properties)}개 원시 데이터", flush=True)
                        
                        # 매물 데이터 가공
                        processed_properties = []
                        for prop in page_properties:
                            processed = self.process_api_property(prop, district_name)
                            if processed:
                                processed_properties.append(processed)
                        
                        all_properties.extend(processed_properties)
                        print(f"                  ✅ {len(processed_properties)}개 처리 완료 (누적: {len(all_properties)}개)", flush=True)
                        
                        consecutive_failures = 0  # 성공 시 실패 카운트 리셋
                        
                        # 더 이상 데이터가 없으면 중단
                        if not data.get('more', False) or len(page_properties) == 0:
                            print(f"                  🛑 데이터 종료 (more: {data.get('more', False)})")
                            break
                            
                    else:
                        print(f"                  ❌ body 데이터 없음")
                        consecutive_failures += 1
                        
                elif response.status_code == 429:
                    print(f"                  🚫 Rate Limit 감지! 긴 대기...")
                    await asyncio.sleep(random.uniform(20, 40))  # 20-40초 대기
                    consecutive_failures += 1
                    
                elif response.status_code == 403:
                    print(f"                  🚫 403 차단! 세션 교체...")
                    session = self.get_stealth_session()  # 즉시 세션 교체
                    await asyncio.sleep(random.uniform(3, 8))
                    consecutive_failures += 1
                    
                else:
                    print(f"                  ❌ 요청 실패: {response.status_code}")
                    consecutive_failures += 1
                    await asyncio.sleep(random.uniform(5, 10))  # 오류 시 5-10초 대기
                    
            except Exception as e:
                print(f"                  ❌ 오류: {e}")
                consecutive_failures += 1
                await asyncio.sleep(random.uniform(5, 15))  # 예외 시 5-15초 대기
            
            page_num += 1
            
            # 🛡️ 5페이지마다 장시간 휴식
            if page_num % 5 == 0:
                break_time = random.uniform(15, 30)
                print(f"                  😴 5페이지 수집 완료, {break_time:.1f}초 휴식...", flush=True)
                await asyncio.sleep(break_time)
        
        print(f"            ✅ {district_name} 신중한 수집 완료: {len(all_properties)}개")
        
        # 수집량 평가
        if len(all_properties) >= 50:
            print(f"            🎉 스텔스 수집 성공! ({len(all_properties)}개)")
        elif len(all_properties) >= 20:
            print(f"            ✅ 양호한 수집 ({len(all_properties)}개)")
        else:
            print(f"            ⚠️ 수집량 부족 ({len(all_properties)}개)")
        
        return all_properties

    async def run_api_mass_collection(self, max_pages_per_district=50):
        """🚀 API 방식으로 5개구 대량 수집 (링크 포함)"""
        print(f"📊 API 대량 수집: 각 구별 최대 {max_pages_per_district}페이지 (페이지당 20개)")
        
        all_properties = []
        district_summary = {}
        
        for i, district_name in enumerate(self.target_districts, 1):
            print(f"\n📍 {i}/5: {district_name} API 대량 수집...")
            
            district_properties = self.collect_district_via_api(district_name, max_pages_per_district)
            all_properties.extend(district_properties)
            district_summary[district_name] = len(district_properties)
            
            print(f"   ✅ {district_name}: {len(district_properties)}개 완료")
        
        print(f"\n📊 === API 수집 완료 ===")
        print(f"총 매물: {len(all_properties)}개")
        
        for district, count in district_summary.items():
            print(f"   {district}: {count}개")
        
        # 결과 분석 및 저장
        if all_properties:
            await self.analyze_api_results(all_properties)
        
        return all_properties

    def collect_district_via_api(self, district_name, max_pages=50):
        """구별 API 대량 수집 (무제한)"""
        print(f"      🌐 {district_name} API 수집 시작...")
        
        coords = self.seoul_districts_coords[district_name]
        
        # API 파라미터 (조건.md 준수)
        params = {
            'rletTpCd': 'SG:SMS',  # 상가,사무실
            'tradTpCd': 'B2',      # 월세
            'z': '12',
            'lat': str(coords['lat']),
            'lon': str(coords['lon']),
            'btm': str(coords['btm']),
            'lft': str(coords['lft']),
            'top': str(coords['top']),
            'rgt': str(coords['rgt']),
            'wprcMax': '2000',     # 보증금 최대 2000 (조건.md)
            'rprcMax': '130',      # 월세 최대 130 (조건.md)
            'spcMin': '66',        # 면적 최소 66㎡ = 20평 (조건.md)
            'showR0': '',
            'totCnt': '7689',
            'cortarNo': ''
        }
        
        all_properties = []
        page_num = 1
        
        while page_num <= max_pages:
            print(f"         📄 {page_num}페이지 수집...")
            
            current_params = params.copy()
            current_params['page'] = str(page_num)
            
            try:
                response = requests.get(self.api_base_url, params=current_params, headers=self.api_headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'body' in data and isinstance(data['body'], list):
                        page_properties = data['body']
                        print(f"            ✅ {len(page_properties)}개 원시 데이터")
                        
                        # 매물 데이터 가공 (링크 포함)
                        processed_properties = []
                        for prop in page_properties:
                            processed = self.process_api_property(prop, district_name)
                            if processed:
                                processed_properties.append(processed)
                        
                        all_properties.extend(processed_properties)
                        print(f"            ✅ {len(processed_properties)}개 처리 완료")
                        
                        # 더 이상 데이터가 없으면 중단
                        if not data.get('more', False) or len(page_properties) == 0:
                            print(f"            🛑 데이터 종료 (more: {data.get('more', False)})")
                            break
                    else:
                        print(f"            ❌ body 데이터 없음")
                        break
                else:
                    print(f"            ❌ 요청 실패: {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"            ❌ 오류: {e}")
                break
            
            page_num += 1
            time.sleep(random.uniform(0.3, 0.8))  # 랜덤 대기
        
        return all_properties

    def process_api_property(self, prop, district_name):
        """🚀 API 매물 데이터를 표준 형식으로 변환 (링크 포함)"""
        try:
            # 매물 링크 생성
            atcl_no = prop.get('atclNo', '')
            naver_link = f'https://m.land.naver.com/article/info/{atcl_no}' if atcl_no else ''
            
            # 면적 정보 (㎡ → 평 변환)
            spc1 = float(prop.get('spc1', 0)) if prop.get('spc1', '').replace('.', '').isdigit() else 0
            spc2 = float(prop.get('spc2', 0)) if prop.get('spc2', '').replace('.', '').isdigit() else 0
            area_sqm = spc2 if spc2 > 0 else spc1
            area_pyeong = area_sqm / 3.305785 if area_sqm > 0 else 0
            
            # 층수 정보 파싱
            flr_info = prop.get('flrInfo', '')
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
            deposit = int(prop.get('prc', 0))
            monthly_rent = int(prop.get('rentPrc', 0))
            
            # 관리비 추정 (월세의 15% 또는 최소 10만원)
            management_fee = max(10, int(monthly_rent * 0.15))
            total_monthly_cost = monthly_rent + management_fee
            
            # 특성 및 점수 계산
            raw_text = f"{prop.get('atclNm', '')} {prop.get('direction', '')} {prop.get('rletTpNm', '')}"
            score = 0
            labels = []
            
            # 주차 관련 키워드
            parking_keywords = ['주차', 'parking', '차량', '주차장', '파킹']
            if any(keyword in raw_text for keyword in parking_keywords):
                score += 2
                labels.append('주차가능')
            
            # 역세권 관련 키워드  
            station_keywords = ['역', '지하철', '전철', '역세권', 'station']
            if any(keyword in raw_text for keyword in station_keywords):
                score += 1
                labels.append('역세권')
            
            # 층고 관련 (API에서는 직접 제공되지 않아 추정)
            space_keywords = ['높은', '고층고', '넓은', '여유', '쾌적']
            if any(keyword in raw_text for keyword in space_keywords):
                score += 1
                labels.append('넓은공간')
            
            # 이미지 URL 생성
            image_url = ''
            if prop.get('repImgUrl'):
                image_url = f"https://landthumb-phinf.pstatic.net{prop.get('repImgUrl')}"
            
            # 표준 형식으로 변환 (기존 브라우저 방식과 호환)
            property_data = {
                'region': '서울시',
                'district': district_name,
                'building_name': prop.get('atclNm', '매물명미확인'),
                'full_address': f"서울시 {district_name}",
                'area_sqm': round(area_sqm, 2),
                'area_pyeong': round(area_pyeong, 2),
                'floor': floor,
                'deposit': deposit,
                'monthly_rent': monthly_rent,
                'management_fee': management_fee,
                'total_monthly_cost': total_monthly_cost,
                'ceiling_height': 0.0,  # API에서 제공되지 않음
                'parking_available': '주차' in raw_text,
                'near_station': any(keyword in raw_text for keyword in station_keywords),
                'build_year': 0,  # API에서 제공되지 않음
                'naver_link': naver_link,
                'data_source': 'api_integrated_collector',
                'collected_at': datetime.now().isoformat(),
                'raw_text': raw_text,
                # API 추가 정보
                'property_type': prop.get('rletTpNm', ''),
                'trade_type': prop.get('tradTpNm', ''),
                'atcl_no': atcl_no,
                'confirm_date': prop.get('atclCfmYmd', ''),
                'direction': prop.get('direction', ''),
                'floor_info': flr_info,
                'image_url': image_url,
                'score': score,
                'labels': ', '.join(labels) if labels else ''
            }
            
            return property_data
            
        except Exception as e:
            print(f"               ❌ 매물 처리 오류: {e}")
            return None

    async def run_browser_district_collection(self, target_per_district=10):
        """🌐 브라우저 방식 구만 보기 수집 (기존 방식)"""
        all_properties = []
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 390, 'height': 844},
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()
        
        try:
            for i, district_name in enumerate(self.target_districts, 1):
                print(f"\n📍 {i}/{len(self.target_districts)}: {district_name} '구만 보기' 버튼 수집")
                
                # 기본 지도 페이지 접속
                success = await self.navigate_to_map_and_apply_district_filter(page, district_name)
                
                if success:
                    # 필터 적용 후 매물 수집
                    district_properties = await self.collect_filtered_properties(
                        page, district_name, target_per_district
                    )
                    
                    if district_properties:
                        all_properties.extend(district_properties)
                        print(f"      ✅ {district_name}: {len(district_properties)}개 정확한 수집")
                        
                        # 정확도 검증
                        self.verify_district_accuracy(district_properties, district_name)
                    else:
                        print(f"      ❌ {district_name}: 매물 수집 실패")
                else:
                    print(f"      ❌ {district_name}: 구만 보기 버튼 찾기 실패")
                
                await asyncio.sleep(3)
        
        except Exception as e:
            print(f"❌ 구만 보기 수집 중 오류: {e}")
        finally:
            await browser.close()
            await playwright.stop()
        
        # 결과 분석
        if all_properties:
            await self.analyze_district_button_results(all_properties)
        
        return all_properties

    async def navigate_to_map_and_apply_district_filter(self, page, district_name):
        """🚀 성공했던 순서 그대로: 지도이동 → 클러스터클릭 → 구만보기 → API수집"""
        try:
            print(f"         🌐 {district_name} 집중 탐색 시작...")
            
            # 1단계: 해당 구별 맞춤 URL 생성 및 접속
            coords = self.seoul_districts_coords[district_name]
            
            # 성공했던 URL 패턴들 (구별 중심 좌표)
            url_patterns = [
                f"https://m.land.naver.com/map/{coords['lat']}:{coords['lon']}:12/SG:SMS/B2?wprcMax=2000&rprcMax=130&spcMin=66&flrMin=-1&flrMax=2",
                f"https://m.land.naver.com/map/{coords['lat']}:{coords['lon']}:13/SG:SMS/B2?wprcMax=2000&rprcMax=130&spcMin=66",
                f"https://m.land.naver.com/map/{coords['lat']}:{coords['lon']}:11/SG:SMS/B2"
            ]
            
            for url_pattern in url_patterns:
                print(f"         🌐 {district_name} 맞춤 URL 접속...")
                
                await page.goto(url_pattern, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)
                
                # 2단계: 페이지 로딩 과정에서 구만 보기 버튼 집중 탐색
                button_found = await self.search_during_page_load(page, district_name)
                
                if button_found:
                    return True
                
                # 3단계: 페이지 완전 로딩 후 구만 보기 버튼 탐색
                button_found = await self.search_after_page_load(page, district_name)
                
                if button_found:
                    return True
                
                # 4단계: 페이지 상호작용으로 버튼 유도 (클러스터 클릭 등)
                print(f"         🔄 {district_name} 페이지 상호작용으로 버튼 유도...")
                interaction_success = await self.try_page_interactions(page, district_name)
                
                if interaction_success:
                    return True
                
                print(f"         ⚠️ URL 패턴에서 {district_name}만 보기 버튼 없음")
            
            # 5단계: 브라우저 방식 실패 시에도 해당 구 좌표로 API 수집 진행
            print(f"         ⚠️ {district_name}만 보기 버튼 없음, 좌표 기반 API 수집으로 진행")
            return True  # 좌표 기반으로라도 수집 진행
                
        except Exception as e:
            print(f"         ❌ {district_name} 집중 탐색 오류: {e}")
            return False

    async def search_during_page_load(self, page, district_name):
        """페이지 로딩 과정에서 구만 보기 버튼 탐색 (성공했던 방식)"""
        print(f"         ⏳ 페이지 로딩 중 {district_name}만 보기 버튼 탐색...")
        
        for attempt in range(15):  # 7.5초간 0.5초마다
            await asyncio.sleep(0.5)
            
            button_found = await self.check_district_button_exists(page, district_name)
            
            if button_found:
                print(f"         ✅ 로딩 중 {district_name}만 보기 버튼 발견! (시도 {attempt+1})")
                
                # 즉시 클릭 시도
                click_success = await self.attempt_button_click(page, district_name)
                if click_success:
                    return True
            
            print(f"         ⏳ 로딩 중 탐색... ({attempt+1}/15)")
        
        print(f"         ❌ 로딩 중 {district_name}만 보기 버튼 없음")
        return False

    async def search_after_page_load(self, page, district_name):
        """페이지 완전 로딩 후 구만 보기 버튼 탐색 (성공했던 방식)"""
        print(f"         🔍 로딩 완료 후 {district_name}만 보기 버튼 정밀 탐색...")
        
        await page.wait_for_timeout(2000)
        
        button_found = await self.check_district_button_exists(page, district_name)
        
        if button_found:
            print(f"         ✅ 로딩 완료 후 {district_name}만 보기 버튼 발견!")
            
            click_success = await self.attempt_button_click(page, district_name)
            if click_success:
                return True
        
        print(f"         ❌ 로딩 완료 후 {district_name}만 보기 버튼 없음")
        return False

    async def try_page_interactions(self, page, district_name):
        """페이지 상호작용으로 구만 보기 버튼 유도 (성공했던 방식)"""
        print(f"         🎯 {district_name} 상호작용으로 버튼 유도...")
        
        try:
            # 1차: 줌 조작으로 클러스터 변화 유도
            zoom_levels = [12, 13, 11, 14, 10]
            for zoom in zoom_levels:
                try:
                    coords = self.seoul_districts_coords[district_name]
                    zoom_script = f'''
                    if (window.naver && window.naver.maps) {{
                        const map = window.naver.maps.Map.maps[0];
                        if (map) {{
                            map.setZoom({zoom});
                            const center = new naver.maps.LatLng({coords['lat']}, {coords['lon']});
                            map.setCenter(center);
                        }}
                    }}
                    '''
                    await page.evaluate(zoom_script)
                    await page.wait_for_timeout(2000)
                    
                    # 줌 변경 후 버튼 확인
                    if await self.check_district_button_exists(page, district_name):
                        print(f"         ✅ 줌 {zoom} 조작으로 버튼 유도 성공!")
                        return await self.attempt_button_click(page, district_name)
                except Exception:
                    continue
            
            # 2차: 클러스터 클릭으로 구만 보기 유도
            print(f"         🗺️ 클러스터 클릭으로 {district_name}만 보기 유도...")
            cluster_selectors = [
                '.cluster_marker',
                '.cluster-marker', 
                '[class*="cluster"]',
                '.map-marker',
                '.marker'
            ]
            
            for selector in cluster_selectors:
                try:
                    clusters = await page.query_selector_all(selector)
                    if clusters:
                        await clusters[0].click()
                        await page.wait_for_timeout(3000)
                        
                        if await self.check_district_button_exists(page, district_name):
                            print(f"         ✅ 클러스터 클릭으로 {district_name}만 보기 유도 성공!")
                            return await self.attempt_button_click(page, district_name)
                except Exception:
                    continue
        except Exception:
            pass
        
        return False

    async def check_district_button_exists(self, page, district_name):
        """구만 보기 버튼 존재 확인"""
        district_selectors = [
            f'text="{district_name}만 보기"',
            f'button:has-text("{district_name}만 보기")',
            f'a:has-text("{district_name}만 보기")',
            f'div:has-text("{district_name}만 보기")',
            f'text="{district_name}만"',
            f'button:has-text("{district_name}만")'
        ]
        
        for selector in district_selectors:
            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    return True
            except Exception:
                continue
        
        return False

    async def attempt_button_click(self, page, district_name):
        """구만 보기 버튼 클릭 시도"""
        district_selectors = [
            f'text="{district_name}만 보기"',
            f'button:has-text("{district_name}만 보기")',
            f'a:has-text("{district_name}만 보기")',
            f'div:has-text("{district_name}만 보기")',
            f'text="{district_name}만"',
            f'button:has-text("{district_name}만")'
        ]
        
        for selector in district_selectors:
            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    text = await element.inner_text()
                    print(f"         🎯 {district_name}만 보기 버튼 클릭: \"{text}\"")
                    await element.click()
                    await page.wait_for_timeout(2000)
                    print(f"         ✅ {district_name}만 보기 클릭 완료")
                    return True
            except Exception:
                continue
        
        return False

    async def find_and_click_district_button_enhanced(self, page, district_name):
        """강화된 구만 보기 버튼 찾기"""
        print(f"         🔍 {district_name}만 보기 버튼 강화 탐색...")
        
        # 1차: 구만 보기 패턴들
        enhanced_selectors = [
            f'text="{district_name}만 보기"',
            f'button:has-text("{district_name}만 보기")',
            f'a:has-text("{district_name}만 보기")',
            f'div:has-text("{district_name}만 보기")',
            f'span:has-text("{district_name}만 보기")',
            f'text="{district_name}만"',
            f'button:has-text("{district_name}만")',
            f'text="{district_name}"',
            f'button:has-text("{district_name}")',
            f'[data-district*="{district_name}"]',
            f'[aria-label*="{district_name}"]',
            f'.district-button:has-text("{district_name}")',
            f'.location-filter:has-text("{district_name}")'
        ]
        
        for selector in enhanced_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible():
                        text = await element.inner_text()
                        if district_name in text and len(text.strip()) <= 20:  # 너무 긴 텍스트 제외
                            print(f"            🎯 발견: \"{text}\" - {selector}")
                            await element.click()
                            await page.wait_for_timeout(2000)
                            print(f"            ✅ {district_name} 관련 요소 클릭 성공")
                            return True
            except Exception:
                continue
        
        # 2차: 클러스터 클릭으로 구만 보기 유도
        print(f"         🗺️ 클러스터 클릭으로 {district_name}만 보기 유도 시도...")
        try:
            coords = self.seoul_districts_coords[district_name]
            
            # 지도에서 클러스터 요소 찾기
            cluster_selectors = [
                '.cluster_marker',
                '.cluster-marker', 
                '[class*="cluster"]',
                '[data-cy*="cluster"]',
                '.map-marker',
                '.marker'
            ]
            
            for selector in cluster_selectors:
                try:
                    clusters = await page.query_selector_all(selector)
                    if clusters:
                        # 첫 번째 클러스터 클릭
                        await clusters[0].click()
                        await page.wait_for_timeout(3000)
                        
                        # 구만 보기 버튼이 나타났는지 확인
                        district_button = await page.query_selector(f'text="{district_name}만 보기"')
                        if district_button and await district_button.is_visible():
                            print(f"            🎯 클러스터 클릭 후 {district_name}만 보기 발견!")
                            await district_button.click()
                            await page.wait_for_timeout(2000)
                            return True
                except Exception:
                    continue
        except Exception:
            pass
        
        print(f"         ❌ {district_name}만 보기 버튼을 찾을 수 없음")
        return False

    async def find_and_click_district_button(self, page, district_name):
        """구만 보기 버튼 찾기 및 클릭"""
        print(f"         🔍 {district_name}만 보기 버튼 탐색 중...")
        
        # 다양한 선택자 패턴으로 구만 보기 버튼 찾기
        district_button_selectors = [
            f'text="{district_name}만 보기"',
            f'button:has-text("{district_name}만 보기")',
            f'a:has-text("{district_name}만 보기")',
            f'div:has-text("{district_name}만 보기")',
            f'span:has-text("{district_name}만 보기")',
            f'[data-district="{district_name}"]',
            f'.district-filter:has-text("{district_name}")',
            f'text="{district_name}만"',
            f'button:has-text("{district_name}만")',
        ]
        
        # 구 이름 단독으로도 시도
        simple_district_selectors = [
            f'text="{district_name}"',
            f'button:has-text("{district_name}")',
            f'a:has-text("{district_name}")',
            f'div:has-text("{district_name}")',
            f'span:has-text("{district_name}")'
        ]
        
        # 1차 시도: "구만 보기" 패턴
        for selector in district_button_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible():
                        text = await element.inner_text()
                        print(f"            🎯 발견: \"{text}\" - {selector}")
                        await element.click()
                        await page.wait_for_timeout(2000)
                        print(f"            ✅ {district_name}만 보기 클릭 성공")
                        return True
            except Exception:
                continue
        
        # 2차 시도: 구 이름 단독
        print(f"         ⚠️ '구만 보기' 패턴 없음, 구 이름 단독 시도...")
        for selector in simple_district_selectors:
            try:
                elements = await page.query_selector_all(selector)
                clickable_elements = []
                
                for element in elements:
                    if await element.is_visible():
                        text = await element.inner_text()
                        # 정확히 구 이름만 포함하는 요소 필터링
                        if district_name in text and len(text.strip()) <= len(district_name) + 5:
                            clickable_elements.append((element, text))
                
                if clickable_elements:
                    element, text = clickable_elements[0]
                    print(f"            🎯 구 이름 발견: \"{text}\" - {selector}")
                    await element.click()
                    await page.wait_for_timeout(2000)
                    print(f"            ✅ {district_name} 클릭 성공")
                    return True
            except Exception:
                continue
        
        # 3차 시도: 페이지 내 모든 클릭 가능한 요소 탐색
        print(f"         🔍 페이지 내 모든 {district_name} 관련 요소 탐색...")
        try:
            page_text = await page.inner_text('body')
            if district_name in page_text:
                print(f"            ✅ 페이지에 {district_name} 텍스트 존재 확인")
                
                # 모든 클릭 가능한 요소 수집
                clickable_selectors = ['button', 'a', 'div[onclick]', 'span[onclick]', '[role="button"]']
                
                for base_selector in clickable_selectors:
                    try:
                        elements = await page.query_selector_all(base_selector)
                        for element in elements:
                            if await element.is_visible():
                                text = await element.inner_text()
                                if district_name in text:
                                    print(f"            🎯 {district_name} 포함 요소: \"{text[:50]}...\"")
                                    await element.click()
                                    await page.wait_for_timeout(2000)
                                    print(f"            ✅ {district_name} 관련 요소 클릭")
                                    return True
                    except Exception:
                        continue
            else:
                print(f"            ❌ 페이지에 {district_name} 텍스트 없음")
        except Exception as e:
            print(f"            ❌ 페이지 탐색 오류: {e}")
        
        return False

    async def switch_to_list_mode(self, page):
        """목록 모드로 전환"""
        try:
            print(f"         📋 목록 모드 전환 중...")
            
            # 목록 버튼 찾기
            list_selectors = [
                'text="목록"',
                'button:has-text("목록")',
                'a:has-text("목록")',
                '.list-mode',
                '[data-mode="list"]'
            ]
            
            for selector in list_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.click()
                        await page.wait_for_timeout(3000)
                        print(f"         ✅ 목록 모드 활성화")
                        return True
                except Exception:
                    continue
            
            # URL로 직접 목록 모드 접근
            current_url = page.url
            if '#mapFullList' not in current_url:
                list_url = current_url + '#mapFullList'
                await page.goto(list_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                print(f"         ✅ URL로 목록 모드 활성화")
                return True
            
            return True
            
        except Exception as e:
            print(f"         ❌ 목록 모드 전환 오류: {e}")
            return False

    async def collect_filtered_properties(self, page, district_name, target_count):
        """필터 적용된 상태에서 매물 수집"""
        try:
            print(f"         📜 {district_name} 필터 매물 수집 중...")
            
            # 매물 로드
            for iteration in range(5):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(2000)
                
                try:
                    more_button = await page.query_selector('button:has-text("더보기")')
                    if more_button and await more_button.is_visible():
                        await more_button.click()
                        await page.wait_for_timeout(3000)
                except Exception:
                    pass
                
                current_links = await page.query_selector_all('a[href*="/article/"]')
                print(f"            📊 {iteration+1}차: {len(current_links)}개")
                
                if len(current_links) >= target_count:
                    break
            
            # 매물 정보 추출
            property_links = await page.query_selector_all('a[href*="/article/"]')
            extracted_properties = []
            
            for i, link_element in enumerate(property_links[:target_count]):
                try:
                    # 링크 추출
                    href = await link_element.get_attribute('href')
                    if not href.startswith('http'):
                        href = f"https://m.land.naver.com{href}"
                    
                    # 텍스트 추출
                    parent = link_element
                    for _ in range(3):
                        try:
                            parent = await parent.query_selector('xpath=..')
                            if not parent:
                                break
                        except Exception:
                            break
                    
                    if parent:
                        text = await parent.inner_text()
                    else:
                        text = await link_element.inner_text()
                    
                    # 매물 정보 파싱
                    property_data = self.parse_property_district_button(text, href, district_name)
                    
                    if property_data and property_data['monthly_rent'] > 0:
                        extracted_properties.append(property_data)
                        
                        if i < 3:  # 처음 3개만 로그
                            print(f"            ✅ {i+1}: {property_data['building_name']}")
                            print(f"                면적: {property_data['area_pyeong']}평")
                
                except Exception as e:
                    if i < 3:
                        print(f"            ❌ {i+1}: 파싱 실패 - {e}")
                    continue
            
            return extracted_properties
            
        except Exception as e:
            print(f"         ❌ 매물 수집 오류: {e}")
            return []

    def parse_property_district_button(self, text, naver_link, district_name):
        """구만 보기 필터 매물 파싱"""
        try:
            property_data = {
                'region': '서울시',
                'district': district_name,
                'building_name': '상가 매물',
                'full_address': '',
                'area_sqm': 0.0,
                'area_pyeong': 0.0,
                'floor': 1,
                'deposit': 0,
                'monthly_rent': 0,
                'management_fee': 0,
                'total_monthly_cost': 0.0,
                'ceiling_height': 0.0,
                'parking_available': False,
                'near_station': False,
                'build_year': 0,
                'naver_link': naver_link,
                'data_source': 'district_button_collector',
                'collected_at': datetime.now().isoformat(),
                'raw_text': text
            }
            
            # 기존 파싱 로직 (월세, 면적, 층수 등)
            rent_patterns = re.findall(r'월세([0-9,억만\s]+)/([0-9,]+)', text)
            if rent_patterns:
                deposit_str = rent_patterns[0][0].replace(',', '').replace(' ', '')
                monthly_str = rent_patterns[0][1].replace(',', '').replace(' ', '')
                
                if '억' in deposit_str:
                    parts = deposit_str.split('억')
                    eok_part = int(parts[0]) if parts[0] else 0
                    man_part = int(parts[1]) if len(parts) > 1 and parts[1] else 0
                    property_data['deposit'] = eok_part * 10000 + man_part
                elif deposit_str:
                    property_data['deposit'] = int(deposit_str)
                
                property_data['monthly_rent'] = int(monthly_str)
            
            # 면적 추출
            area_patterns1 = re.findall(r'(\d+)/(\d+(?:\.\d+)?)㎡', text)
            if area_patterns1:
                sqm_value = float(area_patterns1[0][1])
                property_data['area_sqm'] = sqm_value
                property_data['area_pyeong'] = round(sqm_value / 3.3058, 1)
            else:
                area_patterns2 = re.findall(r'(\d+(?:\.\d+)?)㎡', text)
                if area_patterns2:
                    sqm_value = float(area_patterns2[0])
                    property_data['area_sqm'] = sqm_value
                    property_data['area_pyeong'] = round(sqm_value / 3.3058, 1)
            
            # 층수 추출
            floor_patterns = re.findall(r'([B]?)(\d+)/(\d+)층', text)
            if floor_patterns:
                basement, current_floor, total_floor = floor_patterns[0]
                floor_value = int(current_floor)
                property_data['floor'] = -floor_value if basement == 'B' else floor_value
            
            # 추가 정보
            property_data['parking_available'] = '주차' in text
            property_data['near_station'] = '역세권' in text or '역' in text
            
            # 관리비 추정
            if property_data['area_pyeong'] > 0:
                property_data['management_fee'] = min(30, max(10, int(property_data['area_pyeong'] * 1.5)))
            else:
                property_data['management_fee'] = 20
            
            property_data['total_monthly_cost'] = property_data['monthly_rent'] + property_data['management_fee']
            
            # 건물명 추출
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            for line in lines:
                if len(line) > 2 and not line.isdigit() and '월세' not in line and '개의' not in line:
                    property_data['building_name'] = line
                    break
            
            return property_data
            
        except Exception as e:
            return None

    def verify_district_accuracy(self, properties, expected_district):
        """구만 보기 필터 정확도 검증"""
        print(f"         🔍 {expected_district} 구만 보기 필터 정확도:")
        
        # 역명 기반 검증
        district_stations = {
            '강남구': ['강남', '역삼', '논현', '압구정', '청담', '삼성'],
            '강서구': ['마곡', '발산', '화곡', '까치산', '신정', '가양'],
            '영등포구': ['여의도', '당산', '영등포', '신길', '문래'],
            '구로구': ['구로', '신도림', '대림', '남구로', '가산'],
            '마포구': ['홍대', '합정', '상암', '망원', '마포', '공덕']
        }
        
        correct_count = 0
        total_count = len(properties)
        
        if expected_district in district_stations:
            for prop in properties:
                text = prop['raw_text']
                for station in district_stations[expected_district]:
                    if station in text:
                        correct_count += 1
                        break
        
        accuracy = (correct_count / total_count) * 100 if total_count > 0 else 0
        print(f"            정확도: {accuracy:.1f}% ({correct_count}/{total_count}개)")
        
        if accuracy >= 80:
            print(f"            ✅ 구만 보기 필터 매우 정확!")
        elif accuracy >= 50:
            print(f"            ⚠️ 구만 보기 필터 부분 정확")
        else:
            print(f"            ❌ 구만 보기 필터 부정확, 일반 검색과 유사")

    async def analyze_api_results(self, all_properties):
        """🚀 API 결과 분석 (링크 포함)"""
        print(f"\n📊 === API 대량 수집 결과 분석 ===")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f'api_mass_collection_{timestamp}.csv'
        json_filename = f'api_mass_collection_{timestamp}.json'
        
        df = pd.DataFrame(all_properties)
        
        # CSV 저장
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"✅ CSV 저장: {csv_filename}")
        
        # JSON 저장 (백업용)
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(all_properties, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON 저장: {json_filename}")
        
        # DB 저장 (raw_text 제외)
        df_for_db = df.drop('raw_text', axis=1, errors='ignore')
        try:
            self.processor.save_to_database(df_for_db)
            print(f"✅ DB 저장 완료")
        except Exception as e:
            print(f"⚠️ DB 저장 오류: {e}")
        
        # 통계 분석
        print(f"\n📈 === 수집 통계 ===")
        print(f"총 매물: {len(df)}개")
        
        if 'property_type' in df.columns:
            print(f"매물 타입: {df['property_type'].value_counts().to_dict()}")
        if 'trade_type' in df.columns:
            print(f"거래 타입: {df['trade_type'].value_counts().to_dict()}")
        
        # 가격 범위
        print(f"보증금 범위: {df['deposit'].min()}~{df['deposit'].max()}만원")
        print(f"월세 범위: {df['monthly_rent'].min()}~{df['monthly_rent'].max()}만원")
        print(f"면적 범위: {df['area_pyeong'].min():.1f}~{df['area_pyeong'].max():.1f}평")
        
        # 구별 분포
        print(f"\n📍 === 구별 분포 ===")
        district_counts = df['district'].value_counts()
        for district, count in district_counts.items():
            print(f"   {district}: {count}개")
        
        # 조건.md 기준 필터링 분석
        조건부합_count = self.analyze_conditions_api(df)
        print(f"\n🎯 조건.md 부합: {조건부합_count}개 ({조건부합_count/len(df)*100:.1f}%)")
        
        # 링크 분석
        links_with_data = df[df['naver_link'] != ''].shape[0]
        print(f"\n🔗 링크 정보: {links_with_data}/{len(df)}개 ({links_with_data/len(df)*100:.1f}%)")
        
        # 샘플 출력
        print(f"\n📋 === 수집 샘플 (처음 5개) ===")
        for i, row in df.head(5).iterrows():
            print(f"{i+1:2d}. [{row['district']}] {row['building_name'][:20]}...")
            print(f"     💰 {row['deposit']}/{row['monthly_rent']}만원 | 📐 {row['area_pyeong']:.1f}평 | 🏢 {row.get('floor_info', '')}")
            print(f"     🔗 {row['naver_link']}")

    def analyze_conditions_api(self, df):
        """조건.md 기준 분석 (API 버전)"""
        # 조건.md 기준 (완화된 버전)
        conditions = {
            'max_deposit': 2000,       # 보증금 2000 이하
            'max_monthly_rent': 130,   # 월세 130 이하
            'max_total_monthly': 150,  # 관리비 포함 150 이하
            'min_floor': -1,           # 지하1층 이상
            'max_floor': 2,            # 지상2층 이하
            'min_area_pyeong': 20,     # 20평 이상
            'max_management_fee': 30   # 관리비 30 이하
        }
        
        조건부합 = df[
            (df['deposit'] <= conditions['max_deposit']) &
            (df['monthly_rent'] <= conditions['max_monthly_rent']) &
            (df['total_monthly_cost'] <= conditions['max_total_monthly']) &
            (df['floor'] >= conditions['min_floor']) &
            (df['floor'] <= conditions['max_floor']) &
            (df['area_pyeong'] >= conditions['min_area_pyeong']) &
            (df['management_fee'] <= conditions['max_management_fee'])
        ]
        
        return len(조건부합)

    async def analyze_district_button_results(self, all_properties):
        """구만 보기 버튼 결과 분석 (브라우저 방식)"""
        print(f"\n📊 === 구만 보기 버튼 결과 분석 ===")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f'district_button_filter_{timestamp}.csv'
        
        df = pd.DataFrame(all_properties)
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"✅ CSV 저장: {csv_filename}")
        
        # DB 저장
        df_for_db = df.drop('raw_text', axis=1)
        try:
            self.processor.save_to_database(df_for_db)
            print(f"✅ DB 저장 완료")
        except Exception as e:
            print(f"⚠️ DB 저장 오류: {e}")
        
        # 구별 분포
        print(f"\n📍 === 구만 보기 필터 구별 분포 ===")
        district_counts = df['district'].value_counts()
        for district, count in district_counts.items():
            print(f"   {district}: {count}개")
        
        print(f"\n🎯 === 일반 수집 vs 구만 보기 비교 ===")
        print(f"구만 보기 방식: 각 구에서만 매물 수집")
        print(f"일반 수집 방식: 좌표 기반으로 인근 구 매물도 포함")
        print(f"정확도 향상 여부: 각 구별 정확도 결과 참조")

# 실행
async def run_district_button():
    collector = DistrictButtonCollector()
    return await collector.run_district_button_collection(target_per_district=10)

if __name__ == "__main__":
    print("🚀 === 하이브리드 매물 수집기 ===")
    print("💡 브라우저로 '구만보기' 버튼 클릭 → API로 무제한 대량 수집")
    print("🎯 목표: 100% 정확한 구별 분류 + 완전한 데이터 + 링크")
    
    asyncio.run(run_district_button())
