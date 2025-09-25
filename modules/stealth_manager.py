#!/usr/bin/env python3
"""
🥷 StealthManager - 스텔스 기능 관리
- 다중 세션 풀 관리
- User-Agent 로테이션
- 인간적인 대기시간
- 봇 탐지 우회
"""

import random
import time
import requests
from typing import List, Dict, Any


class StealthManager:
    """🥷 스텔스 기능을 관리하는 클래스"""
    
    def __init__(self, pool_size: int = 5):
        self.pool_size = pool_size
        
        # 🎯 실제 디바이스 User-Agent 풀
        self.stealth_user_agents = [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.7 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36'
        ]
        
        # 🎯 다중 세션 풀
        self.session_pool: List[requests.Session] = []
        self.current_session_idx = 0
        self.session_usage_count = {}
        self.max_session_usage = 50  # 세션당 최대 사용 횟수
        
        # 페르소나별 행동 패턴
        self.personas = {
            '부동산전문가': {
                'speed_multiplier': 0.9,  # 빠른 탐색
                'wait_range': (0.5, 3.0),
                'long_wait_range': (5.0, 15.0)
            },
            '일반사용자': {
                'speed_multiplier': 1.0,  # 보통 속도
                'wait_range': (1.0, 5.0),
                'long_wait_range': (5.0, 20.0)
            },
            '신중한사용자': {
                'speed_multiplier': 1.2,  # 느린 탐색
                'wait_range': (2.0, 8.0),
                'long_wait_range': (10.0, 30.0)
            }
        }
        
        self.current_persona = '일반사용자'
        
        # 초기화
        self.create_stealth_session_pool()
    
    def create_stealth_session_pool(self) -> None:
        """🔄 스텔스 세션 풀 생성"""
        self.session_pool = []
        self.session_usage_count = {}
        
        for i in range(self.pool_size):
            session = requests.Session()
            user_agent = random.choice(self.stealth_user_agents)
            
            session.headers.update({
                'User-Agent': user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://m.land.naver.com/',
                'Origin': 'https://m.land.naver.com',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            })
            
            self.session_pool.append(session)
            self.session_usage_count[i] = 0
            
            print(f"   세션 #{i+1}: {user_agent[:50]}...")
    
    def get_stealth_session(self) -> requests.Session:
        """🎯 로테이션 방식으로 세션 반환"""
        session_idx = self.current_session_idx
        session = self.session_pool[session_idx]
        
        # 사용 횟수 증가
        self.session_usage_count[session_idx] += 1
        
        # 세션 사용량이 한계에 도달하면 전체 풀 리셋
        if self.session_usage_count[session_idx] >= self.max_session_usage:
            if all(count >= self.max_session_usage for count in self.session_usage_count.values()):
                print("🔄 세션 풀 리셋 (모든 세션 사용량 한계)")
                self.create_stealth_session_pool()
                session_idx = 0
                session = self.session_pool[0]
        
        # 다음 세션으로 로테이션
        self.current_session_idx = (self.current_session_idx + 1) % self.pool_size
        
        return session
    
    def get_human_wait_time(self, long_wait: bool = False) -> float:
        """⏳ 인간적인 대기시간 반환"""
        persona_config = self.personas[self.current_persona]
        
        if long_wait:
            base_wait = random.uniform(*persona_config['long_wait_range'])
        else:
            base_wait = random.uniform(*persona_config['wait_range'])
        
        # 페르소나별 속도 조정
        adjusted_wait = base_wait * persona_config['speed_multiplier']
        
        return round(adjusted_wait, 1)
    
    def set_persona(self, persona: str) -> None:
        """🎭 페르소나 설정"""
        if persona in self.personas:
            self.current_persona = persona
            print(f"   🎭 페르소나: {persona} (속도: {self.personas[persona]['speed_multiplier']}x)")
        else:
            print(f"⚠️ 알 수 없는 페르소나: {persona}")
    
    def get_random_persona(self) -> str:
        """🎲 랜덤 페르소나 선택"""
        return random.choice(list(self.personas.keys()))
    
    def wait_with_message(self, wait_time: float, message: str = "") -> None:
        """⏳ 메시지와 함께 대기"""
        if message:
            print(f"         ⏳ {wait_time}초 대기 중... {message}", flush=True)
        else:
            print(f"         ⏳ {wait_time}초 대기 중... (인간 패턴)", flush=True)
        
        time.sleep(wait_time)
    
    def rest_between_operations(self, operation_name: str = "작업") -> None:
        """😴 작업 간 휴식"""
        rest_time = self.get_human_wait_time(long_wait=True)
        print(f"         😴 {operation_name} 완료, 다음까지 {rest_time}초 휴식...", flush=True)
        time.sleep(rest_time)
    
    def get_session_info(self) -> Dict[str, Any]:
        """📊 현재 세션 풀 상태 반환"""
        return {
            'pool_size': self.pool_size,
            'current_session': self.current_session_idx,
            'usage_counts': self.session_usage_count.copy(),
            'current_persona': self.current_persona,
            'total_sessions_created': len(self.session_pool)
        }
    
    def print_stealth_status(self) -> None:
        """📊 스텔스 상태 출력"""
        info = self.get_session_info()
        print(f"🥷 스텔스 상태: {info['current_persona']} | 세션 {info['current_session']+1}/{info['pool_size']}")
        print(f"   사용량: {list(info['usage_counts'].values())}")
