#!/usr/bin/env python3
"""
🎯 DistrictCollector - 메인 오케스트레이터
모듈화된 하이브리드 수집 시스템의 중앙 관리자
- 브라우저 + API 하이브리드 방식
- 스텔스 기능 통합
- 완전한 데이터 처리
"""

import asyncio
import pandas as pd
from datetime import datetime
from playwright.async_api import async_playwright
from typing import List, Dict, Any, Optional

# 모듈 임포트
from modules.stealth_manager import StealthManager
from modules.browser_controller import BrowserController
from modules.api_collector import APICollector
from modules.property_parser import PropertyParser
from data_processor import PropertyDataProcessor

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
            # 브라우저 컨텍스트 생성
            browser, context, page = await self.browser_controller.create_mobile_context(playwright)
            
            try:
                for i, district_name in enumerate(self.target_districts, 1):
                    # 중지 요청 확인
                    if self.progress_manager.is_stop_requested():
                        print(f"\n🛑 수집 중지 요청으로 인해 {district_name} 수집을 건너뜁니다.")
                        break
                        
                    print(f"\n📍 {i}/{len(self.target_districts)}: {district_name} 하이브리드 수집")
                    
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
                    
                    # 구간별 휴식
                    if i < len(self.target_districts):
                        self.stealth_manager.rest_between_operations(f"{district_name} 완료")
                
            finally:
                await browser.close()
                
        finally:
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
        """🚀 2단계: API로 대량 데이터 수집"""
        print(f"         🚀 2단계: {district_name} 필터 상태에서 API 대량 수집...")
        
        try:
            # 브라우저에서 API 파라미터 추출
            api_params = await self.browser_controller.extract_api_params_from_browser(page, district_name)
            
            if not api_params:
                print(f"            ❌ API 파라미터 추출 실패")
                return None
            
            # API 수집기를 통한 대량 수집
            properties = await self.api_collector.collect_with_api_params(
                api_params, district_name, self.max_pages_per_district
            )
            
            return properties
            
        except Exception as e:
            print(f"            ❌ API 수집 오류: {e}")
            return None
    
    def enhance_and_validate_data(self, properties: List[Dict[str, Any]], district_name: str) -> List[Dict[str, Any]]:
        """✨ 3단계: 데이터 향상 및 검증"""
        print(f"         ✨ 3단계: {district_name} 데이터 향상 및 검증...")
        
        enhanced_properties = []
        
        for prop in properties:
            try:
                # 이전 성공 코드와 동일하게 원본 데이터 그대로 사용 (PropertyParser 비활성화)
                enhanced_properties.append(prop)
                
            except Exception as e:
                print(f"            ⚠️ 매물 처리 오류: {e}")
                # 원본 데이터라도 포함
                enhanced_properties.append(prop)
        
        # 배치 분석 (이전 성공 코드와 동일하게 비활성화)
        print(f"            📊 분석 결과: {len(enhanced_properties)}개 매물 수집 완료")
        
        return enhanced_properties
    
    async def finalize_results(self, all_properties: List[Dict[str, Any]]) -> None:
        """📊 4단계: 최종 결과 분석 및 저장"""
        print(f"\n📊 === 모듈화된 하이브리드 수집 결과 ===")
        
        if not all_properties:
            print("❌ 수집된 매물이 없습니다.")
            return
        
        try:
            # DataFrame 생성
            df = pd.DataFrame(all_properties)
            
            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"modular_hybrid_collection_{timestamp}.csv"
            json_filename = f"modular_hybrid_collection_{timestamp}.json"
            
            # CSV 저장
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"✅ CSV 저장: {csv_filename}")
            
            # JSON 저장
            df.to_json(json_filename, orient='records', force_ascii=False, indent=2)
            print(f"✅ JSON 저장: {json_filename}")
            
            # 데이터베이스 저장 시도
            try:
                # DB 저장을 위한 컬럼 정리
                db_df = df.copy()
                
                # 복잡한 객체 컬럼 제거
                columns_to_drop = ['conditions_compliance', 'raw_data']
                for col in columns_to_drop:
                    if col in db_df.columns:
                        db_df = db_df.drop(columns=[col])
                
                # 기존 데이터베이스 초기화
                self.data_processor.initialize_database()
                
                # DB에 저장
                for _, row in db_df.iterrows():
                    self.data_processor.save_property(row.to_dict())
                
                print(f"✅ DB 저장 완료")
                
            except Exception as db_error:
                print(f"⚠️ DB 저장 오류: {db_error}")
            
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
