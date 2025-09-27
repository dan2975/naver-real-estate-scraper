#!/usr/bin/env python3
"""
🎯 DistrictCollector - 메인 오케스트레이터
모듈화된 하이브리드 수집 시스템의 중앙 관리자
- 브라우저 + API 하이브리드 방식
- 스텔스 기능 통합
- 완전한 데이터 처리
"""

import asyncio
import aiohttp
import os
import pandas as pd
from datetime import datetime
from playwright.async_api import async_playwright
from typing import List, Dict, Any, Optional

# 모듈 임포트
from modules.stealth_manager import StealthManager
from modules.browser_controller import BrowserController
from modules.api_collector import APICollector
from modules.property_parser import PropertyParser
from modules.data_processor import PropertyDataProcessor

# 진행률 관리자 임포트
try:
    from progress_manager import get_progress_manager
except ImportError:
    def get_progress_manager():
        class DummyProgressManager:
            def start_collection(self, *args, **kwargs): pass
            def update_district_start(self, *args, **kwargs): pass
            def update_district_complete(self, *args, **kwargs): pass
            def complete_collection(self, *args, **kwargs): pass
        return DummyProgressManager()


class DistrictCollector:
    """🎯 메인 하이브리드 수집 시스템 오케스트레이터"""
    
    def __init__(self, streamlit_params=None):
        # 모듈 초기화
        self.stealth_manager = StealthManager(pool_size=5)
        self.browser_controller = BrowserController()
        
        # Streamlit 필터를 API 수집기에 전달
        streamlit_filters = None
        if streamlit_params:
            streamlit_filters = {
                'deposit_max': streamlit_params.get('filters', {}).get('deposit_max', 2000),
                'monthly_rent_max': streamlit_params.get('filters', {}).get('monthly_rent_max', 130),
                'area_min': streamlit_params.get('filters', {}).get('area_min', 20)
            }
            print(f"         🎯 Streamlit 필터 전달: {streamlit_filters}")
        
        self.api_collector = APICollector(self.stealth_manager)
        self.property_parser = PropertyParser(streamlit_filters)
        self.data_processor = PropertyDataProcessor()
        self.progress_manager = get_progress_manager()
        
        # Streamlit 매개변수 적용
        if streamlit_params:
            self.target_districts = streamlit_params.get('districts', ['강남구'])
            self.filter_conditions = {
                'min_deposit': streamlit_params.get('deposit_range', (0, 10000))[0],
                'max_deposit': streamlit_params.get('deposit_range', (0, 10000))[1],
                'min_monthly_rent': streamlit_params.get('rent_range', (0, 1000))[0],
                'max_monthly_rent': streamlit_params.get('rent_range', (0, 1000))[1],
                'min_area_pyeong': streamlit_params.get('area_range', (0, 200))[0],
                'max_area_pyeong': streamlit_params.get('area_range', (0, 200))[1]
            }
        else:
            # 기본 설정 (수집량이 많은 주요 구들)
            self.target_districts = [
                '강남구', '강서구', '영등포구', '구로구', '마포구',
                '서초구', '송파구', '용산구', '중구', '종로구'
            ]
            self.filter_conditions = {
                'min_deposit': 0,
                'max_deposit': 2000,
                'min_monthly_rent': 0,
                'max_monthly_rent': 130,
                'min_area_pyeong': 20,
                'max_area_pyeong': 100
            }
        
        # 수집 설정
        self.max_pages_per_district = 200  # 구별 최대 페이지 (4,000개)
        self.total_target = len(self.target_districts) * self.max_pages_per_district * 20  # 목표
    
    async def run_hybrid_collection(self) -> List[Dict[str, Any]]:
        """🚀 하이브리드 수집 메인 실행"""
        print("🗺️ === 모듈화된 하이브리드 수집 시스템 ===")
        print("💡 방식: 브라우저 '구만보기' → API 대량수집")
        print("🎯 목표: 100% 정확한 구별 분류 + 완전한 데이터")
        print(f"🎯 수집 목표: {self.total_target:,}개 매물 ({len(self.target_districts)}개구 × {self.max_pages_per_district}페이지 × 20개)")
        
        # 진행률 시작
        self.progress_manager.start_collection(self.target_districts, self.max_pages_per_district * 20)
        
        all_properties = []
        
        # Playwright 초기화
        playwright = await async_playwright().start()
        
        try:
            for i, district_name in enumerate(self.target_districts, 1):
                # 중지 요청 확인
                if self.progress_manager.is_stop_requested():
                    print(f"\n🛑 수집 중지 요청으로 인해 {district_name} 수집을 건너뜁니다.")
                    break
                    
                print(f"\n📍 {i}/{len(self.target_districts)}: {district_name} 하이브리드 수집")
                
                # 🔄 구별 브라우저 재시작 (세션 격리)
                print(f"         🔄 {district_name} 전용 브라우저 시작...")
                browser, context, page = await self.browser_controller.create_mobile_context(playwright)
                
                try:
                    # 진행률 업데이트: 구별 시작
                    self.progress_manager.update_district_start(district_name, i-1)
                    
                    # 1단계: 브라우저로 구별 필터 설정
                    success = await self.setup_district_filter(page, district_name)
                    
                    if success:
                        # 2단계: API로 대량 수집
                        district_properties = await self.collect_district_data(page, district_name)
                        
                        if district_properties:
                            # 3단계: 데이터 향상 및 검증
                            enhanced_properties = self.enhance_and_validate_data(district_properties, district_name)
                            all_properties.extend(enhanced_properties)
                            
                            print(f"      ✅ {district_name}: {len(enhanced_properties)}개 하이브리드 수집 완료")
                            
                            # 진행률 업데이트: 구별 완료
                            self.progress_manager.update_district_complete(district_name, len(enhanced_properties))
                        else:
                            print(f"      ❌ {district_name}: 하이브리드 수집 실패")
                            self.progress_manager.update_district_complete(district_name, 0)
                    else:
                        print(f"      ❌ {district_name}: 구만 보기 버튼 찾기 실패")
                    
                finally:
                    # 🔄 구별 브라우저 종료 (세션 완전 격리)
                    print(f"         🔄 {district_name} 브라우저 종료...")
                    await browser.close()
                
                # 구간별 휴식
                if i < len(self.target_districts):
                    self.stealth_manager.rest_between_operations(f"{district_name} 완료")
                
        finally:
            # Playwright 종료
            await playwright.stop()
        
        # 4단계: 최종 결과 분석 및 저장
        await self.finalize_results(all_properties)
        
        # 중지 요청 확인 후 완료 처리
        if self.progress_manager.is_stop_requested():
            self.progress_manager.complete_collection(len(all_properties), success=False)
            print(f"\n🛑 사용자 요청으로 수집이 중지되었습니다. 총 {len(all_properties)}개 매물 수집됨")
        else:
            self.progress_manager.complete_collection(len(all_properties), success=True)
        
        return all_properties
    
    async def setup_district_filter(self, page, district_name: str) -> bool:
        """🌐 1단계: 브라우저로 구별 필터 설정"""
        print(f"         🌐 1단계: 브라우저로 {district_name}만 보기 활성화...")
        
        # 브라우저 컨트롤러를 통한 필터 설정
        success = await self.browser_controller.navigate_to_map_and_apply_district_filter(page, district_name)
        
        if success:
            # 목록 모드로 전환
            await self.browser_controller.switch_to_list_mode(page)
        
        return success
    
    async def collect_district_data(self, page, district_name: str) -> Optional[List[Dict[str, Any]]]:
        """🚀 2단계: 무한 스크롤 + 네트워크 모니터링으로 대량 수집"""
        print(f"         🚀 2단계: {district_name} 무한 스크롤 + 네트워크 모니터링 수집...")
        
        try:
            # 현재 페이지 상태 확인
            current_url = page.url
            print(f"            📍 현재 페이지: {current_url}")
            
            # URL이 정상적인지 확인
            if "404" in current_url or "error" in current_url:
                print(f"            ❌ 잘못된 페이지로 이동됨: {current_url}")
                return None
            
            # 🎯 무한 스크롤 + 네트워크 모니터링 방식으로 매물 수집
            properties = await self.collect_with_infinite_scroll_and_network_monitoring(page, district_name)
            
            print(f"            ✅ {district_name} 무한 스크롤 + 네트워크 수집 완료: {len(properties)}개")
            return properties
            
        except Exception as e:
            print(f"            ❌ 무한 스크롤 + 네트워크 수집 오류: {e}")
            return None
    
    def enhance_and_validate_data(self, properties: List[Dict[str, Any]], district_name: str) -> List[Dict[str, Any]]:
        """✨ 3단계: data_processor를 통한 데이터 향상 및 검증"""
        print(f"         ✨ 3단계: {district_name} data_processor 파싱 및 검증...")

        if not properties:
            return []

        try:
            # API 데이터를 DataFrame으로 변환
            df = pd.DataFrame(properties)
            print(f"            📊 API 데이터 DataFrame 변환: {len(df)}개")

            # 지역 정보 먼저 추가 (파싱 전에 필요)
            df_with_district = df.copy()
            df_with_district['district'] = district_name
            df_with_district['region'] = '서울특별시'

            # data_processor를 통한 상세 파싱
            enhanced_df = self.data_processor.csv_to_db_dataframe(df_with_district)
            print(f"            ✅ 파싱 완료: {len(enhanced_df)}개 매물")

            # 지역 정보 확인 (파싱 후에도 유지되는지 확인)
            print(f"            📍 파싱 후 지역: {enhanced_df['district'].iloc[0] if len(enhanced_df) > 0 else 'N/A'}")

            # 기본값 설정
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            enhanced_df['collected_at'] = current_time
            enhanced_df['created_at'] = current_time
            enhanced_df['score'] = 0
            enhanced_df['labels'] = ''

            # DataFrame을 딕셔너리 리스트로 변환
            enhanced_properties = enhanced_df.to_dict('records')

            print(f"            📊 향상된 매물: {len(enhanced_properties)}개")
            return enhanced_properties

        except Exception as e:
            print(f"            ⚠️ 파싱 오류: {e}")
            # 오류 발생 시 원본 데이터라도 반환
            return properties
    
    async def finalize_results(self, all_properties: List[Dict[str, Any]]) -> None:
        """📊 4단계: 최종 결과 분석 및 저장"""
        print(f"\n📊 === 모듈화된 하이브리드 수집 결과 ===")
        
        if not all_properties:
            print("❌ 수집된 매물이 없습니다.")
            return
        
        try:
            # DataFrame 생성
            df = pd.DataFrame(all_properties)
            
            # 고정 파일명 사용 (로그 파일 중복 방지)
            csv_filename = "latest_collection.csv"
            json_filename = "latest_collection.json"
            
            # 기존 파일이 있으면 백업
            if os.path.exists(csv_filename):
                backup_csv = f"backup_{csv_filename}"
                os.rename(csv_filename, backup_csv)
                print(f"📦 이전 CSV 백업: {backup_csv}")
            
            if os.path.exists(json_filename):
                backup_json = f"backup_{json_filename}"
                os.rename(json_filename, backup_json)
                print(f"📦 이전 JSON 백업: {backup_json}")
            
            # 🎯 DB 중심 시스템: UPSERT 방식으로 저장 (중복 시 업데이트)
            try:
                stats = self.data_processor.import_with_upsert(df)
                if stats['error_count'] > 0:
                    print(f"✅ DB UPSERT: 신규 {stats['new_count']}개, 업데이트 {stats['updated_count']}개, ⚠️ 오류 {stats['error_count']}개")
                else:
                    print(f"✅ DB UPSERT: 신규 {stats['new_count']}개, 업데이트 {stats['updated_count']}개")
                
                # 백업용 CSV만 생성 (옵션)
                backup_csv = f"backup_collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df.to_csv(backup_csv, index=False, encoding='utf-8-sig')
                print(f"📦 백업 CSV: {backup_csv}")
                
            except Exception as db_error:
                print(f"⚠️ DB 저장 오류: {db_error}")
                # DB 실패 시에만 CSV로 폴백
                fallback_csv = f"fallback_collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df.to_csv(fallback_csv, index=False, encoding='utf-8-sig')
                print(f"📄 폴백 CSV 저장: {fallback_csv}")
            
            # 통계 출력
            await self.print_collection_statistics(df)
            
        except Exception as e:
            print(f"❌ 결과 처리 오류: {e}")
    
    async def print_collection_statistics(self, df: pd.DataFrame) -> None:
        """📈 수집 통계 출력"""
        print(f"\n📈 === 수집 통계 ===")
        
        total_count = len(df)
        print(f"총 매물: {total_count:,}개")
        
        # 매물 타입별 분포
        if 'property_type' in df.columns:
            type_counts = df['property_type'].value_counts().to_dict()
            print(f"매물 타입: {type_counts}")
        
        # 거래 타입별 분포
        if 'trade_type' in df.columns:
            trade_counts = df['trade_type'].value_counts().to_dict()
            print(f"거래 타입: {trade_counts}")
        
        # 가격 범위
        if 'deposit' in df.columns and 'monthly_rent' in df.columns:
            valid_deposits = df[df['deposit'] > 0]['deposit']
            valid_rents = df[df['monthly_rent'] > 0]['monthly_rent']
            
            if not valid_deposits.empty:
                print(f"보증금 범위: {valid_deposits.min()}~{valid_deposits.max()}만원")
            if not valid_rents.empty:
                print(f"월세 범위: {valid_rents.min()}~{valid_rents.max()}만원")
        
        # 면적 범위
        if 'area_pyeong' in df.columns:
            valid_areas = df[df['area_pyeong'] > 0]['area_pyeong']
            if not valid_areas.empty:
                print(f"면적 범위: {valid_areas.min():.1f}~{valid_areas.max():.1f}평")
        
        # 구별 분포
        print(f"\n📍 === 구별 분포 ===")
        if 'district' in df.columns:
            district_counts = df['district'].value_counts()
            for district, count in district_counts.items():
                print(f"   {district}: {count}개")
        
        # 조건 부합 분석
        compliant_count = 0
        if 'conditions_compliance' in df.columns:
            for idx, row in df.iterrows():
                compliance = row.get('conditions_compliance', {})
                if isinstance(compliance, dict) and compliance.get('meets_all_conditions', False):
                    compliant_count += 1
        
        compliance_rate = (compliant_count / total_count * 100) if total_count > 0 else 0
        print(f"🎯 조건.md 부합: {compliant_count}개 ({compliance_rate:.1f}%)")
        
        # 링크 정보
        if 'naver_link' in df.columns:
            link_count = df['naver_link'].notna().sum()
            link_rate = (link_count / total_count * 100) if total_count > 0 else 0
            print(f"🔗 링크 정보: {link_count}/{total_count}개 ({link_rate:.1f}%)")
        
        # 샘플 매물 출력
        await self.print_sample_properties(df)
    
    async def print_sample_properties(self, df: pd.DataFrame) -> None:
        """📋 샘플 매물 출력"""
        print(f"\n📋 === 수집 샘플 (처음 5개) ===")
        
        for i in range(min(5, len(df))):
            row = df.iloc[i]
            
            district = row.get('district', '정보없음')
            property_type = row.get('property_type', '정보없음')
            deposit = row.get('deposit', 0)
            monthly_rent = row.get('monthly_rent', 0)
            area_pyeong = row.get('area_pyeong', 0)
            floor_info = row.get('floor_info', '정보없음')
            naver_link = row.get('naver_link', '')
            
            print(f" {i+1}. [{district}] {property_type}...")
            print(f"     💰 {deposit}/{monthly_rent}만원 | 📐 {area_pyeong:.1f}평 | 🏢 {floor_info}")
            if naver_link:
                print(f"     🔗 {naver_link}")
    
    async def collect_with_infinite_scroll_and_network_monitoring(self, page, district_name: str) -> List[Dict[str, Any]]:
        """🚀 무한 스크롤 + 네트워크 모니터링으로 매물 수집"""
        print(f"            🚀 {district_name} 무한 스크롤 + 네트워크 모니터링 수집 시작...")
        
        # 네트워크 요청 모니터링
        api_requests = []
        all_properties = []
        total_property_count = 0  # 전체 매물 수 (totCnt에서 추출)
        
        def handle_response(response):
            nonlocal total_property_count
            # 더 넓은 범위의 API 요청 감지
            if any(keyword in response.url for keyword in ['article', 'atcl', 'ajax', 'cluster', 'list', 'land', 'm.land']):
                api_requests.append({
                    'url': response.url,
                    'status': response.status,
                    'timestamp': asyncio.get_event_loop().time()
                })
                print(f'🌐 API 발견: {response.status} {response.url}')
                
                # totCnt 추출 (전체 매물 수)
                if 'totCnt=' in response.url:
                    import re
                    match = re.search(r'totCnt=(\d+)', response.url)
                    if match and total_property_count == 0:
                        total_property_count = int(match.group(1))
                        print(f'🎯 전체 매물 수 감지: {total_property_count}개')
                
                # 매물 관련 API인지 추가 확인
                if any(keyword in response.url for keyword in ['articleList', 'cluster', 'ajax']):
                    print(f'🎯 매물 API 확인: {response.url}')
                    
                    # 실시간으로 API 처리 (비동기 태스크로 실행)
                    asyncio.create_task(process_api_request(response.url))
        
        page.on('response', handle_response)
        
        # API 요청을 실시간으로 처리하는 함수
        async def process_api_request(url):
            try:
                print(f'                🎯 실시간 API 처리: {url}')
                
                # aiohttp로 직접 요청
                async with aiohttp.ClientSession() as session:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
                        'Referer': page.url,
                        'Accept': 'application/json, text/javascript, */*; q=0.01',
                        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                    
                    async with session.get(url, headers=headers) as response:
                        print(f'                📡 응답 상태: {response.status}')
                        
                        if response.status == 200:
                            data = await response.json()
                            print(f'                📋 응답 키들: {list(data.keys()) if isinstance(data, dict) else "리스트 형태"}')
                            
                            if 'body' in data and isinstance(data['body'], list):
                                new_properties = data['body']
                                all_properties.extend(new_properties)
                                print(f'                📊 매물 데이터: {len(new_properties)}개 추가 (총 {len(all_properties)}개)')
                                
                                # 매물 데이터 샘플 출력
                                for j, prop in enumerate(new_properties[:3]):  # 처음 3개만
                                    name = prop.get('atclNm', '이름없음')
                                    deposit = prop.get('prc', 0)
                                    rent = prop.get('rentPrc', 0)
                                    area = prop.get('spc1', 0)
                                    print(f'                  매물 {j+1}: {name} - {deposit}/{rent}만원 ({area}㎡)')
                                return True
                            else:
                                print(f'                ❌ 응답 구조 오류: body 키 없음 또는 리스트 아님')
                                print(f'                📋 응답 구조 (처음 500자): {str(data)[:500]}')
                        else:
                            print(f'                ❌ HTTP 오류: {response.status}')
                            
            except Exception as e:
                print(f'                ❌ API 데이터 추출 실패: {e}')
                import traceback
                print(f'                📋 상세 오류: {traceback.format_exc()}')
            
            return False
        
        # 초기 상태 확인
        articles = await page.query_selector_all('a[href*="article"]')
        print(f'            초기 매물 링크: {len(articles)}개')
        print(f'            초기 API 요청: {len(api_requests)}개')
        
        # 무한 스크롤하면서 네트워크 모니터링
        no_new_data_count = 0  # 연속으로 새 데이터가 없는 횟수
        max_scroll_attempts = 100  # 최대 스크롤 시도 횟수

        i = 0
        while i < max_scroll_attempts:  # 무한 루프 대신 제한된 횟수로 변경
            print(f'            --- 스크롤 {i+1}/{max_scroll_attempts} ---')

            # 스크롤 전 상태
            before_articles = await page.query_selector_all('a[href*="article"]')
            before_count = len(before_articles)
            before_requests = len(api_requests)
            before_properties = len(all_properties)

            # 페이지의 전체 높이 확인
            scroll_height = await page.evaluate('document.body.scrollHeight')
            current_scroll_y = await page.evaluate('window.scrollY')

            print(f'              현재 스크롤 위치: {current_scroll_y}px / 전체 높이: {scroll_height}px')

            # 🚀 강화된 스크롤 방법 (20000px씩 대폭 스크롤)
            # 스크롤 실행 (20000px씩 내림)
            await page.evaluate('window.scrollBy(0, 20000)')
            await asyncio.sleep(2)  # 로딩 대기

            # 스크롤 후 상태
            after_articles = await page.query_selector_all('a[href*="article"]')
            after_count = len(after_articles)
            after_requests = len(api_requests)
            
            # 🔧 스크롤이 안 되면 다른 방법 시도 (이전 성공 코드)
            scroll_y = await page.evaluate('window.scrollY')
            if scroll_y == current_scroll_y:  # 스크롤 위치가 변하지 않았다면
                print('              ❌ 스크롤 안됨, 다른 방법 시도...')
                
                # 방법 1: 키보드 스크롤
                await page.keyboard.press('PageDown')
                await asyncio.sleep(1)
                
                # 방법 2: 마우스 휠 (강화)
                await page.mouse.wheel(0, 15000)
                await asyncio.sleep(1)
                
                # 방법 3: 강제 스크롤 (강화)
                await page.evaluate('window.scrollTo(0, 20000)')
                await asyncio.sleep(1)
                
                new_scroll_y = await page.evaluate('window.scrollY')
                print(f'              강제 스크롤 후: {new_scroll_y}px')

            print(f'              매물: {before_count} → {after_count}개')
            print(f'              API 요청: {before_requests} → {after_requests}개')
            print(f'              수집된 매물 데이터: {len(all_properties)}개')
            
            # 전체 매물 수집 진행률 표시
            if total_property_count > 0:
                progress_percent = (len(all_properties) / total_property_count) * 100
                print(f'              📊 수집 진행률: {len(all_properties)}/{total_property_count}개 ({progress_percent:.1f}%)')

            # 새로운 API 요청이 있으면 데이터 추출 (실시간 처리로 대체)
            if after_requests > before_requests:
                print(f'              ✅ 새로운 API 요청 {after_requests - before_requests}개! (실시간 처리됨)')

                # 실시간 처리된 데이터 확인
                print(f'              📊 현재까지 수집된 매물: {len(all_properties)}개')

                # API 요청이 있으면 새 데이터가 있다는 의미이므로 카운터 리셋
                no_new_data_count = 0
                
                # API 요청이 계속 들어오면 더 적극적으로 스크롤
                if len(all_properties) > before_properties:
                    print(f'              🚀 새 매물 데이터 감지! 적극적 스크롤 계속...')
                    # 추가 시도를 위해 여기서 스크롤 한번 더 (강화)
                    await page.evaluate('window.scrollBy(0, 15000)')
                    await asyncio.sleep(1)

            # 매물이 로딩되면 계속
            if after_count > before_count:
                print(f'              🎉 매물 로딩 성공! {after_count - before_count}개 추가')
                no_new_data_count = 0  # 리셋
            else:
                no_new_data_count += 1
                print(f'              ❌ 매물 로딩 없음 (연속 {no_new_data_count}번)')

            # 페이지 끝 감지 (스크롤이 실제로 작동할 때만)
            current_height = await page.evaluate('document.body.scrollHeight')
            current_scroll = await page.evaluate('window.scrollY')
            
            # 스크롤이 실제로 작동하고 있을 때만 페이지 끝 감지
            if current_scroll > 100:  # 스크롤이 실제로 움직였을 때만
                if current_scroll + await page.evaluate('window.innerHeight') >= current_height - 500:
                    print(f'              📍 페이지 끝 근처 도달: {current_scroll}px / {current_height}px')
                    # 끝에 도달해도 몇 번 더 시도
                    if no_new_data_count >= 5:  # 더 많이 시도
                        break
            else:
                print(f'              🔄 스크롤 위치가 낮음 ({current_scroll}px), 페이지 끝 감지 무시')

            # 🎯 전체 매물 수집 완료 확인 (최우선)
            if total_property_count > 0 and len(all_properties) >= total_property_count * 0.95:  # 95% 이상 수집
                print(f'              🎉 전체 매물 수집 완료! {len(all_properties)}/{total_property_count}개 ({len(all_properties)/total_property_count*100:.1f}%)')
                break
            
            # 연속으로 새 데이터가 없으면 중단 (전체 매물 수가 알려진 경우 더 관대하게)
            max_attempts = 50 if total_property_count > 0 else 30  # 전체 수를 알면 더 많이 시도
            if no_new_data_count >= 15 and i <= 30:  # 처음 30번 중에 15번 연속 실패하면 조기 중단
                print(f'              ⏹️ 초기 수집 완료 (연속 {no_new_data_count}번), 중단')
                break
            elif no_new_data_count >= max_attempts:  # 동적 중단 조건
                print(f'              ⏹️ 연속 {max_attempts}번 새 데이터 없음, 중단')
                break

            # 너무 많은 매물이 수집되면 중단 (안전장치)
            if len(all_properties) >= 3000:  # 3000개 이상 수집되면 중단
                print(f'              ⏹️ 3000개 이상 수집됨, 중단')
                break

            i += 1  # 스크롤 카운터 증가

            # 스크롤 간격 조정 (초기에는 빠르게, 나중에는 천천히)
            sleep_time = 1.0 if i < 20 else 2.0
            await asyncio.sleep(sleep_time)
        
        # 최종 결과
        final_articles = await page.query_selector_all('a[href*="article"]')
        
        print(f'            📊 최종 결과:')
        print(f'              매물 링크: {len(final_articles)}개')
        print(f'              총 API 요청: {len(api_requests)}개')
        print(f'              총 수집된 매물 데이터: {len(all_properties)}개')
        
        # 전체 매물 수집 완성도 표시
        if total_property_count > 0:
            completion_percent = (len(all_properties) / total_property_count) * 100
            print(f'              🎯 수집 완성도: {len(all_properties)}/{total_property_count}개 ({completion_percent:.1f}%)')
            if completion_percent >= 95:
                print(f'              ✅ 거의 완전 수집 달성!')
            elif completion_percent >= 80:
                print(f'              👍 양호한 수집률')
            else:
                print(f'              ⚠️ 추가 수집 필요')
        
        # 수집된 매물 데이터를 표준 형식으로 변환
        converted_properties = []
        if all_properties:
            # 중복 제거
            unique_properties = []
            seen_ids = set()
            for prop in all_properties:
                prop_id = prop.get('atclNo', '')
                if prop_id and prop_id not in seen_ids:
                    seen_ids.add(prop_id)
                    unique_properties.append(prop)
            
            print(f'              중복 제거 후: {len(unique_properties)}개')
            
            # 표준 형식으로 변환
            for prop in unique_properties:
                try:
                    converted_prop = self.convert_api_property_to_standard(prop, district_name)
                    if converted_prop:
                        converted_properties.append(converted_prop)
                except Exception as e:
                    continue
        
        print(f'            📊 변환 완료: {len(converted_properties)}개 유효 매물')
        return converted_properties
    
    def convert_api_property_to_standard(self, api_prop: Dict, district_name: str) -> Optional[Dict[str, Any]]:
        """API 응답을 표준 매물 형식으로 변환"""
        try:
            # API 응답에서 필요한 데이터 추출
            article_no = api_prop.get('atclNo', '')
            trade_type = api_prop.get('tradTpNm', '')
            property_type = api_prop.get('rletTpNm', '')
            
            # 🏷️ 행정구역코드 및 지역 검증
            cortar_no = api_prop.get('cortarNo', '')
            self.log_district_verification(api_prop, article_no, cortar_no, district_name)
            
            # 가격 정보
            deposit = int(api_prop.get('prc', 0))  # 보증금
            monthly_rent = int(api_prop.get('rentPrc', 0))  # 월세
            
            # 면적 정보 (㎡ -> 평 변환)
            area_sqm = float(api_prop.get('spc1', 0))
            area_pyeong = round(area_sqm / 3.3058, 1) if area_sqm > 0 else 0
            
            # 층수 정보
            floor_info = api_prop.get('flrInfo', '0/0')
            floor_parts = floor_info.split('/')
            floor = int(floor_parts[0]) if floor_parts[0].isdigit() else 0
            
            # 조건.md 필터링 비활성화 - 전체 매물 수집 우선
            # if not self.meets_api_conditions(deposit, monthly_rent, area_pyeong, floor):
            #     print(f"               ❌ 조건 불충족: {deposit}/{monthly_rent}만원, {area_pyeong}평, {floor}층")
            #     return None
            # 
            # 대신 조건 부합 여부만 표시
            meets_conditions = self.meets_api_conditions(deposit, monthly_rent, area_pyeong, floor)
            if not meets_conditions:
                print(f"               ℹ️ 참고: {deposit}/{monthly_rent}만원, {area_pyeong}평, {floor}층 (조건 외)")
            else:
                print(f"               ✅ 조건 부합: {deposit}/{monthly_rent}만원, {area_pyeong}평, {floor}층")
            
            # 네이버 링크 생성
            naver_link = f"https://m.land.naver.com/article/info/{article_no}" if article_no else ""
            
            return {
                'region': '서울특별시',
                'district': district_name,
                'building_name': api_prop.get('atclNm', f"매물_{article_no}"),
                'full_address': f"{district_name} {property_type}",
                'area_sqm': area_sqm,
                'area_pyeong': area_pyeong,
                'floor': floor,
                'floor_info': floor_info,
                'deposit': deposit,
                'monthly_rent': monthly_rent,
                'management_fee': 0,  # API에서 제공되지 않음
                'property_type': property_type,
                'trade_type': trade_type,
                'naver_link': naver_link,
                'raw_text': str(api_prop),  # ✅ data_processor가 찾는 raw_text 컬럼으로 저장
                'data_source': 'infinite_scroll_api',
                'collected_at': datetime.now().isoformat(),
                'article_id': article_no,
                'cortar_no': cortar_no,  # 행정구역코드 추가
                'meets_conditions': meets_conditions  # 조건 부합 여부 저장
            }
            
        except Exception as e:
            print(f"               ❌ 매물 변환 오류: {e}")
            return None
    
    def log_district_verification(self, api_prop: Dict, article_no: str, cortar_no: str, expected_district: str):
        """🏷️ 수집 매물의 행정구역코드 및 지역 정보 로깅"""
        try:
            # 기본 정보
            building_name = api_prop.get('atclNm', '이름없음')
            trade_type = api_prop.get('tradTpNm', '')
            property_type = api_prop.get('rletTpNm', '')
            deposit = api_prop.get('prc', 0)
            monthly_rent = api_prop.get('rentPrc', 0)
            
            print(f"               📋 매물: {building_name} ({article_no})")
            print(f"                  💰 {trade_type} {deposit}/{monthly_rent}만원")
            
            # 📍 위치 관련 정보 수집
            location_info = []
            
            # 특징 설명
            feature_desc = api_prop.get('atclFetrDesc', '')
            if feature_desc:
                location_info.append(f"atclFetrDesc: {feature_desc}")
            
            # 방향
            direction = api_prop.get('direction', '')
            if direction:
                location_info.append(f"direction: {direction}")
                
            # 중개업소명
            cp_name = api_prop.get('cpNm', '')
            if cp_name:
                location_info.append(f"cpNm: {cp_name}")
                
            # 공인중개사명
            rltr_name = api_prop.get('rltrNm', '')
            if rltr_name:
                location_info.append(f"rltrNm: {rltr_name}")
            
            # 좌표 정보
            lat = api_prop.get('lat', 0)
            lng = api_prop.get('lng', 0)
            if lat and lng:
                location_info.append(f"좌표: {lat}, {lng}")
            
            # 위치 정보 출력
            if location_info:
                print(f"                  📍 위치 관련 정보:")
                for info in location_info:
                    print(f"                    {info}")
            
            # 🏷️ 행정구역코드 검증
            print(f"                  🏷️ 행정구역코드: {cortar_no}")
            
            # 구별 코드 매핑 (서울 25개구)
            district_codes = {
                '1111': '종로구', '1114': '중구', '1117': '용산구', '1120': '성동구',
                '1121': '광진구', '1123': '동대문구', '1124': '중랑구', '1126': '성북구',
                '1129': '강북구', '1130': '도봉구', '1131': '노원구', '1135': '은평구',
                '1138': '서대문구', '1141': '마포구', '1144': '양천구', '1147': '강서구',
                '1150': '구로구', '1153': '금천구', '1154': '영등포구', '1156': '동작구',
                '1159': '관악구', '1162': '서초구', '1168': '강남구', '1165': '송파구',
                '1171': '강동구'
            }
            
            if cortar_no and len(cortar_no) >= 4:
                district_code = cortar_no[:4]
                actual_district = district_codes.get(district_code, '알수없음')
                
                if expected_district in actual_district or actual_district in expected_district:
                    print(f"                    ✅ {actual_district} 코드 확인됨")
                else:
                    print(f"                    ❌ 예상 {expected_district} vs 실제 {actual_district}")
                    print(f"                    ⚠️ 지역 불일치 발견!")
            else:
                print(f"                    ❓ 행정구역코드 형식 오류")
                
        except Exception as e:
            print(f"                  ❌ 지역 검증 로그 오류: {e}")
    
    def meets_api_conditions(self, deposit: int, monthly_rent: int, area_pyeong: float, floor: int) -> bool:
        """API 데이터용 조건.md 필터링"""
        # 조건.md 기준
        if deposit > 2000:  # 보증금 2000만원 이하
            return False
        if monthly_rent > 130:  # 월세 130만원 이하
            return False
        if area_pyeong < 20:  # 최소 20평 이상
            return False
        # 층수 조건: 지하1층~지상2층 (조건.md 원래 기준)
        if floor < -1 or floor > 2:  # 지하1층~지상2층
            return False
        
        return True

    def get_collection_info(self) -> Dict[str, Any]:
        """📊 수집기 정보 반환"""
        return {
            'target_districts': self.target_districts,
            'max_pages_per_district': self.max_pages_per_district,
            'estimated_total': self.total_target,
            'stealth_status': self.stealth_manager.get_session_info(),
            'conditions': self.property_parser.conditions
        }


