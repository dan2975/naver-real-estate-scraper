#!/usr/bin/env python3
"""
📊 ProgressManager - 실시간 진행률 관리
- Streamlit과 API 수집기 간 실시간 상태 공유
- 파일 기반 진행률 저장 및 읽기
- 안전한 멀티 프로세스 지원
"""

import json
import os
import time
from typing import Dict, Any, Optional
from datetime import datetime
import fcntl


class ProgressManager:
    """📊 실시간 진행률 관리 클래스"""
    
    def __init__(self, progress_file: str = "data/collection_progress.json"):
        self.progress_file = progress_file
        self.ensure_data_directory()
        self.init_progress_file()
    
    def ensure_data_directory(self):
        """데이터 디렉토리 생성"""
        os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)
    
    def init_progress_file(self):
        """진행률 파일 초기화"""
        initial_data = {
            "status": "idle",
            "progress_percent": 0,
            "current_step": "대기 중",
            "total_districts": 0,
            "current_district": "",
            "district_index": 0,
            "total_properties_target": 0,
            "current_properties_collected": 0,
            "current_page": 0,
            "total_pages_estimated": 0,
            "start_time": None,
            "last_update": datetime.now().isoformat(),
            "errors": [],
            "completed_districts": [],
            "current_district_properties": 0,
            "estimated_completion": None
        }
        
        # 파일이 없거나 손상된 경우에만 초기화
        if not os.path.exists(self.progress_file):
            self._write_progress_safe(initial_data)
    
    def _write_progress_safe(self, data: Dict[str, Any]) -> bool:
        """안전한 진행률 파일 쓰기 (파일 락 사용)"""
        try:
            data["last_update"] = datetime.now().isoformat()
            
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                # 파일 락 적용 (멀티 프로세스 안전)
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(data, f, ensure_ascii=False, indent=2)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return True
        except Exception as e:
            print(f"⚠️ 진행률 저장 오류: {e}")
            return False
    
    def _read_progress_safe(self) -> Dict[str, Any]:
        """안전한 진행률 파일 읽기"""
        try:
            if not os.path.exists(self.progress_file):
                self.init_progress_file()
            
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                data = json.load(f)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return data
        except Exception as e:
            print(f"⚠️ 진행률 읽기 오류: {e}")
            # 오류 시 기본 데이터 반환
            return {"status": "error", "progress_percent": 0, "current_step": f"오류: {e}"}
    
    def start_collection(self, districts: list, estimated_properties_per_district: int = 4000):
        """수집 시작"""
        total_target = len(districts) * estimated_properties_per_district
        
        data = {
            "status": "running",
            "progress_percent": 0,
            "current_step": "수집 시작",
            "total_districts": len(districts),
            "current_district": "",
            "district_index": 0,
            "total_properties_target": total_target,
            "current_properties_collected": 0,
            "current_page": 0,
            "total_pages_estimated": len(districts) * 200,  # 구별 200페이지
            "start_time": datetime.now().isoformat(),
            "errors": [],
            "completed_districts": [],
            "current_district_properties": 0,
            "estimated_completion": None,
            "stop_requested": False  # 중지 요청 플래그 초기화
        }
        
        return self._write_progress_safe(data)
    
    def update_district_start(self, district_name: str, district_index: int):
        """구별 수집 시작"""
        data = self._read_progress_safe()
        data.update({
            "current_district": district_name,
            "district_index": district_index,
            "current_step": f"{district_name} 수집 시작",
            "current_district_properties": 0,
            "current_page": 0
        })
        
        # 진행률 계산 (구별 진행률)
        district_progress = (district_index / data["total_districts"]) * 100
        data["progress_percent"] = min(district_progress, 95)  # 최대 95%까지
        
        return self._write_progress_safe(data)
    
    def update_page_progress(self, current_page: int, properties_in_page: int, total_properties_found: Optional[int] = None):
        """페이지별 진행률 업데이트"""
        data = self._read_progress_safe()
        data.update({
            "current_page": current_page,
            "current_properties_collected": data.get("current_properties_collected", 0) + properties_in_page,
            "current_district_properties": data.get("current_district_properties", 0) + properties_in_page,
            "last_update": datetime.now().isoformat()
        })
        
        # 브라우저에서 감지한 총 매물 수가 있으면 더 정확한 진행률 계산
        if total_properties_found and total_properties_found > 0:
            current_collected = data["current_district_properties"]
            district_progress = min((current_collected / total_properties_found) * 100, 99)
            print(f"                  📊 정확한 진행률: {current_collected}/{total_properties_found}개 ({district_progress:.1f}%)")
            
            # 🎯 브라우저 기준 진행률을 메인 진행률로 사용
            data["progress_percent"] = district_progress
        else:
            # 브라우저 총 매물 수를 저장된 데이터에서 확인
            browser_totals = data.get("browser_totals", {})
            current_district = data.get("current_district", "")
            browser_total = browser_totals.get(current_district, 0)
            
            if browser_total > 0:
                current_collected = data["current_district_properties"]
                district_progress = min((current_collected / browser_total) * 100, 99)
                print(f"                  📊 저장된 브라우저 총 매물 수 기준 진행률: {current_collected}/{browser_total}개 ({district_progress:.1f}%)")
                data["progress_percent"] = district_progress
            else:
                # 폴백: 기존 방식
                if data["total_properties_target"] > 0:
                    overall_progress = min((data["current_properties_collected"] / data["total_properties_target"]) * 90, 90)
                    data["progress_percent"] = overall_progress
        
        return self._write_progress_safe(data)
    
    def set_district_browser_total(self, district_name: str, browser_total: int):
        """브라우저에서 감지한 구별 총 매물 수 설정"""
        data = self._read_progress_safe()
        if "browser_totals" not in data:
            data["browser_totals"] = {}
        
        data["browser_totals"][district_name] = browser_total
        data["current_step"] = f"{district_name} 브라우저 감지: {browser_total}개 매물"
        
        print(f"                  🎯 진행률 관리자: {district_name} 총 {browser_total}개 설정")
        return self._write_progress_safe(data)
    
    def update_district_complete(self, district_name: str, properties_collected: int):
        """구별 수집 완료"""
        data = self._read_progress_safe()
        data["completed_districts"].append({
            "name": district_name,
            "properties": properties_collected,
            "completed_at": datetime.now().isoformat()
        })
        
        data.update({
            "current_step": f"{district_name} 완료 ({properties_collected}개)"
        })
        
        return self._write_progress_safe(data)
    
    def complete_collection(self, total_collected: int, success: bool = True):
        """전체 수집 완료"""
        data = self._read_progress_safe()
        data.update({
            "status": "completed" if success else "cancelled",
            "progress_percent": 100,
            "current_step": f"수집 완료! 총 {total_collected}개 매물" if success else "수집 중지됨",
            "current_properties_collected": total_collected,
            "estimated_completion": datetime.now().isoformat()
        })
        
        return self._write_progress_safe(data)
    
    def request_stop(self):
        """수집 중지 요청"""
        data = self._read_progress_safe()
        data["stop_requested"] = True
        data["current_step"] = "수집 중지 요청됨..."
        
        return self._write_progress_safe(data)
    
    def is_stop_requested(self) -> bool:
        """수집 중지 요청 여부 확인"""
        data = self._read_progress_safe()
        return data.get("stop_requested", False)
    
    def add_error(self, error_message: str):
        """오류 추가"""
        data = self._read_progress_safe()
        data["errors"].append({
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        })
        
        return self._write_progress_safe(data)
    
    def get_progress(self) -> Dict[str, Any]:
        """현재 진행률 조회 (최신 데이터 보장)"""
        # 파일을 직접 읽어서 캐시 무효화
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"🔍 진행률 파일 직접 읽기: progress_percent={data.get('progress_percent', 0)}")
            else:
                data = self._get_default_progress()
        except Exception as e:
            print(f"⚠️ 진행률 파일 읽기 오류: {e}")
            data = self._read_progress_safe()
        
        # 추가 계산된 정보
        if data.get("start_time") and data["status"] == "running":
            start_time = datetime.fromisoformat(data["start_time"])
            elapsed = (datetime.now() - start_time).total_seconds()
            
            if data["progress_percent"] > 0:
                estimated_total_time = elapsed / (data["progress_percent"] / 100)
                remaining_time = estimated_total_time - elapsed
                data["estimated_remaining_seconds"] = max(0, remaining_time)
            else:
                data["estimated_remaining_seconds"] = None
        else:
            data["estimated_remaining_seconds"] = None
        
        return data
    
    def reset_progress(self):
        """진행률 리셋"""
        self.init_progress_file()
        return True
    
    def is_running(self) -> bool:
        """수집 진행 중인지 확인"""
        data = self._read_progress_safe()
        return data.get("status") == "running"


# 싱글톤 인스턴스
_progress_manager = None

def get_progress_manager() -> ProgressManager:
    """전역 진행률 매니저 인스턴스 반환"""
    global _progress_manager
    if _progress_manager is None:
        _progress_manager = ProgressManager()
    return _progress_manager
