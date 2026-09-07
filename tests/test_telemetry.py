import pytest
import time
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bc_telemetry.trace_context import (
    global_tracer,
    parse_traceparent,
    format_traceparent,
    generate_trace_id,
    generate_span_id,
)
from bc_telemetry.metrics import global_metrics
from bc_telemetry.middleware import TelemetryMiddleware


def test_w3c_traceparent_format_and_parse():
    trace_id = generate_trace_id()
    span_id = generate_span_id()
    assert len(trace_id) == 32
    assert len(span_id) == 16

    header = format_traceparent(trace_id, span_id)
    assert header.startswith("00-")
    assert header.endswith("-01")

    parsed = parse_traceparent(header)
    assert parsed is not None
    assert parsed["trace_id"] == trace_id
    assert parsed["parent_id"] == span_id
    assert parsed["flags"] == "01"

    # Test invalid headers
    assert parse_traceparent("") is None
    assert parse_traceparent("invalid-header") is None
    assert parse_traceparent("01-trace-span-00") is None


def test_tracer_span_lifecycle_and_hierarchy():
    global_tracer.clear()
    root = global_tracer.start_span("root_operation", service_name="test_service")
    assert root.trace_id is not None
    assert root.parent_span_id is None

    # Child span
    child = global_tracer.start_span("child_operation", service_name="child_service")
    assert child.trace_id == root.trace_id
    assert child.parent_span_id == root.span_id

    time.sleep(0.01)
    global_tracer.end_span(child, status_code=200)
    assert child.duration_ms is not None
    assert child.duration_ms >= 5.0

    global_tracer.end_span(root, status_code=200)
    assert root.duration_ms is not None

    trace = global_tracer.get_trace(root.trace_id)
    assert trace is not None
    assert trace["span_count"] == 2
    assert trace["root_name"] == "root_operation"


def test_metrics_collector_and_prometheus_rendering():
    global_metrics.record_http_request("backend-api", "GET", "/api/cases", 200, 0.045)
    global_metrics.record_http_request("backend-api", "POST", "/api/cases/{case_id}/call-originate", 200, 0.085)
    global_metrics.record_http_request("backend-api", "POST", "/api/cases/{case_id}/call-originate", 403, 0.012)
    global_metrics.record_adapter_call("cti_adapter", "originate_call", "SUCCESS", 0.040)
    global_metrics.record_guardrail_eval("PASSED")
    global_metrics.record_guardrail_eval("VIOLATION_TIME_WINDOW")

    stats = global_metrics.get_aggregated_stats()
    assert stats["total_requests"] >= 3
    assert stats["total_errors"] >= 1
    assert "backend-api" in stats["service_breakdown"]

    prom_text = global_metrics.render_prometheus_text()
    assert "# HELP http_requests_total" in prom_text
    assert "# TYPE http_requests_total counter" in prom_text
    assert 'http_requests_total{service="backend-api"' in prom_text
    assert "# HELP http_request_duration_seconds" in prom_text
    assert 'adapter_calls_total{adapter="cti_adapter"' in prom_text
    assert 'guardrail_evaluations_total{verdict="PASSED"}' in prom_text


def test_telemetry_middleware_e2e():
    app = FastAPI()
    app.add_middleware(TelemetryMiddleware, service_name="test-api")

    @app.get("/api/cases/{case_id}/test")
    def sample_endpoint(case_id: str):
        return {"status": "OK", "case": case_id}

    client = TestClient(app)
    resp = client.get("/api/cases/CASE-2026-10423/test")
    assert resp.status_code == 200
    assert "traceparent" in resp.headers
    assert "X-Trace-Id" in resp.headers
    assert "X-Response-Time-Ms" in resp.headers

    trace_id = resp.headers["X-Trace-Id"]
    trace = global_tracer.get_trace(trace_id)
    assert trace is not None
    assert trace["attributes"].get("business.case_id") == "CASE-2026-10423"
