#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 부동산 필터 옵션 탐색
브라우저에서 실제 필터 버튼들을 클릭하여 어떤 옵션들이 있는지 파악
"""

import time
import random
from playwright.sync_api import sync_playwright

class FilterExplorer:
    def __init__(self, headless=False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None
        
    def setup_browser(self):
        """브라우저 설정"""
        self.playwright = sync_playwright().start()
        
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
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
        
    def explore_main_tabs(self):
        """메인 탭들 탐색 (아파트, 상가, 오피스텔 등)"""
        print("\n=== 📋 메인 탭 탐색 ===")
        
        try:
            # 네이버 부동산 접속
            self.page.goto('https://new.land.naver.com', wait_until='networkidle')
            print("✅ 네이버 부동산 접속 완료")
            self.random_delay(3, 5)
            
            # 탭 요소들 찾기
            tab_selectors = [
                'a[href*="APT"]',  # 아파트
                'a[href*="VL"]',   # 빌라
                'a[href*="SG"]',   # 상가
                'a[href*="OPST"]', # 오피스텔
                '.tab_item',
                '.nav_tab',
                '[role="tab"]',
                '.filter_tab'
            ]
            
            found_tabs = []
            for selector in tab_selectors:
                try:
                    tabs = self.page.query_selector_all(selector)
                    for tab in tabs:
                        try:
                            text = tab.inner_text().strip()
                            href = tab.get_attribute('href') or ''
                            if text and text not in [t['text'] for t in found_tabs]:
                                found_tabs.append({
                                    'text': text,
                                    'href': href,
                                    'selector': selector
                                })
                        except:
                            continue
                except:
                    continue
            
            print("🔍 발견된 탭들:")
            for i, tab in enumerate(found_tabs[:10]):  # 처음 10개만
                print(f"  {i+1}. {tab['text']} (href: {tab['href'][:50]}...)")
            
            return found_tabs
            
        except Exception as e:
            print(f"❌ 메인 탭 탐색 오류: {e}")
            return []
    
    def explore_commercial_tab(self):
        """상가 탭 클릭하고 옵션 확인"""
        print("\n=== 🏢 상가 탭 탐색 ===")
        
        try:
            # 상가 탭 찾기 및 클릭
            commercial_selectors = [
                'a[href*="SG"]',
                'a[href*="OPST"]',
                'button:has-text("상가")',
                'button:has-text("오피스텔")',
                '.tab_commercial',
                '[data-tab="SG"]'
            ]
            
            commercial_clicked = False
            for selector in commercial_selectors:
                try:
                    tabs = self.page.query_selector_all(selector)
                    for tab in tabs:
                        try:
                            text = tab.inner_text().strip()
                            if '상가' in text or '오피스텔' in text:
                                print(f"✅ 상가/오피스텔 탭 발견: {text} ({selector})")
                                tab.click()
                                commercial_clicked = True
                                self.random_delay(3, 5)
                                break
                        except:
                            continue
                    if commercial_clicked:
                        break
                except:
                    continue
            
            if not commercial_clicked:
                print("⚠️ 상가 탭을 직접 찾을 수 없음, URL로 접속")
                # 상가/오피스텔 페이지로 직접 이동
                self.page.goto('https://new.land.naver.com/search?ms=37.5665,126.9784,13&a=SG:OPST', wait_until='networkidle')
                self.random_delay(3, 5)
            
            print("✅ 상가 페이지 접속 완료")
            return True
            
        except Exception as e:
            print(f"❌ 상가 탭 탐색 오류: {e}")
            return False
    
    def explore_filter_buttons(self):
        """필터 버튼들 탐색"""
        print("\n=== 🎛️ 필터 버튼 탐색 ===")
        
        try:
            # 필터 버튼들 찾기
            filter_selectors = [
                'button:has-text("가격")',
                'button:has-text("면적")',
                'button:has-text("층")',
                'button:has-text("층수")',
                'button:has-text("필터")',
                'button:has-text("더보기")',
                '.filter_btn',
                '.btn_filter',
                '.filter_item',
                '[data-filter]',
                '.price_filter',
                '.area_filter',
                '.floor_filter'
            ]
            
            found_filters = []
            for selector in filter_selectors:
                try:
                    buttons = self.page.query_selector_all(selector)
                    for button in buttons:
                        try:
                            text = button.inner_text().strip()
                            if text and len(text) < 20 and text not in [f['text'] for f in found_filters]:
                                found_filters.append({
                                    'text': text,
                                    'selector': selector,
                                    'element': button
                                })
                        except:
                            continue
                except:
                    continue
            
            print("🔍 발견된 필터 버튼들:")
            for i, filter_btn in enumerate(found_filters):
                print(f"  {i+1}. '{filter_btn['text']}' ({filter_btn['selector']})")
            
            return found_filters
            
        except Exception as e:
            print(f"❌ 필터 버튼 탐색 오류: {e}")
            return []
    
    def explore_price_filter(self):
        """가격 필터 상세 탐색"""
        print("\n=== 💰 가격 필터 상세 탐색 ===")
        
        try:
            # 가격 필터 버튼 찾기 및 클릭
            price_selectors = [
                'button:has-text("가격")',
                '.filter_price',
                '.btn_price',
                '[data-filter="price"]'
            ]
            
            for selector in price_selectors:
                try:
                    price_btn = self.page.query_selector(selector)
                    if price_btn:
                        print(f"✅ 가격 필터 버튼 발견: {selector}")
                        price_btn.click()
                        self.random_delay(2, 3)
                        
                        # 가격 필터 옵션들 탐색
                        print("🔍 가격 필터 내부 옵션 탐색...")
                        
                        # 입력 필드들 찾기
                        inputs = self.page.query_selector_all('input')
                        print(f"📝 발견된 입력 필드: {len(inputs)}개")
                        
                        for i, inp in enumerate(inputs):
                            try:
                                placeholder = inp.get_attribute('placeholder') or ''
                                name = inp.get_attribute('name') or ''
                                type_attr = inp.get_attribute('type') or ''
                                value = inp.get_attribute('value') or ''
                                
                                if any(keyword in placeholder.lower() for keyword in ['가격', '보증금', '월세', '임대료']):
                                    print(f"  💰 가격 관련 입력: placeholder='{placeholder}', name='{name}', type='{type_attr}', value='{value}'")
                            except:
                                continue
                        
                        # 버튼들 찾기
                        buttons = self.page.query_selector_all('button')
                        price_buttons = []
                        for btn in buttons:
                            try:
                                text = btn.inner_text().strip()
                                if text and len(text) < 20:
                                    price_buttons.append(text)
                            except:
                                continue
                        
                        print(f"🔘 가격 필터 내 버튼들: {price_buttons[:10]}")
                        
                        # 닫기 (ESC 또는 외부 클릭)
                        self.page.keyboard.press('Escape')
                        self.random_delay(1, 2)
                        
                        return True
                except Exception as e:
                    print(f"⚠️ {selector} 가격 필터 탐색 실패: {e}")
                    continue
            
            print("❌ 가격 필터 버튼을 찾을 수 없음")
            return False
            
        except Exception as e:
            print(f"❌ 가격 필터 탐색 오류: {e}")
            return False
    
    def explore_area_filter(self):
        """면적 필터 상세 탐색"""
        print("\n=== 📐 면적 필터 상세 탐색 ===")
        
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
                        self.random_delay(2, 3)
                        
                        print("🔍 면적 필터 내부 옵션 탐색...")
                        
                        # 면적 관련 입력 필드들
                        inputs = self.page.query_selector_all('input')
                        for inp in inputs:
                            try:
                                placeholder = inp.get_attribute('placeholder') or ''
                                if any(keyword in placeholder.lower() for keyword in ['면적', '평', '㎡', '최소', '최대']):
                                    name = inp.get_attribute('name') or ''
                                    type_attr = inp.get_attribute('type') or ''
                                    print(f"  📐 면적 관련 입력: placeholder='{placeholder}', name='{name}', type='{type_attr}'")
                            except:
                                continue
                        
                        # 면적 단위 확인 (평/㎡)
                        page_text = self.page.inner_text('body')
                        if '평' in page_text:
                            print("  📏 평 단위 지원 확인")
                        if '㎡' in page_text or 'm²' in page_text:
                            print("  📏 ㎡ 단위 지원 확인")
                        
                        self.page.keyboard.press('Escape')
                        self.random_delay(1, 2)
                        return True
                        
                except Exception as e:
                    print(f"⚠️ {selector} 면적 필터 탐색 실패: {e}")
                    continue
            
            return False
            
        except Exception as e:
            print(f"❌ 면적 필터 탐색 오류: {e}")
            return False
    
    def explore_floor_filter(self):
        """층수 필터 상세 탐색"""
        print("\n=== 🏢 층수 필터 상세 탐색 ===")
        
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
                        self.random_delay(2, 3)
                        
                        print("🔍 층수 필터 내부 옵션 탐색...")
                        
                        # 체크박스들 찾기
                        checkboxes = self.page.query_selector_all('input[type="checkbox"]')
                        print(f"☑️ 발견된 체크박스: {len(checkboxes)}개")
                        
                        floor_options = []
                        for checkbox in checkboxes:
                            try:
                                value = checkbox.get_attribute('value') or ''
                                label_text = ""
                                
                                # 라벨 텍스트 찾기
                                parent = checkbox.locator('..')
                                try:
                                    label_text = parent.inner_text().strip()
                                except:
                                    pass
                                
                                if value or label_text:
                                    floor_options.append(f"value='{value}', label='{label_text}'")
                            except:
                                continue
                        
                        print("🏢 층수 옵션들:")
                        for option in floor_options[:15]:  # 처음 15개만
                            print(f"  - {option}")
                        
                        # 라디오 버튼들도 확인
                        radios = self.page.query_selector_all('input[type="radio"]')
                        if radios:
                            print(f"🔘 라디오 버튼: {len(radios)}개")
                            for radio in radios[:10]:
                                try:
                                    value = radio.get_attribute('value') or ''
                                    name = radio.get_attribute('name') or ''
                                    print(f"  - name='{name}', value='{value}'")
                                except:
                                    continue
                        
                        self.page.keyboard.press('Escape')
                        self.random_delay(1, 2)
                        return True
                        
                except Exception as e:
                    print(f"⚠️ {selector} 층수 필터 탐색 실패: {e}")
                    continue
            
            return False
            
        except Exception as e:
            print(f"❌ 층수 필터 탐색 오류: {e}")
            return False
    
    def explore_all_filters(self):
        """모든 필터 버튼 클릭해서 옵션 확인"""
        print("\n=== 🔍 전체 필터 탐색 ===")
        
        try:
            filter_buttons = self.explore_filter_buttons()
            
            for i, filter_btn in enumerate(filter_buttons[:5]):  # 처음 5개만
                try:
                    print(f"\n--- 필터 {i+1}: '{filter_btn['text']}' 탐색 ---")
                    
                    # 버튼 클릭
                    filter_btn['element'].click()
                    self.random_delay(2, 3)
                    
                    # 필터 내부 요소들 탐색
                    print("🔍 필터 내부 요소들:")
                    
                    # 모든 입력 필드
                    inputs = self.page.query_selector_all('input:visible')
                    for inp in inputs[:5]:  # 처음 5개만
                        try:
                            placeholder = inp.get_attribute('placeholder') or ''
                            type_attr = inp.get_attribute('type') or ''
                            if placeholder or type_attr:
                                print(f"  📝 입력: type='{type_attr}', placeholder='{placeholder}'")
                        except:
                            continue
                    
                    # 모든 버튼
                    buttons = self.page.query_selector_all('button:visible')
                    button_texts = []
                    for btn in buttons[:8]:  # 처음 8개만
                        try:
                            text = btn.inner_text().strip()
                            if text and len(text) < 15:
                                button_texts.append(text)
                        except:
                            continue
                    print(f"  🔘 버튼들: {button_texts}")
                    
                    # 선택 옵션들 (select, checkbox, radio)
                    selects = self.page.query_selector_all('select:visible')
                    if selects:
                        print(f"  📋 드롭다운: {len(selects)}개")
                    
                    checkboxes = self.page.query_selector_all('input[type="checkbox"]:visible')
                    if checkboxes:
                        print(f"  ☑️ 체크박스: {len(checkboxes)}개")
                    
                    # 닫기
                    self.page.keyboard.press('Escape')
                    self.random_delay(1, 2)
                    
                except Exception as e:
                    print(f"⚠️ 필터 '{filter_btn['text']}' 탐색 실패: {e}")
                    continue
            
        except Exception as e:
            print(f"❌ 전체 필터 탐색 오류: {e}")
    
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
    """필터 탐색 실행"""
    print("🔍 네이버 부동산 필터 옵션 탐색 시작...")
    
    explorer = FilterExplorer(headless=False)  # 브라우저 창 보이기
    
    try:
        explorer.setup_browser()
        
        # 1. 메인 탭들 탐색
        tabs = explorer.explore_main_tabs()
        
        # 2. 상가 탭으로 이동
        if explorer.explore_commercial_tab():
            
            # 3. 각종 필터들 탐색
            explorer.explore_price_filter()
            explorer.explore_area_filter()
            explorer.explore_floor_filter()
            
            # 4. 전체 필터 탐색
            explorer.explore_all_filters()
        
        print("\n🎉 필터 탐색 완료! 10초 후 브라우저 종료...")
        explorer.random_delay(10, 10)
        
    except Exception as e:
        print(f"❌ 탐색 중 오류: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        explorer.close_browser()

if __name__ == "__main__":
    main()
