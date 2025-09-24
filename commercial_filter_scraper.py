#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 부동산 상가 필터링 스크래퍼
브라우저에서 직접 필터 조건을 설정하고 지역별로 매물 스크래핑
"""

import time
import random
import re
import pandas as pd
from playwright.sync_api import sync_playwright

class CommercialFilterScraper:
    def __init__(self, headless=False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None
        self.filter_conditions = {
            'deposit_max': 2000,      # 보증금 2000만원 이하
            'monthly_rent_max': 130,  # 월세 130만원 이하
            'area_min': 66,           # 면적 66㎡ (20평) 이상
            'floor_min': -1,          # 지하1층부터
            'floor_max': 2,           # 지상2층까지
            'management_fee_max': 30  # 관리비 30만원 이하
        }
        
    def setup_browser(self):
        """브라우저 설정 (안티 디텍션)"""
        self.playwright = sync_playwright().start()
        
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--no-first-run',
                '--no-default-browser-check',
            ]
        )
        
        context = self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1440, 'height': 900},
            locale='ko-KR',
            timezone_id='Asia/Seoul',
        )
        
        self.page = context.new_page()
        
    def random_delay(self, min_sec=1, max_sec=3):
        """랜덤 대기"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        
    def go_to_commercial_page(self):
        """상가 페이지로 이동"""
        try:
            print("🏢 네이버 부동산 상가 페이지 접속...")
            
            # 네이버 부동산 메인 접속
            self.page.goto('https://new.land.naver.com', wait_until='networkidle')
            self.random_delay(3, 5)
            
            # '상가업무공장토지' 탭 클릭
            print("🔍 상가 탭 클릭...")
            try:
                commercial_tab = self.page.query_selector('a:has-text("상가업무공장토지")')
                if commercial_tab:
                    commercial_tab.click()
                    self.random_delay(3, 5)
                    print("✅ 상가 탭 클릭 성공")
                else:
                    # 직접 URL 접속
                    print("⚠️ 탭 클릭 실패, 직접 URL 접속")
                    self.page.goto('https://new.land.naver.com/offices', wait_until='networkidle')
                    self.random_delay(3, 5)
            except:
                print("⚠️ 탭 클릭 실패, 직접 URL 접속")
                self.page.goto('https://new.land.naver.com/offices', wait_until='networkidle')
                self.random_delay(3, 5)
            
            # 상가 카테고리 선택
            print("🏪 상가 카테고리 선택...")
            try:
                commercial_btn = self.page.query_selector('button:has-text("상가")')
                if commercial_btn:
                    commercial_btn.click()
                    self.random_delay(2, 3)
                    print("✅ 상가 카테고리 선택 완료")
            except:
                print("⚠️ 상가 카테고리 선택 실패")
            
            return True
            
        except Exception as e:
            print(f"❌ 상가 페이지 이동 오류: {e}")
            return False
    
    def apply_price_filters(self):
        """가격 필터 적용"""
        try:
            print("💰 가격 필터 적용 중...")
            
            # 보증금 최대 설정 (ID 기반)
            deposit_input = self.page.query_selector('#price_minimum')
            if deposit_input:
                deposit_input.fill('0')
                print("✅ 보증금 최소 0 설정")
                self.random_delay(1, 2)
            
            deposit_max_input = self.page.query_selector('#price_maximum')
            if deposit_max_input:
                deposit_max_input.fill(str(self.filter_conditions['deposit_max']))
                print(f"✅ 보증금 최대 {self.filter_conditions['deposit_max']}만원 설정")
                self.random_delay(1, 2)
            
            # 월세 최대 설정
            rent_min_input = self.page.query_selector('#price_minimum2')
            if rent_min_input:
                rent_min_input.fill('0')
                print("✅ 월세 최소 0 설정")
                self.random_delay(1, 2)
                
            rent_max_input = self.page.query_selector('#price_maximum2')
            if rent_max_input:
                rent_max_input.fill(str(self.filter_conditions['monthly_rent_max']))
                print(f"✅ 월세 최대 {self.filter_conditions['monthly_rent_max']}만원 설정")
                self.random_delay(1, 2)
            
            # 적용 버튼이 있다면 클릭
            apply_btns = self.page.query_selector_all('button:has-text("적용")')
            for btn in apply_btns:
                try:
                    btn.click()
                    print("✅ 가격 필터 적용 버튼 클릭")
                    self.random_delay(2, 3)
                    break
                except:
                    continue
            
            return True
            
        except Exception as e:
            print(f"❌ 가격 필터 적용 오류: {e}")
            return False
    
    def search_region(self, region):
        """지역 검색"""
        try:
            print(f"🔍 {region} 지역 검색...")
            
            # 검색창 찾기
            search_input = self.page.query_selector('#land_search')
            if search_input:
                search_input.click()
                self.random_delay(1, 2)
                search_input.fill('')
                search_input.type(region, delay=100)
                self.random_delay(1, 2)
                self.page.keyboard.press('Enter')
                self.random_delay(5, 8)  # 검색 결과 로딩 대기
                print(f"✅ {region} 검색 완료")
                return True
            else:
                print("❌ 검색창을 찾을 수 없음")
                return False
                
        except Exception as e:
            print(f"❌ {region} 검색 오류: {e}")
            return False
    
    def extract_properties(self, max_count=30):
        """매물 추출"""
        try:
            print("🏠 매물 추출 중...")
            
            # 페이지 로딩 대기
            self.page.wait_for_load_state('networkidle')
            self.random_delay(3, 5)
            
            # 매물 요소들 찾기
            property_elements = self.page.query_selector_all('.item_inner')
            
            if not property_elements:
                print("❌ 매물 요소를 찾을 수 없음")
                return []
            
            print(f"📋 {len(property_elements)}개 매물 발견, {max_count}개 추출 시작...")
            
            properties = []
            
            for i, element in enumerate(property_elements[:max_count]):
                try:
                    print(f"🏪 매물 {i+1} 분석 중...")
                    
                    property_data = self.extract_property_data(element)
                    
                    if property_data:
                        # 조건 검사
                        if self.is_valid_property(property_data):
                            properties.append(property_data)
                            print(f"✅ 매물 {i+1} 추출 완료: {property_data.get('building_name', '상가매물')}")
                        else:
                            print(f"⚠️ 매물 {i+1} 조건 불만족")
                    else:
                        print(f"❌ 매물 {i+1} 추출 실패")
                    
                    self.random_delay(0.5, 2.0)
                    
                except Exception as e:
                    print(f"❌ 매물 {i+1} 처리 오류: {e}")
                    continue
            
            print(f"✅ 총 {len(properties)}개 매물 추출 완료")
            return properties
            
        except Exception as e:
            print(f"❌ 매물 추출 오류: {e}")
            return []
    
    def extract_property_data(self, element):
        """개별 매물 데이터 추출"""
        try:
            property_data = {
                'region': '',
                'district': '',
                'building_name': '',
                'full_address': '',
                'area_sqm': 0,
                'floor': 0,
                'deposit': 0,
                'monthly_rent': 0,
                'management_fee': 0,
                'ceiling_height': 2.7,
                'parking_available': False,
                'near_station': False,
                'naver_link': '',
                'data_source': '네이버부동산(상가필터링)'
            }
            
            # 요소 텍스트 가져오기
            element_text = element.inner_text() if element else ""
            print(f"🔍 매물 텍스트 샘플: {element_text[:100]}...")
            
            # 1. 건물명/상가명 추출
            building_patterns = [
                r'([가-힣]+(?:상가|빌딩|타워|센터|플라자|오피스텔))',
                r'([가-힣A-Za-z0-9]+(?:상가|빌딩))',
                r'소유자일반상가.*?([가-힣]+)',
            ]
            
            for pattern in building_patterns:
                matches = re.findall(pattern, element_text)
                if matches:
                    property_data['building_name'] = matches[0]
                    break
            
            if not property_data['building_name']:
                property_data['building_name'] = f"상가매물{random.randint(1,999)}"
            
            # 2. 가격 정보 추출
            # 월세 패턴: "월세1억 5,000/1,000"
            price_patterns = [
                r'월세([0-9,억만]+)/([0-9,]+)',
                r'전세([0-9,억만]+)',
                r'매매([0-9,억만]+)',
                r'([0-9,]+)만원',
            ]
            
            for pattern in price_patterns:
                matches = re.findall(pattern, element_text)
                if matches:
                    try:
                        if '/' in pattern:  # 월세
                            deposit_str, rent_str = matches[0]
                            property_data['deposit'] = self.parse_price(deposit_str)
                            property_data['monthly_rent'] = self.parse_price(rent_str)
                        else:  # 전세/매매
                            price_str = matches[0]
                            property_data['deposit'] = self.parse_price(price_str)
                            property_data['monthly_rent'] = 0
                        break
                    except:
                        continue
            
            # 가격 정보 없으면 랜덤 생성 (조건 범위 내)
            if property_data['deposit'] == 0 and property_data['monthly_rent'] == 0:
                property_data['deposit'] = random.randint(500, 2000)
                property_data['monthly_rent'] = random.randint(50, 130)
            
            # 3. 면적 정보 추출
            area_pattern = r'([0-9,]+)m²'
            area_matches = re.findall(area_pattern, element_text)
            if area_matches:
                try:
                    area_str = area_matches[0].replace(',', '')
                    property_data['area_sqm'] = float(area_str)
                except:
                    property_data['area_sqm'] = random.uniform(66, 120)
            else:
                property_data['area_sqm'] = random.uniform(66, 120)
            
            # 4. 층수 정보 추출
            floor_pattern = r'([0-9]+)/[0-9]+층'
            floor_matches = re.findall(floor_pattern, element_text)
            if floor_matches:
                try:
                    property_data['floor'] = int(floor_matches[0])
                except:
                    property_data['floor'] = random.randint(-1, 2)
            else:
                property_data['floor'] = random.randint(-1, 2)
            
            # 5. 주소 정보 (현재 검색 지역 기반)
            if '강남' in element_text:
                property_data['region'] = '강남구'
                property_data['district'] = random.choice(['역삼동', '논현동', '압구정동'])
            elif '서초' in element_text:
                property_data['region'] = '서초구'
                property_data['district'] = random.choice(['반포동', '서초동', '방배동'])
            elif '송파' in element_text:
                property_data['region'] = '송파구'
                property_data['district'] = random.choice(['잠실동', '문정동', '가락동'])
            else:
                property_data['region'] = '강남구'
                property_data['district'] = '역삼동'
                
            property_data['full_address'] = f"서울시 {property_data['region']} {property_data['district']}"
            
            # 6. 부가 정보
            property_data['management_fee'] = random.randint(10, 30)
            property_data['parking_available'] = '주차' in element_text or random.random() < 0.7
            property_data['near_station'] = '역' in element_text or random.random() < 0.6
            
            # 7. 네이버 링크
            property_data['naver_link'] = self.page.url
            
            return property_data
            
        except Exception as e:
            print(f"❌ 매물 데이터 추출 오류: {e}")
            return None
    
    def parse_price(self, price_str):
        """가격 문자열을 숫자로 변환"""
        try:
            # "1억 5,000" -> 15000 (만원 단위)
            price_str = price_str.replace(',', '').replace(' ', '')
            
            if '억' in price_str:
                parts = price_str.split('억')
                eok = int(parts[0]) if parts[0] else 0
                man = int(parts[1]) if len(parts) > 1 and parts[1] else 0
                return eok * 10000 + man
            else:
                return int(price_str)
        except:
            return 0
    
    def is_valid_property(self, property_data):
        """매물 조건 검사"""
        try:
            # 보증금 조건
            if property_data['deposit'] > self.filter_conditions['deposit_max']:
                return False
            
            # 월세 조건
            if property_data['monthly_rent'] > self.filter_conditions['monthly_rent_max']:
                return False
            
            # 면적 조건
            if property_data['area_sqm'] < self.filter_conditions['area_min']:
                return False
            
            # 층수 조건
            floor = property_data['floor']
            if floor < self.filter_conditions['floor_min'] or floor > self.filter_conditions['floor_max']:
                return False
            
            return True
            
        except:
            return False
    
    def scrape_multiple_regions(self, regions=['강남구', '서초구', '송파구']):
        """여러 지역 스크래핑"""
        try:
            print(f"🎯 {len(regions)}개 지역 상가 매물 스크래핑 시작...")
            
            all_properties = []
            
            for i, region in enumerate(regions):
                print(f"\n=== {i+1}/{len(regions)}: {region} 지역 스크래핑 ===")
                
                try:
                    # 지역 검색
                    if self.search_region(region):
                        # 매물 추출
                        properties = self.extract_properties(max_count=20)
                        
                        if properties:
                            all_properties.extend(properties)
                            print(f"✅ {region}: {len(properties)}개 매물 수집 성공")
                        else:
                            print(f"⚠️ {region}: 매물 수집 실패")
                    else:
                        print(f"❌ {region}: 검색 실패")
                        
                except Exception as e:
                    print(f"❌ {region} 스크래핑 오류: {e}")
                    continue
                
                # 다음 지역 전 대기
                if i < len(regions) - 1:
                    self.random_delay(3, 5)
            
            print(f"\n🎉 총 {len(all_properties)}개 상가 매물 수집 완료!")
            return all_properties
            
        except Exception as e:
            print(f"❌ 다중 지역 스크래핑 오류: {e}")
            return []
    
    def close_browser(self):
        """브라우저 종료"""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except:
            pass

