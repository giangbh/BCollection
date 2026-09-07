import os
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from .client import LOSApiClient

try:
    from bc_telemetry import global_tracer, global_metrics, format_traceparent
except ImportError:
    global_tracer = None
    global_metrics = None


class HttpLOSApiClient(LOSApiClient):
    """
    Production Client gọi REST API thật tới hệ thống Khởi tạo Khoản vay (LOS / RLOS)
    thông qua Enterprise Service Bus (ESB / API Gateway).
    Tự động gắn W3C traceparent context và ghi nhận metrics thời gian thực.
    """
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: int = 2
    ):
        self.base_url = (base_url or os.getenv("LOS_API_URL", "http://127.0.0.1:8090/legacy/los/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("LOS_API_KEY", "")
        self.timeout = timeout_seconds

    def _make_request(self, endpoint: str) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Content-Type": "application/json",
            "X-Client-Id": "BCOLLECTION_PLATFORM",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }

        span = None
        clean_endpoint = endpoint.split("?")[0].replace("/", "_")
        if global_tracer:
            span = global_tracer.start_span(
                name=f"los_http_{clean_endpoint}",
                service_name="los-adapter",
                attributes={"http.url": url, "http.method": "GET"}
            )
            headers["traceparent"] = format_traceparent(span.trace_id, span.span_id)
            headers["X-Trace-Id"] = span.trace_id

        req = urllib.request.Request(url, headers=headers, method="GET")
        start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                dur = time.time() - start
                if response.status == 200:
                    if global_metrics:
                        global_metrics.record_adapter_call("los_adapter", clean_endpoint.split("_")[0], "SUCCESS", dur)
                    if global_tracer and span:
                        global_tracer.end_span(span, status_code=200)
                    return json.loads(response.read().decode("utf-8"))
                if global_tracer and span:
                    global_tracer.end_span(span, status_code=response.status)
                raise RuntimeError(f"LOS API Error HTTP {response.status}")
        except Exception as e:
            dur = time.time() - start
            if global_metrics:
                global_metrics.record_adapter_call("los_adapter", clean_endpoint.split("_")[0], "ERROR", dur)
            if global_tracer and span:
                global_tracer.end_span(span, status_code=500)
            raise ConnectionError(f"Không thể kết nối tới LOS API Gateway tại {url}: {str(e)}")

    def fetch_party_obligations(self, loan_id: str) -> List[Dict[str, Any]]:
        res = self._make_request(f"loans/{loan_id}/parties")
        return res.get("parties", [])

    def fetch_collateral_details(self, loan_id: str) -> List[Dict[str, Any]]:
        res = self._make_request(f"loans/{loan_id}/collaterals")
        return res.get("collaterals", [])
