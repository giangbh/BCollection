"""
Nền tảng W3C Distributed Tracing cho B.Collection.
Tuân thủ chuẩn W3C Trace Context (RFC 8410 / W3C Recommendation):
- Định dạng traceparent: 00-{trace_id_32_hex}-{parent_id_16_hex}-{trace_flags_2_hex}
- Quản lý phân cấp Spans theo từng Async Task / Request Context
- Lưu trữ In-Memory Circular Buffer 250 traces gần nhất phục vụ Live Visualizer Dashboard
"""

import os
import time
import secrets
import threading
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

# ContextVar quản lý span đang hoạt động trong luồng hiện tại
_current_span: ContextVar[Optional["Span"]] = ContextVar("current_span", default=None)


@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    service_name: str
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status_code: int = 200
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def finish(self, status_code: Optional[int] = None):
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        if status_code is not None:
            self.status_code = status_code

    def add_attribute(self, key: str, value: Any):
        self.attributes[key] = value

    def add_event(self, name: str, payload: Optional[Dict[str, Any]] = None):
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "payload": payload or {}
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "service_name": self.service_name,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms or (round((time.time() - self.start_time) * 1000, 2) if not self.end_time else 0.0),
            "status_code": self.status_code,
            "attributes": self.attributes,
            "events": self.events,
        }


@dataclass
class Trace:
    trace_id: str
    root_span: Span
    spans: List[Span] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.spans:
            self.spans = [self.root_span]

    def add_span(self, span: Span):
        self.spans.append(span)

    @property
    def duration_ms(self) -> float:
        if self.root_span.duration_ms is not None:
            return self.root_span.duration_ms
        if self.spans:
            start = min(s.start_time for s in self.spans)
            end = max(s.end_time or time.time() for s in self.spans)
            return round((end - start) * 1000, 2)
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "root_service": self.root_span.service_name,
            "root_name": self.root_span.name,
            "status_code": self.root_span.status_code,
            "duration_ms": self.duration_ms,
            "created_at": datetime.fromtimestamp(self.created_at, timezone.utc).isoformat(),
            "attributes": self.root_span.attributes,
            "span_count": len(self.spans),
            "spans": [s.to_dict() for s in sorted(self.spans, key=lambda s: s.start_time)]
        }


def generate_trace_id() -> str:
    """Sinh 32 ký tự hex (128-bit) theo chuẩn W3C Trace ID."""
    return secrets.token_hex(16)


def generate_span_id() -> str:
    """Sinh 16 ký tự hex (64-bit) theo chuẩn W3C Span ID."""
    return secrets.token_hex(8)


def parse_traceparent(header_value: Optional[str]) -> Optional[Dict[str, str]]:
    """
    Phân tích W3C traceparent header:
    Định dạng: 00-{trace_id}-{parent_id}-{trace_flags}
    """
    if not header_value:
        return None
    parts = header_value.strip().split("-")
    if len(parts) != 4 or parts[0] != "00":
        return None
    trace_id, parent_id, flags = parts[1], parts[2], parts[3]
    if len(trace_id) != 32 or len(parent_id) != 16:
        return None
    return {
        "trace_id": trace_id,
        "parent_id": parent_id,
        "flags": flags
    }


def format_traceparent(trace_id: str, span_id: str, flags: str = "01") -> str:
    """Đóng gói thành header W3C traceparent chuẩn."""
    return f"00-{trace_id}-{span_id}-{flags}"


class Tracer:
    """
    Quản lý tập trung toàn bộ Traces & Spans trong tiến trình.
    Sử dụng Circular Buffer luồng an toàn (Thread-safe) lưu 250 traces gần nhất.
    """
    def __init__(self, service_name: str = "bcollection", max_history: int = 250):
        self.default_service_name = service_name
        self.max_history = max_history
        self._traces: Dict[str, Trace] = {}
        self._trace_order: List[str] = []
        self._lock = threading.Lock()

    def start_span(
        self,
        name: str,
        service_name: Optional[str] = None,
        traceparent: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        is_root: bool = False,
    ) -> Span:
        parsed = parse_traceparent(traceparent)
        parent = None if is_root else _current_span.get()

        if parsed:
            trace_id = parsed["trace_id"]
            parent_span_id = parsed["parent_id"]
        elif parent:
            trace_id = parent.trace_id
            parent_span_id = parent.span_id
        else:
            trace_id = generate_trace_id()
            parent_span_id = None

        span_id = generate_span_id()
        svc = service_name or self.default_service_name

        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            service_name=svc,
            name=name,
            start_time=time.time(),
            attributes=attributes or {}
        )

        with self._lock:
            if trace_id not in self._traces:
                trace = Trace(trace_id=trace_id, root_span=span)
                self._traces[trace_id] = trace
                self._trace_order.append(trace_id)
                if len(self._trace_order) > self.max_history:
                    oldest = self._trace_order.pop(0)
                    self._traces.pop(oldest, None)
            else:
                self._traces[trace_id].add_span(span)

        _current_span.set(span)
        return span

    def end_span(self, span: Span, status_code: Optional[int] = None):
        span.finish(status_code)
        curr = _current_span.get()
        if curr and curr.span_id == span.span_id:
            parent_span = None
            if span.parent_span_id:
                with self._lock:
                    trace = self._traces.get(span.trace_id)
                    if trace:
                        for s in trace.spans:
                            if s.span_id == span.parent_span_id:
                                parent_span = s
                                break
            _current_span.set(parent_span)

    def get_current_span(self) -> Optional[Span]:
        return _current_span.get()

    def get_current_traceparent(self) -> Optional[str]:
        span = _current_span.get()
        if span:
            return format_traceparent(span.trace_id, span.span_id)
        return None

    def get_recent_traces(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            ordered_ids = list(reversed(self._trace_order[-limit:]))
            result = []
            for tid in ordered_ids:
                t = self._traces.get(tid)
                if t:
                    result.append(t.to_dict())
            return result

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            t = self._traces.get(trace_id)
            return t.to_dict() if t else None

    def clear(self):
        with self._lock:
            self._traces.clear()
            self._trace_order.clear()


# Singleton Tracer toàn cục
global_tracer = Tracer()
