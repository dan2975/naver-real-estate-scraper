# 설정 파일
import os

# 필수 조건 (하드 필터)
FILTER_CONDITIONS = {
    'deposit_max': 2000,  # 보증금 최대 (만원)
    'monthly_rent_max': 130,  # 월세 최대 (만원)
    'total_rent_max': 150,  # 관리비 포함 월세 최대 (만원)
    'floor_min': -1,  # 최소 층수 (지하1층)
    'floor_max': 2,   # 최대 층수 (지상2층)
    'area_min': 66,   # 최소 면적 (㎡)
    'management_fee_max': 30  # 관리비 최대 (만원)
}

# 선택 조건 (점수 시스템)
SCORING_CONDITIONS = {
    'ceiling_height': {
        'threshold': 2.8,  # 층고 2.8m 이상
        'score': 10
    },
    'near_station': {
        'score': 15  # 역세권
    },
    'parking': {
        'score': 20  # 주차 가능 (가장 중요)
    }
}

# 공공데이터포털 API 설정
PUBLIC_DATA_API = {
    'base_url': 'http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc',
    'service_key': '',  # API 키 입력 필요
    'endpoints': {
        'apt_rent': 'getRTMSDataSvcAptRent',  # 아파트 전월세
        'apt_trade': 'getRTMSDataSvcAptTrade',  # 아파트 매매
        'villa_rent': 'getRTMSDataSvcVillaRent',  # 연립다세대 전월세
    }
}

# 네이버 부동산 스크래핑 설정
NAVER_SETTINGS = {
    'base_url': 'https://new.land.naver.com',
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    },
    'delay': 2  # 요청 간격 (초)
}

# 데이터베이스 설정
DATABASE = {
    'name': 'data/properties.db'
}

# 지역 코드 (서울 주요 구)
REGION_CODES = {
    '강남구': '11680',
    '강동구': '11740',
    '강북구': '11305',
    '강서구': '11500',
    '관악구': '11620',
    '광진구': '11215',
    '구로구': '11530',
    '금천구': '11545',
    '노원구': '11350',
    '도봉구': '11320',
    '동대문구': '11230',
    '동작구': '11590',
    '마포구': '11440',
    '서대문구': '11410',
    '서초구': '11650',
    '성동구': '11200',
    '성북구': '11290',
    '송파구': '11710',
    '양천구': '11470',
    '영등포구': '11560',
    '용산구': '11170',
    '은평구': '11380',
    '종로구': '11110',
    '중구': '11140',
    '중랑구': '11260'
}
