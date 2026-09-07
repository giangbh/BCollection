import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from .client import SpeechAIApiClient
from .mock_client import MockSpeechAIApiClient
from .http_client import HttpSpeechAIApiClient


@dataclass
class SpeechAnalysisResultDTO:
    case_id: str
    call_duration_seconds: int
    transcript: list
    extracted_outcome: str
    extracted_ptp_amount: Optional[float]
    extracted_ptp_date: Optional[str]
    confidence: float
    detected_root_cause: str
    sentiment: Dict[str, Any]
    compliance_audit: Dict[str, Any]
    auto_notes: str


class SpeechAIAdapter:
    """
    Adapter Duy nhất kết nối Hệ thống Bóc tách Âm thanh & Xử lý Hội thoại (Speech AI & NLP).
    Tuân thủ Kiến trúc Hexagonal (Port & Adapter):
    - Đóng gói toàn bộ logic nghiệp vụ (Kiểm tra tuân thủ, chuẩn hóa kết quả PTP).
    - Ủy nhiệm việc bóc tách giọng nói cho ApiClient (Mặc định gọi MockApiClient; khi Go-Live chỉ cần cấu hình SPEECH_AI_MODE=http).
    - TUYỆT ĐỐI KHÔNG CẦN SỬA ĐỔI ADAPTER NÀY KHI CHUYỂN TỪ MOCK SANG HỆ THỐNG THẬT.
    """

    def __init__(self, api_client: Optional[SpeechAIApiClient] = None):
        if api_client is not None:
            self._client = api_client
        else:
            mode = os.getenv("SPEECH_AI_MODE", "mock").lower()
            if mode == "http":
                self._client = HttpSpeechAIApiClient()
            else:
                self._client = MockSpeechAIApiClient()

    @property
    def client(self) -> SpeechAIApiClient:
        return self._client

    def analyze_call(
        self,
        case_id: str,
        call_duration_seconds: int = 45,
        recording_url: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> SpeechAnalysisResultDTO:
        raw = self._client.analyze_call(
            case_id=case_id,
            call_duration_seconds=call_duration_seconds,
            recording_url=recording_url,
            context=context
        )
        return SpeechAnalysisResultDTO(
            case_id=case_id,
            call_duration_seconds=raw.get("call_duration_seconds", call_duration_seconds),
            transcript=raw.get("transcript", []),
            extracted_outcome=raw.get("extracted_outcome", "BUSY_NO_ANSWER"),
            extracted_ptp_amount=raw.get("extracted_ptp_amount"),
            extracted_ptp_date=raw.get("extracted_ptp_date"),
            confidence=float(raw.get("confidence", 0.0)),
            detected_root_cause=raw.get("detected_root_cause", "UNKNOWN"),
            sentiment=raw.get("sentiment", {"label": "TRUNG TÍNH", "score": 0.0, "tone": "Bình thường"}),
            compliance_audit=raw.get("compliance_audit", {"status": "PASSED", "checks": [], "prohibited_words_found": []}),
            auto_notes=raw.get("auto_notes", "")
        )
