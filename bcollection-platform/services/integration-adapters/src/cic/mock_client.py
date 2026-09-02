from typing import Dict, Any
from .client import CICApiClient

class MockCICApiClient(CICApiClient):
    """Mock Service giả lập cổng dữ liệu CIC phục vụ DEV/UAT"""
    def fetch_credit_score_and_obligations(self, debtor_cif: str, national_id: str) -> Dict[str, Any]:
        cif_hash = sum(ord(ch) for ch in debtor_cif)
        worst_group = 1 if (cif_hash % 3 != 0) else 2
        return {
            "status": "SUCCESS",
            "data": {
                "debtor_cif": debtor_cif,
                "national_id": national_id,
                "credit_score": 620,
                "worst_group_other_banks": worst_group,
                "obligations_at_other_banks_count": (cif_hash % 3) + 1,
                "total_obligation_other_banks": 85000000.0,
                "paying_other_banks_while_overdue": (worst_group == 1)
            }
        }
