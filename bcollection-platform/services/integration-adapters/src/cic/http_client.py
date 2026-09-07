import os
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from .client import CICApiClient

try:
    from bc_telemetry import global_tracer, global_metrics, format_traceparent
except ImportError:
    global_tracer = None
    global_metrics = None


class HttpCICApiClient(CICApiClient):
    """
    Production Client gọi REST API cổng CIC nội bộ ngân hàng.
    Tự động gắn W3C traceparent context và ghi nhận metrics thời gian thực.
    """
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: int = 2
    ):
        self.base_url = (base_url or os.getenv("CIC_GATEWAY_URL", "http://127.0.0.1:8090/legacy/cic/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("CIC_GATEWAY_KEY", "")
        self.timeout = timeout_seconds

    def fetch_credit_score_and_obligations(self, debtor_cif: str, national_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/reports?cif={debtor_cif}&national_id={national_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Client-Id": "BCOLLECTION_CIC",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }

        span = None
        if global_tracer:
            span = global_tracer.start_span(
                name="cic_http_fetch_report",
                service_name="cic-adapter",
                attributes={"http.url": url, "http.method": "GET", "business.cif": debtor_cif}
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
                        global_metrics.record_adapter_call("cic_adapter", "reports", "SUCCESS", dur)
                    if global_tracer and span:
                        global_tracer.end_span(span, status_code=200)
                    return json.loads(response.read().decode("utf-8"))
                if global_tracer and span:
                    global_tracer.end_span(span, status_code=response.status)
                raise RuntimeError(f"CIC Gateway Error HTTP {response.status}")
        except Exception as e:
            dur = time.time() - start
            if global_metrics:
                global_metrics.record_adapter_call("cic_adapter", "reports", "ERROR", dur)
            if global_tracer and span:
                global_tracer.end_span(span, status_code=500)
            raise ConnectionError(f"Không thể kết nối tới CIC Gateway tại {url}: {str(e)}")
