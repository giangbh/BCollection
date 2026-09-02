import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from .client import CoreBankingApiClient

class HttpCoreBankingApiClient(CoreBankingApiClient):
    """
    Production Client gọi REST API thật tới hệ thống Core Banking BIDV
    thông qua Enterprise Service Bus (ESB / API Gateway).
    Hỗ trợ cấu hình Endpoint URL, API Key, Token và Timeout qua biến môi trường.
    """
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: int = 5
    ):
        self.base_url = (base_url or os.getenv("CORE_BANKING_API_URL", "https://esb.bidv.vn/api/core/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("CORE_BANKING_API_KEY", "")
        self.timeout = timeout_seconds

    def _make_request(self, endpoint: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Content-Type": "application/json",
            "X-Client-Id": "BCOLLECTION_PLATFORM",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }
        data = json.dumps(payload).encode("utf-8") if payload else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status in (200, 201):
                    return json.loads(response.read().decode("utf-8"))
                raise RuntimeError(f"Core Banking API Error HTTP {response.status}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Không thể kết nối tới Core Banking ESB tại {url}: {str(e)}")

    def fetch_loan_balance(self, loan_id: str) -> Dict[str, Any]:
        return self._make_request(f"loans/{loan_id}/balance")

    def fetch_recent_payments(self, loan_id: str, lookback_minutes: int = 15) -> List[Dict[str, Any]]:
        res = self._make_request(f"loans/{loan_id}/payments?lookback_minutes={lookback_minutes}")
        return res.get("payments", [])

    def fetch_overdue_portfolio(self, max_dpd: int = 30) -> List[Dict[str, Any]]:
        res = self._make_request(f"portfolio/delinquent?max_dpd={max_dpd}")
        return res.get("loans", [])

    def fetch_customer_inflows(self, debtor_cif: str, months: int = 3) -> Dict[str, Any]:
        return self._make_request(f"customers/{debtor_cif}/cashflows?months={months}")
