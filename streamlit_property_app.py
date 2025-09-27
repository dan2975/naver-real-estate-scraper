#!/usr/bin/env python3
"""
부동산 매물 동적 필터링 및 수집 Streamlit 앱
PRD v2.1 구현: 4개 탭 구조 + 범위 필터 시스템
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import glob
import asyncio
import subprocess
import threading
import time

# 실시간 진행률 관리자 임포트
try:
    from progress_manager import get_progress_manager
except ImportError:
    def get_progress_manager():
        class DummyProgressManager:
            def get_progress(self): return {"status": "idle", "progress_percent": 0}
            def reset_progress(self): pass
        return DummyProgressManager()

# 페이지 설정
st.set_page_config(
    page_title="부동산 매물 수집 & 분석 시스템",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    color: #1f77b4;
    text-align: center;
    margin-bottom: 2rem;
}
.metric-card {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 0.5rem 0;
}
.filter-section {
    background-color: #ffffff;
    padding: 1.5rem;
    border-radius: 0.5rem;
    border: 1px solid #e0e0e0;
    margin-bottom: 1rem;
}
.status-success {
    background-color: #d4edda;
    color: #155724;
    padding: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #c3e6cb;
}
.status-error {
    background-color: #f8d7da;
    color: #721c24;
    padding: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #f5c6cb;
}
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if 'collection_started' not in st.session_state:
    st.session_state.collection_started = False
if 'collection_params' not in st.session_state:
    st.session_state.collection_params = {}
if 'collection_progress' not in st.session_state:
    st.session_state.collection_progress = 0

# API 전용 수집 세션 상태 초기화
if 'api_collection_started' not in st.session_state:
    st.session_state.api_collection_started = False
if 'api_collection_progress' not in st.session_state:
    st.session_state.api_collection_progress = 0
if 'api_collection_status' not in st.session_state:
    st.session_state.api_collection_status = ""
if 'collection_status' not in st.session_state:
    st.session_state.collection_status = ""

@st.cache_data
def load_property_data():
    """매물 데이터 로드 및 전처리"""
    try:
        # 최신 CSV 파일 자동 선택
        csv_files = glob.glob('*_properties_*.csv') + glob.glob('*corrected*.csv') + glob.glob('api_mass_collection*.csv')
        if csv_files:
            latest_csv = max(csv_files, key=lambda x: os.path.getmtime(x))
            print(f"📄 최신 CSV 파일 로드: {latest_csv}")
        else:
            return pd.DataFrame()
        
        df = pd.read_csv(latest_csv)
        
        # 데이터 정리
        df = df.fillna('')
        
        # 숫자 컬럼 변환
        numeric_columns = ['area_pyeong', 'area_sqm', 'floor', 'deposit', 'monthly_rent', 'management_fee', 'total_monthly_cost', 'score']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # district 컬럼이 없으면 생성
        if 'district' not in df.columns:
            df['district'] = '기타'
        
        return df
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return pd.DataFrame()

def load_database_data():
    """데이터베이스에서 매물 데이터 로드"""
    try:
        from modules.data_processor import PropertyDataProcessor
        processor = PropertyDataProcessor()
        
        # DB 매물 개수 확인
        db_count = processor.get_properties_count()
        
        if db_count == 0:
            st.warning("⚠️ 데이터베이스가 비어있습니다.")
            
            # CSV → DB 자동 가져오기 제안
            if st.button("📥 최신 CSV → DB 자동 가져오기"):
                csv_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'collection' in f]
                if csv_files:
                    latest_csv = max(csv_files, key=lambda x: os.path.getmtime(x))
                    saved_count = processor.import_csv_to_db(latest_csv, overwrite=True)
                    st.success(f"✅ {saved_count}개 매물을 DB에 저장했습니다!")
                    st.rerun()
                else:
                    st.error("❌ CSV 파일을 찾을 수 없습니다.")
            
            return pd.DataFrame()
        
        # DB에서 데이터 로드
        df = processor.get_all_properties_from_db()
        st.info(f"📊 데이터베이스: {len(df)}개 매물 로드됨")
        
        # 데이터 전처리 (CSV와 동일하게)
        df = df.fillna('')
        
        # 숫자 컬럼 변환
        numeric_columns = ['area_pyeong', 'area_sqm', 'floor', 'deposit', 'monthly_rent', 'management_fee', 'total_monthly_cost', 'score']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df
        
    except Exception as e:
        st.error(f"❌ DB 로드 오류: {e}")
        return pd.DataFrame()

def apply_enhanced_filters(df, districts=None, deposit_range=None, rent_range=None, floor_range=None, area_range=None, include_whole_building=True):
    """🎯 개선된 필터 적용 함수 (층수 포함, 0층 옵션)"""
    if df.empty:
        return df
        
    filtered = df.copy()
    
    # 지역 필터
    if districts:
        filtered = filtered[filtered['district'].isin(districts)]
    
    # 보증금 범위
    if deposit_range and 'deposit' in filtered.columns:
        filtered = filtered[
            (filtered['deposit'] >= deposit_range[0]) &
            (filtered['deposit'] <= deposit_range[1])
        ]
    
    # 월세 범위
    if rent_range and 'monthly_rent' in filtered.columns:
        filtered = filtered[
            (filtered['monthly_rent'] >= rent_range[0]) &
            (filtered['monthly_rent'] <= rent_range[1])
        ]
    
    # 🏢 층수 범위 (0층 = 건물 전체 처리)
    if floor_range and 'floor' in filtered.columns:
        if include_whole_building:
            # 0층(건물 전체) 포함
            filtered = filtered[
                (filtered['floor'] >= floor_range[0]) &
                (filtered['floor'] <= floor_range[1])
            ]
        else:
            # 0층(건물 전체) 제외
            filtered = filtered[
                (filtered['floor'] >= floor_range[0]) &
                (filtered['floor'] <= floor_range[1]) &
                (filtered['floor'] != 0)
            ]
    
    # 면적 범위 (전용면적 기준)
    if area_range:
        # 전용면적이 있으면 전용면적 기준으로 필터링
        if 'exclusive_area_pyeong' in filtered.columns:
            try:
                # 안전한 숫자 변환: 에러 발생 시 0으로 처리
                area_numeric = pd.to_numeric(filtered['exclusive_area_pyeong'], errors='coerce')
                # 유효한 숫자 값만 필터링 (NaN 제외)
                area_valid = area_numeric.notna()
                if area_valid.any():
                    filtered = filtered[
                        area_valid &
                        (area_numeric >= area_range[0]) &
                        (area_numeric <= area_range[1])
                    ]
            except Exception as e:
                print(f"면적 필터링 오류: {e}")
        # 전용면적이 없으면 기존 area_pyeong 기준으로 필터링
        elif 'area_pyeong' in filtered.columns:
            try:
                # 안전한 숫자 변환: 에러 발생 시 0으로 처리
                area_numeric = pd.to_numeric(filtered['area_pyeong'], errors='coerce')
                # 유효한 숫자 값만 필터링 (NaN 제외)
                area_valid = area_numeric.notna()
                if area_valid.any():
                    filtered = filtered[
                        area_valid &
                        (area_numeric >= area_range[0]) &
                        (area_numeric <= area_range[1])
                    ]
            except Exception as e:
                print(f"면적 필터링 오류: {e}")
    
    return filtered

def apply_sorting(df, sort_by):
    """정렬 적용"""
    if df.empty:
        return df
        
    sort_mapping = {
        "보증금 낮은순": ('deposit', True),
        "보증금 높은순": ('deposit', False),
        "월세 낮은순": ('monthly_rent', True),
        "월세 높은순": ('monthly_rent', False),
        "면적 큰순": ('area_pyeong', False),
        "면적 작은순": ('area_pyeong', True),
        "등록순": (None, None)
    }
    
    column, ascending = sort_mapping.get(sort_by, (None, None))
    if column and column in df.columns:
        return df.sort_values(column, ascending=ascending)
    
    return df

def calculate_compliance_rate(df):
    """조건 부합률 계산"""
    if df.empty:
        return {"조건 미충족": 100}
    
    # 조건.md 기준
    compliant = df[
        (df['deposit'] <= 2000) &
        (df['monthly_rent'] <= 130) &
        (df['area_pyeong'] >= 20)
    ]
    
    compliant_rate = len(compliant) / len(df) * 100
    return {
        "조건 부합": compliant_rate,
        "조건 미충족": 100 - compliant_rate
    }

def run_collection_in_background(params):
    """백그라운드에서 수집 실행 (하이브리드 방식)"""
    try:
        st.session_state.collection_status = "🚀 하이브리드 수집 시스템 시작..."
        st.session_state.collection_progress = 10
        
        # district_collector 임포트 및 실행
        from district_collector import run_streamlit_collection_sync
        
        st.session_state.collection_status = "📍 브라우저 지역 설정 중..."
        st.session_state.collection_progress = 20
        
        # 실제 수집 실행
        properties = run_streamlit_collection_sync(params)
        
        st.session_state.collection_progress = 100
        
        if properties and len(properties) > 0:
            st.session_state.collection_status = f"✅ 하이브리드 수집 완료! {len(properties)}개 매물 수집됨"
        else:
            st.session_state.collection_status = "⚠️ 하이브리드 수집 완료되었으나 조건에 맞는 매물이 없습니다"
            
    except Exception as e:
        st.session_state.collection_status = f"❌ 하이브리드 수집 오류: {str(e)}"

def run_api_collection_in_background(params):
    """백그라운드에서 API 전용 수집 실행 (progress_manager 통합)"""
    try:
        # progress_manager 가져오기 (district_collector와 동일한 방식)
        try:
            from progress_manager import get_progress_manager
            progress_manager = get_progress_manager()
            use_progress_manager = True
        except ImportError:
            progress_manager = None
            use_progress_manager = False
        
        # 초기화
        st.session_state.api_collection_status = "⚡ API 전용 수집 시스템 초기화..."
        st.session_state.api_collection_progress = 5
        
        # 선택된 지역 수 확인
        selected_districts = params.get('districts', [])
        total_districts = len(selected_districts)
        estimated_total = total_districts * 1000  # 구별 예상 1000개씩
        
        # progress_manager 시작 (district_collector 방식)
        if use_progress_manager:
            progress_manager.start_collection(selected_districts, estimated_total)
        
        st.session_state.api_collection_status = f"📍 {total_districts}개 지역 수집 준비 중..."
        st.session_state.api_collection_progress = 10
        
        # api_only_collector 임포트 및 실행
        from api_only_collector import run_streamlit_api_collection_sync
        
        st.session_state.api_collection_status = "⚡ 하드코딩 좌표로 API 직접 호출 시작..."
        st.session_state.api_collection_progress = 15
        
        # 지역별 진행률 업데이트 (progress_manager 통합)
        for i, district in enumerate(selected_districts):
            if use_progress_manager:
                progress_manager.update_district_start(district, i)
            
            progress = 20 + (i / total_districts) * 60  # 20% ~ 80%
            st.session_state.api_collection_status = f"📍 {district} 수집 중... ({i+1}/{total_districts})"
            st.session_state.api_collection_progress = int(progress)
        
        # 전체 수집 실행
        properties = run_streamlit_api_collection_sync(params)
        
        # 각 지역 완료 처리 (progress_manager)
        if use_progress_manager and properties:
            # 지역별 매물 수 추정 (전체를 지역 수로 나눔)
            properties_per_district = len(properties) // total_districts if total_districts > 0 else len(properties)
            for district in selected_districts:
                progress_manager.update_district_complete(district, properties_per_district)
        
        st.session_state.api_collection_status = f"💾 {total_districts}개 지역 데이터 저장 중..."
        st.session_state.api_collection_progress = 85
        
        # 결과 처리
        st.session_state.api_collection_status = "📊 수집 결과 분석 중..."
        st.session_state.api_collection_progress = 95
        
        # 완료
        st.session_state.api_collection_progress = 100
        
        # progress_manager 완료 처리
        if use_progress_manager:
            progress_manager.complete_collection(len(properties) if properties else 0, success=True)
        
        if properties and len(properties) > 0:
            st.session_state.api_collection_status = f"✅ API 전용 수집 완료! {len(properties):,}개 매물 수집 (지역: {', '.join(selected_districts)})"
        else:
            st.session_state.api_collection_status = "⚠️ API 전용 수집 완료되었으나 조건에 맞는 매물이 없습니다"
            
    except Exception as e:
        st.session_state.api_collection_status = f"❌ API 전용 수집 오류: {str(e)}"
        st.session_state.api_collection_progress = 0
        
        # progress_manager 오류 처리
        if use_progress_manager and progress_manager:
            progress_manager.complete_collection(0, success=False)

def tab_collection():
    """Tab 1: 🚀 수집"""
    st.header("🚀 매물 수집")
    
    # 사이드바 필터
    with st.sidebar:
        st.header("🎯 필터 설정")
        st.info("📝 상가+사무실 월세 전용")
        
        # 지역 선택 (서울 전체 25개 구)
        all_districts = [
            '강남구', '강동구', '강북구', '강서구', '관악구',
            '광진구', '구로구', '금천구', '노원구', '도봉구',
            '동대문구', '동작구', '마포구', '서대문구', '서초구',
            '성동구', '성북구', '송파구', '양천구', '영등포구',
            '용산구', '은평구', '종로구', '중구', '중랑구'
        ]
        
        # 전체 선택/해제 버튼
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗺️ 전체 구 선택", key="select_all_districts"):
                st.session_state.selected_districts = all_districts
        with col2:
            if st.button("❌ 전체 해제", key="clear_all_districts"):
                st.session_state.selected_districts = []
        
        # 세션 상태에서 선택된 구 가져오기
        if 'selected_districts' not in st.session_state:
            st.session_state.selected_districts = ['강남구']
        
        districts = st.multiselect(
            "📍 수집 지역", 
            all_districts,
            default=st.session_state.selected_districts,
            help="수집할 구를 선택하세요 (서울 전체 25개 구)",
            key="districts_multiselect"
        )
        
        # 선택된 구 상태 업데이트
        st.session_state.selected_districts = districts
        
        # 선택된 구 정보 표시
        if districts:
            st.info(f"✅ 선택된 지역: {len(districts)}개 구")
            if len(districts) <= 5:
                st.write("🏢 " + ", ".join(districts))
            else:
                st.write(f"🏢 {districts[0]}, {districts[1]}, {districts[2]} 외 {len(districts)-3}개 구")
        else:
            st.warning("📍 최소 1개 지역을 선택해주세요")
        
        # 보증금 범위
        st.subheader("💰 보증금 조건")
        col1, col2 = st.columns(2)
        with col1:
            deposit_min = st.number_input(
                "최소 (만원)", 
                min_value=0, max_value=10000, value=0, step=100,
                key="deposit_min"
            )
        with col2:
            deposit_max = st.number_input(
                "최대 (만원)", 
                min_value=0, max_value=10000, value=2000, step=100,
                key="deposit_max"
            )
        
        # 월세 범위
        st.subheader("🏠 월세 조건")
        col1, col2 = st.columns(2)
        with col1:
            rent_min = st.number_input(
                "최소 (만원)", 
                min_value=0, max_value=1000, value=0, step=10,
                key="rent_min"
            )
        with col2:
            rent_max = st.number_input(
                "최대 (만원)", 
                min_value=0, max_value=1000, value=130, step=10,
                key="rent_max"
            )
        
        # 면적 범위
        st.subheader("📐 면적 조건")
        col1, col2 = st.columns(2)
        with col1:
            area_min = st.number_input(
                "최소 (평)", 
                min_value=0, max_value=200, value=20, step=1,
                key="area_min"
            )
        with col2:
            area_max = st.number_input(
                "최대 (평)", 
                min_value=0, max_value=200, value=100, step=1,
                key="area_max"
            )
        
        # 조건 검증
        validation_errors = []
        if deposit_min > deposit_max:
            validation_errors.append("⚠️ 보증금 최소값이 최대값보다 큽니다")
        if rent_min > rent_max:
            validation_errors.append("⚠️ 월세 최소값이 최대값보다 큽니다")
        if area_min > area_max:
            validation_errors.append("⚠️ 면적 최소값이 최대값보다 큽니다")
        
        for error in validation_errors:
            st.error(error)
    
    # 메인 화면
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # 현재 설정 요약 카드
        st.info("📋 현재 필터 조건")
        st.write(f"🏢 **매물**: 상가+사무실 (월세)")
        st.write(f"📍 **지역**: {len(districts)}개 구")
        st.write(f"💰 **보증금**: {deposit_min:,}~{deposit_max:,}만원")
        st.write(f"🏠 **월세**: {rent_min:,}~{rent_max:,}만원") 
        st.write(f"📐 **면적**: {area_min}~{area_max}평")
        
        # 지역구별 최대 수집량 (구별 최대 200페이지 × 20개 = 4,000개)
        max_collection = len(districts) * 4000  # 구당 최대 4,000개
        st.metric("지역구별 최대 수집량", f"{max_collection:,}개")
        
        # 필터 조건 검증
        conditions_valid = (
            len(districts) > 0 and
            deposit_min <= deposit_max and
            rent_min <= rent_max and
            area_min <= area_max
        )
        
        # 수집 방식 선택 및 버튼
        st.subheader("📋 수집 방식 선택")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🌐 하이브리드 수집 (기존)**")
            st.caption("✅ 브라우저 + API 조합")
            st.caption("✅ 최고 정확도")
            st.caption("⚠️ 느린 속도 (브라우저 필요)")
            
            if st.button(
                "🌐 하이브리드 수집 시작", 
                type="primary", 
                disabled=not conditions_valid,
                key="hybrid_collection"
            ):
                st.session_state.collection_started = True
                st.session_state.collection_params = {
                    'districts': districts,
                    'filters': {
                        'deposit_max': deposit_max,
                        'monthly_rent_max': rent_max, 
                        'area_min': area_min
                    },
                    'deposit_range': (deposit_min, deposit_max),
                    'rent_range': (rent_min, rent_max),
                    'area_range': (area_min, area_max)
                }
                st.session_state.collection_progress = 0
                st.session_state.collection_status = "하이브리드 수집 시작..."
                
                # 백그라운드 하이브리드 수집 시작
                thread = threading.Thread(
                    target=run_collection_in_background, 
                    args=(st.session_state.collection_params,)
                )
                thread.start()
                st.rerun()

    with col2:
        st.markdown("**⚡ API 전용 수집 (신규)**")
        st.caption("⚡ API만 사용 (브라우저 없음)")
        st.caption("⚡ 3-5배 빠른 속도")
        st.caption("✅ 하드코딩 좌표 사용")
        
        if st.button(
            "⚡ API 전용 수집 시작", 
            type="secondary", 
            disabled=not conditions_valid,
            key="api_collection"
        ):
            st.session_state.api_collection_started = True
            st.session_state.api_collection_params = {
                'districts': districts,
                'filters': {
                    'deposit_max': deposit_max,
                    'monthly_rent_max': rent_max, 
                    'area_min': area_min
                },
                'deposit_range': (deposit_min, deposit_max),
                'rent_range': (rent_min, rent_max),
                'area_range': (area_min, area_max)
            }
            st.session_state.api_collection_progress = 0
            st.session_state.api_collection_status = "API 전용 수집 시작..."
            
            # 백그라운드 API 전용 수집 시작
            thread = threading.Thread(
                target=run_api_collection_in_background, 
                args=(st.session_state.api_collection_params,)
            )
            thread.start()
            st.rerun()

    # 진행률 표시 섹션
    st.subheader("📊 수집 진행률")
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("**🌐 하이브리드 수집**")
        # 실시간 진행률 표시
        progress_manager = get_progress_manager()
        current_progress = progress_manager.get_progress()
        
        if st.session_state.get('collection_started', False) or current_progress.get('status') == 'running':
            st.success("🚀 수집이 진행 중입니다!")
            
            # 🔄 수동 새로고침 버튼 (WebSocket 오류 방지)
            col_refresh1, col_refresh2 = st.columns([3, 1])
            with col_refresh2:
                if st.button("🔄 새로고침", key="refresh_progress"):
                    st.rerun()
            
            with col_refresh1:
                last_update = current_progress.get('last_update', '')
                if last_update:
                    from datetime import datetime
                    try:
                        update_time = datetime.fromisoformat(last_update)
                        st.caption(f"마지막 업데이트: {update_time.strftime('%H:%M:%S')}")
                    except:
                        st.caption("마지막 업데이트: 알 수 없음")
            
            # 메인 진행률 바 (브라우저 기준)
            progress_percent = current_progress.get('progress_percent', 0)
            current_collected = current_progress.get('current_district_properties', 0)
            browser_totals = current_progress.get('browser_totals', {})
            current_district = current_progress.get('current_district', '')
            browser_total = browser_totals.get(current_district, 0)
            
            # 브라우저 총 매물 수가 있으면 실시간 재계산
            if browser_total > 0 and current_collected > 0:
                real_progress = min((current_collected / browser_total) * 100, 100)
                st.progress(real_progress / 100, text=f"전체 진행률: {real_progress:.1f}% ({current_collected}/{browser_total}개)")
                
                # 중복 통계 표시
                if current_collected > browser_total:
                    duplicate_count = current_collected - browser_total
                    efficiency = (browser_total / current_collected) * 100 if current_collected > 0 else 0
                    st.info(f"📊 중복 제거: {duplicate_count}개 중복 감지됨 (효율성: {efficiency:.1f}%)")
                    st.caption(f"✅ 유니크 매물: {browser_total}개 / 전체 수집: {current_collected}개")
            else:
                st.progress(progress_percent / 100, text=f"전체 진행률: {progress_percent:.1f}%")
            
            # 상세 진행 정보
            col2_1, col2_2 = st.columns(2)
            
            with col2_1:
                st.metric(
                    "📍 현재 지역", 
                    current_progress.get('current_district', '대기 중'),
                    f"{current_progress.get('district_index', 0) + 1}/{current_progress.get('total_districts', 0)}"
                )
                
                st.metric(
                    "📄 현재 페이지",
                    current_progress.get('current_page', 0),
                    f"진행 중..."
                )
            
            with col2_2:
                # 브라우저 감지 총 매물 수 기준으로 표시
                if browser_total > 0:
                    st.metric(
                        "🏠 수집된 매물", 
                        f"{current_collected:,}개",
                        f"목표: {browser_total:,}개"
                    )
                else:
                    st.metric(
                        "🏠 수집된 매물",
                        f"{current_progress.get('current_properties_collected', 0):,}개",
                        f"목표: {current_progress.get('total_properties_target', 0):,}개"
                    )
                
                # 예상 완료 시간
                remaining = current_progress.get('estimated_remaining_seconds')
                if remaining:
                    remaining_min = int(remaining / 60)
                    remaining_sec = int(remaining % 60)
                    st.metric("⏱️ 예상 완료", f"{remaining_min}분 {remaining_sec}초")
                else:
                    st.metric("⏱️ 예상 완료", "계산 중...")
            
            # 현재 상태
            current_step = current_progress.get('current_step', '진행 중...')
            st.info(f"🔄 {current_step}")
            
            # 완료된 지역 목록
            completed = current_progress.get('completed_districts', [])
            if completed:
                with st.expander(f"✅ 완료된 지역 ({len(completed)}개)"):
                    for district in completed:
                        st.write(f"• {district.get('name', '')}: {district.get('properties', 0)}개")
            
            # 오류 목록
            errors = current_progress.get('errors', [])
            if errors:
                with st.expander(f"⚠️ 오류 로그 ({len(errors)}개)", expanded=False):
                    for error in errors[-5:]:  # 최근 5개만 표시
                        st.error(f"{error.get('timestamp', '')}: {error.get('message', '')}")
            
            # 수집 파라미터 표시
            params = st.session_state.get('collection_params', {})
            if params:
                with st.expander("🔧 수집 파라미터"):
                    st.json(params)
            
            # 수집 중지 버튼
            if current_progress.get('status') == 'running':
                if st.button("🛑 수집 중지", type="secondary"):
                    # 중지 요청 전송
                    progress_manager.request_stop()
                    st.session_state.collection_started = False
                    st.success("🛑 수집 중지 요청을 전송했습니다. 잠시 후 중지됩니다...")
                    st.rerun()
                    
        else:
            st.info("🎯 필터 조건을 설정하고 '수집 시작'을 눌러주세요")
            
            # 이전 수집 결과가 있다면 표시
            if current_progress.get('status') == 'completed':
                st.success(f"✅ 이전 수집 완료: {current_progress.get('current_properties_collected', 0)}개 매물")
                
                if st.button("🔄 진행률 초기화"):
                    progress_manager.reset_progress()
                    st.rerun()
            
            # 조건 유효성 검사 메시지
            if not conditions_valid:
                if len(districts) == 0:
                    st.warning("📍 최소 1개 지역을 선택해주세요")
                for error in validation_errors:
                    st.error(error.replace("⚠️ ", ""))
    
    with col4:
        st.markdown("**⚡ API 전용 수집**")
        
        # API 전용 수집 진행률 표시 (progress_manager 통합)
        if st.session_state.get('api_collection_started', False):
            st.success("🚀 API 전용 수집이 진행 중입니다!")
            
            # 🔄 수동 새로고침 버튼
            col_refresh3, col_refresh4 = st.columns([3, 1])
            with col_refresh4:
                if st.button("🔄 새로고침", key="refresh_api_progress"):
                    st.rerun()
            
            # progress_manager에서 실시간 진행률 가져오기 (하이브리드와 동일)
            try:
                progress_manager = get_progress_manager()
                current_progress = progress_manager.get_progress()
                
                # progress_manager 기반 진행률 (더 정확함)
                if current_progress.get('status') == 'running':
                    progress_percent = current_progress.get('progress_percent', 0)
                    current_collected = current_progress.get('current_properties_collected', 0)
                    total_target = current_progress.get('total_properties_target', 0)
                    current_district = current_progress.get('current_district', '')
                    
                    # 메인 진행률 바 (progress_manager 기반)
                    st.progress(progress_percent / 100, text=f"전체 진행률: {progress_percent:.1f}% ({current_collected}/{total_target}개)")
                    
                    # 상세 진행 정보 (하이브리드와 동일한 레이아웃)
                    api_col1, api_col2 = st.columns(2)
                    
                    with api_col1:
                        st.metric(
                            "📍 현재 지역", 
                            current_district or '수집 중...',
                            f"{current_progress.get('district_index', 0) + 1}/{current_progress.get('total_districts', 0)}"
                        )
                    
                    with api_col2:
                        st.metric(
                            "🏠 수집된 매물", 
                            f"{current_collected:,}개",
                            f"목표: {total_target:,}개"
                        )
                    
                    # 현재 상태 (progress_manager에서)
                    current_step = current_progress.get('current_step', '진행 중...')
                    st.info(f"🔄 {current_step}")
                    
                else:
                    # 폴백: session_state 기반 진행률
                    api_progress = st.session_state.get('api_collection_progress', 0)
                    api_status = st.session_state.get('api_collection_status', '대기 중...')
                    st.progress(api_progress / 100, text=f"진행률: {api_progress}%")
                    st.info(f"🔄 {api_status}")
                    
            except:
                # 오류 시 폴백: session_state 기반 진행률
                api_progress = st.session_state.get('api_collection_progress', 0)
                api_status = st.session_state.get('api_collection_status', '대기 중...')
                st.progress(api_progress / 100, text=f"진행률: {api_progress}%")
                st.info(f"🔄 {api_status}")
            
            # API 수집 파라미터 표시
            api_params = st.session_state.get('api_collection_params', {})
            if api_params:
                with st.expander("🔧 API 수집 파라미터"):
                    st.json(api_params)
            
            # API 수집 완료 시 결과 표시
            api_progress = st.session_state.get('api_collection_progress', 0)
            if api_progress >= 100:
                st.success("✅ API 전용 수집이 완료되었습니다!")
                
                if st.button("🔄 API 진행률 초기화", key="reset_api_progress"):
                    st.session_state.api_collection_started = False
                    st.session_state.api_collection_progress = 0
                    st.session_state.api_collection_status = ""
                    # progress_manager도 초기화
                    try:
                        progress_manager = get_progress_manager()
                        progress_manager.reset_progress()
                    except:
                        pass
                    st.rerun()
                    
        else:
            st.info("⚡ 필터 조건을 설정하고 'API 전용 수집 시작'을 눌러주세요")
            
            # 조건 유효성 검사 메시지
            if not conditions_valid:
                if len(districts) == 0:
                    st.warning("📍 최소 1개 지역을 선택해주세요")
                for error in validation_errors:
                    st.error(error.replace("⚠️ ", ""))

def tab_advanced_collection():
    """Tab 2: 🔍 상세수집"""
    st.header("🔍 상세 수집")
    st.warning("🚧 2차 구현 예정 - 향후 업데이트")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("📝 **향후 추가 기능**")
        st.write("- 층수별 세부 필터링")
        st.write("- 주차/역세권 정보 수집") 
        st.write("- 개별 매물 상세 분석")
        st.write("- 커스텀 스크래핑 조건")
    
    with col2:
        st.info("🎯 **예상 개발 일정**")
        st.write("- Phase 1: 층수 필터 (1주)")
        st.write("- Phase 2: 부가정보 수집 (2주)")
        st.write("- Phase 3: 고급 분석 (1주)")
    
    # 플레이스홀더 버튼
    st.button("🚧 준비 중...", disabled=True)

def tab_results():
    """Tab 3: 📊 결과"""
    st.header("📊 수집 결과")
    
    # 🎯 DB 중심 시스템: 데이터베이스만 사용
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.info("📊 데이터베이스 중심 시스템 - 모든 데이터는 DB에서 로드됩니다")
    with col2:
        # DB 새로고침
        if st.button("🔄 DB 새로고침"):
            st.cache_data.clear()
            st.rerun()
    with col3:
        # DB → CSV 내보내기 (백업용)
        if st.button("📥 CSV 백업"):
            try:
                from modules.data_processor import PropertyDataProcessor
                processor = PropertyDataProcessor()
                db_df = processor.get_all_properties_from_db()
                if not db_df.empty:
                    csv_data = db_df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        "💾 백업 CSV 다운로드",
                        csv_data,
                        f"backup_properties_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        "text/csv"
                    )
                else:
                    st.warning("⚠️ DB가 비어있습니다")
            except Exception as e:
                st.error(f"❌ 백업 실패: {e}")
    
    # 🔍 DB 상태 디버그 정보
    with st.expander("🔍 디버그 정보"):
        try:
            from modules.data_processor import PropertyDataProcessor
            processor = PropertyDataProcessor()
            db_count = processor.get_properties_count()
            st.write(f"📊 실제 DB 매물 수: {db_count}개")
            
            if db_count > 0:
                # 샘플 데이터 표시
                import sqlite3
                conn = sqlite3.connect('data/properties.db')
                sample_df = pd.read_sql_query('SELECT district, building_name, deposit, monthly_rent FROM properties LIMIT 3', conn)
                conn.close()
                st.write("📋 샘플 데이터:")
                st.dataframe(sample_df)
        except Exception as e:
            st.error(f"❌ DB 디버그 오류: {e}")
    
    # 데이터 로드 (DB만 사용)
    df = load_database_data()
    
    if df.empty:
        st.info("📭 아직 수집된 매물이 없습니다. '수집' 탭에서 데이터를 수집해주세요.")
        return
    
    # 🔍 깔끔한 필터 섹션
    st.subheader("🔍 결과 필터링")
    
    # 지역 선택 (최상단)
    filter_districts = st.multiselect(
        "📍 지역 선택", 
        options=sorted(df['district'].unique()),
        default=sorted(df['district'].unique()),
        help="표시할 지역을 선택하세요"
    )
    
    # 3개 컬럼으로 필터 정리
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 💰 보증금 범위
        st.markdown("**💰 보증금 범위**")
        filter_deposit_min = st.number_input(
            "최소", min_value=0, max_value=10000, value=0, step=100,
            key="filter_deposit_min"
        )
        filter_deposit_max = st.number_input(
            "최대", min_value=0, max_value=10000, value=10000, step=100,
            key="filter_deposit_max"
        )
    
    with col2:
        # 🏠 월세 범위
        st.markdown("**🏠 월세 범위**")
        filter_rent_min = st.number_input(
            "최소", min_value=0, max_value=1000, value=0, step=10,
            key="filter_rent_min"
        )
        filter_rent_max = st.number_input(
            "최대", min_value=0, max_value=1000, value=1000, step=10,
            key="filter_rent_max"
        )
    
    with col3:
        # 🏢 층수 범위 (새로 추가)
        st.markdown("**🏢 층수 범위**")
        filter_floor_min = st.number_input(
            "최소 층", min_value=-5, max_value=50, value=-1, step=1,
            key="filter_floor_min",
            help="지하층: 음수 (예: 지하1층 = -1) | 0층: 건물 전체 임대"
        )
        filter_floor_max = st.number_input(
            "최대 층", min_value=-5, max_value=50, value=10, step=1,
            key="filter_floor_max"
        )
        
        # 0층 설명 추가
        include_whole_building = st.checkbox("0층 포함 (건물 전체 임대)", value=True, key="include_whole_building")
        if include_whole_building:
            st.caption("💡 0층은 건물 전체 임대 매물입니다")
        else:
            st.caption("ℹ️ 0층(건물 전체) 제외됨")
    
    # 면적 범위 (전용면적 기준)
    st.markdown("**📐 면적 범위 (전용면적 기준)**")
    col4, col5 = st.columns(2)
    with col4:
        filter_area_min = st.number_input(
            "최소 평 (전용면적)", min_value=0.0, max_value=200.0, value=20.0, step=1.0,
            key="filter_area_min"
        )
    with col5:
        filter_area_max = st.number_input(
            "최대 평 (전용면적)", min_value=0.0, max_value=200.0, value=100.0, step=1.0,
            key="filter_area_max"
        )
    
    # 🎯 개선된 필터 적용 (층수 포함)
    filtered_df = apply_enhanced_filters(
        df, 
        districts=filter_districts,
        deposit_range=(filter_deposit_min, filter_deposit_max),
        rent_range=(filter_rent_min, filter_rent_max),
        floor_range=(filter_floor_min, filter_floor_max),
        area_range=(filter_area_min, filter_area_max),
        include_whole_building=include_whole_building
    )
    
    # 필터 결과 표시
    st.success(f"🎯 필터 적용 후: **{len(filtered_df):,}개** 매물 (전체 {len(df):,}개 중)")
    
    # 📋 필터링된 데이터 테이블 표시
    if len(filtered_df) > 0:
        # 🎯 동적 컬럼 표시 (필터 결과에 맞게)
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"📋 필터 결과 ({len(filtered_df):,}개 매물)")
        with col2:
            # 표시 모드 선택
            display_mode = st.selectbox(
                "표시 모드",
                ["전체 컬럼", "핵심 컬럼만"],
                key="display_mode"
            )
        
        st.info("💡 좌우 스크롤하여 모든 데이터를 확인할 수 있습니다")
        
        # DB 컬럼 순서대로 정렬 (46개 전체)
        db_column_order = [
            'id', 'region', 'district', 'building_name', 'full_address',
            'area_sqm', 'area_pyeong', 'exclusive_area_sqm', 'exclusive_area_pyeong', 
            'contract_area_sqm', 'contract_area_pyeong', 'floor', 'total_floors', 'floor_display', 
            'deposit', 'monthly_rent', 'management_fee', 'total_monthly_cost', 'ceiling_height',
            'parking_available', 'near_station', 'build_year', 'naver_link',
            'data_source', 'score', 'labels', 'collected_at', 'raw_text', 'created_at',
            # 추가 컬럼들 (15개)
            'management_fee_from_tags', 'management_fee_to_tags', 'loan_status',
            'build_year_from_tags', 'build_year_to_tags', 'station_distance', 'station_name',
            'facilities', 'usage_type', 'conditions', 'price_quality',
            'broker_name', 'broker_company', 'floor_detail', 'parking_available_from_tags'
        ]
        
        # 표시 모드에 따른 컬럼 선택
        if display_mode == "핵심 컬럼만":
            # 핵심 컬럼만 선택 (사용자 친화적)
            core_columns = [
                'id', 'district', 'deposit', 'monthly_rent', 'area_pyeong', 
                'floor_display', 'building_name', 'data_source', 'naver_link', 'collected_at'
            ]
            selected_order = core_columns
            st.caption("📌 핵심 10개 컬럼만 표시")
        else:
            # 전체 42개 컬럼
            selected_order = db_column_order
            st.caption("📌 전체 42개 컬럼 표시")
        
        # 실제 존재하는 컬럼만 선택
        available_columns = [col for col in selected_order if col in filtered_df.columns]
        missing_columns = [col for col in selected_order if col not in filtered_df.columns]
        
        if missing_columns:
            st.caption(f"⚠️ 누락된 컬럼: {', '.join(missing_columns)}")
        
        # 한글 컬럼명 매핑 (46개 전체)
        column_config = {
            'id': st.column_config.NumberColumn('ID', width="small"),
            'region': '지역',
            'district': '구/군',
            'building_name': '건물명',
            'full_address': '주소',
            'area_sqm': st.column_config.NumberColumn('면적(㎡)', format="%.1f"),
            'area_pyeong': st.column_config.NumberColumn('면적(평)', format="%.1f"),
            'exclusive_area_sqm': st.column_config.NumberColumn('전용면적(㎡)', format="%.1f"),
            'exclusive_area_pyeong': st.column_config.NumberColumn('전용면적(평)', format="%.1f"),
            'contract_area_sqm': st.column_config.NumberColumn('계약면적(㎡)', format="%.1f"),
            'contract_area_pyeong': st.column_config.NumberColumn('계약면적(평)', format="%.1f"),
            'floor': st.column_config.NumberColumn('층수'),
            'total_floors': st.column_config.NumberColumn('총층수'),
            'floor_display': '층수정보',
            'deposit': st.column_config.NumberColumn('보증금(만원)', format="%d"),
            'monthly_rent': st.column_config.NumberColumn('월세(만원)', format="%d"),
            'management_fee': st.column_config.NumberColumn('관리비(만원)', format="%d"),
            'total_monthly_cost': st.column_config.NumberColumn('총월비용(만원)', format="%.1f"),
            'ceiling_height': st.column_config.NumberColumn('천장높이(m)', format="%.1f"),
            'parking_available': st.column_config.CheckboxColumn('주차가능'),
            'near_station': st.column_config.CheckboxColumn('역세권'),
            'build_year': st.column_config.NumberColumn('건축년도'),
            'naver_link': st.column_config.LinkColumn('네이버링크'),
            'data_source': '매물유형',
            'score': st.column_config.NumberColumn('점수'),
            'labels': '라벨',
            'collected_at': st.column_config.DatetimeColumn('수집일시'),
            'raw_text': st.column_config.TextColumn('원시데이터', width="large"),
            'created_at': st.column_config.DatetimeColumn('생성일시'),
            # 추가 컬럼들 (15개)
            'management_fee_from_tags': st.column_config.NumberColumn('관리비(태그)하한'),
            'management_fee_to_tags': st.column_config.NumberColumn('관리비(태그)상한'),
            'loan_status': '융자금상태',
            'build_year_from_tags': st.column_config.NumberColumn('건물연식(태그)하한'),
            'build_year_to_tags': st.column_config.NumberColumn('건물연식(태그)상한'),
            'station_distance': st.column_config.NumberColumn('역거리(분)'),
            'station_name': '역명',
            'facilities': '시설',
            'usage_type': '용도',
            'conditions': '조건',
            'price_quality': '가격품질',
            'broker_name': '중개사명',
            'broker_company': '중개사법인',
            'floor_detail': '층수상세',
            'parking_available_from_tags': st.column_config.CheckboxColumn('주차가능(태그)')
        }
        
        # 컬럼 개수 표시
        total_possible = len(db_column_order) if display_mode == "전체 컬럼" else len(core_columns)
        st.caption(f"📊 표시 컬럼: {len(available_columns)}개 / 선택된 {total_possible}개 / DB 전체 {len(db_column_order)}개")
        
        # 전체 데이터프레임 표시 (가로 스크롤)
        st.dataframe(
            filtered_df[available_columns],
            height=400,  # 세로 스크롤 지원
            column_config=column_config,
            use_container_width=True,  # 가로 너비 꽉 차게
            hide_index=True  # 인덱스 숨김
        )

        # 추가: 모든 컬럼을 볼 수 있는 HTML 테이블 (필요시)
        with st.expander("📋 전체 컬럼 HTML 뷰 (개발용)"):
            # HTML로 모든 컬럼 표시
            html_table = filtered_df[available_columns].to_html(
                index=False,
                classes="table table-striped",
                justify="left",
                table_id="full_property_table"
            )

            # CSS 스타일 추가
            st.markdown("""
            <style>
            #full_property_table {
                width: 100%;
                font-size: 12px;
                border-collapse: collapse;
            }
            #full_property_table th, #full_property_table td {
                padding: 4px 8px;
                border: 1px solid #ddd;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                max-width: 120px;
            }
            #full_property_table th {
                background-color: #f8f9fa;
                position: sticky;
                top: 0;
                z-index: 1;
            }
            </style>
            """, unsafe_allow_html=True)

            st.markdown(html_table, unsafe_allow_html=True)
        
        # 다운로드 버튼
        csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            "📥 CSV 다운로드", 
            data=csv, 
            file_name=f"매물검색결과_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("🔍 필터 조건에 맞는 매물이 없습니다.")
        st.info("💡 필터 조건을 완화하거나 다른 지역을 선택해보세요.")

def tab_statistics():
    """Tab 4: 📈 통계"""
    st.header("📈 통계 대시보드")
    
    # 데이터 로드
    df = load_property_data()
    
    if df.empty:
        st.info("📊 통계를 보려면 먼저 데이터를 수집해주세요.")
        return
    
    # 상단 메트릭
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric(
        "총 매물수", 
        f"{len(df):,}개",
        delta=f"+{len(df)}" if st.session_state.get('prev_count', 0) > 0 else None
    )
    
    if 'deposit' in df.columns:
        col2.metric(
            "평균 보증금", 
            f"{df['deposit'].mean():.0f}만원",
            delta=f"{df['deposit'].std():.0f} (표준편차)"
        )
    
    if 'monthly_rent' in df.columns:
        col3.metric(
            "평균 월세", 
            f"{df['monthly_rent'].mean():.0f}만원",
            delta=f"최저 {df['monthly_rent'].min():.0f}만원"
        )
    
    if 'area_pyeong' in df.columns:
        col4.metric(
            "평균 면적", 
            f"{df['area_pyeong'].mean():.1f}평",
            delta=f"최대 {df['area_pyeong'].max():.1f}평"
        )
    
    # 차트 영역
    col1, col2 = st.columns(2)
    
    with col1:
        # 지역별 매물 수
        if 'district' in df.columns:
            district_counts = df['district'].value_counts()
            fig1 = px.bar(
                x=district_counts.values, 
                y=district_counts.index,
                orientation='h',
                title="📍 지역별 매물 수",
                labels={'x': '매물 수', 'y': '지역'}
            )
            st.plotly_chart(fig1, width='stretch')
        
    with col2:
        # 가격 분포
        if 'deposit' in df.columns and 'monthly_rent' in df.columns:
            fig2 = px.scatter(
                df, 
                x='deposit', 
                y='monthly_rent',
                color='district' if 'district' in df.columns else None,
                size='area_pyeong' if 'area_pyeong' in df.columns else None,
                title="💰 보증금 vs 월세 분포",
                labels={'deposit': '보증금(만원)', 'monthly_rent': '월세(만원)'}
            )
            st.plotly_chart(fig2, width='stretch')
    
    # 하단 차트
    col1, col2 = st.columns(2)
    
    with col1:
        # 면적별 가격 관계
        if 'district' in df.columns and 'area_pyeong' in df.columns:
            fig3 = px.box(
                df, 
                x='district', 
                y='area_pyeong',
                title="📐 지역별 면적 분포"
            )
            fig3.update_xaxes(tickangle=45)
            st.plotly_chart(fig3, width='stretch')
        
    with col2:
        # 조건 부합률
        compliance_data = calculate_compliance_rate(df)
        fig4 = px.pie(
            values=list(compliance_data.values()),
            names=list(compliance_data.keys()),
            title="🎯 조건.md 부합률"
        )
        st.plotly_chart(fig4, width='stretch')

def main():
    """메인 함수"""
    # 메인 헤더
    st.markdown('<h1 class="main-header">🏢 부동산 매물 수집 & 분석 시스템</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("💼 **상가·사무실 전문**")
    with col2:
        st.info("📊 **동적 필터링**")
    with col3:
        st.info("🎯 **범위 설정**")
    
    # 4개 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs(["🚀 수집", "🔍 상세수집", "📊 결과", "📈 통계"])
    
    with tab1:
        tab_collection()
    
    with tab2:
        tab_advanced_collection()
    
    with tab3:
        tab_results()
    
    with tab4:
        tab_statistics()
    
    # 푸터
    st.markdown("---")
    st.markdown("💡 **Tip**: PRD v2.1 구현 - 범위 필터 시스템으로 정확한 조건 설정이 가능합니다!")

if __name__ == "__main__":
    main()