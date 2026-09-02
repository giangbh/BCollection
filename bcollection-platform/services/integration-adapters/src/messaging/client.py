from abc import ABC, abstractmethod
from typing import Dict, Any

class MessagingApiClient(ABC):
    """
    Interface cấp thấp gửi tin nhắn qua SMS Gateway (VNPT/Viettel) hoặc Zalo ZNS Gateway.
    """
    @abstractmethod
    def dispatch_sms(self, phone_e164: str, message: str, brandname: str = "BIDV") -> Dict[str, Any]:
        pass

    @abstractmethod
    def dispatch_zns(self, phone_e164: str, template_id: str, template_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
