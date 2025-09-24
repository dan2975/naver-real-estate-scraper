import requests
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
import time
from config import PUBLIC_DATA_API, REGION_CODES

class PublicDataCollector:
    """공공데이터포털 부동산 실거래가 API 클래스"""
    
    def __init__(self, service_key):
        self.service_key = service_key
        self.base_url = PUBLIC_DATA_API['base_url']
        
    def get_rent_data(self, region_code, year_month):
        """전월세 실거래가 데이터 수집"""
        try:
            # 아파트 전월세
            apt_data = self._fetch_data('apt_rent', region_code, year_month)
            # 연립다세대 전월세
            villa_data = self._fetch_data('villa_rent', region_code, year_month)
            
            # 데이터 병합
            all_data = []
            if apt_data:
                all_data.extend(apt_data)
            if villa_data:
                all_data.extend(villa_data)
                
            return self._process_rent_data(all_data)
            
        except Exception as e:
            print(f"데이터 수집 오류: {e}")
            return pd.DataFrame()
    
    def _fetch_data(self, endpoint_type, region_code, year_month):
        """API 데이터 가져오기"""
        endpoint = PUBLIC_DATA_API['endpoints'][endpoint_type]
        url = f"{self.base_url}/{endpoint}"
        
        params = {
            'serviceKey': self.service_key,
            'LAWD_CD': region_code,
            'DEAL_YMD': year_month,
            'numOfRows': 1000
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            # XML 파싱
            root = ET.fromstring(response.content)
            items = root.findall('.//item')
            
            data_list = []
            for item in items:
                data = {}
                for child in item:
                    data[child.tag] = child.text
                data_list.append(data)
                
            time.sleep(0.1)  # API 호출 간격
            return data_list
            
        except Exception as e:
            print(f"API 호출 오류 ({endpoint_type}): {e}")
            return []
    
    def _process_rent_data(self, raw_data):
        """데이터 정제 및 가공"""
        if not raw_data:
            return pd.DataFrame()
            
        df = pd.DataFrame(raw_data)
        
        # 필요한 컬럼만 선택 및 이름 변경
        column_mapping = {
            '법정동': 'district',
            '지번': 'address_detail', 
            '아파트': 'building_name',
            '전용면적': 'area',
            '층': 'floor',
            '보증금액': 'deposit',
            '월세금액': 'monthly_rent',
            '건축년도': 'build_year',
            '계약구분': 'contract_type'
        }
        
        # 존재하는 컬럼만 매핑
        available_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
        df = df.rename(columns=available_columns)
        
        # 데이터 타입 변환
        numeric_columns = ['area', 'floor', 'deposit', 'monthly_rent', 'build_year']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
        
        # 기본값 설정
        if 'monthly_rent' not in df.columns:
            df['monthly_rent'] = 0
        if 'deposit' not in df.columns:
            df['deposit'] = 0
            
        # 면적을 제곱미터로 변환 (평 -> ㎡)
        if 'area' in df.columns:
            df['area_sqm'] = df['area']
            df['area_pyeong'] = df['area'] / 3.3058
        
        # 주소 정보 생성
        if 'district' in df.columns and 'address_detail' in df.columns:
            df['full_address'] = df['district'] + ' ' + df['address_detail'].fillna('')
        
        # 데이터 소스 표시
        df['data_source'] = '공공데이터'
        df['collected_at'] = datetime.now()
        
        return df
    
    def collect_all_regions(self, year_month=None):
        """모든 지역 데이터 수집"""
        if year_month is None:
            year_month = datetime.now().strftime('%Y%m')
            
        all_data = []
        
        for region_name, region_code in REGION_CODES.items():
            print(f"수집 중: {region_name}")
            data = self.get_rent_data(region_code, year_month)
            if not data.empty:
                data['region'] = region_name
                all_data.append(data)
            time.sleep(1)  # 지역별 수집 간격
            
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        else:
            return pd.DataFrame()

# 사용 예시
if __name__ == "__main__":
    # API 키가 있다면 테스트 가능
    service_key = "YOUR_SERVICE_KEY_HERE"
    collector = PublicDataCollector(service_key)
    
    # 테스트 데이터 생성 (API 키 없을 때)
    sample_data = pd.DataFrame({
        'region': ['강남구', '서초구', '송파구'] * 10,
        'district': ['역삼동', '반포동', '잠실동'] * 10,
        'building_name': [f'테스트아파트{i}' for i in range(30)],
        'area_sqm': [70, 85, 95] * 10,
        'floor': [1, 2, -1] * 10,
        'deposit': [1500, 2500, 1800] * 10,
        'monthly_rent': [120, 80, 150] * 10,
        'full_address': ['강남구 역삼동', '서초구 반포동', '송파구 잠실동'] * 10,
        'data_source': ['공공데이터'] * 30
    })
    
    print("샘플 데이터 생성 완료")
    print(sample_data.head())
