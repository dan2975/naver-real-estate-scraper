# 📋 Streamlit 동적 필터 시스템 PRD v2.1

## 🎯 핵심 요구사항

### 1. 4개 탭 구조
- **🚀 수집**: 기본 필터 + district_collector 연동
- **🔍 상세수집**: 고급 스크래핑 (2차 구현)  
- **📊 결과**: DB 테이블 뷰 (필터링/정렬)
- **📈 통계**: 시각화 대시보드

### 2. 필터 조건 (최대/최소 범위 설정)
- **매물 타입**: 상가+사무실 (하드코딩)
- **거래 방식**: 월세 (하드코딩)
- **범위 필터**: 보증금, 월세, 면적 (최소~최대)
- **다중 선택**: 지역구 (체크박스)

## 🔧 상세 설계

### Tab 1: 🚀 수집

#### 사이드바 필터 (범위 설정)
```python
# === 사이드바 필터 ===
st.sidebar.header("🎯 필터 설정")
st.sidebar.info("📝 상가+사무실 월세 전용")

# 지역 선택 (다중 선택)
districts = st.sidebar.multiselect(
    "📍 수집 지역", 
    ['강남구', '강서구', '영등포구', '구로구', '마포구', '중구', '종로구', '용산구'],
    default=['강남구'],
    help="수집할 구를 선택하세요"
)

# 보증금 범위 (최소~최대)
st.sidebar.subheader("💰 보증금 조건")
col1, col2 = st.sidebar.columns(2)
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

# 월세 범위 (최소~최대)
st.sidebar.subheader("🏠 월세 조건")
col1, col2 = st.sidebar.columns(2)
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

# 면적 범위 (최소~최대)
st.sidebar.subheader("📐 면적 조건")
col1, col2 = st.sidebar.columns(2)
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
if deposit_min > deposit_max:
    st.sidebar.error("⚠️ 보증금 최소값이 최대값보다 큽니다")
if rent_min > rent_max:
    st.sidebar.error("⚠️ 월세 최소값이 최대값보다 큽니다")
if area_min > area_max:
    st.sidebar.error("⚠️ 면적 최소값이 최대값보다 큽니다")
```

#### 메인 화면
```python
# === 메인 화면 ===
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

with col2:
    # 수집 상태 및 실시간 로그
    if st.session_state.get('collection_started', False):
        st.success("🚀 수집이 시작되었습니다!")
        
        # 진행률 표시
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 실시간 로그
        with st.container():
            log_placeholder = st.empty()
            
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
            if deposit_min > deposit_max:
                st.error("💰 보증금 범위를 올바르게 설정해주세요")
            if rent_min > rent_max:
                st.error("🏠 월세 범위를 올바르게 설정해주세요")
            if area_min > area_max:
                st.error("📐 면적 범위를 올바르게 설정해주세요")
```

### Tab 2: 🔍 상세수집
```python
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
```

### Tab 3: 📊 결과 (범위 필터)
```python
st.header("📊 수집 결과")

# === 상단 필터 바 (범위 설정) ===
st.subheader("🔍 결과 필터링")

col1, col2 = st.columns(2)

with col1:
    # 지역 필터
    filter_districts = st.multiselect(
        "📍 지역 선택", 
        options=sorted(df['district'].unique()) if not df.empty else [],
        default=sorted(df['district'].unique()) if not df.empty else [],
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
with col3:
    st.metric("필터 적용 후", "0개" if df.empty else f"{len(filtered_df):,}개")

# === 데이터 테이블 ===
if not df.empty:
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
    
    if len(sorted_df) > 0:
        st.success(f"📋 {len(sorted_df):,}개 매물 표시 (전체 {len(df):,}개 중)")
        
        # 데이터프레임 표시
        st.dataframe(
            sorted_df[['district', 'deposit', 'monthly_rent', 'area_pyeong', 'naver_link']], 
            use_container_width=True,
            column_config={
                'district': '지역',
                'deposit': '보증금(만원)',
                'monthly_rent': '월세(만원)', 
                'area_pyeong': '면적(평)',
                'naver_link': st.column_config.LinkColumn('네이버링크')
            }
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
        
else:
    st.info("📭 아직 수집된 매물이 없습니다. '수집' 탭에서 데이터를 수집해주세요.")
```

