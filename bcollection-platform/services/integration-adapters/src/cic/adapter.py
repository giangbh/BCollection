import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from .client import CICApiClient
from .mock_client import MockCICApiClient
from .http_client import HttpCICApiClient

@dataclass
class CICReportDTO:
    debtor_cif: str
    credit_score: int
    worst_group_other_banks: int
    obligations_at_other_banks_count: int
    total_obligation_other_banks: float
    paying_other_banks_while_overdue: bool


class CICAdapter:
    """
    Adapter Duy nhất kết nối Cổng Thông tin Tín dụng Quốc gia (CIC).
    Tuân thủ Kiến trúc Hexagonal (Port & Adapter):
    - Đóng gói toàn bộ logic nghiệp vụ (Chuẩn hóa điểm tín dụng, Phân loại nhóm nợ xấu).
    - Ủy nhiệm việc truy vấn cho ApiClient (Mặc định gọi MockApiClient; khi Go-Live chỉ cần cấu hình CIC_MODE=http).
    - TUYỆT ĐỐI KHÔNG CẦN SỬA ĐỔI ADAPTER NÀY KHI CHUYỂN TỪ MOCK SANG HỆ THỐNG THẬT.
    """
    def __init__(self, api_client: Optional[CICApiClient] = None):
        if api_client is not None:
            self._client = api_client
        else:
            mode = os.getenv("CIC_MODE", "mock").lower()
            if mode == "http":
                self._client = HttpCICApiClient()
            else:
                self._client = MockCICApiClient()

    @property
    def client(self) -> CICApiClient:
        return self._client

    def get_credit_report(self, debtor_cif: str, national_id: str = "") -> CICReportDTO:
        """Lấy báo cáo quan hệ tín dụng toàn ngành từ CIC"""
        raw_res = self._client.fetch_credit_score_and_obligations(debtor_cif, national_id)
        data = raw_res.get("data", raw_res)
        return CICReportDTO(
            debtor_cif=debtor_cif,
            credit_score=int(data.get("credit_score", 600)),
            worst_group_other_banks=int(data.get("worst_group_other_banks", 1)),
            obligations_at_other_banks_count=int(data.get("obligations_at_other_banks_count", 0)),
            total_obligation_other_banks=float(data.get("total_obligation_other_banks", 0.0)),
            paying_other_banks_while_overdue=bool(data.get("paying_other_banks_while_overdue", False))
        )
