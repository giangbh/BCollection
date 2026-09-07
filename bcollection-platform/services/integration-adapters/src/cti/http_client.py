import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from .client import CTIApiClient


class HttpCTIApiClient(CTIApiClient):
    """
    Production Client gọi REST API tới hệ thống Tổng đài CTI (FreeSWITCH / Avaya API Gateway).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: int = 5
    ):
        self.base_url = (base_url or os.getenv("CTI_GATEWAY_URL", "http://127.0.0.1:8090/legacy/cti/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("CTI_GATEWAY_KEY", "")
        self.timeout = timeout_seconds

    def _make_request(self, endpoint: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Content-Type": "application/json",
            "X-Client-Id": "BCOLLECTION_CTI",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }
        data = json.dumps(payload).encode("utf-8") if payload else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status in (200, 201):
                    return json.loads(response.read().decode("utf-8"))
                raise RuntimeError(f"CTI Gateway Error HTTP {response.status}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Không thể kết nối tới CTI Gateway tại {url}: {str(e)}")

    def originate_call(
        self,
        agent_id: str,
        agent_extension: str,
        destination_phone: str,
        case_id: str,
        guardrail_token: str
    ) -> Dict[str, Any]:
        payload = {
            "agent_id": agent_id,
            "agent_extension": agent_extension,
            "destination_phone": destination_phone,
            "case_id": case_id,
            "guardrail_token": guardrail_token
        }
        return self._make_request("calls/originate", method="POST", payload=payload)

    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        return self._make_request(f"calls/{call_id}/status", method="GET")

    def hangup_call(self, call_id: str) -> Dict[str, Any]:
        return self._make_request(f"calls/{call_id}/hangup", method="POST")
