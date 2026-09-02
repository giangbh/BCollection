from typing import Dict, Any, List
from .client import LOSApiClient

class MockLOSApiClient(LOSApiClient):
    """
    Mock Service giả lập Backend API của LOS / RLOS.
    Trả về dữ liệu thô (Raw JSON Response) chuẩn hợp đồng IF-LOS-02.
    """
    def __init__(self):
        self._mock_obligations: Dict[str, List[Dict[str, Any]]] = {
            "LOAN-MO-20001": [
                {
                    "loan_id": "LOAN-MO-20001",
                    "party_id": "CIF100001",
                    "party_name": "VŨ THỊ TRANG",
                    "party_type": "PERSON",
                    "edge_type": "BORROWED",
                    "contact_eligible": "YES",
                    "phone_e164": "+84932753329",
                    "source_system": "LOS"
                },
                {
                    "loan_id": "LOAN-MO-20001",
                    "party_id": "CIF100001_G1",
                    "party_name": "VŨ ĐÌNH TRỌNG",
                    "party_type": "PERSON",
                    "edge_type": "GUARANTEES",
                    "contact_eligible": "YES",
                    "phone_e164": "+84912222333",
                    "source_system": "LOS"
                }
            ]
        }
        self._mock_collateral: Dict[str, List[Dict[str, Any]]] = {
            "LOAN-MO-20001": [
                {
                    "collateral_id": "COL-BDS-001",
                    "collateral_type": "REAL_ESTATE",
                    "valuation_amount": 1200000000.0,
                    "address": "Số 15 Lê Duẩn, Hoàn Kiếm, Hà Nội",
                    "ltv_ratio": 0.42
                }
            ]
        }

    def add_mock_party_obligation(self, loan_id: str, record: Dict[str, Any]):
        if loan_id not in self._mock_obligations:
            self._mock_obligations[loan_id] = []
        self._mock_obligations[loan_id].append(record)

    def fetch_party_obligations(self, loan_id: str) -> List[Dict[str, Any]]:
        return self._mock_obligations.get(loan_id, [
            {
                "loan_id": loan_id,
                "party_id": "CIF_DEFAULT_BORROWER",
                "party_name": "KHÁCH HÀNG VAY CHÍNH",
                "party_type": "PERSON",
                "edge_type": "BORROWED",
                "contact_eligible": "YES",
                "phone_e164": "+84912345678",
                "source_system": "LOS"
            }
        ])

    def fetch_collateral_details(self, loan_id: str) -> List[Dict[str, Any]]:
        return self._mock_collateral.get(loan_id, [])