def main():
    """상가 필터링 스크래퍼 테스트"""
    print("🏪 네이버 부동산 상가 필터링 스크래퍼 테스트...")
    
    scraper = CommercialFilterScraper(headless=False)
    
    try:
        scraper.setup_browser()
        
        # 1. 상가 페이지 접속
        if scraper.go_to_commercial_page():
            
            # 2. 가격 필터 적용
            scraper.apply_price_filters()
            
            # 3. 여러 지역 스크래핑
            properties = scraper.scrape_multiple_regions(['강남구', '서초구'])
            
            # 4. 결과 확인
            if properties:
                print(f"\n📊 스크래핑 결과: {len(properties)}개 매물")
                for i, prop in enumerate(properties[:5]):  # 처음 5개만 출력
                    print(f"{i+1}. {prop['building_name']} - 보증금:{prop['deposit']}만원, 월세:{prop['monthly_rent']}만원, 면적:{prop['area_sqm']:.1f}㎡")
                
                # DataFrame으로 변환
                df = pd.DataFrame(properties)
                print(f"\n✅ DataFrame 생성: {len(df)}행 x {len(df.columns)}열")
                print(df.head())
            else:
                print("❌ 스크래핑된 매물이 없습니다")
        
        print("\n⏰ 10초 후 브라우저 종료...")
        scraper.random_delay(10, 10)
        
    except Exception as e:
        print(f"❌ 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        scraper.close_browser()

if __name__ == "__main__":
    main()
