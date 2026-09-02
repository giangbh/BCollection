import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from .client import LOSApiClient

class HttpLOSApiClient(LOSApiClient):
    """
    Production Client gọi REST API thật tới hệ thống Khởi tạo Khoản vay (LOS / RLOS)
    thông qua Enterprise Service Bus (ESB / API Gateway).
    """
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: int = 5
    ):
        self.base_url = (base_url or os.getenv("LOS_API_URL", "https://esb.bidv.vn/api/los/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("LOS_API_KEY", "")
        self.timeout = timeout_seconds

    def _make_request(self, endpoint: str) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Content-Type": "application/json",
            "X-Client-Id": "BCOLLECTION_PLATFORM",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    return json.loads(response.read().decode("utf-8"))
                raise RuntimeError(f"LOS API Error HTTP {response.status}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Không thể kết nối tới LOS API Gateway tại {url}: {str(e)}")

    def fetch_party_obligations(self, loan_id: str) -> List[Dict[str, Any]]:
        res = self._make_request(f"loans/{loan_id}/parties")
        return res.get("parties", [])

    def fetch_collateral_details(self, loan_id: str) -> List[Dict[str, Any]]:
        res = self._make_request(f"loans/{loan_id}/collaterals")
        return res.get("collaterals", [])