async def run_modular_collection():
    """🎯 모듈화된 수집 시스템 실행"""
    collector = DistrictCollector()
    
    print("🎯 === 모듈화된 하이브리드 수집 시스템 시작 ===")
    collector.stealth_manager.print_stealth_status()
    
    try:
        properties = await collector.run_hybrid_collection()
        
        print(f"\n🎉 === 수집 완료 ===")
        print(f"✅ 총 {len(properties)}개 매물 수집 완료")
        
        return properties
        
    except Exception as e:
        print(f"❌ 수집 시스템 오류: {e}")
        return []

async def run_streamlit_collection(streamlit_params):
    """🎯 Streamlit에서 호출하는 수집 함수"""
    collector = DistrictCollector(streamlit_params=streamlit_params)
    
    print("🚀 === Streamlit 수집 시스템 시작 ===")
    print(f"📍 대상 지역: {collector.target_districts}")
    print(f"💰 보증금 범위: {collector.filter_conditions['min_deposit']}~{collector.filter_conditions['max_deposit']}만원")
    print(f"🏠 월세 범위: {collector.filter_conditions['min_monthly_rent']}~{collector.filter_conditions['max_monthly_rent']}만원")
    print(f"📐 면적 범위: {collector.filter_conditions['min_area_pyeong']}~{collector.filter_conditions['max_area_pyeong']}평")
    
    collector.stealth_manager.print_stealth_status()
    
    try:
        properties = await collector.run_hybrid_collection()
        
        print(f"\n🎉 === Streamlit 수집 완료 ===")
        print(f"✅ 총 {len(properties)}개 매물 수집 완료")
        
        return properties
        
    except Exception as e:
        print(f"❌ Streamlit 수집 오류: {e}")
        return []

def run_streamlit_collection_sync(streamlit_params):
    """🎯 Streamlit용 동기 래퍼 함수"""
    return asyncio.run(run_streamlit_collection(streamlit_params))


if __name__ == "__main__":
    # 메인 실행
    asyncio.run(run_modular_collection())
