"""
ASGI / FastAPI Middleware tự động bắt và truyền W3C Trace Context và thu thập Metrics.
- Tự động gắn W3C traceparent và X-Trace-Id vào HTTP Response
- Đo lường chính xác thời gian thực thi (Latency in Milliseconds)
- Trích xuất metadata nghiệp vụ (case_id, agent_id, endpoint path template)
"""

import time
import re
from typing import Optional, Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .trace_context import global_tracer, parse_traceparent, format_traceparent
from .metrics import global_metrics

# Regex chuẩn hóa path loại bỏ param ID để gom nhóm metrics
CASE_ID_REGEX = re.compile(r"CASE-\d{4}-\d+")
LOAN_ID_REGEX = re.compile(r"(LN|LOAN)-[A-Z0-9-]+")
CIF_REGEX = re.compile(r"CIF\d+")


def normalize_path(path: str) -> str:
    p = CASE_ID_REGEX.sub("{case_id}", path)
    p = LOAN_ID_REGEX.sub("{loan_id}", p)
    p = CIF_REGEX.sub("{cif}", p)
    return p


class TelemetryMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_name: str = "bcollection"):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1. Trích xuất traceparent từ header hoặc sinh mới
        incoming_traceparent = request.headers.get("traceparent")
        incoming_trace_id = request.headers.get("x-trace-id")

        method = request.method
        raw_path = request.url.path
        norm_path = normalize_path(raw_path)
        span_name = f"{method} {norm_path}"

        # Bắt đầu Span
        span = global_tracer.start_span(
            name=span_name,
            service_name=self.service_name,
            traceparent=incoming_traceparent,
            is_root=True,
            attributes={
                "http.method": method,
                "http.url": str(request.url),
                "http.path": raw_path,
                "http.client_ip": request.client.host if request.client else "unknown",
            }
        )

        # Trích xuất nghiệp vụ (case_id, agent_id)
        if "CASE-" in raw_path:
            match = CASE_ID_REGEX.search(raw_path)
            if match:
                span.add_attribute("business.case_id", match.group(0))

        start_time = time.time()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            span.add_attribute("error", True)
            span.add_attribute("error.message", str(exc))
            raise
        finally:
            duration_s = time.time() - start_time
            # Kết thúc Span
            global_tracer.end_span(span, status_code=status_code)

            # Ghi nhận metric
            global_metrics.record_http_request(
                service=self.service_name,
                method=method,
                path=norm_path,
                status_code=status_code,
                duration_seconds=duration_s
            )

            # Gắn headers vào response nếu có
            if 'response' in locals() and isinstance(response, Response):
                response.headers["traceparent"] = format_traceparent(span.trace_id, span.span_id)
                response.headers["X-Trace-Id"] = span.trace_id
                response.headers["X-Span-Id"] = span.span_id
                response.headers["X-Response-Time-Ms"] = str(round(duration_s * 1000, 2))
