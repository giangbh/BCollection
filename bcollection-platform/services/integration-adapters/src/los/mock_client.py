from typing import Dict, Any, List
from .client import LOSApiClient

class MockLOSApiClient(LOSApiClient):
    """
    Mock Service giả lập Backend API của Hệ thống Khởi tạo Khoản vay (LOS / RLOS).
    Tự động nhận diện loại sản phẩm tín dụng từ mã loan_id:
    - MORTGAGE (MO): Bất động sản (Real Estate), LTV 0.40 - 0.75
    - AUTO_LOAN (AL): Xe cơ giới (Vehicle), LTV 0.55 - 0.80
    - SME_WORKING_CAPITAL (SM): Quyền đòi nợ / Thiết bị, LTV 0.50 - 0.80
    - CREDIT_CARD (CC) / UNSECURED (UN): Tín chấp (Không có TSBĐ)
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
        if loan_id in self._mock_obligations:
            return self._mock_obligations[loan_id]

        loan_hash = sum(ord(c) for c in loan_id)
        cif_code = f"CIF{100000 + (loan_hash % 90000)}"
        phone = f"+849{(loan_hash * 13 % 89999999) + 10000000}"

        parties = [
            {
                "loan_id": loan_id,
                "party_id": cif_code,
                "party_name": "KHÁCH HÀNG VAY CHÍNH",
                "party_type": "PERSON",
                "edge_type": "BORROWED",
                "contact_eligible": "YES",
                "phone_e164": phone,
                "source_system": "LOS"
            }
        ]

        # 33% hồ sơ có thêm Người bảo lãnh hợp đồng
        if loan_hash % 3 == 0:
            parties.append({
                "loan_id": loan_id,
                "party_id": f"{cif_code}_G1",
                "party_name": "NGƯỜI BẢO LÃNH NGHĨA VỤ",
                "party_type": "PERSON",
                "edge_type": "GUARANTEES",
                "contact_eligible": "YES",
                "phone_e164": f"+849{(loan_hash * 17 % 89999999) + 10000000}",
                "source_system": "LOS"
            })

        return parties

    def fetch_collateral_details(self, loan_id: str) -> List[Dict[str, Any]]:
        if loan_id in self._mock_collateral:
            return self._mock_collateral[loan_id]

        loan_hash = sum(ord(c) for c in loan_id)
        lid_upper = loan_id.upper()

        # 1. Bất động sản thế chấp (Mortgage Loan)
        if "-MO-" in lid_upper or "MORTGAGE" in lid_upper or "HOME" in lid_upper:
            val = 1_500_000_000.0 + (loan_hash % 20) * 100_000_000.0
            ltv = round(0.40 + (loan_hash % 35) * 0.01, 2)
            street_no = (loan_hash % 180) + 1
            return [
                {
                    "collateral_id": f"COL-BDS-{loan_id.replace('LOAN-', '')}",
                    "collateral_type": "REAL_ESTATE",
                    "valuation_amount": val,
                    "address": f"Số {street_no} Phố Nguyễn Trãi, Quận Thanh Xuân, Hà Nội",
                    "ltv_ratio": ltv
                }
            ]

        # 2. Vay mua ô tô (Auto Loan)
        elif "-AL-" in lid_upper or "AUTO" in lid_upper:
            val = 450_000_000.0 + (loan_hash % 15) * 30_000_000.0
            ltv = round(0.55 + (loan_hash % 25) * 0.01, 2)
            plate = (loan_hash % 89999) + 10000
            return [
                {
                    "collateral_id": f"COL-CAR-{loan_id.replace('LOAN-', '')}",
                    "collateral_type": "VEHICLE",
                    "valuation_amount": val,
                    "address": f"Xe ô tô du lịch BKS 30H-{plate}",
                    "ltv_ratio": ltv
                }
            ]

        # 3. Doanh nghiệp vừa và nhỏ / Hộ kinh doanh (SME Loan)
        elif "-SM-" in lid_upper or "SME" in lid_upper:
            val = 800_000_000.0 + (loan_hash % 12) * 100_000_000.0
            ltv = round(0.50 + (loan_hash % 30) * 0.01, 2)
            return [
                {
                    "collateral_id": f"COL-SME-{loan_id.replace('LOAN-', '')}",
                    "collateral_type": "RECEIVABLES_EQUIPMENT",
                    "valuation_amount": val,
                    "address": "Dây chuyền thiết bị & Quyền đòi nợ hợp đồng thương mại",
                    "ltv_ratio": ltv
                }
            ]

        # 4. Thẻ tín dụng & Vay tiêu dùng tín chấp: Không có TSBĐ
        return []
