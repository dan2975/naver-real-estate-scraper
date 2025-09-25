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

def apply_range_filters(df, districts=None, deposit_range=None, rent_range=None, area_range=None):
    """범위 필터 적용 함수"""
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
    
    # 면적 범위
    if area_range and 'area_pyeong' in filtered.columns:
        filtered = filtered[
            (filtered['area_pyeong'] >= area_range[0]) &
            (filtered['area_pyeong'] <= area_range[1])
        ]
    
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
    """백그라운드에서 수집 실행"""
    try:
        st.session_state.collection_status = "🚀 수집 시스템 시작..."
        st.session_state.collection_progress = 10
        
        # district_collector 임포트 및 실행
        from district_collector import run_streamlit_collection_sync
        
        st.session_state.collection_status = "📍 지역 설정 중..."
        st.session_state.collection_progress = 20
        
        # 실제 수집 실행
        properties = run_streamlit_collection_sync(params)
        
        st.session_state.collection_progress = 100
        
        if properties and len(properties) > 0:
            st.session_state.collection_status = f"✅ 수집 완료! {len(properties)}개 매물 수집됨"
        else:
            st.session_state.collection_status = "⚠️ 수집 완료되었으나 조건에 맞는 매물이 없습니다"
            
    except Exception as e:
        st.session_state.collection_status = f"❌ 수집 오류: {str(e)}"
        st.session_state.collection_progress = 0

def tab_collection():
    """Tab 1: 🚀 수집"""
    st.header("🚀 매물 수집")
    
    # 사이드바 필터
    with st.sidebar:
        st.header("🎯 필터 설정")
        st.info("📝 상가+사무실 월세 전용")
        
        # 지역 선택
        districts = st.multiselect(
            "📍 수집 지역", 
            ['강남구', '강서구', '영등포구', '구로구', '마포구', '중구', '종로구', '용산구'],
            default=['강남구'],
            help="수집할 구를 선택하세요"
        )
        
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
        
        # 예상 수집량
        estimated = len(districts) * 400  # 구당 400개 예상
        st.metric("예상 수집량", f"{estimated:,}개")
        
        # 필터 조건 검증
        conditions_valid = (
            len(districts) > 0 and
            deposit_min <= deposit_max and
            rent_min <= rent_max and
            area_min <= area_max
        )
        
        # 수집 버튼
        if st.button(
            "🚀 수집 시작", 
            type="primary", 
            use_container_width=True,
            disabled=not conditions_valid
        ):
            st.session_state.collection_started = True
            st.session_state.collection_params = {
                'districts': districts,
                'deposit_range': (deposit_min, deposit_max),
                'rent_range': (rent_min, rent_max),
                'area_range': (area_min, area_max)
            }
            st.session_state.collection_progress = 0
            st.session_state.collection_status = "수집 시작..."
            
            # 백그라운드 수집 시작
            thread = threading.Thread(
                target=run_collection_in_background, 
                args=(st.session_state.collection_params,)
            )
            thread.start()
            st.experimental_rerun()

    with col2:
        # 수집 상태 및 실시간 로그
        if st.session_state.get('collection_started', False):
            st.success("🚀 수집이 시작되었습니다!")
            
            # 진행률 표시
            progress = st.session_state.get('collection_progress', 0)
            progress_bar = st.progress(progress / 100)
            status_text = st.empty()
            status_text.text(st.session_state.get('collection_status', ''))
            
            # 수집 파라미터 표시
            params = st.session_state.get('collection_params', {})
            with st.expander("🔧 수집 파라미터"):
                st.json(params)
                
        else:
            st.info("🎯 필터 조건을 설정하고 '수집 시작'을 눌러주세요")
            
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
    st.button("🚧 준비 중...", disabled=True, use_container_width=True)

