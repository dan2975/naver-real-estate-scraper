#!/usr/bin/env python3
"""
부동산 매물 필터링 및 분석 Streamlit 앱
- 기존 CSV 데이터 사용
- 조건.md 기반 동적 필터링
- 구별/동별 필터링
- 정렬 기능
- 실시간 통계
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# 페이지 설정
st.set_page_config(
    page_title="부동산 매물 분석 시스템",
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
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_property_data():
    """매물 데이터 로드 및 전처리"""
    try:
        # 최신 CSV 파일 자동 선택
        import glob
        csv_files = glob.glob('*_properties_*.csv')
        if csv_files:
            latest_csv = max(csv_files, key=lambda x: os.path.getmtime(x))
            print(f"📄 최신 CSV 파일 로드: {latest_csv}")
        else:
            latest_csv = 'naver_commercial_properties_20250925_004134.csv'  # 기본값
        
        df = pd.read_csv(latest_csv)
        
        # 데이터 정리
        df = df.fillna('')
        
        # 숫자 컬럼 확인
        numeric_columns = ['area_pyeong', 'area_sqm', 'floor', 'deposit', 'monthly_rent', 'management_fee', 'total_monthly_cost', 'score']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # district 컬럼이 없으면 생성
        if 'district' not in df.columns:
            df['district'] = '기타'
        
        # 불린 컬럼 처리
        if 'parking_available' in df.columns:
            df['parking_available'] = df['parking_available'].astype(bool)
        if 'near_station' in df.columns:
            df['near_station'] = df['near_station'].astype(bool)
            
        return df
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return pd.DataFrame()

def display_main_header():
    """메인 헤더 표시"""
    st.markdown('<h1 class="main-header">🏢 부동산 매물 분석 시스템</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("💼 **상가·사무실 전문**")
    with col2:
        st.info("📊 **실시간 필터링**")
    with col3:
        st.info("🎯 **조건.md 기반**")

def display_sidebar_filters(df):
    """사이드바 필터 UI"""
    st.sidebar.markdown("## 🔍 매물 필터링")
    
    # 기본 통계
    total_properties = len(df)
    st.sidebar.metric("전체 매물", f"{total_properties:,}개")
    
    if total_properties == 0:
        return {}
    
    # 지역 필터
    st.sidebar.markdown("### 📍 지역 선택")
    available_districts = sorted(df['district'].unique()) if 'district' in df.columns else ['전체']
    selected_districts = st.sidebar.multiselect(
        "구 선택",
        options=available_districts,
        default=available_districts,
        help="원하는 구를 선택하세요"
    )
    
    # 가격 필터
    st.sidebar.markdown("### 💰 가격 조건")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        min_deposit = st.number_input(
            "최소 보증금 (만원)", 
            min_value=0, 
            max_value=int(df['deposit'].max()) if 'deposit' in df.columns else 10000,
            value=0,
            step=100
        )
    with col2:
        max_deposit = st.number_input(
            "최대 보증금 (만원)", 
            min_value=0, 
            max_value=int(df['deposit'].max()) if 'deposit' in df.columns else 10000,
            value=int(df['deposit'].max()) if 'deposit' in df.columns and df['deposit'].max() > 0 else 5000,
            step=100
        )
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        min_monthly = st.number_input(
            "최소 월세 (만원)", 
            min_value=0, 
            max_value=int(df['monthly_rent'].max()) if 'monthly_rent' in df.columns else 1000,
            value=0,
            step=10
        )
    with col2:
        max_monthly = st.number_input(
            "최대 월세 (만원)", 
            min_value=0, 
            max_value=int(df['monthly_rent'].max()) if 'monthly_rent' in df.columns else 1000,
            value=int(df['monthly_rent'].max()) if 'monthly_rent' in df.columns and df['monthly_rent'].max() > 0 else 500,
            step=10
        )
    
    # 면적 필터
    st.sidebar.markdown("### 📐 면적 조건")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        min_area = st.number_input(
            "최소 면적 (평)", 
            min_value=0.0, 
            max_value=float(df['area_pyeong'].max()) if 'area_pyeong' in df.columns else 100.0,
            value=0.0,
            step=1.0
        )
    with col2:
        max_area = st.number_input(
            "최대 면적 (평)", 
            min_value=0.0, 
            max_value=float(df['area_pyeong'].max()) if 'area_pyeong' in df.columns else 100.0,
            value=float(df['area_pyeong'].max()) if 'area_pyeong' in df.columns and df['area_pyeong'].max() > 0 else 100.0,
            step=1.0
        )
    
    # 층수 필터
    st.sidebar.markdown("### 🏢 층수 조건")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        min_floor = st.number_input(
            "최소 층수", 
            min_value=int(df['floor'].min()) if 'floor' in df.columns else -5,
            max_value=int(df['floor'].max()) if 'floor' in df.columns else 50,
            value=int(df['floor'].min()) if 'floor' in df.columns else -1,
            step=1
        )
    with col2:
        max_floor = st.number_input(
            "최대 층수", 
            min_value=int(df['floor'].min()) if 'floor' in df.columns else -5,
            max_value=int(df['floor'].max()) if 'floor' in df.columns else 50,
            value=int(df['floor'].max()) if 'floor' in df.columns and df['floor'].max() > 0 else 20,
            step=1
        )
    
    # 추가 조건
    st.sidebar.markdown("### ➕ 추가 조건")
    parking_required = st.sidebar.checkbox("주차 가능 필수", value=False)
    station_required = st.sidebar.checkbox("역세권 필수", value=False)
    
    # 정렬 옵션
    st.sidebar.markdown("### 📊 정렬 기준")
    sort_options = {
        'deposit': '보증금 낮은순',
        'deposit_desc': '보증금 높은순',
        'monthly_rent': '월세 낮은순',
        'monthly_rent_desc': '월세 높은순',
        'total_monthly_cost': '총 월비용 낮은순',
        'area_pyeong': '면적 작은순',
        'area_pyeong_desc': '면적 큰순',
        'score': '점수 높은순'
    }
    
    selected_sort = st.sidebar.selectbox(
        "정렬 기준",
        options=list(sort_options.keys()),
        format_func=lambda x: sort_options[x],
        index=0
    )
    
    return {
        'districts': selected_districts,
        'min_deposit': min_deposit,
        'max_deposit': max_deposit,
        'min_monthly': min_monthly,
        'max_monthly': max_monthly,
        'min_area': min_area,
        'max_area': max_area,
        'min_floor': min_floor,
        'max_floor': max_floor,
        'parking_required': parking_required,
        'station_required': station_required,
        'sort': selected_sort
    }

def apply_filters(df, filters):
    """필터 적용"""
    if df.empty:
        return df
    
    filtered_df = df.copy()
    
    # 지역 필터
    if filters['districts']:
        filtered_df = filtered_df[filtered_df['district'].isin(filters['districts'])]
    
    # 가격 필터
    if 'deposit' in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df['deposit'] >= filters['min_deposit']) &
            (filtered_df['deposit'] <= filters['max_deposit'])
        ]
    
    if 'monthly_rent' in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df['monthly_rent'] >= filters['min_monthly']) &
            (filtered_df['monthly_rent'] <= filters['max_monthly'])
        ]
    
    # 면적 필터
    if 'area_pyeong' in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df['area_pyeong'] >= filters['min_area']) &
            (filtered_df['area_pyeong'] <= filters['max_area'])
        ]
    
    # 층수 필터
    if 'floor' in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df['floor'] >= filters['min_floor']) &
            (filtered_df['floor'] <= filters['max_floor'])
        ]
    
    # 주차 조건
    if filters['parking_required'] and 'parking_available' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['parking_available'] == True]
    
    # 역세권 조건
    if filters['station_required'] and 'near_station' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['near_station'] == True]
    
    # 정렬 적용
    sort_option = filters['sort']
    if sort_option and not filtered_df.empty:
        if sort_option.endswith('_desc'):
            column = sort_option.replace('_desc', '')
            if column in filtered_df.columns:
                filtered_df = filtered_df.sort_values(column, ascending=False)
        else:
            if sort_option in filtered_df.columns:
                filtered_df = filtered_df.sort_values(sort_option, ascending=True)
    
    return filtered_df

def display_summary_stats(df, filtered_df):
    """요약 통계 표시"""
    st.markdown("## 📊 매물 현황")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="총 매물",
            value=f"{len(df):,}개",
            delta=f"필터링 후: {len(filtered_df):,}개"
        )
    
    if not filtered_df.empty:
        with col2:
            if 'deposit' in filtered_df.columns:
                avg_deposit = filtered_df['deposit'].mean()
                st.metric(
                    label="평균 보증금",
                    value=f"{avg_deposit:,.0f}만원"
                )
        
        with col3:
            if 'monthly_rent' in filtered_df.columns:
                avg_monthly = filtered_df['monthly_rent'].mean()
                st.metric(
                    label="평균 월세",
                    value=f"{avg_monthly:,.0f}만원"
                )
        
        with col4:
            if 'area_pyeong' in filtered_df.columns:
                avg_area = filtered_df['area_pyeong'].mean()
                st.metric(
                    label="평균 면적",
                    value=f"{avg_area:.1f}평"
                )

def display_charts(filtered_df):
    """차트 표시"""
    if filtered_df.empty:
        st.warning("표시할 데이터가 없습니다.")
        return
    
    st.markdown("## 📈 데이터 분석")
    
    col1, col2 = st.columns(2)
    
    # 구별 매물 분포
    with col1:
        if 'district' in filtered_df.columns:
            district_counts = filtered_df['district'].value_counts()
            if not district_counts.empty:
                fig = px.bar(
                    x=district_counts.index,
                    y=district_counts.values,
                    title="구별 매물 분포",
                    labels={'x': '구', 'y': '매물 수'}
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, width='stretch')
    
    # 가격 분포
    with col2:
        if 'monthly_rent' in filtered_df.columns and filtered_df['monthly_rent'].sum() > 0:
            fig = px.histogram(
                filtered_df,
                x='monthly_rent',
                nbins=20,
                title="월세 분포",
                labels={'monthly_rent': '월세 (만원)', 'count': '매물 수'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, width='stretch')

def display_property_table(filtered_df):
    """매물 테이블 표시"""
    if filtered_df.empty:
        st.warning("조건에 맞는 매물이 없습니다.")
        return
    
    st.markdown("## 📋 매물 목록")
    
    # 총 월비용 설명 추가
    st.info("💡 **총 월비용 = 월세 + 관리비** (예: 월세 120만원 + 관리비 24만원 = 총 144만원)")
    
    # 데이터 한계 설명
    st.warning("⚠️ **현재 데이터 한계**: 층고, 상세주소, 부동산 전화번호는 네이버 상세 페이지에서만 확인 가능하며, 대량 수집 시 추가 추출 예정")
    
    # 표시할 컬럼 선택
    display_columns = []
    available_columns = {
        'building_name': '건물명',
        'district': '구',
        'full_address': '주소',
        'area_pyeong': '면적(평)', 
        'area_sqm': '면적(㎡)',
        'floor': '층수',
        'deposit': '보증금(만원)',
        'monthly_rent': '월세(만원)',
        'management_fee': '관리비(만원)',
        'total_monthly_cost': '총월비용(만원)',
        'ceiling_height': '층고(m)',
        'parking_available': '주차',
        'near_station': '역세권',
        'score': '점수',
        'data_source': '출처',
        'naver_link': '링크'
    }
    
    for col, name in available_columns.items():
        if col in filtered_df.columns:
            display_columns.append(col)
    
    if display_columns:
        # 페이지네이션
        items_per_page = st.selectbox("페이지당 표시 개수", [10, 20, 50, 100], index=1)
        total_pages = (len(filtered_df) - 1) // items_per_page + 1
        
        if total_pages > 1:
            page = st.selectbox(f"페이지 (총 {total_pages}페이지)", range(1, total_pages + 1))
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            display_df = filtered_df.iloc[start_idx:end_idx]
        else:
            display_df = filtered_df
        
        # 컬럼명 한글화
        display_df_renamed = display_df[display_columns].copy()
        display_df_renamed.columns = [available_columns.get(col, col) for col in display_columns]
        
        st.dataframe(
            display_df_renamed,
            width='stretch',
            hide_index=True
        )
        
        # CSV 다운로드
        csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 CSV 다운로드",
            data=csv,
            file_name=f"filtered_properties_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

def main():
    """메인 함수"""
    display_main_header()
    
    # 데이터 로드
    df = load_property_data()
    
    if df.empty:
        st.error("데이터를 로드할 수 없습니다. CSV 파일을 확인해주세요.")
        return
    
    # 사이드바 필터
    filters = display_sidebar_filters(df)
    
    # 필터 적용
    filtered_df = apply_filters(df, filters)
    
    # 메인 컨텐츠
    display_summary_stats(df, filtered_df)
    display_charts(filtered_df)
    display_property_table(filtered_df)
    
    # 푸터
    st.markdown("---")
    st.markdown("💡 **Tip**: 사이드바에서 조건을 조정하여 원하는 매물을 찾아보세요!")

if __name__ == "__main__":
    main()
