import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from .client import CTIApiClient
from .mock_client import MockCTIApiClient
from .http_client import HttpCTIApiClient


@dataclass
class CallSessionDTO:
    call_id: str
    case_id: str
    destination_phone: str
    status: str
    started_at: str
    recording_url: Optional[str] = None
    gateway: str = "FREESWITCH"


class CTITelephonyAdapter:
    """
    Adapter Duy nhất kết nối Hệ thống Tổng đài Thoại CTI (FreeSWITCH / Avaya / Cisco).
    Tuân thủ Kiến trúc Hexagonal (Port & Adapter):
    - Đóng gói toàn bộ logic nghiệp vụ (Kiểm tra Guardrail Token bắt buộc, Chuẩn hóa DTO).
    - Ủy nhiệm việc điều khiển tổng đài cho ApiClient (Mặc định gọi MockApiClient; khi Go-Live chỉ cần cấu hình CTI_MODE=http).
    - TUYỆT ĐỐI KHÔNG CẦN SỬA ĐỔI ADAPTER NÀY KHI CHUYỂN TỪ MOCK SANG HỆ THỐNG THẬT.
    """

    def __init__(self, api_client: Optional[CTIApiClient] = None):
        if api_client is not None:
            self._client = api_client
        else:
            mode = os.getenv("CTI_MODE", "mock").lower()
            if mode == "http":
                self._client = HttpCTIApiClient()
            else:
                self._client = MockCTIApiClient()

    @property
    def client(self) -> CTIApiClient:
        return self._client

    def originate_call(
        self,
        agent_id: str,
        agent_extension: str,
        destination_phone: str,
        case_id: str,
        guardrail_token: str
    ) -> CallSessionDTO:
        """
        Khởi tạo cuộc gọi từ bàn điện thoại viên tới khách nợ.
        Bắt buộc phải có Guardrail Token hợp lệ do L6 Guardrail cấp.
        """
        if not guardrail_token or not guardrail_token.startswith("ey"):
            raise ValueError("LỖI PHÁP CHẾ L6: Không có Guardrail Token hợp lệ. Chặn quay số CTI.")

        raw = self._client.originate_call(
            agent_id=agent_id,
            agent_extension=agent_extension,
            destination_phone=destination_phone,
            case_id=case_id,
            guardrail_token=guardrail_token
        )
        return CallSessionDTO(
            call_id=raw.get("call_id", "UNKNOWN"),
            case_id=case_id,
            destination_phone=destination_phone,
            status=raw.get("status", "INITIATED"),
            started_at=raw.get("started_at", ""),
            recording_url=raw.get("recording_url"),
            gateway=raw.get("gateway", "FREESWITCH")
        )

    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        return self._client.get_call_status(call_id)

    def hangup_call(self, call_id: str) -> Dict[str, Any]:
        return self._client.hangup_call(call_id)
