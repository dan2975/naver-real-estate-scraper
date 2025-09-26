#!/usr/bin/env python3
"""
🏠 PropertyParser - 매물 데이터 파싱 및 검증
- 가격 정보 파싱 (보증금/월세)
- 면적 정보 변환 (㎡ ↔ 평)
- 층수 정보 추출
- 조건.md 부합 여부 검증
"""

import re
from typing import Dict, Any, Optional, List, Tuple


class PropertyParser:
    """🏠 매물 데이터 파싱을 담당하는 클래스"""
    
    def __init__(self, streamlit_filters=None):
        # 기본 조건 (조건.md 기준)
        default_conditions = {
            'max_deposit': 2000,      # 보증금 2000만원 이하
            'max_monthly_rent': 130,  # 월세 130만원 이하
            'max_total_monthly': 150, # 총 월비용 150만원 이하
            'min_area_pyeong': 20,    # 20평 이상
            'min_floor': -1,          # 지하1층 이상
            'max_floor': 2,           # 2층 이하
            'max_management_fee': 30  # 관리비 30만원 이하
        }
        
        # Streamlit 필터가 있으면 적용
        if streamlit_filters:
            default_conditions.update({
                'max_deposit': streamlit_filters.get('deposit_max', 2000),
                'max_monthly_rent': streamlit_filters.get('monthly_rent_max', 130),
                'min_area_pyeong': streamlit_filters.get('area_min', 20)
            })
        
        self.conditions = default_conditions
        
        # 가격 파싱 정규식
        self.price_patterns = {
            'deposit_rent': re.compile(r'월세\s*([0-9억만,\s]+)\s*/\s*([0-9만,\s]+)'),
            'simple_numbers': re.compile(r'([0-9억만,\s]+)'),
            'eok_pattern': re.compile(r'(\d+)억'),
            'man_pattern': re.compile(r'(\d+(?:,\d+)?)만?원?')
        }
        
        # 면적 파싱 정규식
        self.area_patterns = {
            'pyeong': re.compile(r'(\d+\.?\d*)평'),
            'square_meter': re.compile(r'(\d+\.?\d*)㎡'),
            'area_slash': re.compile(r'(\d+\.?\d*)/(\d+\.?\d*)㎡'),
            'exclusive_area': re.compile(r'전용\s*(\d+\.?\d*)㎡')
        }
        
        # 층수 파싱 정규식
        self.floor_patterns = {
            'floor_info': re.compile(r'([B0-9]+)/([0-9]+)층?'),
            'basement': re.compile(r'B(\d+)'),
            'single_floor': re.compile(r'(\d+)층')
        }
    
    def parse_price_from_text(self, text: str) -> Tuple[int, int]:
        """💰 텍스트에서 보증금/월세 추출"""
        try:
            # 월세 패턴 찾기 (예: "월세2억/600만원")
            deposit_rent_match = self.price_patterns['deposit_rent'].search(text)
            if deposit_rent_match:
                deposit_str = deposit_rent_match.group(1).strip()
                rent_str = deposit_rent_match.group(2).strip()
                
                deposit = self.convert_korean_price_to_number(deposit_str)
                monthly_rent = self.convert_korean_price_to_number(rent_str)
                
                return deposit, monthly_rent
            
            return 0, 0
            
        except Exception as e:
            print(f"⚠️ 가격 파싱 오류: {e}")
            return 0, 0
    
    def convert_korean_price_to_number(self, price_str: str) -> int:
        """🔢 한국어 가격을 숫자로 변환"""
        try:
            # 공백과 쉼표 제거
            clean_str = re.sub(r'[,\s]', '', price_str)
            
            # 억 단위 처리
            eok_match = self.price_patterns['eok_pattern'].search(clean_str)
            eok_amount = 0
            if eok_match:
                eok_amount = int(eok_match.group(1)) * 10000  # 억 = 10000만원
                clean_str = self.price_patterns['eok_pattern'].sub('', clean_str)
            
            # 만원 단위 처리
            man_match = self.price_patterns['man_pattern'].search(clean_str)
            man_amount = 0
            if man_match:
                man_str = man_match.group(1).replace(',', '')
                man_amount = int(man_str)
            
            return eok_amount + man_amount
            
        except Exception as e:
            print(f"⚠️ 가격 변환 오류: {e}")
            return 0
    
    def parse_area_from_text(self, text: str) -> Tuple[float, float]:
        """📐 텍스트에서 면적 정보 추출 (㎡, 평)"""
        try:
            area_m2 = 0
            area_pyeong = 0
            
            # 평 단위 찾기
            pyeong_match = self.area_patterns['pyeong'].search(text)
            if pyeong_match:
                area_pyeong = float(pyeong_match.group(1))
                area_m2 = area_pyeong * 3.306
                return area_m2, area_pyeong
            
            # 제곱미터 찾기
            m2_match = self.area_patterns['square_meter'].search(text)
            if m2_match:
                area_m2 = float(m2_match.group(1))
                area_pyeong = area_m2 / 3.306
                return area_m2, area_pyeong
            
            # 슬래시 형태 면적 (예: "16.5/33.1㎡")
            slash_match = self.area_patterns['area_slash'].search(text)
            if slash_match:
                area1 = float(slash_match.group(1))
                area2 = float(slash_match.group(2))
                area_m2 = max(area1, area2)  # 더 큰 면적 사용
                area_pyeong = area_m2 / 3.306
                return area_m2, area_pyeong
            
            # 전용면적 찾기
            exclusive_match = self.area_patterns['exclusive_area'].search(text)
            if exclusive_match:
                area_m2 = float(exclusive_match.group(1))
                area_pyeong = area_m2 / 3.306
                return area_m2, area_pyeong
            
            return 0, 0
            
        except Exception as e:
            print(f"⚠️ 면적 파싱 오류: {e}")
            return 0, 0
    
    def parse_floor_from_text(self, text: str) -> Tuple[str, int]:
        """🏢 텍스트에서 층수 정보 추출"""
        try:
            # "4/5층" 형태
            floor_match = self.floor_patterns['floor_info'].search(text)
            if floor_match:
                current_floor_str = floor_match.group(1)
                total_floors = int(floor_match.group(2))
                
                # 지하층 처리
                if current_floor_str.startswith('B'):
                    basement_match = self.floor_patterns['basement'].search(current_floor_str)
                    if basement_match:
                        basement_level = int(basement_match.group(1))
                        return f"지하{basement_level}층", -basement_level
                else:
                    current_floor = int(current_floor_str)
                    return f"{current_floor}층", current_floor
            
            # 단일 층수 (예: "2층")
            single_match = self.floor_patterns['single_floor'].search(text)
            if single_match:
                floor_num = int(single_match.group(1))
                return f"{floor_num}층", floor_num
            
            return "정보없음", None
            
        except Exception as e:
            print(f"⚠️ 층수 파싱 오류: {e}")
            return "정보없음", None
    
    def check_conditions_compliance(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """🎯 조건.md 부합 여부 검사"""
        compliance = {
            'meets_all_conditions': True,
            'failed_conditions': [],
            'condition_details': {}
        }
        
        try:
            # 보증금 체크
            deposit = property_data.get('deposit', 0)
            if deposit > self.conditions['max_deposit']:
                compliance['meets_all_conditions'] = False
                compliance['failed_conditions'].append('보증금')
                compliance['condition_details']['deposit'] = f"{deposit}만원 > {self.conditions['max_deposit']}만원"
            
            # 월세 체크
            monthly_rent = property_data.get('monthly_rent', 0)
            if monthly_rent > self.conditions['max_monthly_rent']:
                compliance['meets_all_conditions'] = False
                compliance['failed_conditions'].append('월세')
                compliance['condition_details']['monthly_rent'] = f"{monthly_rent}만원 > {self.conditions['max_monthly_rent']}만원"
            
            # 면적 체크
            area_pyeong = property_data.get('area_pyeong', 0)
            if area_pyeong < self.conditions['min_area_pyeong']:
                compliance['meets_all_conditions'] = False
                compliance['failed_conditions'].append('면적')
                compliance['condition_details']['area'] = f"{area_pyeong}평 < {self.conditions['min_area_pyeong']}평"
            
            # 층수 체크 (floor 필드 사용, 이전 성공 코드와 동일)
            floor = property_data.get('floor')
            if floor is not None and isinstance(floor, (int, float)):
                try:
                    if floor < self.conditions['min_floor'] or floor > self.conditions['max_floor']:
                        compliance['meets_all_conditions'] = False
                        compliance['failed_conditions'].append('층수')
                        compliance['condition_details']['floor'] = f"{floor}층 (범위: {self.conditions['min_floor']}~{self.conditions['max_floor']}층)"
                except (TypeError, ValueError) as e:
                    print(f"            ⚠️ 층수 비교 오류: floor={floor}, type={type(floor)}, error={e}")
                    # 층수 정보가 잘못된 경우 조건 실패로 처리하지 않음 (무시)
            
            # 총 월비용 체크 (월세 + 관리비)
            management_fee = property_data.get('management_fee', 0)
            total_monthly = monthly_rent + management_fee
            if total_monthly > self.conditions['max_total_monthly']:
                compliance['meets_all_conditions'] = False
                compliance['failed_conditions'].append('총월비용')
                compliance['condition_details']['total_monthly'] = f"{total_monthly}만원 > {self.conditions['max_total_monthly']}만원"
            
        except Exception as e:
            print(f"⚠️ 조건 검사 오류: {e}")
            compliance['error'] = str(e)
        
        return compliance
    
    def enhance_property_data(self, raw_property: Dict[str, Any]) -> Dict[str, Any]:
        """✨ 매물 데이터 향상 (파싱 결과 추가)"""
        enhanced = raw_property.copy()
        
        try:
            # 원본 텍스트 (있는 경우)
            raw_text = raw_property.get('raw_text', '')
            
            # 가격 정보가 없으면 텍스트에서 추출 시도
            if not enhanced.get('deposit') and not enhanced.get('monthly_rent') and raw_text:
                deposit, monthly_rent = self.parse_price_from_text(raw_text)
                if deposit or monthly_rent:
                    enhanced['deposit'] = deposit
                    enhanced['monthly_rent'] = monthly_rent
            
            # 면적 정보가 없으면 텍스트에서 추출 시도
            if not enhanced.get('area_pyeong') and raw_text:
                area_m2, area_pyeong = self.parse_area_from_text(raw_text)
                if area_pyeong:
                    enhanced['area_m2'] = area_m2
                    enhanced['area_pyeong'] = area_pyeong
            
            # 층수 정보가 없으면 텍스트에서 추출 시도 (이전 성공 코드 방식)
            if not enhanced.get('floor_info') and raw_text:
                floor_info, floor_number = self.parse_floor_from_text(raw_text)
                if floor_info != "정보없음":
                    enhanced['floor_info'] = floor_info
                    # floor 필드에 숫자 값 설정 (floor_number 대신)
                    if floor_number is not None and enhanced.get('floor') is None:
                        enhanced['floor'] = floor_number
            
            # 조건 부합 여부 검사
            compliance = self.check_conditions_compliance(enhanced)
            enhanced['conditions_compliance'] = compliance
            
        except Exception as e:
            print(f"⚠️ 데이터 향상 오류: {e}")
            enhanced['parsing_error'] = str(e)
        
        return enhanced
    
    def analyze_properties_batch(self, properties: List[Dict[str, Any]]) -> Dict[str, Any]:
        """📊 매물 배치 분석"""
        if not properties:
            return {}
        
        # 기본 통계
        total_count = len(properties)
        compliant_properties = [p for p in properties if p.get('conditions_compliance', {}).get('meets_all_conditions', False)]
        compliance_rate = len(compliant_properties) / total_count * 100
        
        # 가격 통계
        deposits = [p.get('deposit', 0) for p in properties if p.get('deposit', 0) > 0]
        rents = [p.get('monthly_rent', 0) for p in properties if p.get('monthly_rent', 0) > 0]
        areas = [p.get('area_pyeong', 0) for p in properties if p.get('area_pyeong', 0) > 0]
        
        # 실패한 조건 분석
        failed_conditions = {}
        for prop in properties:
            compliance = prop.get('conditions_compliance', {})
            for condition in compliance.get('failed_conditions', []):
                failed_conditions[condition] = failed_conditions.get(condition, 0) + 1
        
        return {
            'total_count': total_count,
            'compliant_count': len(compliant_properties),
            'compliance_rate': round(compliance_rate, 1),
            'price_stats': {
                'deposit_range': f"{min(deposits)}~{max(deposits)}만원" if deposits else "N/A",
                'rent_range': f"{min(rents)}~{max(rents)}만원" if rents else "N/A",
                'area_range': f"{min(areas):.1f}~{max(areas):.1f}평" if areas else "N/A"
            },
            'failed_conditions': failed_conditions,
            'parsing_success': {
                'deposit_parsed': len(deposits),
                'rent_parsed': len(rents),
                'area_parsed': len(areas)
            }
        }
