#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
브라우저 기반 필터링 테스트
- 브라우저에서 직접 필터 조건 설정
- 지역별로 이동하면서 매물 스크래핑
"""

import time
import random
import re
from playwright.sync_api import sync_playwright

class BrowserFilterScraper:
    def __init__(self, headless=False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None
        
    def setup_browser(self):
        """브라우저 설정 (기존 안티 디텍션 유지)"""
        self.playwright = sync_playwright().start()
        
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-dev-shm-usage',
                '--no-first-run',
                '--no-default-browser-check',
            ]
        )
        
        real_user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        
        context = self.browser.new_context(
            user_agent=random.choice(real_user_agents),
            viewport={'width': random.randint(1366, 1920), 'height': random.randint(768, 1080)},
            locale='ko-KR',
            timezone_id='Asia/Seoul',
        )
        
        self.page = context.new_page()
        
    def random_delay(self, min_sec=1, max_sec=3):
        """랜덤 대기"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        
    def test_filter_setup(self):
        """브라우저에서 필터 설정 테스트"""
        try:
            print("🌐 네이버 부동산 접속...")
            self.setup_browser()
            
            # 네이버 부동산 메인 페이지 접속
            self.page.goto('https://new.land.naver.com', wait_until='networkidle')
            print("✅ 네이버 부동산 접속 완료")
            self.random_delay(3, 5)
            
            # 상가 탭 클릭
            print("🏢 상가 탭 찾는 중...")
            commercial_selectors = [
                'a[href*="SG"]',  # 상가 탭
                'a[href*="OPST"]',  # 오피스텔 탭
                '.tab_commercial',
                'button:has-text("상가")',
                'button:has-text("오피스텔")',
                '[data-tab="SG"]',
                '[data-tab="OPST"]'
            ]
            
            commercial_clicked = False
            for selector in commercial_selectors:
                try:
                    tab = self.page.query_selector(selector)
                    if tab:
                        print(f"✅ 상가 탭 발견: {selector}")
                        tab.click()
                        commercial_clicked = True
                        self.random_delay(2, 4)
                        break
                except Exception as e:
                    print(f"⚠️ {selector} 클릭 실패: {e}")
                    continue
            
            if not commercial_clicked:
                print("⚠️ 상가 탭을 찾을 수 없음, 직접 URL 접속")
                self.page.goto('https://new.land.naver.com/search?ms=37.5665,126.9784,13&a=SG:OPST', wait_until='networkidle')
                self.random_delay(3, 5)
            
            print("💰 가격 필터 설정 시작...")
            self.setup_price_filter()
            
            print("📐 면적 필터 설정 시작...")
            self.setup_area_filter()
            
            print("🏢 층수 필터 설정 시작...")
            self.setup_floor_filter()
            
            print("⏰ 필터 설정 완료 후 10초 대기...")
            self.random_delay(8, 12)
            
            return True
            
        except Exception as e:
            print(f"❌ 필터 설정 테스트 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def setup_price_filter(self):
        """가격 필터 설정 (보증금 2000만원 이하, 월세 130만원 이하)"""
        try:
            # 가격 필터 버튼 찾기
            price_selectors = [
                'button:has-text("가격")',
                '.filter_price',
                '.btn_price',
                '[data-filter="price"]',
                '.price_filter_btn'
            ]
            
            for selector in price_selectors:
                try:
                    price_btn = self.page.query_selector(selector)
                    if price_btn:
                        print(f"✅ 가격 필터 버튼 발견: {selector}")
                        price_btn.click()
                        self.random_delay(1, 2)
                        
                        # 보증금 최대값 설정
                        deposit_inputs = [
                            'input[placeholder*="보증금"]',
                            'input[placeholder*="최대"]',
                            '.deposit_max',
                            '#deposit_max'
                        ]
                        
                        for dep_selector in deposit_inputs:
                            try:
                                deposit_input = self.page.query_selector(dep_selector)
                                if deposit_input:
                                    deposit_input.fill('2000')
                                    print("✅ 보증금 2000만원 설정")
                                    self.random_delay(1, 2)
                                    break
                            except:
                                continue
                        
                        # 월세 최대값 설정
                        rent_inputs = [
                            'input[placeholder*="월세"]',
                            'input[placeholder*="임대료"]',
                            '.rent_max',
                            '#rent_max'
                        ]
                        
                        for rent_selector in rent_inputs:
                            try:
                                rent_input = self.page.query_selector(rent_selector)
                                if rent_input:
                                    rent_input.fill('130')
                                    print("✅ 월세 130만원 설정")
                                    self.random_delay(1, 2)
                                    break
                            except:
                                continue
                        
                        # 적용 버튼 클릭
                        apply_btns = [
                            'button:has-text("적용")',
                            'button:has-text("확인")',
                            '.btn_apply',
                            '.apply_filter'
                        ]
                        
                        for apply_selector in apply_btns:
                            try:
                                apply_btn = self.page.query_selector(apply_selector)
                                if apply_btn:
                                    apply_btn.click()
                                    print("✅ 가격 필터 적용 완료")
                                    self.random_delay(2, 3)
                                    return
                            except:
                                continue
                        
                        break
                except Exception as e:
                    print(f"⚠️ {selector} 가격 필터 실패: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ 가격 필터 설정 오류: {e}")
    
    def setup_area_filter(self):
        """면적 필터 설정 (20평/66㎡ 이상)"""
        try:
            area_selectors = [
                'button:has-text("면적")',
                '.filter_area',
                '.btn_area',
                '[data-filter="area"]'
            ]
            
            for selector in area_selectors:
                try:
                    area_btn = self.page.query_selector(selector)
                    if area_btn:
                        print(f"✅ 면적 필터 버튼 발견: {selector}")
                        area_btn.click()
                        self.random_delay(1, 2)
                        
                        # 최소 면적 설정
                        area_inputs = [
                            'input[placeholder*="최소"]',
                            'input[placeholder*="면적"]',
                            '.area_min',
                            '#area_min'
                        ]
                        
                        for area_input_selector in area_inputs:
                            try:
                                area_input = self.page.query_selector(area_input_selector)
                                if area_input:
                                    area_input.fill('66')  # 66㎡ (20평)
                                    print("✅ 최소 면적 66㎡ 설정")
                                    self.random_delay(1, 2)
                                    break
                            except:
                                continue
                        
                        # 적용 버튼
                        apply_btns = [
                            'button:has-text("적용")',
                            'button:has-text("확인")',
                            '.btn_apply'
                        ]
                        
                        for apply_selector in apply_btns:
                            try:
                                apply_btn = self.page.query_selector(apply_selector)
                                if apply_btn:
                                    apply_btn.click()
                                    print("✅ 면적 필터 적용 완료")
                                    self.random_delay(2, 3)
                                    return
                            except:
                                continue
                        
                        break
                except Exception as e:
                    print(f"⚠️ {selector} 면적 필터 실패: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ 면적 필터 설정 오류: {e}")
    
    def setup_floor_filter(self):
        """층수 필터 설정 (지하1층~지상2층)"""
        try:
            floor_selectors = [
                'button:has-text("층")',
                'button:has-text("층수")',
                '.filter_floor',
                '.btn_floor',
                '[data-filter="floor"]'
            ]
            
            for selector in floor_selectors:
                try:
                    floor_btn = self.page.query_selector(selector)
                    if floor_btn:
                        print(f"✅ 층수 필터 버튼 발견: {selector}")
                        floor_btn.click()
                        self.random_delay(1, 2)
                        
                        # 층수 체크박스들 찾기
                        floor_checkboxes = [
                            'input[value*="B1"]',  # 지하1층
                            'input[value*="-1"]',  # 지하1층 (다른 표현)
                            'input[value*="1"]',   # 1층
                            'input[value*="2"]',   # 2층
                        ]
                        
                        floors_checked = 0
                        for floor_checkbox_selector in floor_checkboxes:
                            try:
                                checkboxes = self.page.query_selector_all(floor_checkbox_selector)
                                for checkbox in checkboxes:
                                    if not checkbox.is_checked():
                                        checkbox.check()
                                        floors_checked += 1
                                        print(f"✅ 층수 체크: {floor_checkbox_selector}")
                                        self.random_delay(0.5, 1)
                            except:
                                continue
                        
                        if floors_checked > 0:
                            print(f"✅ 총 {floors_checked}개 층수 조건 설정")
                        
                        # 적용 버튼
                        apply_btns = [
                            'button:has-text("적용")',
                            'button:has-text("확인")',
                            '.btn_apply'
                        ]
                        
                        for apply_selector in apply_btns:
                            try:
                                apply_btn = self.page.query_selector(apply_selector)
                                if apply_btn:
                                    apply_btn.click()
                                    print("✅ 층수 필터 적용 완료")
                                    self.random_delay(2, 3)
                                    return
                            except:
                                continue
                        
                        break
                except Exception as e:
                    print(f"⚠️ {selector} 층수 필터 실패: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ 층수 필터 설정 오류: {e}")
    
    def test_region_search(self, region='강남구'):
        """지역 검색 테스트"""
        try:
            print(f"🔍 {region} 지역 검색 테스트...")
            
            # 검색창 찾기
            search_selectors = [
                '#land_search',
                'input[placeholder*="지역"]',
                'input[placeholder*="검색"]',
                '.search_input input'
            ]
            
            for selector in search_selectors:
                try:
                    search_input = self.page.query_selector(selector)
                    if search_input:
                        print(f"✅ 검색창 발견: {selector}")
                        search_input.click()
                        self.random_delay(1, 2)
                        search_input.fill('')
                        search_input.type(region, delay=100)
                        self.random_delay(1, 2)
                        self.page.keyboard.press('Enter')
                        print(f"✅ {region} 검색 완료")
                        self.random_delay(5, 8)
                        return True
                except:
                    continue
            
            print("❌ 검색창을 찾을 수 없음")
            return False
            
        except Exception as e:
            print(f"❌ 지역 검색 오류: {e}")
            return False
    
    def test_property_extraction(self):
        """매물 추출 테스트"""
        try:
            print("🏠 매물 리스트 추출 테스트...")
            
            # 매물 요소 찾기
            property_selectors = [
                '.item_inner',
                '.list_item',
                '.property_item',
                '.commercial_item',
                '.item_area'
            ]
            
            found_properties = []
            for selector in property_selectors:
                try:
                    elements = self.page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        print(f"✅ 매물 요소 발견: {selector} ({len(elements)}개)")
                        
                        # 처음 5개 매물 정보 추출 테스트
                        for i, element in enumerate(elements[:5]):
                            try:
                                text = element.inner_text()
                                print(f"📋 매물 {i+1}: {text[:100]}...")
                                found_properties.append(text)
                            except:
                                continue
                        break
                except:
                    continue
            
            if found_properties:
                print(f"✅ 총 {len(found_properties)}개 매물 정보 추출 성공")
                return True
            else:
                print("❌ 매물 정보를 찾을 수 없음")
                return False
                
        except Exception as e:
            print(f"❌ 매물 추출 오류: {e}")
            return False
    
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
    """브라우저 필터링 테스트 실행"""
    print("🧪 브라우저 기반 필터링 테스트 시작...")
    
    scraper = BrowserFilterScraper(headless=False)  # 브라우저 창 보이기
    
    try:
        # 1. 필터 설정 테스트
        print("\n=== 1단계: 필터 설정 테스트 ===")
        if scraper.test_filter_setup():
            print("✅ 필터 설정 테스트 성공")
        else:
            print("❌ 필터 설정 테스트 실패")
            return
        
        # 2. 지역 검색 테스트
        print("\n=== 2단계: 지역 검색 테스트 ===")
        if scraper.test_region_search('강남구'):
            print("✅ 지역 검색 테스트 성공")
        else:
            print("❌ 지역 검색 테스트 실패")
            return
        
        # 3. 매물 추출 테스트
        print("\n=== 3단계: 매물 추출 테스트 ===")
        if scraper.test_property_extraction():
            print("✅ 매물 추출 테스트 성공")
        else:
            print("❌ 매물 추출 테스트 실패")
        
        print("\n🎉 모든 테스트 완료! 15초 후 브라우저 종료...")
        scraper.random_delay(15, 15)
        
    except Exception as e:
        print(f"❌ 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        scraper.close_browser()

if __name__ == "__main__":
    main()
