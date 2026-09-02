from abc import ABC, abstractmethod
from typing import Dict, Any

class CICApiClient(ABC):
    """Interface kết nối Trung tâm Thông tin Tín dụng Quốc gia (CIC Data Gateway)"""
    @abstractmethod
    def fetch_credit_score_and_obligations(self, debtor_cif: str, national_id: str) -> Dict[str, Any]:
        pass
