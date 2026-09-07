"""
Speech AI & NLP Microservice (Port 8095)
Cung cấp các API:
- Bóc tách nhận diện âm thanh ASR Whisper
- Trích xuất thực thể cam kết PTP, ngày hẹn trả và số tiền
- Phân tích sắc thái cảm xúc và kiểm soát tuân thủ từ ngữ cấm
"""

from typing import Dict, Any, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .generators import generate_speech_ai_analysis

app = FastAPI(
    title="Speech AI & NLP Service (Mock)",
    description="Hệ thống Bóc tách Thoại Speech AI & NLP (Port 8095) — Whisper ASR & Phân tích cảm xúc",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "speech-ai-nlp", "port": 8095}


class SpeechAnalysisRequest(BaseModel):
    case_id: str
    call_duration_seconds: int = 45
    recording_url: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@app.post("/api/speech-ai/v1/analyze-call")
def analyze_call(payload: SpeechAnalysisRequest):
    return generate_speech_ai_analysis(payload.case_id, payload.call_duration_seconds)


def run():
    import uvicorn
    uvicorn.run("legacy_servers.speech_server:app", host="127.0.0.1", port=8095, reload=False)


if __name__ == "__main__":
    run()
