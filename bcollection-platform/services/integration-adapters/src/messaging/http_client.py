import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from .client import MessagingApiClient

class HttpMessagingApiClient(MessagingApiClient):
    """Production Client gọi REST API thật tới SMS Brandname / Zalo ZNS Gateway"""
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: int = 5
    ):
        self.base_url = (base_url or os.getenv("MSG_GATEWAY_URL", "https://esb.bank.vn/api/messaging/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("MSG_GATEWAY_KEY", "")
        self.timeout = timeout_seconds

    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Content-Type": "application/json",
            "X-Client-Id": "BCOLLECTION_MESSAGING",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status in (200, 201):
                    return json.loads(response.read().decode("utf-8"))
                raise RuntimeError(f"Messaging Gateway Error HTTP {response.status}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Không thể kết nối tới SMS/ZNS Gateway tại {url}: {str(e)}")

    def dispatch_sms(self, phone_e164: str, message: str, brandname: str = "BANK") -> Dict[str, Any]:
        return self._make_request("sms/send", {
            "phone_e164": phone_e164,
            "message": message,
            "brandname": brandname
        })

    def dispatch_zns(self, phone_e164: str, template_id: str, template_data: Dict[str, Any]) -> Dict[str, Any]:
        return self._make_request("zns/send", {
            "phone_e164": phone_e164,
            "template_id": template_id,
            "template_data": template_data
        })
