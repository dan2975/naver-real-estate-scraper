#!/usr/bin/env python3
"""
🔄 CSV → DB 변환 테스트 스크립트
최신 CSV 데이터를 DB로 가져오기
"""

from modules.data_processor import PropertyDataProcessor
import os

def main():
    print("🔄 CSV → DB 변환 테스트 시작")
    
    # 데이터 프로세서 초기화
    processor = PropertyDataProcessor()
    
    # 테이블 생성
    processor.create_tables()
    print("✅ DB 테이블 준비 완료")
    
    # 최신 CSV 파일 찾기
    csv_file = "latest_collection.csv"
    if not os.path.exists(csv_file):
        print(f"❌ CSV 파일이 없습니다: {csv_file}")
        return
    
    print(f"📁 CSV 파일 찾음: {csv_file}")
    
    # CSV → DB 가져오기 (덮어쓰기)
    saved_count = processor.import_csv_to_db(csv_file, overwrite=True)
    
    # 결과 확인
    total_count = processor.get_properties_count()
    print(f"📊 최종 DB 매물 개수: {total_count}개")
    
    if total_count > 0:
        # 샘플 데이터 확인
        df = processor.get_all_properties_from_db()
        print("\n🔍 샘플 데이터 (처음 3개):")
        print(df[['district', 'deposit', 'monthly_rent', 'area_pyeong', 'naver_link']].head(3))
        
        print("\n✅ CSV → DB 변환 완료!")
    else:
        print("❌ DB에 데이터가 없습니다.")

if __name__ == "__main__":
    main()
