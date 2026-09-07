"""
CTI Telephony Gateway Microservice (Port 8094)
Cung cấp các API:
- Khởi tạo cuộc gọi click-to-call từ tổng đài FreeSWITCH/Avaya
- Tra cứu trạng thái cuộc gọi
- Kết thúc cuộc gọi và phát sinh file ghi âm
"""

from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .generators import generate_cti_call_session

app = FastAPI(
    title="CTI Telephony Gateway Service (Mock)",
    description="Hệ thống Tổng đài Thoại CTI FreeSWITCH / Avaya (Port 8094) — Điều khiển cuộc gọi và ghi âm",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_active_calls: Dict[str, Dict[str, Any]] = {}


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "cti-telephony", "port": 8094}


class OriginateCallRequest(BaseModel):
    agent_id: str
    agent_extension: str
    destination_phone: str
    case_id: str
    guardrail_token: str


@app.post("/api/cti/v1/calls/originate")
def originate_call(payload: OriginateCallRequest):
    if not payload.guardrail_token or not payload.guardrail_token.startswith("ey"):
        raise HTTPException(status_code=403, detail="LỖI PHÁP CHẾ L6: Thiếu Guardrail Token hợp lệ. Chặn quay số CTI.")

    session = generate_cti_call_session(
        agent_id=payload.agent_id,
        agent_extension=payload.agent_extension,
        destination_phone=payload.destination_phone,
        case_id=payload.case_id
    )
    _active_calls[session["call_id"]] = session
    return session


@app.get("/api/cti/v1/calls/{call_id}/status")
def get_call_status(call_id: str):
    if call_id in _active_calls:
        return _active_calls[call_id]
    return {"call_id": call_id, "status": "COMPLETED"}


@app.post("/api/cti/v1/calls/{call_id}/hangup")
def hangup_call(call_id: str):
    if call_id in _active_calls:
        _active_calls[call_id]["status"] = "HUNGUP"
        _active_calls[call_id]["ended_at"] = datetime.now(timezone.utc).isoformat()
        return _active_calls[call_id]
    return {"call_id": call_id, "status": "HUNGUP"}


def run():
    import uvicorn
    uvicorn.run("legacy_servers.cti_server:app", host="127.0.0.1", port=8094, reload=False)


if __name__ == "__main__":
    run()
