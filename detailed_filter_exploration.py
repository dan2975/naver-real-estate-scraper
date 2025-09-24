#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 부동산 상가 필터 상세 탐색
실제 상가 페이지에서 필터 요소들을 찾아서 조건 설정 방법 파악
"""

import time
import random
from playwright.sync_api import sync_playwright

class DetailedFilterExplorer:
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
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
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
        print("🏢 상가 페이지로 이동 중...")
        try:
            # 네이버 부동산 메인 접속
            self.page.goto('https://new.land.naver.com', wait_until='networkidle')
            self.random_delay(3, 5)
            
            # '상가업무공장토지' 탭 클릭
            print("🔍 상가 탭 찾는 중...")
            commercial_tab_clicked = False
            
            # 탭 텍스트로 찾기
            tab_texts = ['상가업무공장토지', '상가', '업무', '오피스텔']
            for text in tab_texts:
                try:
                    # 다양한 방법으로 탭 찾기
                    selectors = [
                        f'button:has-text("{text}")',
                        f'a:has-text("{text}")',
                        f'span:has-text("{text}")',
                        f'div:has-text("{text}")'
                    ]
                    
                    for selector in selectors:
                        try:
                            element = self.page.query_selector(selector)
                            if element:
                                print(f"✅ 상가 탭 발견: {text} ({selector})")
                                element.click()
                                commercial_tab_clicked = True
                                self.random_delay(3, 5)
                                break
                        except:
                            continue
                    
                    if commercial_tab_clicked:
                        break
                except:
                    continue
            
            if not commercial_tab_clicked:
                print("⚠️ 탭 클릭 실패, 직접 URL 접속")
                # 상가 직접 URL 접속 시도
                urls = [
                    'https://new.land.naver.com/search?ms=37.5665,126.9784,13&a=SG',
                    'https://new.land.naver.com/search?ms=37.5665,126.9784,13&a=OPST',
                    'https://new.land.naver.com/search?ms=37.5665,126.9784,13&a=SG:OPST'
                ]
                
                for url in urls:
                    try:
                        print(f"🌐 URL 직접 접속: {url}")
                        self.page.goto(url, wait_until='networkidle')
                        self.random_delay(3, 5)
                        
                        # 페이지가 제대로 로드되었는지 확인
                        title = self.page.title()
                        print(f"📄 페이지 제목: {title}")
                        
                        if '네이버 부동산' in title:
                            print("✅ 상가 페이지 접속 성공")
                            return True
                    except Exception as e:
                        print(f"❌ {url} 접속 실패: {e}")
                        continue
            else:
                print("✅ 상가 탭 클릭 성공")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ 상가 페이지 이동 오류: {e}")
            return False
    
    def explore_page_structure(self):
        """페이지 구조 탐색"""
        print("\n=== 📋 페이지 구조 탐색 ===")
        
        try:
            # 현재 URL 확인
            current_url = self.page.url
            print(f"🌐 현재 URL: {current_url}")
            
            # 페이지의 주요 섹션들 찾기
            sections = [
                'header', 'nav', 'main', 'aside', 'footer',
                '.header', '.nav', '.main', '.sidebar', '.content',
                '.filter', '.search', '.list', '.map'
            ]
            
            print("📍 발견된 주요 섹션들:")
            for section in sections:
                try:
                    elements = self.page.query_selector_all(section)
                    if elements:
                        print(f"  - {section}: {len(elements)}개")
                except:
                    continue
            
            # 모든 버튼 찾기
            buttons = self.page.query_selector_all('button')
            button_texts = []
            for btn in buttons:
                try:
                    text = btn.inner_text().strip()
                    if text and len(text) < 20 and text not in button_texts:
                        button_texts.append(text)
                except:
                    continue
            
            print(f"🔘 페이지 내 버튼들 ({len(button_texts)}개):")
            for i, text in enumerate(button_texts[:20]):  # 처음 20개만
                print(f"  {i+1}. '{text}'")
            
            return button_texts
            
        except Exception as e:
            print(f"❌ 페이지 구조 탐색 오류: {e}")
            return []
    
    def find_filter_elements(self):
        """필터 관련 요소들 찾기"""
        print("\n=== 🎛️ 필터 요소 상세 탐색 ===")
        
        try:
            # 다양한 필터 관련 키워드로 요소 찾기
            filter_keywords = ['필터', '조건', '가격', '면적', '층', '보증금', '월세', '임대료']
            
            found_elements = []
            
            for keyword in filter_keywords:
                try:
                    # 텍스트 포함하는 모든 요소 찾기
                    elements = self.page.query_selector_all(f'*:has-text("{keyword}")')
                    
                    for element in elements[:5]:  # 각 키워드당 최대 5개
                        try:
                            tag = element.evaluate('el => el.tagName.toLowerCase()')
                            text = element.inner_text().strip()[:50]
                            class_name = element.get_attribute('class') or ''
                            
                            found_elements.append({
                                'keyword': keyword,
                                'tag': tag,
                                'text': text,
                                'class': class_name
                            })
                        except:
                            continue
                except:
                    continue
            
            print("🔍 필터 관련 요소들:")
            for elem in found_elements[:15]:  # 처음 15개만
                print(f"  - {elem['keyword']}: <{elem['tag']}> '{elem['text']}' (class: {elem['class'][:30]}...)")
            
            return found_elements
            
        except Exception as e:
            print(f"❌ 필터 요소 탐색 오류: {e}")
            return []
    
    def explore_input_fields(self):
        """모든 입력 필드 탐색"""
        print("\n=== 📝 입력 필드 탐색 ===")
        
        try:
            # 모든 input 요소 찾기
            inputs = self.page.query_selector_all('input')
            print(f"📄 총 발견된 input: {len(inputs)}개")
            
            for i, inp in enumerate(inputs):
                try:
                    type_attr = inp.get_attribute('type') or 'text'
                    placeholder = inp.get_attribute('placeholder') or ''
                    name = inp.get_attribute('name') or ''
                    id_attr = inp.get_attribute('id') or ''
                    class_name = inp.get_attribute('class') or ''
                    value = inp.get_attribute('value') or ''
                    
                    # 관련성 있는 필드만 출력
                    relevant_keywords = ['가격', '보증금', '월세', '면적', '평', '층', '검색', '임대료']
                    is_relevant = any(keyword in f"{placeholder}{name}{id_attr}{class_name}".lower() for keyword in relevant_keywords)
                    
                    if is_relevant or type_attr in ['number', 'range'] or placeholder:
                        print(f"  {i+1}. type='{type_attr}', placeholder='{placeholder}', name='{name}', id='{id_attr}', class='{class_name[:30]}...', value='{value}'")
                        
                except:
                    continue
            
            # select 요소들도 찾기
            selects = self.page.query_selector_all('select')
            if selects:
                print(f"\n📋 select 요소: {len(selects)}개")
                for i, select in enumerate(selects):
                    try:
                        name = select.get_attribute('name') or ''
                        id_attr = select.get_attribute('id') or ''
                        class_name = select.get_attribute('class') or ''
                        print(f"  {i+1}. name='{name}', id='{id_attr}', class='{class_name[:30]}...'")
                    except:
                        continue
            
        except Exception as e:
            print(f"❌ 입력 필드 탐색 오류: {e}")
    
    def test_search_functionality(self):
        """검색 기능 테스트"""
        print("\n=== 🔍 검색 기능 테스트 ===")
        
        try:
            # 검색창 찾기
            search_selectors = [
                'input[placeholder*="검색"]',
                'input[placeholder*="지역"]',
                'input[type="search"]',
                '#land_search',
                '.search_input input',
                '.autocomplete_input input'
            ]
            
            for selector in search_selectors:
                try:
                    search_input = self.page.query_selector(selector)
                    if search_input:
                        print(f"✅ 검색창 발견: {selector}")
                        
                        # 테스트 검색어 입력
                        test_query = "강남구"
                        search_input.click()
                        self.random_delay(1, 2)
                        search_input.fill('')
                        search_input.type(test_query, delay=100)
                        self.random_delay(1, 2)
                        
                        print(f"🔍 '{test_query}' 입력 완료")
                        
                        # Enter 키 또는 검색 버튼 클릭
                        self.page.keyboard.press('Enter')
                        self.random_delay(3, 5)
                        
                        print("✅ 검색 실행 완료")
                        return True
                        
                except Exception as e:
                    print(f"⚠️ {selector} 검색 실패: {e}")
                    continue
            
            print("❌ 검색창을 찾을 수 없음")
            return False
            
        except Exception as e:
            print(f"❌ 검색 기능 테스트 오류: {e}")
            return False
    
    def explore_after_search(self):
        """검색 후 페이지 상태 탐색"""
        print("\n=== 📊 검색 후 페이지 탐색 ===")
        
        try:
            # 검색 결과 확인
            print("🔍 검색 결과 확인 중...")
            
            # 매물 리스트 요소 찾기
            list_selectors = [
                '.item_inner',
                '.list_item',
                '.property_item',
                '.commercial_item',
                '.item_area',
                '.item_box'
            ]
            
            for selector in list_selectors:
                try:
                    items = self.page.query_selector_all(selector)
                    if items:
                        print(f"🏠 매물 리스트 발견: {selector} ({len(items)}개)")
                        
                        # 첫 번째 매물 정보 확인
                        if items:
                            first_item = items[0]
                            text = first_item.inner_text()[:100]
                            print(f"📋 첫 번째 매물 샘플: {text}...")
                        break
                except:
                    continue
            
            # 필터 상태 재확인
            print("\n🎛️ 검색 후 필터 상태:")
            buttons = self.page.query_selector_all('button')
            filter_buttons = []
            
            for btn in buttons:
                try:
                    text = btn.inner_text().strip()
                    if text and any(keyword in text for keyword in ['가격', '면적', '층', '필터', '조건']):
                        filter_buttons.append(text)
                except:
                    continue
            
            print(f"🔘 필터 관련 버튼들: {filter_buttons}")
            
            return True
            
        except Exception as e:
            print(f"❌ 검색 후 탐색 오류: {e}")
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
    """상세 필터 탐색 실행"""
    print("🔍 네이버 부동산 상가 필터 상세 탐색 시작...")
    
    explorer = DetailedFilterExplorer(headless=False)
    
    try:
        explorer.setup_browser()
        
        # 1. 상가 페이지로 이동
        if explorer.go_to_commercial_page():
            
            # 2. 페이지 구조 탐색
            explorer.explore_page_structure()
            
            # 3. 필터 요소들 찾기
            explorer.find_filter_elements()
            
            # 4. 입력 필드 탐색
            explorer.explore_input_fields()
            
            # 5. 검색 기능 테스트
            if explorer.test_search_functionality():
                # 6. 검색 후 상태 탐색
                explorer.explore_after_search()
        
        print("\n🎉 상세 탐색 완료! 15초 후 브라우저 종료...")
        explorer.random_delay(15, 15)
        
    except Exception as e:
        print(f"❌ 탐색 중 오류: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        explorer.close_browser()

if __name__ == "__main__":
    main()
