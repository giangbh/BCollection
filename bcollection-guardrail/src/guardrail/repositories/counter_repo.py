import time
from typing import Dict, List
from abc import ABC, abstractmethod

class CounterRepository(ABC):
    @abstractmethod
    def get_daily_attempts(self, loan_id: str, party_id: str, channel: str) -> int:
        pass

    @abstractmethod
    def increment_attempt(self, loan_id: str, party_id: str, channel: str):
        pass


class InMemoryCounterRepository(CounterRepository):
    """Giả lập Redis Sorted Set / Sliding Window Counters"""
    def __init__(self):
        # Key: "loan:party", Value: List of timestamps (seconds)
        self._total_attempts: Dict[str, List[float]] = {}
        self._channel_attempts: Dict[str, List[float]] = {}

    def _clean_old_entries(self, timestamps: List[float], window_seconds: float = 86400) -> List[float]:
        now = time.time()
        return [ts for ts in timestamps if now - ts < window_seconds]

    def get_daily_attempts(self, loan_id: str, party_id: str, channel: str) -> int:
        key = f"{loan_id}:{party_id}"
        chan_key = f"{loan_id}:{party_id}:{channel}"
        
        # Clean & return count in 24h
        self._total_attempts[key] = self._clean_old_entries(self._total_attempts.get(key, []))
        self._channel_attempts[chan_key] = self._clean_old_entries(self._channel_attempts.get(chan_key, []))
        
        return len(self._total_attempts[key])

    def get_daily_channel_attempts(self, loan_id: str, party_id: str, channel: str) -> int:
        chan_key = f"{loan_id}:{party_id}:{channel}"
        self._channel_attempts[chan_key] = self._clean_old_entries(self._channel_attempts.get(chan_key, []))
        return len(self._channel_attempts[chan_key])

    def increment_attempt(self, loan_id: str, party_id: str, channel: str):
        now = time.time()
        key = f"{loan_id}:{party_id}"
        chan_key = f"{loan_id}:{party_id}:{channel}"
        
        if key not in self._total_attempts:
            self._total_attempts[key] = []
        self._total_attempts[key].append(now)

        if chan_key not in self._channel_attempts:
            self._channel_attempts[chan_key] = []
        self._channel_attempts[chan_key].append(now)
