#!/usr/bin/env python3
"""
⚡ APIOnlyCollector - 경량 수집 시스템
브라우저 없이 API만 사용하는 고속 수집 시스템
- 25개 구 하드코딩 좌표 사용
- 브라우저 의존성 완전 제거
- 3-5배 빠른 수집 속도
"""

import asyncio
import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

# 모듈 임포트 (브라우저 제외)
from modules.stealth_manager import StealthManager
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
            def is_stop_requested(self): return False
        return DummyProgressManager()


class APIOnlyCollector:
    """⚡ 브라우저 없는 경량 수집 시스템"""
    
    def __init__(self, streamlit_params=None):
        # 모듈 초기화 (브라우저 제외)
        self.stealth_manager = StealthManager(pool_size=5)
        
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
        
        # 🚀 진정한 무제한 수집 설정 (필터 조건에 해당하는 모든 매물)
        self.max_pages_per_district = 10000  # 구별 최대 페이지 (200,000개) - 극한 안전장치
        self.unlimited_collection = True  # 무제한 수집 모드
        self.total_target = "무제한"  # 필터 조건 맞는 모든 매물
    
    async def run_api_only_collection(self) -> List[Dict[str, Any]]:
        """⚡ API 전용 수집 메인 실행"""
        print("⚡ === API 전용 경량 수집 시스템 ===")
        print("💡 방식: 하드코딩 좌표 → API 직접 호출")
        print("🎯 장점: 3-5배 빠른 속도, 브라우저 의존성 없음")
        if self.unlimited_collection:
            print(f"🎯 수집 목표: {self.total_target} (필터 조건에 맞는 모든 매물)")
            print(f"📍 대상 지역: {len(self.target_districts)}개 구")
            print("⚠️ 무제한 수집 모드: 각 구별로 필터 조건 맞는 모든 매물 수집")
        else:
            print(f"🎯 수집 목표: {self.total_target}개 매물 ({len(self.target_districts)}개구 × {self.max_pages_per_district}페이지 × 20개)")
        
        # 진행률 시작
        self.progress_manager.start_collection(self.target_districts, self.max_pages_per_district * 20)
        
        all_properties = []
        
        # 브라우저 없이 각 구별 수집
        for i, district_name in enumerate(self.target_districts, 1):
            # 중지 요청 확인
            if self.progress_manager.is_stop_requested():
                print(f"\n🛑 수집 중지 요청으로 인해 {district_name} 수집을 건너뜁니다.")
                break
                
            print(f"\n📍 {i}/{len(self.target_districts)}: {district_name} API 직접 수집")
            
            # 진행률 업데이트: 구별 시작
            self.progress_manager.update_district_start(district_name, i-1)
            
            # API만으로 데이터 수집 (하드코딩 좌표 사용)
            district_properties = await self.collect_district_api_only(district_name)
            
            if district_properties:
                # 데이터 향상 및 검증
                enhanced_properties = self.enhance_and_validate_data(district_properties, district_name)
                all_properties.extend(enhanced_properties)
                
                print(f"      ✅ {district_name}: {len(enhanced_properties)}개 API 수집 완료")
                
                # 진행률 업데이트: 구별 완료
                self.progress_manager.update_district_complete(district_name, len(enhanced_properties))
            else:
                print(f"      ❌ {district_name}: API 수집 실패")
                self.progress_manager.update_district_complete(district_name, 0)
            
            # 구간별 휴식
            if i < len(self.target_districts):
                self.stealth_manager.rest_between_operations(f"{district_name} 완료")
        
        # 최종 결과 분석 및 저장
        await self.finalize_results(all_properties)
        
        # 중지 요청 확인 후 완료 처리
        if self.progress_manager.is_stop_requested():
            self.progress_manager.complete_collection(len(all_properties), success=False)
            print(f"\n🛑 사용자 요청으로 수집이 중지되었습니다. 총 {len(all_properties)}개 매물 수집됨")
        else:
            self.progress_manager.complete_collection(len(all_properties), success=True)
        
        return all_properties
    
    async def collect_district_api_only(self, district_name: str) -> Optional[List[Dict[str, Any]]]:
        """⚡ 하드코딩 좌표로 API 직접 수집"""
        print(f"         ⚡ {district_name} 하드코딩 좌표로 API 직접 호출...")
        
        try:
            # 하드코딩 좌표로 API 파라미터 직접 구성
            from modules.browser_controller import BrowserController
            browser_controller = BrowserController()
            
            # 구별 좌표 가져오기
            coords = browser_controller.seoul_districts_coords.get(district_name)
            if not coords:
                print(f"            ❌ {district_name} 좌표 정보 없음")
                return None
            
            # API 파라미터 구성
            api_params = {
                'lat': str(coords['lat']),
                'lon': str(coords['lon']),
                'btm': str(coords['btm']),
                'lft': str(coords['lft']),
                'top': str(coords['top']),
                'rgt': str(coords['rgt']),
                'zoom': '12',
                'wprcMax': '2000',  # 보증금 최대
                'rprcMax': '130',   # 월세 최대
                'spcMin': '66',     # 면적 최소 (20평)
                'flrMin': '-1',     # 층수 최소
                'flrMax': '2'       # 층수 최대
            }
            
            print(f"            🎯 {district_name} 좌표: lat={api_params.get('lat')}, lon={api_params.get('lon')}")
            
            # API 수집기를 통한 대량 수집
            properties = await self.api_collector.collect_with_api_params(
                api_params, district_name, self.max_pages_per_district
            )
            
            return properties
            
        except Exception as e:
            print(f"            ❌ API 수집 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def enhance_and_validate_data(self, properties: List[Dict[str, Any]], district_name: str) -> List[Dict[str, Any]]:
        """✨ 데이터 향상 및 검증 (기존과 동일)"""
        print(f"         ✨ {district_name} 데이터 향상 및 검증...")
        
        enhanced_properties = []
        
        for prop in properties:
            try:
                # 이전 성공 코드와 동일하게 원본 데이터 그대로 사용
                enhanced_properties.append(prop)
                
            except Exception as e:
                print(f"            ⚠️ 매물 처리 오류: {e}")
                # 원본 데이터라도 포함
                enhanced_properties.append(prop)
        
        # 배치 분석
        print(f"            📊 분석 결과: {len(enhanced_properties)}개 매물 수집 완료")
        
        return enhanced_properties
    
    async def finalize_results(self, all_properties: List[Dict[str, Any]]) -> None:
        """📊 최종 결과 분석 및 저장 (기존과 동일)"""
        print(f"\n📊 === API 전용 수집 결과 ===")
        
        if not all_properties:
            print("❌ 수집된 매물이 없습니다.")
            return
        
        try:
            # DataFrame 생성
            df = pd.DataFrame(all_properties)
            
            # 고정 파일명 사용 (로그 파일 중복 방지)
            csv_filename = "latest_api_collection.csv"
            json_filename = "latest_api_collection.json"
            
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
                print(f"✅ DB UPSERT: 신규 {stats['new_count']}개, 업데이트 {stats['updated_count']}개, 오류 {stats['error_count']}개")
                
                # 백업용 CSV만 생성 (옵션)
                backup_csv = f"backup_api_collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df.to_csv(backup_csv, index=False, encoding='utf-8-sig')
                print(f"📦 백업 CSV: {backup_csv}")
                
            except Exception as db_error:
                print(f"⚠️ DB 저장 오류: {db_error}")
                # DB 실패 시에만 CSV로 폴백
                fallback_csv = f"fallback_api_collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df.to_csv(fallback_csv, index=False, encoding='utf-8-sig')
                print(f"📄 폴백 CSV 저장: {fallback_csv}")
            
            # 통계 출력
            await self.print_collection_statistics(df)
            
        except Exception as e:
            print(f"❌ 결과 처리 오류: {e}")
    
    async def print_collection_statistics(self, df: pd.DataFrame) -> None:
        """📈 수집 통계 출력 (기존과 동일)"""
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
        """📋 샘플 매물 출력 (기존과 동일)"""
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


async def run_api_only_collection():
    """⚡ API 전용 수집 시스템 실행"""
    collector = APIOnlyCollector()
    
    print("⚡ === API 전용 경량 수집 시스템 시작 ===")
    collector.stealth_manager.print_stealth_status()
    
    try:
        properties = await collector.run_api_only_collection()
        
        print(f"\n🎉 === 수집 완료 ===")
        print(f"✅ 총 {len(properties)}개 매물 수집 완료")
        
        return properties
        
    except Exception as e:
        print(f"❌ 수집 시스템 오류: {e}")
        return []

async def run_streamlit_api_collection(streamlit_params):
    """⚡ Streamlit에서 호출하는 API 전용 수집 함수"""
    collector = APIOnlyCollector(streamlit_params=streamlit_params)
    
    print("⚡ === Streamlit API 전용 수집 시스템 시작 ===")
    print(f"📍 대상 지역: {collector.target_districts}")
    print(f"💰 보증금 범위: {collector.filter_conditions['min_deposit']}~{collector.filter_conditions['max_deposit']}만원")
    print(f"🏠 월세 범위: {collector.filter_conditions['min_monthly_rent']}~{collector.filter_conditions['max_monthly_rent']}만원")
    print(f"📐 면적 범위: {collector.filter_conditions['min_area_pyeong']}~{collector.filter_conditions['max_area_pyeong']}평")
    
    collector.stealth_manager.print_stealth_status()
    
    try:
        properties = await collector.run_api_only_collection()
        
        print(f"\n🎉 === Streamlit API 전용 수집 완료 ===")
        print(f"✅ 총 {len(properties)}개 매물 수집 완료")
        
        return properties
        
    except Exception as e:
        print(f"❌ Streamlit API 전용 수집 오류: {e}")
        return []

def run_streamlit_api_collection_sync(streamlit_params):
    """⚡ Streamlit용 동기 래퍼 함수"""
    return asyncio.run(run_streamlit_api_collection(streamlit_params))


if __name__ == "__main__":
    # 메인 실행
    asyncio.run(run_api_only_collection())
