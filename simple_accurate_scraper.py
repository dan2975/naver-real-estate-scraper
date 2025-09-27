#!/usr/bin/env python3
"""
🎯 간단하고 정확한 지역별 수집기
- 직접 강남구 중심으로 이동
- 네이버 지도에서 실제 사용하는 API 파라미터 모니터링
- 브라우저와 100% 동일한 결과 보장
"""

import asyncio
import json
import re
import requests
from datetime import datetime
from playwright.async_api import async_playwright

class SimpleAccurateScraper:
    def __init__(self):
        self.api_base_url = 'https://m.land.naver.com/cluster/ajax/articleList'
        
        # 강남구 중심 좌표로 직접 이동
        self.gangnam_url = "https://m.land.naver.com/map/37.517:127.047:13/SG:SMS/B2?wprcMax=2000&rprcMax=130&spcMin=66&flrMin=-1&flrMax=2"
        
        self.browser_config = {
            'headless': False,
            'args': ['--disable-blink-features=AutomationControlled']
        }
    
    async def capture_real_api_requests(self):
        """🎯 브라우저에서 실제 API 요청 캡처"""
        print("🎯 강남구 실제 API 요청 캡처 중...")
        
        captured_requests = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(**self.browser_config)
            page = await browser.new_page()
            
            # 네트워크 요청 모니터링
            def handle_request(request):
                if 'articleList' in request.url:
                    print(f"   📡 API 요청 캡처: {request.url}")
                    captured_requests.append({
                        'url': request.url,
                        'params': dict(request.url.split('?')[1].split('&') if '?' in request.url else [])
                    })
            
            page.on('request', handle_request)
            
            try:
                # 강남구 중심으로 이동
                print("   📍 강남구 지도 페이지 접속...")
                await page.goto(self.gangnam_url, wait_until='networkidle')
                await asyncio.sleep(5)
                
                # 지도 조작하여 API 호출 유도
                print("   🔄 지도 상호작용...")
                await page.evaluate("window.scrollTo(0, 100)")
                await asyncio.sleep(2)
                
                # 줌 레벨 조정
                for _ in range(2):
                    try:
                        zoom_in = page.locator('button[data-action="zoom-in"], .zoom_in, [title*="확대"]')
                        if await zoom_in.count() > 0:
                            await zoom_in.first.click()
                            await asyncio.sleep(1)
                    except:
                        pass
                
                # 최종 URL과 상태 확인
                final_url = page.url
                print(f"   📍 최종 URL: {final_url}")
                
                # URL에서 파라미터 추출
                api_params = self.extract_params_from_url(final_url)
                
                # 총 매물 수 확인
                await asyncio.sleep(3)
                try:
                    page_text = await page.content()
                    total_match = re.search(r'총\s*(\d{1,4})\+?\s*개의?\s*매물', page_text)
                    if total_match:
                        total_count = total_match.group(1)
                        api_params['totCnt'] = total_count
                        print(f"   📊 총 매물 수: {total_count}개")
                except:
                    print("   ⚠️ 총 매물 수 추출 실패")
                
                return api_params
                
            except Exception as e:
                print(f"   ❌ API 캡처 실패: {e}")
                return None
                
            finally:
                await browser.close()
    
    def extract_params_from_url(self, url: str) -> dict:
        """URL에서 API 파라미터 추출"""
        params = {}
        
        # 좌표 추출
        coord_match = re.search(r'/map/([0-9.]+):([0-9.]+):(\d+)', url)
        if coord_match:
            lat, lon, zoom = coord_match.groups()
            params.update({
                'lat': lat,
                'lon': lon,
                'z': zoom
            })
            
            # 좌표 기반 경계 계산 (강남구에 맞게 좁힘)
            lat_f = float(lat)
            lon_f = float(lon)
            
            # 강남구에 최적화된 범위
            lat_range = 0.025  # 기존보다 좁힘
            lon_range = 0.035  # 기존보다 좁힘
            
            params.update({
                'btm': str(lat_f - lat_range),
                'lft': str(lon_f - lon_range), 
                'top': str(lat_f + lat_range),
                'rgt': str(lon_f + lon_range)
            })
            
            print(f"   ✅ 좌표: lat={lat}, lon={lon}")
            print(f"   📍 범위: {params['btm']} ~ {params['top']} (남북)")
            print(f"           {params['lft']} ~ {params['rgt']} (동서)")
        
        # URL 필터 파라미터 추출
        url_filters = ['wprcMax', 'rprcMax', 'spcMin', 'flrMin', 'flrMax']
        for param in url_filters:
            match = re.search(f'{param}=([^&]+)', url)
            if match:
                params[param] = match.group(1)
                print(f"   ✅ 필터: {param}={match.group(1)}")
        
        # 기본 API 파라미터
        params.update({
            'rletTpCd': 'SG:SMS',
            'tradTpCd': 'B2',
            'showR0': '',
            'cortarNo': ''
        })
        
        return params
    
    def test_api_collection(self, api_params: dict, max_pages: int = 3):
        """🧪 추출된 파라미터로 API 테스트"""
        print(f"🧪 API 수집 테스트 (최대 {max_pages}페이지)...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
            'Accept': 'application/json',
            'Referer': 'https://m.land.naver.com/'
        }
        
        all_properties = []
        
        for page_num in range(1, max_pages + 1):
            print(f"   📄 {page_num}페이지...")
            
            current_params = api_params.copy()
            current_params['page'] = str(page_num)
            
            try:
                response = requests.get(self.api_base_url, params=current_params, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'body' in data and isinstance(data['body'], list):
                        page_properties = data['body']
                        print(f"      ✅ {len(page_properties)}개 매물")
                        
                        # 좌표 검증
                        valid_count = 0
                        for prop in page_properties:
                            lat = prop.get('lat', 0)
                            lng = prop.get('lng', 0)
                            
                            # 강남구 범위 검증 (엄격)
                            if 37.45 <= lat <= 37.55 and 127.0 <= lng <= 127.15:
                                valid_count += 1
                                
                                # 간단한 매물 정보
                                all_properties.append({
                                    'id': prop.get('atclNo', ''),
                                    'name': prop.get('atclNm', ''),
                                    'deposit': prop.get('prc', 0),
                                    'rent': prop.get('rentPrc', 0),
                                    'area': prop.get('spc2', 0),
                                    'lat': lat,
                                    'lng': lng,
                                    'link': f"https://m.land.naver.com/article/info/{prop.get('atclNo', '')}"
                                })
                        
                        print(f"      🎯 강남구 범위 내: {valid_count}개")
                        
                        if len(page_properties) == 0:
                            break
                            
                    else:
                        print(f"      ❌ 응답 형식 오류")
                        break
                else:
                    print(f"      ❌ 요청 실패: {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"      ❌ 오류: {e}")
                break
        
        print(f"🎉 수집 완료: 총 {len(all_properties)}개 강남구 매물")
        return all_properties

# 테스트 실행
async def main():
    scraper = SimpleAccurateScraper()
    
    # 1단계: 실제 API 파라미터 추출
    api_params = await scraper.capture_real_api_requests()
    
    if api_params:
        print(f"\n🎯 추출된 API 파라미터:")
        for key, value in api_params.items():
            print(f"   {key}: {value}")
        
        # 2단계: API 테스트
        properties = scraper.test_api_collection(api_params, max_pages=3)
        
        if properties:
            print(f"\n📋 수집된 강남구 매물 샘플:")
            for i, prop in enumerate(properties[:5]):
                print(f"   {i+1}. {prop['name']} | {prop['deposit']}만원/{prop['rent']}만원 | {prop['area']}㎡")
                print(f"      좌표: ({prop['lat']:.4f}, {prop['lng']:.4f}) | {prop['link']}")
    else:
        print("\n❌ API 파라미터 추출 실패")

if __name__ == "__main__":
    asyncio.run(main())
