"""
Messaging Gateway Microservice (Port 8096)
Cung cấp các API:
- Gửi tin SMS Brandname Ngân hàng
- Gửi tin Zalo ZNS kèm link thanh toán VietQR
"""

from typing import Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .generators import generate_messaging_result

app = FastAPI(
    title="Messaging Gateway Service (Mock)",
    description="Hệ thống Cổng Tin nhắn Viễn thông (Port 8096) — SMS Brandname & Zalo ZNS",
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
    return {"status": "HEALTHY", "service": "messaging-gateway", "port": 8096}


class SMSSendRequest(BaseModel):
    phone_e164: str
    message: str
    brandname: str = "BANK"


@app.post("/api/messaging/v1/sms/send")
def send_sms(payload: SMSSendRequest):
    return generate_messaging_result("SMS", payload.phone_e164, payload.brandname)


class ZNSSendRequest(BaseModel):
    phone_e164: str
    template_id: str
    template_data: Dict[str, Any]


@app.post("/api/messaging/v1/zns/send")
def send_zns(payload: ZNSSendRequest):
    return generate_messaging_result("ZALO", payload.phone_e164)


def run():
    import uvicorn
    uvicorn.run("legacy_servers.messaging_server:app", host="127.0.0.1", port=8096, reload=False)


if __name__ == "__main__":
    run()
