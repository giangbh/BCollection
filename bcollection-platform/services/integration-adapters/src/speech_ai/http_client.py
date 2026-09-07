import os
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from .client import SpeechAIApiClient

try:
    from bc_telemetry import global_tracer, global_metrics, format_traceparent
except ImportError:
    global_tracer = None
    global_metrics = None


class HttpSpeechAIApiClient(SpeechAIApiClient):
    """
    Production Client gọi REST API tới Cụm Dịch vụ Speech AI & NLP (Whisper + Qwen LLM).
    Tự động gắn W3C traceparent context và ghi nhận metrics thời gian thực.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: int = 10
    ):
        self.base_url = (base_url or os.getenv("SPEECH_AI_URL", "http://127.0.0.1:8090/legacy/speech-ai/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("SPEECH_AI_KEY", "")
        self.timeout = timeout_seconds

    def analyze_call(
        self,
        case_id: str,
        call_duration_seconds: int = 45,
        recording_url: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/analyze-call"
        headers = {
            "Content-Type": "application/json",
            "X-Client-Id": "BCOLLECTION_SPEECH_AI",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }

        span = None
        if global_tracer:
            span = global_tracer.start_span(
                name="speech_ai_http_analyze_call",
                service_name="speech-adapter",
                attributes={"http.url": url, "http.method": "POST", "business.case_id": case_id}
            )
            headers["traceparent"] = format_traceparent(span.trace_id, span.span_id)
            headers["X-Trace-Id"] = span.trace_id

        payload = {
            "case_id": case_id,
            "call_duration_seconds": call_duration_seconds,
            "recording_url": recording_url,
            "context": context or {}
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                dur = time.time() - start
                if response.status in (200, 201):
                    if global_metrics:
                        global_metrics.record_adapter_call("speech_ai_adapter", "analyze_call", "SUCCESS", dur)
                    if global_tracer and span:
                        global_tracer.end_span(span, status_code=response.status)
                    return json.loads(response.read().decode("utf-8"))
                if global_tracer and span:
                    global_tracer.end_span(span, status_code=response.status)
                raise RuntimeError(f"Speech AI Service Error HTTP {response.status}")
        except urllib.error.URLError as e:
            dur = time.time() - start
            if global_metrics:
                global_metrics.record_adapter_call("speech_ai_adapter", "analyze_call", "ERROR", dur)
            if global_tracer and span:
                global_tracer.end_span(span, status_code=500)
            raise ConnectionError(f"Không thể kết nối tới Speech AI Service tại {url}: {str(e)}")
