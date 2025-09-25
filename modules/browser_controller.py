#!/usr/bin/env python3
"""
🌐 BrowserController - 브라우저 제어 관리
- 네이버 지도 네비게이션
- "구만 보기" 버튼 클릭
- 목록 모드 전환
- 페이지 인터랙션
"""

import asyncio
import re
from typing import Optional, Dict, Any, Tuple
from playwright.async_api import Page


class BrowserController:
    """🌐 브라우저 제어를 담당하는 클래스"""
    
    def __init__(self):
        # 기본 네이버 지도 URL (필터 적용된 상태)
        self.base_map_url = "https://m.land.naver.com/map/37.5665:126.9780:12/SG:SMS/B2?wprcMax=2000&rprcMax=130&spcMin=66&flrMin=-1&flrMax=2"
        
        # 구별 좌표 정보
        self.seoul_districts_coords = {
            '강남구': {'lat': 37.517, 'lon': 127.047},
            '강서구': {'lat': 37.551, 'lon': 126.849},
            '영등포구': {'lat': 37.526, 'lon': 126.896},
            '구로구': {'lat': 37.495, 'lon': 126.887},
            '마포구': {'lat': 37.566, 'lon': 126.901}
        }
    
    async def create_mobile_context(self, playwright):
        """📱 모바일 브라우저 컨텍스트 생성"""
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 390, 'height': 844},
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()
        return browser, context, page
    
    async def navigate_to_map_and_apply_district_filter(self, page: Page, district_name: str) -> bool:
        """🗺️ 지도로 이동하고 구별 필터 적용"""
        print(f"         🌐 {district_name} 집중 탐색 시작...")
        
        try:
            # 구별 맞춤 URL 생성
            district_url = self.create_district_focused_url(district_name)
            print(f"         🌐 {district_name} 맞춤 URL 접속...")
            
            await page.goto(district_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)
            
            # 페이지 로딩 중에 버튼 찾기 시도
            success = await self.search_during_page_load(page, district_name)
            
            if not success:
                # 페이지 로딩 완료 후 버튼 찾기
                success = await self.search_after_page_load(page, district_name)
            
            if not success:
                # 추가 페이지 인터랙션 시도
                success = await self.try_page_interactions(page, district_name)
            
            return success
            
        except Exception as e:
            print(f"         ❌ {district_name} 네비게이션 오류: {e}")
            return False
    
    def create_district_focused_url(self, district_name: str) -> str:
        """🎯 구별 집중 URL 생성"""
        coords = self.seoul_districts_coords.get(district_name)
        if coords:
            return f"https://m.land.naver.com/map/{coords['lat']}:{coords['lon']}:12/SG:SMS/B2?wprcMax=2000&rprcMax=130&spcMin=66&flrMin=-1&flrMax=2"
        return self.base_map_url
    
    async def search_during_page_load(self, page: Page, district_name: str) -> bool:
        """⏳ 페이지 로딩 중 버튼 탐색"""
        print(f"         ⏳ 페이지 로딩 중 {district_name}만 보기 버튼 탐색...")
        
        max_attempts = 10
        for attempt in range(1, max_attempts + 1):
            try:
                await asyncio.sleep(0.5)
                
                if await self.check_district_button_exists(page, district_name):
                    print(f"         ✅ 로딩 중 {district_name}만 보기 버튼 발견! (시도 {attempt})")
                    return await self.attempt_button_click(page, district_name)
                    
            except Exception as e:
                if attempt == max_attempts:
                    print(f"         ⚠️ 로딩 중 탐색 실패: {e}")
        
        return False
    
    async def search_after_page_load(self, page: Page, district_name: str) -> bool:
        """✅ 페이지 로딩 완료 후 버튼 탐색"""
        print(f"         ✅ 로딩 완료 후 {district_name}만 보기 버튼 탐색...")
        
        try:
            await page.wait_for_load_state('networkidle', timeout=10000)
            await asyncio.sleep(2)
            
            if await self.check_district_button_exists(page, district_name):
                print(f"         ✅ 로딩 완료 후 {district_name}만 보기 버튼 발견!")
                return await self.attempt_button_click(page, district_name)
                
        except Exception as e:
            print(f"         ⚠️ 로딩 완료 후 탐색 실패: {e}")
        
        return False
    
    async def try_page_interactions(self, page: Page, district_name: str) -> bool:
        """🔄 추가 페이지 인터랙션"""
        print(f"         🔄 {district_name} 추가 인터랙션 시도...")
        
        interactions = [
            lambda: page.evaluate("window.scrollTo(0, 100)"),
            lambda: page.evaluate("window.scrollTo(0, 0)"),
            lambda: page.tap("body") if hasattr(page, 'tap') else None,
        ]
        
        for i, interaction in enumerate(interactions, 1):
            try:
                if interaction:
                    await interaction()
                await asyncio.sleep(1)
                
                if await self.check_district_button_exists(page, district_name):
                    print(f"         ✅ 인터랙션 {i} 후 {district_name}만 보기 버튼 발견!")
                    return await self.attempt_button_click(page, district_name)
                    
            except Exception as e:
                print(f"         ⚠️ 인터랙션 {i} 실패: {e}")
        
        return False
    
    async def check_district_button_exists(self, page: Page, district_name: str) -> bool:
        """🔍 구만 보기 버튼 존재 확인"""
        selectors = [
            f"button:has-text('{district_name}만 보기')",
            f"a:has-text('{district_name}만 보기')",
            f"div:has-text('{district_name}만 보기')",
            f"span:has-text('{district_name}만 보기')",
            f"*:has-text('{district_name}만')",
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if district_name in text and '보기' in text:
                        return True
            except:
                continue
        
        return False
    
    async def attempt_button_click(self, page: Page, district_name: str) -> bool:
        """🎯 버튼 클릭 시도"""
        try:
            # 더 정확한 선택자들
            selectors = [
                f"button:has-text('{district_name}만 보기')",
                f"a:has-text('{district_name}만 보기')",
                f"div[role='button']:has-text('{district_name}만 보기')",
                f"*:has-text('{district_name}만 보기')"
            ]
            
            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if district_name in text and '보기' in text:
                            print(f"         🎯 {district_name}만 보기 버튼 클릭: \"{text.strip()}\"")
                            await element.click()
                            await asyncio.sleep(2)
                            print(f"         ✅ {district_name}만 보기 클릭 완료")
                            return True
                except Exception as e:
                    continue
            
            print(f"         ❌ {district_name}만 보기 버튼 클릭 실패")
            return False
            
        except Exception as e:
            print(f"         ❌ 버튼 클릭 중 오류: {e}")
            return False
    
    async def switch_to_list_mode(self, page: Page) -> bool:
        """📋 목록 모드로 전환"""
        print(f"         📋 목록 모드 전환 중...")
        
        try:
            # 목록 모드 버튼 찾기
            list_selectors = [
                "button:has-text('목록')",
                "a:has-text('목록')",
                "*[data-nclicks*='list']",
                "*:has-text('목록')"
            ]
            
            for selector in list_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        await element.click()
                        await asyncio.sleep(2)
                        print(f"         ✅ 목록 모드 활성화")
                        return True
                except:
                    continue
            
            # URL 해시로 목록 모드 강제 활성화
            current_url = page.url
            if '#mapFullList' not in current_url:
                new_url = current_url + '#mapFullList'
                await page.goto(new_url)
                await asyncio.sleep(2)
                print(f"         ✅ 목록 모드 활성화")
                return True
            
            return True
            
        except Exception as e:
            print(f"         ⚠️ 목록 모드 전환 실패: {e}")
            return False
    
    async def extract_api_params_from_browser(self, page: Page, district_name: str) -> Optional[Dict[str, Any]]:
        """🔍 브라우저에서 API 파라미터 추출"""
        try:
            current_url = page.url
            print(f"            📍 현재 URL: {current_url}")
            
            # URL에서 좌표 추출
            coord_match = re.search(r'/map/([0-9.]+):([0-9.]+):(\d+)', current_url)
            if not coord_match:
                print(f"            ❌ URL에서 좌표 추출 실패")
                return None
            
            lat, lon, zoom = coord_match.groups()
            print(f"            ✅ URL에서 좌표 추출: lat={lat}, lon={lon}")
            
            # 필터 파라미터 추출
            api_params = {
                'lat': float(lat),
                'lon': float(lon),
                'zoom': int(zoom),
                'district_name': district_name
            }
            
            # URL 파라미터 파싱
            url_params = [
                ('wprcMax', 'wprcMax'),
                ('rprcMax', 'rprcMax'), 
                ('spcMin', 'spcMin'),
                ('flrMin', 'flrMin'),
                ('flrMax', 'flrMax')
            ]
            
            for url_param, api_param in url_params:
                match = re.search(f'{url_param}=([^&]+)', current_url)
                if match:
                    value = match.group(1)
                    api_params[api_param] = value
                    print(f"            ✅ 필터 적용: {api_param}={value}")
            
            return api_params
            
        except Exception as e:
            print(f"            ❌ API 파라미터 추출 실패: {e}")
            return None
    
    async def get_page_info(self, page: Page) -> Dict[str, Any]:
        """📊 페이지 정보 반환"""
        try:
            return {
                'url': page.url,
                'title': await page.title(),
                'viewport': await page.viewport_size(),
                'user_agent': await page.evaluate('navigator.userAgent')
            }
        except Exception as e:
            return {'error': str(e)}