def tab_results():
    """Tab 3: 📊 결과"""
    st.header("📊 수집 결과")
    
    # 데이터 로드
    df = load_property_data()
    
    if df.empty:
        st.info("📭 아직 수집된 매물이 없습니다. '수집' 탭에서 데이터를 수집해주세요.")
        return
    
    # 상단 필터 바 (범위 설정)
    st.subheader("🔍 결과 필터링")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 지역 필터
        filter_districts = st.multiselect(
            "📍 지역 선택", 
            options=sorted(df['district'].unique()),
            default=sorted(df['district'].unique()),
            help="표시할 지역을 선택하세요"
        )
        
        # 보증금 범위 필터
        st.subheader("💰 보증금 범위")
        col1_1, col1_2 = st.columns(2)
        with col1_1:
            filter_deposit_min = st.number_input(
                "최소", min_value=0, max_value=10000, value=0, step=100,
                key="filter_deposit_min"
            )
        with col1_2:
            filter_deposit_max = st.number_input(
                "최대", min_value=0, max_value=10000, value=10000, step=100,
                key="filter_deposit_max"
            )
    
    with col2:
        # 정렬 옵션
        sort_by = st.selectbox(
            "📊 정렬 기준", 
            [
                "보증금 낮은순", "보증금 높은순",
                "월세 낮은순", "월세 높은순", 
                "면적 큰순", "면적 작은순",
                "등록순"
            ]
        )
        
        # 월세 범위 필터
        st.subheader("🏠 월세 범위")
        col2_1, col2_2 = st.columns(2)
        with col2_1:
            filter_rent_min = st.number_input(
                "최소", min_value=0, max_value=1000, value=0, step=10,
                key="filter_rent_min"
            )
        with col2_2:
            filter_rent_max = st.number_input(
                "최대", min_value=0, max_value=1000, value=1000, step=10,
                key="filter_rent_max"
            )
    
    # 면적 범위 필터
    st.subheader("📐 면적 범위")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        filter_area_min = st.number_input(
            "최소 면적 (평)", min_value=0, max_value=200, value=0, step=1,
            key="filter_area_min"
        )
    with col2:
        filter_area_max = st.number_input(
            "최대 면적 (평)", min_value=0, max_value=200, value=200, step=1,
            key="filter_area_max"
        )
    
    # 범위 필터 적용
    filtered_df = apply_range_filters(
        df, 
        districts=filter_districts,
        deposit_range=(filter_deposit_min, filter_deposit_max),
        rent_range=(filter_rent_min, filter_rent_max),
        area_range=(filter_area_min, filter_area_max)
    )
    
    # 정렬 적용
    sorted_df = apply_sorting(filtered_df, sort_by)
    
    with col3:
        st.metric("필터 적용 후", f"{len(sorted_df):,}개")
    
    # 데이터 테이블
    if len(sorted_df) > 0:
        st.success(f"📋 {len(sorted_df):,}개 매물 표시 (전체 {len(df):,}개 중)")
        
        # 표시할 컬럼 선택
        display_columns = ['district', 'deposit', 'monthly_rent', 'area_pyeong']
        if 'naver_link' in sorted_df.columns:
            display_columns.append('naver_link')
        
        # 컬럼 설정
        column_config = {
            'district': '지역',
            'deposit': '보증금(만원)',
            'monthly_rent': '월세(만원)', 
            'area_pyeong': '면적(평)',
        }
        
        if 'naver_link' in display_columns:
            column_config['naver_link'] = st.column_config.LinkColumn('네이버링크')
        
        # 데이터프레임 표시
        st.dataframe(
            sorted_df[display_columns], 
            use_container_width=True,
            column_config=column_config
        )
        
        # 다운로드 버튼
        csv = sorted_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            "📥 CSV 다운로드", 
            data=csv, 
            file_name=f"매물검색결과_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("🔍 필터 조건에 맞는 매물이 없습니다. 조건을 완화해보세요.")

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
            st.plotly_chart(fig1, use_container_width=True)
        
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
            st.plotly_chart(fig2, use_container_width=True)
    
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
            fig3.update_xaxis(tickangle=45)
            st.plotly_chart(fig3, use_container_width=True)
        
    with col2:
        # 조건 부합률
        compliance_data = calculate_compliance_rate(df)
        fig4 = px.pie(
            values=list(compliance_data.values()),
            names=list(compliance_data.keys()),
            title="🎯 조건.md 부합률"
        )
        st.plotly_chart(fig4, use_container_width=True)

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