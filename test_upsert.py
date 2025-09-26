#!/usr/bin/env python3
"""
🔄 UPSERT 중복 검사 시스템 테스트
"""

import pandas as pd
from data_processor import PropertyDataProcessor
from datetime import datetime

def test_upsert_system():
    print("🔄 UPSERT 중복 검사 시스템 테스트")
    
    processor = PropertyDataProcessor()
    
    # 현재 DB 상태 확인
    current_count = processor.get_properties_count()
    print(f"📊 현재 DB 매물 수: {current_count}개")
    
    # 테스트 데이터 생성 (기존 매물 일부 + 새로운 매물)
    test_data = [
        {
            'district': '강남구',
            'property_type': '사무실',
            'deposit': 1500,
            'monthly_rent': 100,
            'area_sqm': 70.0,
            'area_pyeong': 21.2,
            'floor': 5,
            'building_name': '테스트빌딩',
            'full_address': '서울시 강남구 테스트동',
            'naver_link': 'https://m.land.naver.com/article/info/2552147166',  # 기존 매물
            'article_no': '2552147166',
            'raw_data': '테스트 데이터'
        },
        {
            'district': '서초구',
            'property_type': '상가',
            'deposit': 2000,
            'monthly_rent': 150,
            'area_sqm': 80.0,
            'area_pyeong': 24.2,
            'floor': 1,
            'building_name': '새로운빌딩',
            'full_address': '서울시 서초구 신규동',
            'naver_link': 'https://m.land.naver.com/article/info/9999999999',  # 새로운 매물
            'article_no': '9999999999',
            'raw_data': '신규 테스트 데이터'
        }
    ]
    
    # DataFrame으로 변환
    test_df = pd.DataFrame(test_data)
    print(f"📝 테스트 데이터: {len(test_df)}개 (기존 1개 + 신규 1개)")
    
    # UPSERT 테스트
    stats = processor.import_with_upsert(test_df)
    
    print("\n📊 UPSERT 결과:")
    print(f"   신규: {stats['new_count']}개")
    print(f"   업데이트: {stats['updated_count']}개")
    print(f"   오류: {stats['error_count']}개")
    
    print("\n🔍 상세 결과:")
    for detail in stats['details']:
        print(f"   {detail}")
    
    # 최종 DB 상태 확인
    final_count = processor.get_properties_count()
    print(f"\n📊 최종 DB 매물 수: {final_count}개 (변화: +{final_count - current_count}개)")
    
    # 업데이트된 매물 확인
    if stats['updated_count'] > 0:
        updated_data = processor.get_all_properties_from_db()
        updated_property = updated_data[updated_data['naver_link'] == 'https://m.land.naver.com/article/info/2552147166']
        if not updated_property.empty:
            print(f"\n✅ 업데이트 확인: collected_at = {updated_property.iloc[0]['collected_at']}")

if __name__ == "__main__":
    test_upsert_system()
