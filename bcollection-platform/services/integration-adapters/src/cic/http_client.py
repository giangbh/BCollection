import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from .client import CICApiClient

class HttpCICApiClient(CICApiClient):
    """Production Client gọi REST API cổng CIC nội bộ ngân hàng"""
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: int = 5
    ):
        self.base_url = (base_url or os.getenv("CIC_GATEWAY_URL", "https://esb.bidv.vn/api/cic/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("CIC_GATEWAY_KEY", "")
        self.timeout = timeout_seconds

    def fetch_credit_score_and_obligations(self, debtor_cif: str, national_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/reports?cif={debtor_cif}&national_id={national_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Client-Id": "BCOLLECTION_CIC",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    return json.loads(response.read().decode("utf-8"))
                raise RuntimeError(f"CIC Gateway Error HTTP {response.status}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Không thể kết nối tới CIC Gateway tại {url}: {str(e)}")
