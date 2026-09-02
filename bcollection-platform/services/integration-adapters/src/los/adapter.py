import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from .client import LOSApiClient
from .mock_client import MockLOSApiClient
from .http_client import HttpLOSApiClient

@dataclass
class PartyObligationDTO:
    loan_id: str
    party_id: str
    party_name: str
    party_type: str        # PERSON / ORG
    edge_type: str         # BORROWED, GUARANTEES, CO_BORROWER_WITH, LEGAL_REP_OF
    contact_eligible: str  # YES / NO / CONDITIONAL
    phone_e164: str
    source_system: str     # LOS, RLOS


@dataclass
class CollateralDTO:
    collateral_id: str
    collateral_type: str   # REAL_ESTATE, VEHICLE, DEPOSIT
    valuation_amount: float
    address: str
    ltv_ratio: float


class LOSAdapter:
    """
    Adapter Duy nhất kết nối Hệ thống Khởi tạo Khoản vay (LOS / RLOS / CLOS).
    Tuân thủ Kiến trúc Hexagonal (Port & Adapter):
    - Đóng gói toàn bộ logic nghiệp vụ (Kiểm tra điều kiện tiếp cận, Chuyển đổi DTO chuẩn IF-LOS-02).
    - Ủy nhiệm việc gọi mạng cho ApiClient (Mặc định gọi MockApiClient; khi Go-Live chỉ cần cấu hình LOS_MODE=http).
    - TUYỆT ĐỐI KHÔNG CẦN SỬA ĐỔI ADAPTER NÀY KHI CHUYỂN TỪ MOCK SANG HỆ THỐNG THẬT.
    """
    def __init__(self, api_client: Optional[LOSApiClient] = None):
        if api_client is not None:
            self._client = api_client
        else:
            mode = os.getenv("LOS_MODE", "mock").lower()
            if mode == "http":
                self._client = HttpLOSApiClient()
            else:
                self._client = MockLOSApiClient()

    @property
    def client(self) -> LOSApiClient:
        return self._client

    def get_loan_party_obligations(self, loan_id: str) -> List[PartyObligationDTO]:
        """
        Lấy danh sách người có nghĩa vụ liên quan đến khoản vay (IF-LOS-02).
        Đảm bảo lọc và chuẩn hóa dữ liệu cho L6 Guardrail.
        """
        raw_parties = self._client.fetch_party_obligations(loan_id)
        results = []
        for p in raw_parties:
            results.append(PartyObligationDTO(
                loan_id=p.get("loan_id", loan_id),
                party_id=p.get("party_id", "CIF_UNKNOWN"),
                party_name=p.get("party_name", "CHƯA XÁC ĐỊNH"),
                party_type=p.get("party_type", "PERSON"),
                edge_type=p.get("edge_type", "BORROWED"),
                contact_eligible=p.get("contact_eligible", "YES"),
                phone_e164=p.get("phone_e164", ""),
                source_system=p.get("source_system", "LOS")
            ))
        return results

    def get_loan_collateral(self, loan_id: str) -> List[CollateralDTO]:
        """
        Lấy thông tin tài sản bảo đảm thế chấp phục vụ tính điểm D1 Ability Score.
        """
        raw_collat = self._client.fetch_collateral_details(loan_id)
        results = []
        for c in raw_collat:
            results.append(CollateralDTO(
                collateral_id=c.get("collateral_id", ""),
                collateral_type=c.get("collateral_type", "OTHER"),
                valuation_amount=float(c.get("valuation_amount", 0.0)),
                address=c.get("address", ""),
                ltv_ratio=float(c.get("ltv_ratio", 0.0))
            ))
        return results
