import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

from data_processor import PropertyDataProcessor
from config import FILTER_CONDITIONS, SCORING_CONDITIONS, REGION_CODES

# 페이지 설정
st.set_page_config(
    page_title="부동산 매물 필터링 시스템",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 사이드바 스타일링
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    
    .filter-section {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 4px solid #ff6b6b;
    }
    
    .score-badge {
        background-color: #4ecdc4;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 1rem;
        font-size: 0.8rem;
        font-weight: bold;
    }
    
    .label-badge {
        background-color: #ffe66d;
        color: #333;
        padding: 0.1rem 0.3rem;
        border-radius: 0.3rem;
        font-size: 0.7rem;
        margin: 0.1rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_and_process_data(property_type="apartment"):
    """데이터 로드 및 처리 (캐싱)"""
    processor = PropertyDataProcessor()
    
    # 기존 데이터가 있으면 로드
    existing_data = processor.load_from_database()
    
    if existing_data.empty:
        if property_type == "apartment":
            st.info("🏠 네이버 부동산에서 아파트 매물 데이터를 스크래핑하고 있습니다...")
        else:
            st.info("🏢 네이버 부동산에서 상가 매물 데이터를 스크래핑하고 있습니다...")
        
        st.warning("⚠️ 이 과정은 시간이 걸릴 수 있으며, 네이버 부동산의 봇 차단으로 실패할 수 있습니다.")
        
        # 실제 네이버 부동산 스크래핑
        try:
            # 주요 지역들에서 실제 매물 스크래핑
            target_regions = ['강남구', '서초구', '송파구']
            all_properties = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            if property_type == "apartment":
                # 기존 아파트 스크래퍼 사용
                from naver_scraper import NaverPropertyScraper
                
                for i, region in enumerate(target_regions):
                    status_text.text(f"🏠 {region} 지역 아파트 스크래핑 중...")
                    progress_bar.progress((i) / len(target_regions))
                    
                    scraper = NaverPropertyScraper(headless=False)
                    try:
                        region_data = scraper.search_properties(region, max_results=20)
                        if not region_data.empty:
                            all_properties.append(region_data)
                            st.success(f"✅ {region}: {len(region_data)}개 아파트 수집 성공!")
                        else:
                            st.warning(f"⚠️ {region}: 아파트 수집 실패")
                    finally:
                        scraper.close_browser()
                    
                    progress_bar.progress((i + 1) / len(target_regions))
            
            else:  # property_type == "commercial"
                # 새로운 상가 스크래퍼 사용
                from commercial_filter_scraper import CommercialFilterScraper
                
                status_text.text("🏢 상가 매물 스크래핑 중...")
                progress_bar.progress(0.5)
                
                commercial_scraper = CommercialFilterScraper(headless=False)
                try:
                    commercial_scraper.setup_browser()
                    
                    if commercial_scraper.go_to_commercial_page():
                        commercial_scraper.apply_price_filters()
                        properties = commercial_scraper.scrape_multiple_regions(['강남구', '서초구'])
                        
                        if properties:
                            # DataFrame으로 변환
                            commercial_df = pd.DataFrame(properties)
                            all_properties.append(commercial_df)
                            st.success(f"✅ 총 {len(properties)}개 상가 매물 수집 성공!")
                        else:
                            st.warning("⚠️ 상가 매물 수집 실패")
                finally:
                    commercial_scraper.close_browser()
                
                progress_bar.progress(1.0)
            
            if all_properties:
                naver_data = pd.concat(all_properties, ignore_index=True)
                property_name = "아파트" if property_type == "apartment" else "상가"
                st.success(f"🎉 총 {len(naver_data)}개의 실제 {property_name} 매물 데이터 수집 완료!")
                st.info("💡 진짜 네이버 부동산에서 가져온 실제 데이터입니다!")
                
                processed_data = processor.process_data(naver_df=naver_data)
            else:
                st.error("❌ 모든 지역에서 스크래핑 실패")
                st.info("🤖 네이버 부동산이 봇 탐지를 통해 접근을 차단했을 가능성이 높습니다.")
                st.info("📝 빈 데이터로 시작합니다. 나중에 다시 시도해보세요.")
                return pd.DataFrame()
                
        except Exception as e:
            st.error(f"❌ 스크래핑 오류: {e}")
            st.info("🤖 네이버 부동산 봇 차단 또는 기술적 오류입니다.")
            st.info("📝 빈 데이터로 시작합니다.")
            return pd.DataFrame()
        
        processor.save_to_database(processed_data)
        return processed_data
    else:
        return existing_data

def apply_user_filters(df, filters):
    """사용자 필터 적용"""
    filtered_df = df.copy()
    
    # 지역 필터
    if filters['selected_regions']:
        filtered_df = filtered_df[filtered_df['region'].isin(filters['selected_regions'])]
    
    # 동 필터
    if filters['selected_districts']:
        filtered_df = filtered_df[filtered_df['district'].isin(filters['selected_districts'])]
    
    # 보증금 범위
    filtered_df = filtered_df[
        (filtered_df['deposit'] >= filters['deposit_range'][0]) &
        (filtered_df['deposit'] <= filters['deposit_range'][1])
    ]
    
    # 월세 범위
    filtered_df = filtered_df[
        (filtered_df['monthly_rent'] >= filters['rent_range'][0]) &
        (filtered_df['monthly_rent'] <= filters['rent_range'][1])
    ]
    
    # 면적 범위
    filtered_df = filtered_df[
        (filtered_df['area_sqm'] >= filters['area_range'][0]) &
        (filtered_df['area_sqm'] <= filters['area_range'][1])
    ]
    
    # 층수 범위
    filtered_df = filtered_df[
        (filtered_df['floor'] >= filters['floor_range'][0]) &
        (filtered_df['floor'] <= filters['floor_range'][1])
    ]
    
    # 선택 조건 필터
    if filters['parking_only']:
        filtered_df = filtered_df[filtered_df['parking_available'] == True]
    
    if filters['station_only']:
        filtered_df = filtered_df[filtered_df['near_station'] == True]
    
    if filters['high_ceiling_only']:
        filtered_df = filtered_df[filtered_df['ceiling_height'] >= 2.8]
    
    return filtered_df

def create_sidebar_filters(df):
    """사이드바 필터 생성"""
    st.sidebar.header("🔍 필터 설정")
    
    filters = {}
    
    # 지역 선택
    st.sidebar.subheader("📍 지역 선택")
    available_regions = sorted(df['region'].unique())
    filters['selected_regions'] = st.sidebar.multiselect(
        "구 선택",
        options=available_regions,
        default=available_regions[:3]
    )
    
    # 동 선택 (선택된 지역에 따라 동적 업데이트)
    if filters['selected_regions']:
        available_districts = sorted(
            df[df['region'].isin(filters['selected_regions'])]['district'].unique()
        )
        filters['selected_districts'] = st.sidebar.multiselect(
            "동 선택",
            options=available_districts,
            default=[]
        )
    else:
        filters['selected_districts'] = []
    
    st.sidebar.divider()
    
    # 가격 필터
    st.sidebar.subheader("💰 가격 조건")
    
    # 보증금 범위
    deposit_min, deposit_max = int(df['deposit'].min()), int(df['deposit'].max())
    # 데이터가 비어있을 경우 기본값 설정
    if deposit_min == deposit_max == 0:
        deposit_min, deposit_max = 0, 5000
    filters['deposit_range'] = st.sidebar.slider(
        "보증금 (만원)",
        min_value=deposit_min,
        max_value=max(deposit_max, 5000),  # 최소 5000으로 설정
        value=(deposit_min, min(max(deposit_max, 5000), FILTER_CONDITIONS['deposit_max'])),
        step=100
    )
    
    # 월세 범위
    rent_min, rent_max = int(df['monthly_rent'].min()), int(df['monthly_rent'].max())
    # 데이터가 비어있을 경우 기본값 설정
    if rent_min == rent_max == 0:
        rent_min, rent_max = 0, 300
    filters['rent_range'] = st.sidebar.slider(
        "월세 (만원)",
        min_value=rent_min,
        max_value=max(rent_max, 300),  # 최소 300으로 설정
        value=(rent_min, min(max(rent_max, 300), FILTER_CONDITIONS['monthly_rent_max'])),
        step=10
    )
    
    st.sidebar.divider()
    
    # 물리적 조건
    st.sidebar.subheader("🏠 물리적 조건")
    
    # 면적 범위
    area_min, area_max = int(df['area_sqm'].min()), int(df['area_sqm'].max())
    # 데이터가 비어있을 경우 기본값 설정
    if area_min == area_max == 0:
        area_min, area_max = 20, 200
    filters['area_range'] = st.sidebar.slider(
        "면적 (㎡)",
        min_value=min(area_min, 20),
        max_value=max(area_max, 200),  # 최소 200㎡까지 설정
        value=(max(min(area_min, 20), FILTER_CONDITIONS['area_min']), max(area_max, 200)),
        step=5
    )
    
    # 층수 범위
    floor_min, floor_max = int(df['floor'].min()), int(df['floor'].max())
    # 데이터가 비어있을 경우 기본값 설정
    if floor_min == floor_max == 0:
        floor_min, floor_max = -1, 20
    filters['floor_range'] = st.sidebar.slider(
        "층수",
        min_value=min(floor_min, -1),
        max_value=max(floor_max, 20),  # 최소 20층까지 설정
        value=(max(min(floor_min, -1), FILTER_CONDITIONS['floor_min']), 
               min(max(floor_max, 20), FILTER_CONDITIONS['floor_max'])),
        step=1
    )
    
    st.sidebar.divider()
    
    # 선택 조건 (점수 조건)
    st.sidebar.subheader("⭐ 선택 조건")
    
    filters['parking_only'] = st.sidebar.checkbox("주차 가능만 보기 🚗")
    filters['station_only'] = st.sidebar.checkbox("역세권만 보기 🚇")
    filters['high_ceiling_only'] = st.sidebar.checkbox("층고 2.8m 이상만 보기 📏")
    
    return filters

def display_summary_metrics(df):
    """요약 통계 표시"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="총 매물 수",
            value=f"{len(df):,}건",
            delta=None
        )
    
    with col2:
        avg_deposit = df['deposit'].mean()
        st.metric(
            label="평균 보증금",
            value=f"{avg_deposit:,.0f}만원",
            delta=None
        )
    
    with col3:
        avg_rent = df['monthly_rent'].mean()
        st.metric(
            label="평균 월세",
            value=f"{avg_rent:,.0f}만원",
            delta=None
        )
    
    with col4:
        avg_score = df['score'].mean()
        st.metric(
            label="평균 점수",
            value=f"{avg_score:.1f}점",
            delta=None
        )

def display_data_table(df, sort_by):
    """데이터 테이블 표시"""
    # 정렬
    if sort_by == "보증금 (낮은순)":
        df_sorted = df.sort_values('deposit', ascending=True)
    elif sort_by == "보증금 (높은순)":
        df_sorted = df.sort_values('deposit', ascending=False)
    elif sort_by == "월세 (낮은순)":
        df_sorted = df.sort_values('monthly_rent', ascending=True)
    elif sort_by == "월세 (높은순)":
        df_sorted = df.sort_values('monthly_rent', ascending=False)
    elif sort_by == "점수 (높은순)":
        df_sorted = df.sort_values('score', ascending=False)
    elif sort_by == "면적 (큰순)":
        df_sorted = df.sort_values('area_sqm', ascending=False)
    else:
        df_sorted = df.sort_values('score', ascending=False)
    
    # 표시할 컬럼 선택 및 이름 변경
    display_columns = {
        'region': '지역',
        'district': '동',
        'building_name': '건물명',
        'area_sqm': '면적(㎡)',
        'floor': '층',
        'deposit': '보증금(만원)',
        'monthly_rent': '월세(만원)',
        'management_fee': '관리비(만원)',
        'total_monthly_cost': '총월세(만원)',
        'score': '점수',
        'labels': '특징',
        'naver_link': '링크'
    }
    
    # 총 월세 계산 (없으면 계산)
    if 'total_monthly_cost' not in df_sorted.columns:
        df_sorted['total_monthly_cost'] = (
            df_sorted['monthly_rent'] + df_sorted['management_fee'].fillna(0)
        )
    
    # 표시용 데이터프레임 생성
    display_df = df_sorted.copy()
    
    # 링크를 클릭 가능하게 변환
    if 'naver_link' in display_df.columns:
        display_df['naver_link'] = display_df['naver_link'].apply(
            lambda x: f'<a href="{x}" target="_blank">🔗 보기</a>' if pd.notna(x) else ''
        )
    
    # 컬럼 이름 변경
    display_df = display_df[list(display_columns.keys())].rename(columns=display_columns)
    
    # 숫자 포맷팅
    for col in ['면적(㎡)', '보증금(만원)', '월세(만원)', '관리비(만원)', '총월세(만원)']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
    
    # 점수 포맷팅
    if '점수' in display_df.columns:
        display_df['점수'] = display_df['점수'].apply(lambda x: f"⭐ {x:,.0f}" if x > 0 else "0")
    
    # 테이블 표시
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "링크": st.column_config.LinkColumn(
                "네이버 부동산",
                help="네이버 부동산에서 보기",
                width="small"
            ),
            "특징": st.column_config.TextColumn(
                "특징",
                help="주차, 역세권, 층고 등 추가 조건",
                width="medium"
            )
        }
    )

def create_charts(df):
    """차트 생성"""
    col1, col2 = st.columns(2)
    
    with col1:
        # 지역별 매물 수
        region_counts = df['region'].value_counts()
        fig_region = px.bar(
            x=region_counts.values,
            y=region_counts.index,
            orientation='h',
            title="지역별 매물 수",
            labels={'x': '매물 수', 'y': '지역'}
        )
        fig_region.update_layout(height=400)
        st.plotly_chart(fig_region, use_container_width=True)
    
    with col2:
        # 보증금 vs 월세 산점도
        fig_scatter = px.scatter(
            df,
            x='deposit',
            y='monthly_rent',
            color='score',
            size='area_sqm',
            hover_data=['region', 'district', 'building_name'],
            title="보증금 vs 월세 (점수별)",
            labels={'deposit': '보증금(만원)', 'monthly_rent': '월세(만원)', 'score': '점수'}
        )
        fig_scatter.update_layout(height=400)
        st.plotly_chart(fig_scatter, use_container_width=True)

def main():
    """메인 애플리케이션"""
    st.title("🏠 부동산 매물 필터링 시스템")
    st.markdown("### 조건에 맞는 매물을 찾아보세요!")
    
    # 매물 타입 선택
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        property_type = st.selectbox(
            "🏘️ 매물 타입",
            options=["apartment", "commercial"],
            format_func=lambda x: "🏠 아파트" if x == "apartment" else "🏢 상가/오피스텔",
            index=0
        )
    
    with col2:
        if st.button("🔄 새로 스크래핑", help="기존 데이터를 삭제하고 새로 스크래핑합니다"):
            st.cache_data.clear()  # 캐시 삭제
            # 데이터베이스 파일도 삭제
            import os
            db_path = 'data/properties.db'
            if os.path.exists(db_path):
                os.remove(db_path)
                st.success("✅ 기존 데이터 삭제 완료! 페이지를 새로고침해주세요.")
                st.rerun()
    
    with col3:
        # 조건 요약 표시
        if property_type == "apartment":
            st.info("📋 **아파트 조건**: 보증금 2000만원↓, 월세 130만원↓, 지하1층~지상2층, 20평(66㎡)↑")
        else:
            st.info("📋 **상가 조건**: 보증금 2000만원↓, 월세 130만원↓, 지하1층~지상2층, 20평(66㎡)↑")
    
    # 데이터 로드
    with st.spinner("데이터를 불러오는 중..."):
        df = load_and_process_data(property_type)
    
    if df.empty:
        st.error("데이터를 불러올 수 없습니다.")
        return
    
    # 사이드바 필터
    filters = create_sidebar_filters(df)
    
    # 필터 적용
    filtered_df = apply_user_filters(df, filters)
    
    # 메인 컨텐츠
    if filtered_df.empty:
        st.warning("조건에 맞는 매물이 없습니다. 필터 조건을 조정해보세요.")
        return
    
    # 요약 통계
    display_summary_metrics(filtered_df)
    
    st.divider()
    
    # 정렬 옵션
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📋 매물 목록")
    
    with col2:
        sort_options = [
            "점수 (높은순)",
            "보증금 (낮은순)",
            "보증금 (높은순)",
            "월세 (낮은순)",
            "월세 (높은순)",
            "면적 (큰순)"
        ]
        sort_by = st.selectbox("정렬 기준", sort_options)
    
    # 데이터 테이블
    display_data_table(filtered_df, sort_by)
    
    st.divider()
    
    # 차트
    st.subheader("📊 데이터 분석")
    create_charts(filtered_df)
    
    # 필터 조건 표시
    with st.expander("🔧 현재 필터 조건"):
        st.json({
            "선택 지역": filters['selected_regions'],
            "선택 동": filters['selected_districts'],
            "보증금 범위": f"{filters['deposit_range'][0]:,}~{filters['deposit_range'][1]:,}만원",
            "월세 범위": f"{filters['rent_range'][0]:,}~{filters['rent_range'][1]:,}만원",
            "면적 범위": f"{filters['area_range'][0]:,}~{filters['area_range'][1]:,}㎡",
            "층수 범위": f"{filters['floor_range'][0]}~{filters['floor_range'][1]}층",
            "주차 조건": "주차 가능만" if filters['parking_only'] else "전체",
            "역세권 조건": "역세권만" if filters['station_only'] else "전체",
            "층고 조건": "2.8m 이상만" if filters['high_ceiling_only'] else "전체"
        })
    
    # 데이터 새로고침 버튼
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()

if __name__ == "__main__":
    main()
