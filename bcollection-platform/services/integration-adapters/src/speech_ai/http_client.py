import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from .client import SpeechAIApiClient


class HttpSpeechAIApiClient(SpeechAIApiClient):
    """
    Production Client gọi REST API tới Cụm Dịch vụ Speech AI & NLP (Whisper + Qwen LLM).
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
        payload = {
            "case_id": case_id,
            "call_duration_seconds": call_duration_seconds,
            "recording_url": recording_url,
            "context": context or {}
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status in (200, 201):
                    return json.loads(response.read().decode("utf-8"))
                raise RuntimeError(f"Speech AI Service Error HTTP {response.status}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Không thể kết nối tới Speech AI Service tại {url}: {str(e)}")
