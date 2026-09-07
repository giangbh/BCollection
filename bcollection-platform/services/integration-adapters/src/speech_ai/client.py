from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class SpeechAIApiClient(ABC):
    """
    Interface cấp thấp kết nối trực tiếp với Cụm Dịch vụ Speech AI & NLP
    (ASR Whisper, NLP Qwen/PhoBERT, Sentiment Analysis).
    """

    @abstractmethod
    def analyze_call(
        self,
        case_id: str,
        call_duration_seconds: int = 45,
        recording_url: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Bóc tách âm thanh, nhận diện hội thoại, cảm xúc và cam kết PTP."""
        pass
