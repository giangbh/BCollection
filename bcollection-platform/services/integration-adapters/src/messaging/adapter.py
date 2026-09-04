import os
from typing import Dict, Any, Optional
from .client import MessagingApiClient
from .mock_client import MockMessagingApiClient
from .http_client import HttpMessagingApiClient

class MessagingGatewayAdapter:
    """
    Adapter Duy nhất kết nối Cổng Tin nhắn (SMS Brandname / Zalo ZNS) (IF-MSG-01).
    Tuân thủ Kiến trúc Hexagonal (Port & Adapter):
    - Đóng gói toàn bộ logic nghiệp vụ (Kiểm tra Guardrail token hợp lệ, Định dạng mẫu tin nhắn VietQR).
    - Ủy nhiệm việc gửi tin cho ApiClient (Mặc định gọi MockApiClient; khi Go-Live chỉ cần cấu hình MESSAGING_MODE=http).
    - TUYỆT ĐỐI KHÔNG CẦN SỬA ĐỔI ADAPTER NÀY KHI CHUYỂN TỪ MOCK SANG HỆ THỐNG THẬT.
    """
    def __init__(self, api_client: Optional[MessagingApiClient] = None):
        if api_client is not None:
            self._client = api_client
        else:
            mode = os.getenv("MESSAGING_MODE", "mock").lower()
            if mode == "http":
                self._client = HttpMessagingApiClient()
            else:
                self._client = MockMessagingApiClient()

    @property
    def client(self) -> MessagingApiClient:
        return self._client

    def send_sms_notification(
        self,
        phone_e164: str,
        message: str,
        guardrail_token: str,
        brandname: str = "BANK"
    ) -> Dict[str, Any]:
        """Gửi SMS Brandname nhắc nợ chuẩn IF-MSG-01 (Yêu cầu Guardrail Token)"""
        if not guardrail_token or not guardrail_token.startswith("ey"):
            raise ValueError("LỖI PHÁP CHẾ L6: Không có Guardrail Token hợp lệ. Chặn gửi SMS nhắc nợ.")
        
        return self._client.dispatch_sms(phone_e164, message, brandname)

    def send_zns_notification(
        self,
        phone_e164: str,
        template_id: str,
        template_data: Dict[str, Any],
        guardrail_token: str
    ) -> Dict[str, Any]:
        """Gửi Zalo ZNS thông báo kèm link VietQR (Yêu cầu Guardrail Token)"""
        if not guardrail_token or not guardrail_token.startswith("ey"):
            raise ValueError("LỖI PHÁP CHẾ L6: Không có Guardrail Token hợp lệ. Chặn gửi ZNS nhắc nợ.")
        
        return self._client.dispatch_zns(phone_e164, template_id, template_data)
