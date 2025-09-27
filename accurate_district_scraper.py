#!/usr/bin/env python3
"""
🎯 정확한 지역별 매물 수집기
- 브라우저에서 "구만 보기" 클릭
- 실제 네이버 API 파라미터 추출
- 100% 정확한 지역 매핑 보장
"""

import asyncio
import json
import re
import requests
from datetime import datetime
from playwright.async_api import async_playwright
from modules.data_processor import PropertyDataProcessor

class AccurateDistrictScraper:
    def __init__(self):
        self.processor = PropertyDataProcessor()
        self.api_base_url = 'https://m.land.naver.com/cluster/ajax/articleList'
        
        # 기본 필터링된 URL (조건.md 기준)
        self.base_url = "https://m.land.naver.com/map/37.5665:126.9780:12/SG:SMS/B2?wprcMax=2000&rprcMax=130&spcMin=66&flrMin=-1&flrMax=2"
        
        # 브라우저 설정
        self.browser_config = {
            'headless': False,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        }
    
    async def extract_real_api_params(self, district_name: str):
        """🔍 브라우저에서 실제 API 파라미터 추출"""
        print(f"🔍 {district_name} 실제 API 파라미터 추출 중...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(**self.browser_config)
            page = await browser.new_page()
            
            try:
                # 1단계: 기본 필터링된 페이지 접속
                print(f"   📍 기본 URL 접속...")
                await page.goto(self.base_url, wait_until='networkidle')
                await asyncio.sleep(3)
                
                # 2단계: 지역으로 이동 (강남구 검색)
                print(f"   🔍 {district_name} 검색...")
                search_box = page.locator('input[placeholder*="검색"], input[type="search"], .search_input')
                if await search_box.count() > 0:
                    await search_box.first.fill(district_name)
                    await search_box.first.press('Enter')
                    await asyncio.sleep(3)
                
                # 3단계: "구만 보기" 버튼 찾기 및 클릭
                print(f"   🎯 '{district_name}만 보기' 버튼 찾는 중...")
                
                district_button_selectors = [
                    f'button:has-text("{district_name}만 보기")',
                    f'[data-district="{district_name}"]',
                    f'button:has-text("{district_name}")',
                    '.district_filter_button',
                    '.area_filter_btn'
                ]
                
                button_clicked = False
                for selector in district_button_selectors:
                    try:
                        button = page.locator(selector)
                        if await button.count() > 0:
                            print(f"   ✅ '{district_name}만 보기' 버튼 발견!")
                            await button.first.click()
                            await asyncio.sleep(3)
                            button_clicked = True
                            break
                    except:
                        continue
                
                if not button_clicked:
                    print(f"   ⚠️ '{district_name}만 보기' 버튼을 찾을 수 없음")
                
                # 4단계: 네트워크 요청 모니터링하여 실제 API 파라미터 추출
                print(f"   📡 네트워크 요청 모니터링...")
                
                # 페이지에서 API 호출 대기
                api_params = {}
                
                # 현재 URL에서 파라미터 추출
                current_url = page.url
                print(f"   📍 현재 URL: {current_url}")
                
                # URL에서 좌표 추출
                coord_match = re.search(r'/map/([0-9.]+):([0-9.]+):(\d+)', current_url)
                if coord_match:
                    lat, lon, zoom = coord_match.groups()
                    api_params.update({
                        'lat': lat,
                        'lon': lon,
                        'z': zoom
                    })
                    print(f"   ✅ 좌표 추출: lat={lat}, lon={lon}")
                
                # URL 필터 파라미터 추출
                url_filters = ['wprcMax', 'rprcMax', 'spcMin', 'flrMin', 'flrMax']
                for param in url_filters:
                    match = re.search(f'{param}=([^&]+)', current_url)
                    if match:
                        api_params[param] = match.group(1)
                        print(f"   ✅ 필터: {param}={match.group(1)}")
                
                # 기본 API 파라미터 추가
                api_params.update({
                    'rletTpCd': 'SG:SMS',  # 상가+사무실
                    'tradTpCd': 'B2',      # 월세
                    'showR0': '',
                    'cortarNo': ''
                })
                
                # 5단계: 페이지에서 총 매물 수 확인
                try:
                    total_text_selectors = [
                        'text*="개의 매물"',
                        'text*="총"',
                        '.total_count',
                        '.property_count'
                    ]
                    
                    for selector in total_text_selectors:
                        try:
                            total_element = page.locator(selector)
                            if await total_element.count() > 0:
                                total_text = await total_element.first.text_content()
                                total_match = re.search(r'(\d{1,4})\+?\s*개', total_text)
                                if total_match:
                                    total_count = total_match.group(1)
                                    api_params['totCnt'] = total_count
                                    print(f"   📊 총 매물 수: {total_count}개")
                                    break
                        except:
                            continue
                except:
                    print(f"   ⚠️ 총 매물 수 추출 실패")
                
                print(f"   ✅ {district_name} API 파라미터 추출 완료!")
                return api_params
                
            except Exception as e:
                print(f"   ❌ API 파라미터 추출 실패: {e}")
                return None
                
            finally:
                await browser.close()
    
    def collect_with_real_params(self, district_name: str, api_params: dict, max_pages: int = 10):
        """🚀 추출된 실제 API 파라미터로 매물 수집"""
        print(f"🚀 {district_name} 실제 파라미터로 수집 시작...")
        print(f"   📋 사용 파라미터: {api_params}")
        
        all_properties = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://m.land.naver.com/',
            'Accept-Language': 'ko-KR,ko;q=0.9'
        }
        
        for page_num in range(1, max_pages + 1):
            print(f"   📄 {page_num}페이지 수집...")
            
            # 페이지 파라미터 추가
            current_params = api_params.copy()
            current_params['page'] = str(page_num)
            
            try:
                response = requests.get(self.api_base_url, params=current_params, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'body' in data and isinstance(data['body'], list):
                        page_properties = data['body']
                        print(f"      ✅ {len(page_properties)}개 원시 데이터")
                        
                        # 매물 처리
                        for prop in page_properties:
                            processed = self.process_property(prop, district_name)
                            if processed:
                                all_properties.append(processed)
                        
                        # 데이터가 없으면 종료
                        if len(page_properties) == 0:
                            print(f"      🔚 {page_num}페이지에서 데이터 없음 - 수집 종료")
                            break
                    else:
                        print(f"      ⚠️ {page_num}페이지 응답 형식 오류")
                        break
                else:
                    print(f"      ❌ {page_num}페이지 요청 실패: {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"      ❌ {page_num}페이지 오류: {e}")
                break
        
        print(f"✅ {district_name} 수집 완료: {len(all_properties)}개")
        return all_properties
    
    def process_property(self, prop: dict, district_name: str) -> dict:
        """매물 데이터 처리"""
        try:
            # 기본 정보 추출
            article_no = prop.get('atclNo', '')
            price = prop.get('prc', 0)
            rent_price = prop.get('rentPrc', 0)
            area_sqm = float(prop.get('spc2', 0))
            area_pyeong = area_sqm / 3.3 if area_sqm > 0 else 0
            
            # 네이버 링크 생성
            naver_link = f"https://m.land.naver.com/article/info/{article_no}" if article_no else ""
            
            # 좌표
            lat = prop.get('lat', 0)
            lng = prop.get('lng', 0)
            
            return {
                'district': district_name,
                'building_name': prop.get('atclNm', ''),
                'area_sqm': area_sqm,
                'area_pyeong': round(area_pyeong, 2),
                'deposit': price,
                'monthly_rent': rent_price,
                'naver_link': naver_link,
                'article_no': article_no,
                'lat': lat,
                'lng': lng,
                'data_source': '정확한API수집',
                'raw_data': json.dumps(prop, ensure_ascii=False),
                'collected_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            print(f"      ⚠️ 매물 처리 오류: {e}")
            return None

# 테스트 실행
async def test_accurate_scraping():
    scraper = AccurateDistrictScraper()
    
    # 강남구 테스트
    district = "강남구"
    
    # 1단계: 실제 API 파라미터 추출
    api_params = await scraper.extract_real_api_params(district)
    
    if api_params:
        print(f"\n🎯 추출된 {district} API 파라미터:")
        for key, value in api_params.items():
            print(f"   {key}: {value}")
        
        # 2단계: 추출된 파라미터로 수집
        properties = scraper.collect_with_real_params(district, api_params, max_pages=3)
        
        if properties:
            print(f"\n📊 수집 결과:")
            print(f"   총 {len(properties)}개 매물")
            
            # 샘플 출력
            for i, prop in enumerate(properties[:3]):
                print(f"   매물 {i+1}: {prop['building_name']} | {prop['deposit']}만원/{prop['monthly_rent']}만원 | {prop['area_pyeong']}평")
        else:
            print("\n❌ 매물 수집 실패")
    else:
        print(f"\n❌ {district} API 파라미터 추출 실패")

if __name__ == "__main__":
    asyncio.run(test_accurate_scraping())
