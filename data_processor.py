import pandas as pd
import sqlite3
import os
from datetime import datetime

class PropertyDataProcessor:
    """부동산 데이터 처리 및 필터링 클래스"""
    
    def __init__(self):
        # 기본 설정
        self.db_path = 'data/properties.db'
        self.filter_conditions = {
            'max_deposit': 2000,      # 보증금 2000만원 이하
            'max_monthly_rent': 130,  # 월세 130만원 이하  
            'max_total_monthly': 150, # 총 월비용 150만원 이하
            'min_area_pyeong': 20,    # 20평 이상
            'min_floor': -1,          # 지하1층 이상
            'max_floor': 2,           # 2층 이하
            'max_management_fee': 30  # 관리비 30만원 이하
        }
        
        # 🎯 CSV ↔ DB 컬럼 매핑
        self.csv_to_db_mapping = {
            'district': 'district',
            'property_type': 'data_source',  # property_type을 data_source로 매핑
            'deposit': 'deposit',
            'monthly_rent': 'monthly_rent',
            'area_sqm': 'area_sqm',
            'area_pyeong': 'area_pyeong',
            'floor': 'floor',
            'floor_info': None,  # DB에 저장하지 않음
            'building_name': 'building_name',
            'property_name': None,  # DB에 저장하지 않음
            'full_address': 'full_address',
            'road_address': None,  # DB에 저장하지 않음
            'jibun_address': None,  # DB에 저장하지 않음
            'naver_link': 'naver_link',
            'article_no': None,  # raw_text에 포함
            'raw_data': 'raw_text'
        }
        
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
                total_floors INTEGER,
                floor_display TEXT,
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
                        raw_text TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def csv_to_db_dataframe(self, csv_df: pd.DataFrame) -> pd.DataFrame:
        """🔄 CSV 데이터를 DB 형식으로 변환 (스마트 파싱 포함)"""
        import ast
        import re
        
        db_df = pd.DataFrame()
        
        # 매핑된 컬럼들 변환
        for csv_col, db_col in self.csv_to_db_mapping.items():
            if db_col and csv_col in csv_df.columns:
                db_df[db_col] = csv_df[csv_col]
        
        # 🎯 스마트 데이터 파싱 및 보완
        current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 🏢 층수 정보 개선 (floor_info에서 총 층수 추출)
        if 'floor_info' in csv_df.columns:
            def parse_floor_info(floor_info):
                if pd.isna(floor_info) or floor_info == '':
                    return None, None, None
                
                floor_str = str(floor_info)
                
                # "전체층/15" 패턴
                if '전체층' in floor_str:
                    if '/' in floor_str:
                        total = floor_str.split('/')[1]
                        try:
                            total_floors = int(total)
                            return 0, total_floors, f"전체층 ({total_floors}층 건물)"
                        except:
                            return 0, None, "전체층"
                    else:
                        return 0, None, "전체층"
                
                # "1/4", "B1/5" 등 일반 패턴
                if '/' in floor_str:
                    parts = floor_str.split('/')
                    if len(parts) == 2:
                        current_part = parts[0].strip()
                        total_part = parts[1].strip()
                        
                        try:
                            # 현재 층 파싱
                            if current_part.startswith('B'):
                                current_floor = -int(current_part[1:])  # B1 → -1
                                current_display = f"지하{current_part[1:]}층"
                            else:
                                current_floor = int(current_part)
                                current_display = f"{current_part}층"
                            
                            # 총 층수 파싱
                            total_floors = int(total_part)
                            
                            # 표시용 문자열
                            display = f"{current_display} ({total_floors}층 건물)"
                            
                            return current_floor, total_floors, display
                        except:
                            pass
                
                # 파싱 실패시 기본값
                return None, None, floor_str
            
            # 각 행에 대해 층수 정보 파싱
            floor_data = csv_df['floor_info'].apply(parse_floor_info)
            
            # 결과를 개별 컬럼으로 분리
            db_df['floor'] = [item[0] for item in floor_data]
            db_df['total_floors'] = [item[1] for item in floor_data]
            db_df['floor_display'] = [item[2] for item in floor_data]
        
        # building_name 보완 (property_name 우선 사용, NaN 처리)
        if 'property_name' in csv_df.columns:
            # NaN을 빈 문자열로 변환하여 처리
            property_names = csv_df['property_name'].fillna('')
            building_names = csv_df.get('building_name', pd.Series([''] * len(csv_df))).fillna('')
            db_df['building_name'] = property_names.where(property_names != '', building_names)
        
        # full_address 보완 (road_address -> jibun_address 순서)
        if 'road_address' in csv_df.columns and 'jibun_address' in csv_df.columns:
            db_df['full_address'] = csv_df['road_address'].fillna(csv_df['jibun_address']).fillna('')
        elif 'road_address' in csv_df.columns:
            db_df['full_address'] = csv_df['road_address'].fillna('')
        elif 'jibun_address' in csv_df.columns:
            db_df['full_address'] = csv_df['jibun_address'].fillna('')
        
        # raw_data에서 추가 정보 파싱
        if 'raw_data' in csv_df.columns:
            def parse_raw_data(row):
                try:
                    if pd.isna(row['raw_data']) or row['raw_data'] == '':
                        return row
                    
                    # Python dict 파싱 (JSON이 아님)
                    if isinstance(row['raw_data'], str):
                        import ast
                        raw_data = ast.literal_eval(row['raw_data'])
                    else:
                        raw_data = row['raw_data']
                    
                    # 관리비 파싱 (minMviFee, maxMviFee)
                    min_fee = raw_data.get('minMviFee', 0)
                    max_fee = raw_data.get('maxMviFee', 0)
                    if max_fee > 0:
                        row['management_fee'] = max_fee
                    elif min_fee > 0:
                        row['management_fee'] = min_fee
                    
                    # 건물명 보완 (bildNm)
                    if pd.isna(row.get('building_name', '')) or row.get('building_name', '') == '':
                        row['building_name'] = raw_data.get('bildNm', raw_data.get('atclNm', ''))
                    
                    # 주차 가능 여부 (tagList에서 '주차가능' 찾기)
                    tag_list = raw_data.get('tagList', [])
                    if isinstance(tag_list, list):
                        row['parking_available'] = '주차가능' in tag_list or '주차' in ' '.join(tag_list)
                    
                    # 역세권 여부 (atclFetrDesc에서 '역', '지하철', '분거리' 찾기)
                    desc = raw_data.get('atclFetrDesc', '')
                    if isinstance(desc, str):
                        station_keywords = ['역', '지하철', '분거리', '역세권', '호선']
                        row['near_station'] = any(keyword in desc for keyword in station_keywords)
                    
                    # 🎯 좌표 정보 저장
                    lat = raw_data.get('lat', 0)
                    lng = raw_data.get('lng', 0)
                    if lat and lng:
                        row['lat'] = float(lat)
                        row['lng'] = float(lng)
                    
                    # 상세주소 보완 (dtlAddr 우선, 없으면 지역구 + 좌표 정보)
                    if pd.isna(row.get('full_address', '')) or row.get('full_address', '') == '':
                        dtl_addr = raw_data.get('dtlAddr', '')
                        if dtl_addr:
                            row['full_address'] = dtl_addr
                        else:
                            # 지역구 + 좌표로 대략적 주소 생성
                            district = row.get('district', '')
                            if district and lat and lng:
                                row['full_address'] = f"서울특별시 {district} (위도: {lat}, 경도: {lng})"
                    
                    return row
                except Exception as e:
                    print(f"⚠️ raw_data 파싱 오류: {e}")
                    return row
            
            # 각 행에 대해 raw_data 파싱 적용
            for idx in range(len(csv_df)):
                row_dict = csv_df.iloc[idx].to_dict()
                parsed_row = parse_raw_data(row_dict)
                
                # 파싱된 값들을 db_df에 적용
                if 'management_fee' in parsed_row:
                    if idx >= len(db_df):
                        continue
                    if 'management_fee' not in db_df.columns:
                        db_df['management_fee'] = 0
                    db_df.at[idx, 'management_fee'] = parsed_row['management_fee']
                
                if 'building_name' in parsed_row:
                    if 'building_name' not in db_df.columns:
                        db_df['building_name'] = ''
                    db_df.at[idx, 'building_name'] = parsed_row['building_name']
                
                if 'parking_available' in parsed_row:
                    if 'parking_available' not in db_df.columns:
                        db_df['parking_available'] = False
                    db_df.at[idx, 'parking_available'] = parsed_row['parking_available']
                
                if 'near_station' in parsed_row:
                    if 'near_station' not in db_df.columns:
                        db_df['near_station'] = False
                    db_df.at[idx, 'near_station'] = parsed_row['near_station']
                
                if 'full_address' in parsed_row:
                    if 'full_address' not in db_df.columns:
                        db_df['full_address'] = ''
                    db_df.at[idx, 'full_address'] = parsed_row['full_address']
                
                # 🎯 좌표 데이터 적용
                if 'lat' in parsed_row:
                    if 'lat' not in db_df.columns:
                        db_df['lat'] = 0.0
                    db_df.at[idx, 'lat'] = parsed_row['lat']
                
                if 'lng' in parsed_row:
                    if 'lng' not in db_df.columns:
                        db_df['lng'] = 0.0
                    db_df.at[idx, 'lng'] = parsed_row['lng']
        
        # 기본값 설정 (파싱되지 않은 컬럼들)
        db_df['region'] = '서울특별시'
        
        if 'management_fee' not in db_df.columns:
            db_df['management_fee'] = 0
        
        if 'total_monthly_cost' not in db_df.columns:
            db_df['total_monthly_cost'] = db_df.get('monthly_rent', 0) + db_df.get('management_fee', 0)
        else:
            db_df['total_monthly_cost'] = db_df.get('monthly_rent', 0) + db_df.get('management_fee', 0)
        
        if 'ceiling_height' not in db_df.columns:
            db_df['ceiling_height'] = 0.0
        
        if 'parking_available' not in db_df.columns:
            db_df['parking_available'] = False
        
        if 'near_station' not in db_df.columns:
            db_df['near_station'] = False
        
        if 'build_year' not in db_df.columns:
            db_df['build_year'] = 0
        
        if 'building_name' not in db_df.columns:
            db_df['building_name'] = ''
        
        if 'full_address' not in db_df.columns:
            db_df['full_address'] = ''
        
        # 층수 관련 기본값
        if 'floor' not in db_df.columns:
            db_df['floor'] = 0
        if 'total_floors' not in db_df.columns:
            db_df['total_floors'] = 0
        if 'floor_display' not in db_df.columns:
            db_df['floor_display'] = ''
        
        db_df['score'] = 0
        db_df['labels'] = ''
        db_df['collected_at'] = current_time_str
        db_df['created_at'] = current_time_str
        
        return db_df
    
    def import_csv_to_db(self, csv_file_path: str, overwrite: bool = True) -> int:
        """📥 CSV 파일을 DB로 가져오기 (덮어쓰기 옵션)"""
        try:
            # CSV 파일 읽기
            csv_df = pd.read_csv(csv_file_path)
            print(f"📁 CSV 파일 로드: {len(csv_df)}개 레코드")
            
            # DB 형식으로 변환
            db_df = self.csv_to_db_dataframe(csv_df)
            print(f"🔄 DB 형식 변환 완료: {len(db_df)}개 레코드")
            
            # 덮어쓰기 옵션 처리
            if overwrite:
                print("🗑️ 기존 DB 데이터 삭제 중...")
                self.clear_all_properties()
            
            # DB에 저장
            saved_count = 0
            conn = sqlite3.connect(self.db_path)
            
            for _, row in db_df.iterrows():
                try:
                    # INSERT 쿼리 실행
                    columns = ', '.join(row.index)
                    placeholders = ', '.join(['?' for _ in row.index])
                    query = f"INSERT INTO properties ({columns}) VALUES ({placeholders})"
                    
                    conn.execute(query, tuple(row.values))
                    saved_count += 1
                    
                except Exception as e:
                    print(f"⚠️ 레코드 저장 오류: {e}")
                    continue
            
            conn.commit()
            conn.close()
            
            print(f"✅ CSV → DB 가져오기 완료: {saved_count}/{len(db_df)}개 저장됨")
            return saved_count
            
        except Exception as e:
            print(f"❌ CSV → DB 가져오기 실패: {e}")
            return 0
    
    def clear_all_properties(self):
        """🗑️ 모든 매물 데이터 삭제"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM properties")
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        print(f"🗑️ {deleted_count}개 기존 레코드 삭제됨")
        return deleted_count
    
    def get_all_properties_from_db(self) -> pd.DataFrame:
        """📊 DB에서 모든 매물 데이터 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = "SELECT * FROM properties ORDER BY created_at DESC"
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            print(f"📊 DB에서 {len(df)}개 매물 로드됨")
            return df
            
        except Exception as e:
            print(f"❌ DB 조회 실패: {e}")
            return pd.DataFrame()
    
    def get_properties_count(self) -> int:
        """📊 DB 매물 개수 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM properties")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    def is_property_exists(self, naver_link: str) -> bool:
        """🔍 매물이 DB에 이미 존재하는지 확인 (naver_link 기준)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM properties WHERE naver_link = ?", (naver_link,))
            count = cursor.fetchone()[0]
            conn.close()
            return count > 0
        except:
            return False
    
    def upsert_property(self, property_data: dict) -> str:
        """🔄 매물 UPSERT (중복 시 업데이트, 신규 시 삽입)"""
        try:
            naver_link = property_data.get('naver_link', '')
            if not naver_link:
                return "❌ naver_link가 없습니다"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 기존 매물 확인
            cursor.execute("SELECT id, collected_at FROM properties WHERE naver_link = ?", (naver_link,))
            existing = cursor.fetchone()
            
            current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if existing:
                # 업데이트
                existing_id, old_collected_at = existing
                property_data['collected_at'] = current_time_str
                
                # 동적 UPDATE 쿼리 생성
                columns = []
                values = []
                for key, value in property_data.items():
                    if key != 'id':  # id는 업데이트하지 않음
                        columns.append(f"{key} = ?")
                        values.append(value)
                
                update_query = f"UPDATE properties SET {', '.join(columns)} WHERE id = ?"
                values.append(existing_id)
                
                cursor.execute(update_query, values)
                conn.commit()
                conn.close()
                
                return f"🔄 업데이트: {naver_link.split('/')[-1]} (이전: {old_collected_at})"
            else:
                # 신규 삽입
                property_data['collected_at'] = current_time_str
                property_data['created_at'] = current_time_str
                
                columns = ', '.join(property_data.keys())
                placeholders = ', '.join(['?' for _ in property_data.keys()])
                insert_query = f"INSERT INTO properties ({columns}) VALUES ({placeholders})"
                
                cursor.execute(insert_query, list(property_data.values()))
                conn.commit()
                conn.close()
                
                return f"✅ 신규: {naver_link.split('/')[-1]}"
                
        except Exception as e:
            return f"❌ 오류: {e}"
    
    def import_csv_to_db_from_dataframe(self, df: pd.DataFrame, overwrite: bool = True) -> int:
        """📥 DataFrame을 직접 DB로 저장 (CSV 파일 거치지 않음)"""
        try:
            print(f"🔄 DataFrame → DB 직접 변환: {len(df)}개 레코드")
            
            # DB 형식으로 변환
            db_df = self.csv_to_db_dataframe(df)
            print(f"🔄 DB 형식 변환 완료: {len(db_df)}개 레코드")
            
            # 덮어쓰기 옵션 처리
            if overwrite:
                print("🗑️ 기존 DB 데이터 삭제 중...")
                self.clear_all_properties()
            
            # DB에 저장
            saved_count = 0
            conn = sqlite3.connect(self.db_path)
            
            for _, row in db_df.iterrows():
                try:
                    # INSERT 쿼리 실행
                    columns = ', '.join(row.index)
                    placeholders = ', '.join(['?' for _ in row.index])
                    query = f"INSERT INTO properties ({columns}) VALUES ({placeholders})"
                    
                    conn.execute(query, tuple(row.values))
                    saved_count += 1
                    
                except Exception as e:
                    print(f"⚠️ 레코드 저장 오류: {e}")
                    continue
            
            conn.commit()
            conn.close()
            
            print(f"✅ DataFrame → DB 저장 완료: {saved_count}/{len(db_df)}개 저장됨")
            return saved_count
            
        except Exception as e:
            print(f"❌ DataFrame → DB 저장 실패: {e}")
            return 0
    
    def import_with_upsert(self, df: pd.DataFrame) -> dict:
        """📥 UPSERT 방식으로 DataFrame 데이터 저장 (중복 시 업데이트)"""
        try:
            print(f"🔄 UPSERT 방식 DB 저장: {len(df)}개 레코드")
            
            # DB 형식으로 변환
            db_df = self.csv_to_db_dataframe(df)
            
            # 통계 변수
            stats = {
                'new_count': 0,
                'updated_count': 0,
                'error_count': 0,
                'details': []
            }
            
            # 각 레코드에 대해 UPSERT 실행
            for _, row in db_df.iterrows():
                row_dict = row.to_dict()
                result = self.upsert_property(row_dict)
                stats['details'].append(result)
                
                if "✅ 신규" in result:
                    stats['new_count'] += 1
                elif "🔄 업데이트" in result:
                    stats['updated_count'] += 1
                else:
                    stats['error_count'] += 1
            
            if stats['error_count'] > 0:
                print(f"✅ UPSERT 완료: 신규 {stats['new_count']}개, 업데이트 {stats['updated_count']}개, ⚠️ 오류 {stats['error_count']}개")
            else:
                print(f"✅ UPSERT 완료: 신규 {stats['new_count']}개, 업데이트 {stats['updated_count']}개")
            
            return stats
            
        except Exception as e:
            print(f"❌ UPSERT 실패: {e}")
            return {'new_count': 0, 'updated_count': 0, 'error_count': len(df), 'details': []}
        
    def apply_filters(self, df):
        """필수 조건 필터링 적용"""
        filtered_df = df.copy()
        
        # 보증금 필터
        if 'deposit' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['deposit'] <= self.filter_conditions['max_deposit']]
        
        # 월세 필터
        if 'monthly_rent' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['monthly_rent'] <= self.filter_conditions['max_monthly_rent']]
        
        # 관리비 포함 월세 필터
        if 'monthly_rent' in filtered_df.columns and 'management_fee' in filtered_df.columns:
            total_rent = filtered_df['monthly_rent'] + filtered_df['management_fee'].fillna(0)
            filtered_df = filtered_df[total_rent <= self.filter_conditions['max_total_monthly']]
        
        # 층수 필터 (None 값 안전 처리)
        if 'floor' in filtered_df.columns:
            # None 값 제외하고 숫자 타입만 필터링
            floor_valid = filtered_df['floor'].notna() & filtered_df['floor'].apply(lambda x: isinstance(x, (int, float)))
            if floor_valid.any():
                filtered_df = filtered_df[
                    floor_valid &
                    (filtered_df['floor'] >= self.filter_conditions['min_floor']) &
                    (filtered_df['floor'] <= self.filter_conditions['max_floor'])
                ]
        
        # 면적 필터
        if 'area_sqm' in filtered_df.columns:
            # 20평 = 66㎡로 변환
            area_pyeong = filtered_df['area_sqm'] / 3.306
            filtered_df = filtered_df[area_pyeong >= self.filter_conditions['min_area_pyeong']]
        
        # 관리비 필터
        if 'management_fee' in filtered_df.columns:
            filtered_df = filtered_df[
                filtered_df['management_fee'].fillna(0) <= self.filter_conditions['max_management_fee']
            ]
        
        return filtered_df
    
    def calculate_scores(self, df):
        """선택 조건 점수 계산"""
        df = df.copy()
        df['score'] = 0
        
        # 층고 점수
        if 'ceiling_height' in df.columns:
            ceiling_condition = df['ceiling_height'] >= 2.8
            df.loc[ceiling_condition, 'score'] += 1
        
        # 역세권 점수
        if 'near_station' in df.columns:
            station_condition = df['near_station'] == True
            df.loc[station_condition, 'score'] += 2
        
        # 주차 점수 (가장 중요)
        if 'parking_available' in df.columns:
            parking_condition = df['parking_available'] == True
            df.loc[parking_condition, 'score'] += 3
        
        return df
    
    def create_labels(self, df):
        """선택 조건 라벨 생성"""
        df = df.copy()
        labels = []
        
        for idx, row in df.iterrows():
            row_labels = []
            
            # 층고 라벨
            if 'ceiling_height' in row and pd.notna(row['ceiling_height']):
                if row['ceiling_height'] >= 2.8:
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
    def apply_range_filters(self, df, filter_conditions):
        """범위 필터 적용 함수"""
        if df.empty or not filter_conditions:
            return df
            
        filtered_df = df.copy()
        
        # 지역 필터
        if 'districts' in filter_conditions and filter_conditions['districts']:
            if 'district' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['district'].isin(filter_conditions['districts'])]
            elif 'region' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['region'].isin(filter_conditions['districts'])]
        
        # 보증금 범위 필터
        if 'deposit_range' in filter_conditions and 'deposit' in filtered_df.columns:
            min_deposit, max_deposit = filter_conditions['deposit_range']
            filtered_df = filtered_df[
                (filtered_df['deposit'] >= min_deposit) &
                (filtered_df['deposit'] <= max_deposit)
            ]
        
        # 월세 범위 필터
        if 'rent_range' in filter_conditions and 'monthly_rent' in filtered_df.columns:
            min_rent, max_rent = filter_conditions['rent_range']
            filtered_df = filtered_df[
                (filtered_df['monthly_rent'] >= min_rent) &
                (filtered_df['monthly_rent'] <= max_rent)
            ]
        
        # 면적 범위 필터
        if 'area_range' in filter_conditions and 'area_pyeong' in filtered_df.columns:
            min_area, max_area = filter_conditions['area_range']
            filtered_df = filtered_df[
                (filtered_df['area_pyeong'] >= min_area) &
                (filtered_df['area_pyeong'] <= max_area)
            ]
        
        return filtered_df
    
    def apply_sorting(self, df, sort_option):
        """정렬 적용 함수"""
        if df.empty or not sort_option:
            return df
            
        sort_mapping = {
            "보증금 낮은순": ('deposit', True),
            "보증금 높은순": ('deposit', False),
            "월세 낮은순": ('monthly_rent', True),
            "월세 높은순": ('monthly_rent', False),
            "면적 큰순": ('area_pyeong', False),
            "면적 작은순": ('area_pyeong', True),
            "점수 높은순": ('score', False),
            "등록순": (None, None)
        }
        
        column, ascending = sort_mapping.get(sort_option, (None, None))
        if column and column in df.columns:
            return df.sort_values(column, ascending=ascending)
        
        return df

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
