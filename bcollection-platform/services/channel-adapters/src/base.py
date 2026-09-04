from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import sys
import os

# Thêm đường dẫn guardrail vào path để verify token
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../bcollection-guardrail')))
from src.guardrail.api.token import verify_guardrail_token


class BaseChannelAdapter(ABC):
    """
    Adapter kênh cơ sở.
    BẮT BUỘC kiểm tra tính hợp lệ của Guardrail Token trước khi phát bất kỳ lệnh nào ra Gateway.
    """
    def __init__(self, channel_name: str):
        self.channel_name = channel_name

    def send_message(self, request_payload: Dict[str, Any]) -> Dict[str, Any]:
        token = request_payload.get("guardrail_token")
        if not token:
            raise PermissionError("LỆNH BỊ TỪ CHỐI: Thiếu Guardrail Token hợp lệ.")

        token_payload = verify_guardrail_token(token)
        if not token_payload:
            raise PermissionError("LỆNH BỊ TỪ CHỐI: Guardrail Token không hợp lệ hoặc đã hết hạn (TTL 5m).")

        # Kiểm tra token có đúng kênh và đúng đối tượng không
        if token_payload.get("chan") != self.channel_name:
            raise PermissionError(f"LỆNH BỊ TỪ CHỐI: Token cấp cho kênh {token_payload.get('chan')}, không thể dùng cho {self.channel_name}.")

        return self._dispatch_to_gateway(request_payload, token_payload)

    @abstractmethod
    def _dispatch_to_gateway(self, request_payload: Dict[str, Any], token_payload: Dict[str, Any]) -> Dict[str, Any]:
        pass


class MockSMSChannelAdapter(BaseChannelAdapter):
    def __init__(self):
        super().__init__("SMS")

    def _dispatch_to_gateway(self, request_payload: Dict[str, Any], token_payload: Dict[str, Any]) -> Dict[str, Any]:
        recipient = request_payload.get("recipient_phone_e164")
        template_id = request_payload.get("template_id", "SMS_B1_STANDARD")
        vietqr_link = request_payload.get("payment_link", "https://bank.vn/c/tkn9982")

        return {
            "status": "SENT",
            "gateway_message_id": f"SMS-GW-{token_payload.get('req_id')}",
            "channel": "SMS",
            "recipient": recipient,
            "vietqr_link": vietqr_link,
            "cost_vnd": 500
        }


class MockZNSChannelAdapter(BaseChannelAdapter):
    def __init__(self):
        super().__init__("ZALO")

    def _dispatch_to_gateway(self, request_payload: Dict[str, Any], token_payload: Dict[str, Any]) -> Dict[str, Any]:
        recipient = request_payload.get("recipient_phone_e164")
        template_id = request_payload.get("template_id", "ZNS_B1_VIETQR")
        vietqr_link = request_payload.get("payment_link", "https://bank.vn/c/tkn9982")

        return {
            "status": "SENT",
            "gateway_message_id": f"ZNS-GW-{token_payload.get('req_id')}",
            "channel": "ZALO",
            "recipient": recipient,
            "vietqr_link": vietqr_link,
            "cost_vnd": 300
        }