### Tab 4: 📈 통계
```python
st.header("📈 통계 대시보드")

if not df.empty:
    # === 상단 메트릭 ===
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric(
        "총 매물수", 
        f"{len(df):,}개",
        delta=f"+{len(df)}" if st.session_state.get('prev_count', 0) > 0 else None
    )
    
    col2.metric(
        "평균 보증금", 
        f"{df['deposit'].mean():.0f}만원",
        delta=f"{df['deposit'].std():.0f} (표준편차)"
    )
    
    col3.metric(
        "평균 월세", 
        f"{df['monthly_rent'].mean():.0f}만원",
        delta=f"최저 {df['monthly_rent'].min():.0f}만원"
    )
    
    col4.metric(
        "평균 면적", 
        f"{df['area_pyeong'].mean():.1f}평",
        delta=f"최대 {df['area_pyeong'].max():.1f}평"
    )
    
    # === 차트 영역 ===
    col1, col2 = st.columns(2)
    
    with col1:
        # 지역별 매물 수
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
        fig2 = px.scatter(
            df, 
            x='deposit', 
            y='monthly_rent',
            color='district',
            size='area_pyeong',
            title="💰 보증금 vs 월세 분포",
            labels={'deposit': '보증금(만원)', 'monthly_rent': '월세(만원)'}
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # === 하단 차트 ===
    col1, col2 = st.columns(2)
    
    with col1:
        # 면적별 가격 관계
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
            values=compliance_data.values(),
            names=compliance_data.keys(),
            title="🎯 조건.md 부합률"
        )
        st.plotly_chart(fig4, use_container_width=True)
        
else:
    st.info("📊 통계를 보려면 먼저 데이터를 수집해주세요.")
```

## 🏗️ 구현 계획

### Phase 1: 수집 탭 - 범위 필터 (1시간)
```python
# district_collector.py 수정
def run_with_streamlit_params(
    districts, 
    deposit_range, 
    rent_range, 
    area_range
):
    # 하드코딩된 값들
    property_type = 'SG:SMS'  # 상가+사무실
    transaction_type = 'B2'   # 월세
    
    # 범위 조건
    collector.target_districts = districts
    collector.filter_conditions = {
        'min_deposit': deposit_range[0],
        'max_deposit': deposit_range[1],
        'min_monthly_rent': rent_range[0],
        'max_monthly_rent': rent_range[1], 
        'min_area_pyeong': area_range[0],
        'max_area_pyeong': area_range[1]
    }
    
    return collector.run_hybrid_collection()
```

### Phase 2: 결과 탭 - 범위 필터링 (45분)
```python
def apply_range_filters(df, districts, deposit_range, rent_range, area_range):
    """범위 필터 적용 함수"""
    filtered = df.copy()
    
    # 지역 필터
    if districts:
        filtered = filtered[filtered['district'].isin(districts)]
    
    # 보증금 범위
    filtered = filtered[
        (filtered['deposit'] >= deposit_range[0]) &
        (filtered['deposit'] <= deposit_range[1])
    ]
    
    # 월세 범위
    filtered = filtered[
        (filtered['monthly_rent'] >= rent_range[0]) &
        (filtered['monthly_rent'] <= rent_range[1])
    ]
    
    # 면적 범위
    filtered = filtered[
        (filtered['area_pyeong'] >= area_range[0]) &
        (filtered['area_pyeong'] <= area_range[1])
    ]
    
    return filtered
```

### Phase 3: 통계 탭 (30분)
- plotly 차트 4개
- 실시간 메트릭
- 범위 기반 통계 계산

## 📁 수정할 파일들

```
streamlit_property_app.py          # 🔄 범위 필터 UI 구현
district_collector.py              # 🔄 범위 조건 매개변수 추가  
data_processor.py                  # 🔄 범위 필터링 함수 추가
```

## 🎯 핵심 개선사항

1. **범위 설정**: 모든 숫자 조건을 최소~최대 범위로 설정
2. **실시간 검증**: 최소값 > 최대값일 때 에러 메시지 표시
3. **유연한 필터링**: 결과 탭에서도 범위 기반 필터링 지원
4. **직관적 UI**: 2열 레이아웃으로 최소/최대 값 나란히 배치
5. **매물 타입**: 상가+사무실 월세로 하드코딩하여 단순화

## 📊 예상 사용자 시나리오

### 1차 - 조건 설정 및 수집
1. 🚀 수집 탭 선택
2. 사이드바에서 **지역 2-3개 선택**
3. **보증금 범위**: 500~2000만원 설정
4. **월세 범위**: 50~130만원 설정  
5. **면적 범위**: 20~50평 설정
6. 조건 요약 확인 후 "🚀 수집 시작"
7. 실시간 진행상황 확인

### 2차 - 결과 분석  
1. 📊 결과 탭으로 이동
2. **지역별 필터**: 관심 지역만 선택
3. **가격 범위 세분화**: 더 정확한 범위 설정
4. **정렬**: 보증금 낮은순으로 정렬
5. 테이블에서 매물 확인
6. CSV 다운로드

### 3차 - 통계 확인
1. 📈 통계 탭 확인  
2. **전체 현황 메트릭** 확인
3. **지역별 비교 차트** 분석
4. **가격-면적 상관관계** 확인

**이제 사용자가 원하는 범위를 정확하게 설정할 수 있는 시스템이 됩니다!** 🎯
