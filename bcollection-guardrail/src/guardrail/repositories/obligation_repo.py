from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

class ObligationRepository(ABC):
    @abstractmethod
    def get_party_obligation(self, loan_id: str, party_id: str) -> Optional[Dict[str, Any]]:
        """Lấy thông tin quan hệ nghĩa vụ giữa đối tượng và khoản nợ"""
        pass

class InMemoryObligationRepository(ObligationRepository):
    """Implementation cho DEV / Testing và có thể nạp từ PostgreSQL trong Prod"""
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}

    def add_obligation(self, loan_id: str, party_id: str, edge_type: str, contact_eligible: str = "YES", source: str = "LOS", contract_ref: str = "HD-001"):
        key = f"{loan_id}:{party_id}"
        self._data[key] = {
            "loan_id": loan_id,
            "party_id": party_id,
            "edge_type": edge_type,
            "contact_eligible": contact_eligible,
            "source": source,
            "contract_ref": contract_ref,
            "status": "ACTIVE"
        }

    def get_party_obligation(self, loan_id: str, party_id: str) -> Optional[Dict[str, Any]]:
        key = f"{loan_id}:{party_id}"
        return self._data.get(key)
