import pandas as pd
import sqlite3
import os
from datetime import datetime
from config import FILTER_CONDITIONS, SCORING_CONDITIONS, DATABASE
from public_data_api import PublicDataCollector
from naver_scraper import NaverPropertyScraper

class PropertyDataProcessor:
    """부동산 데이터 처리 및 필터링 클래스"""
    
    def __init__(self):
        self.db_path = DATABASE['name']
        self.ensure_data_directory()
        
    def ensure_data_directory(self):
        """데이터 디렉토리 생성"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    def create_tables(self):
        """데이터베이스 테이블 생성"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 매물 정보 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                region TEXT,
                district TEXT,
                building_name TEXT,
                full_address TEXT,
                area_sqm REAL,
                area_pyeong REAL,
                floor INTEGER,
                deposit INTEGER,
                monthly_rent INTEGER,
                management_fee INTEGER,
                total_monthly_cost REAL,
                ceiling_height REAL,
                parking_available BOOLEAN,
                near_station BOOLEAN,
                build_year INTEGER,
                naver_link TEXT,
                data_source TEXT,
                score INTEGER DEFAULT 0,
                labels TEXT,
                collected_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def apply_filters(self, df):
        """필수 조건 필터링 적용"""
        filtered_df = df.copy()
        
        # 보증금 필터
        if 'deposit' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['deposit'] <= FILTER_CONDITIONS['deposit_max']]
        
        # 월세 필터
        if 'monthly_rent' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['monthly_rent'] <= FILTER_CONDITIONS['monthly_rent_max']]
        
        # 관리비 포함 월세 필터
        if 'monthly_rent' in filtered_df.columns and 'management_fee' in filtered_df.columns:
            total_rent = filtered_df['monthly_rent'] + filtered_df['management_fee'].fillna(0)
            filtered_df = filtered_df[total_rent <= FILTER_CONDITIONS['total_rent_max']]
        
        # 층수 필터
        if 'floor' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['floor'] >= FILTER_CONDITIONS['floor_min']) &
                (filtered_df['floor'] <= FILTER_CONDITIONS['floor_max'])
            ]
        
        # 면적 필터
        if 'area_sqm' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['area_sqm'] >= FILTER_CONDITIONS['area_min']]
        
        # 관리비 필터
        if 'management_fee' in filtered_df.columns:
            filtered_df = filtered_df[
                filtered_df['management_fee'].fillna(0) <= FILTER_CONDITIONS['management_fee_max']
            ]
        
        return filtered_df
    
    def calculate_scores(self, df):
        """선택 조건 점수 계산"""
        df = df.copy()
        df['score'] = 0
        
        # 층고 점수
        if 'ceiling_height' in df.columns:
            ceiling_condition = df['ceiling_height'] >= SCORING_CONDITIONS['ceiling_height']['threshold']
            df.loc[ceiling_condition, 'score'] += SCORING_CONDITIONS['ceiling_height']['score']
        
        # 역세권 점수
        if 'near_station' in df.columns:
            station_condition = df['near_station'] == True
            df.loc[station_condition, 'score'] += SCORING_CONDITIONS['near_station']['score']
        
        # 주차 점수 (가장 중요)
        if 'parking_available' in df.columns:
            parking_condition = df['parking_available'] == True
            df.loc[parking_condition, 'score'] += SCORING_CONDITIONS['parking']['score']
        
        return df
    
    def create_labels(self, df):
        """선택 조건 라벨 생성"""
        df = df.copy()
        labels = []
        
        for idx, row in df.iterrows():
            row_labels = []
            
            # 층고 라벨
            if 'ceiling_height' in row and pd.notna(row['ceiling_height']):
                if row['ceiling_height'] >= SCORING_CONDITIONS['ceiling_height']['threshold']:
                    row_labels.append(f"층고 {row['ceiling_height']:.1f}m ⭐")
            
            # 역세권 라벨
            if 'near_station' in row and row['near_station']:
                row_labels.append("역세권 🚇")
            
            # 주차 라벨
            if 'parking_available' in row and row['parking_available']:
                row_labels.append("주차가능 🚗")
            
            labels.append(" | ".join(row_labels) if row_labels else "")
        
        df['labels'] = labels
        return df
    
    def process_data(self, public_df=None, naver_df=None):
        """전체 데이터 처리 파이프라인"""
        print("데이터 처리 시작...")
        
        # 데이터 병합
        if public_df is not None and naver_df is not None:
            # 하이브리드: 공공데이터 + 네이버 부동산
            merged_df = self.merge_data_sources(public_df, naver_df)
        elif public_df is not None:
            merged_df = public_df.copy()
        elif naver_df is not None:
            merged_df = naver_df.copy()
        else:
            # 샘플 데이터 생성
            merged_df = self.generate_sample_data()
        
        print(f"병합된 데이터: {len(merged_df)}건")
        
        # 필수 조건 필터링
        filtered_df = self.apply_filters(merged_df)
        print(f"필터링 후: {len(filtered_df)}건")
        
        # 점수 계산
        scored_df = self.calculate_scores(filtered_df)
        
        # 라벨 생성
        labeled_df = self.create_labels(scored_df)
        
        # 총 월세 계산 (월세 + 관리비)
        if 'monthly_rent' in labeled_df.columns and 'management_fee' in labeled_df.columns:
            labeled_df['total_monthly_cost'] = (
                labeled_df['monthly_rent'] + labeled_df['management_fee'].fillna(0)
            )
        
        print("데이터 처리 완료")
        return labeled_df
    
    def merge_data_sources(self, public_df, naver_df):
        """공공데이터와 네이버 부동산 데이터 병합"""
        # 간단한 병합 로직 (실제로는 주소/건물명 매칭 필요)
        merged_list = []
        
        # 공공데이터 우선 사용
        for idx, row in public_df.iterrows():
            merged_row = row.to_dict()
            
            # 네이버 데이터에서 매칭되는 항목 찾기 (간단한 예시)
            matching_naver = naver_df[
                naver_df['region'] == row.get('region', '')
            ].iloc[0:1] if len(naver_df) > 0 else pd.DataFrame()
            
            if not matching_naver.empty:
                naver_row = matching_naver.iloc[0]
                # 네이버에만 있는 정보 추가
                for col in ['ceiling_height', 'parking_available', 'near_station', 'naver_link']:
                    if col in naver_row:
                        merged_row[col] = naver_row[col]
                merged_row['data_source'] = '공공+네이버'
            
            merged_list.append(merged_row)
        
        # 네이버 전용 데이터 추가
        for idx, row in naver_df.iterrows():
            if row.get('region', '') not in public_df.get('region', pd.Series()).values:
                merged_list.append(row.to_dict())
        
        return pd.DataFrame(merged_list)
    
    def generate_sample_data(self, num_samples=100):
        """샘플 데이터 생성"""
        import random
        
        regions = ['강남구', '서초구', '송파구', '마포구', '용산구']
        districts = ['역삼동', '반포동', '잠실동', '상암동', '한남동'] * 20
        
        sample_data = []
        for i in range(num_samples):
            region = random.choice(regions)
            data = {
                'region': region,
                'district': random.choice(districts),
                'building_name': f'{region} 테스트아파트 {i+1}동',
                'full_address': f'{region} {random.choice(districts)} {i+1}번지',
                'area_sqm': random.randint(60, 120),
                'area_pyeong': random.randint(60, 120) / 3.3058,
                'floor': random.randint(-1, 2),
                'deposit': random.randint(1000, 2500),
                'monthly_rent': random.randint(80, 180),
                'management_fee': random.randint(15, 35),
                'ceiling_height': round(random.uniform(2.6, 3.0), 1),
                'parking_available': random.choice([True, False]),
                'near_station': random.choice([True, False]),
                'build_year': random.randint(2000, 2023),
                'naver_link': f'https://new.land.naver.com/detail/test_{i}',
                'data_source': '샘플데이터',
                'collected_at': datetime.now()
            }
            sample_data.append(data)
        
        return pd.DataFrame(sample_data)
    
    def save_to_database(self, df):
        """데이터베이스에 저장"""
        # 기존 데이터베이스 파일 삭제 (스키마 업데이트를 위해)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            print("기존 데이터베이스 삭제됨")
        
        self.create_tables()
        conn = sqlite3.connect(self.db_path)
        
        # 새 데이터 저장
        df.to_sql('properties', conn, if_exists='append', index=False)
        
        conn.commit()
        conn.close()
        print(f"데이터베이스에 {len(df)}건 저장 완료")
    
    def load_from_database(self):
        """데이터베이스에서 로드"""
        if not os.path.exists(self.db_path):
            return pd.DataFrame()
            
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM properties ORDER BY score DESC, deposit ASC", conn)
        conn.close()
        return df

# 사용 예시
if __name__ == "__main__":
    processor = PropertyDataProcessor()
    
    # 샘플 데이터로 테스트
    sample_data = processor.generate_sample_data(50)
    processed_data = processor.process_data(public_df=sample_data)
    
    print("\n처리된 데이터 샘플:")
    print(processed_data[['region', 'deposit', 'monthly_rent', 'score', 'labels']].head(10))
    
    # 데이터베이스 저장
    processor.save_to_database(processed_data)
    
    # 로드 테스트
    loaded_data = processor.load_from_database()
    print(f"\n로드된 데이터: {len(loaded_data)}건")
