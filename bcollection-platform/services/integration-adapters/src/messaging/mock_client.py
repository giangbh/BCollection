from typing import Dict, Any, List
from datetime import datetime
from .client import MessagingApiClient

class MockMessagingApiClient(MessagingApiClient):
    """Mock Service giả lập SMS/ZNS Gateway phục vụ DEV/UAT"""
    def __init__(self):
        self.sent_messages: List[Dict[str, Any]] = []

    def dispatch_sms(self, phone_e164: str, message: str, brandname: str = "BANK") -> Dict[str, Any]:
        msg_id = f"SMS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self.sent_messages)+1}"
        record = {
            "msg_id": msg_id,
            "channel": "SMS",
            "phone_e164": phone_e164,
            "brandname": brandname,
            "content": message,
            "status": "DELIVERED_SUCCESS",
            "sent_at": datetime.now().isoformat()
        }
        self.sent_messages.append(record)
        return {"status": "SUCCESS", "message_id": msg_id, "provider": "MOCK_TELCO"}

    def dispatch_zns(self, phone_e164: str, template_id: str, template_data: Dict[str, Any]) -> Dict[str, Any]:
        msg_id = f"ZNS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self.sent_messages)+1}"
        record = {
            "msg_id": msg_id,
            "channel": "ZALO_ZNS",
            "phone_e164": phone_e164,
            "template_id": template_id,
            "template_data": template_data,
            "status": "DELIVERED_SUCCESS",
            "sent_at": datetime.now().isoformat()
        }
        self.sent_messages.append(record)
        return {"status": "SUCCESS", "message_id": msg_id, "provider": "MOCK_ZALO"}
