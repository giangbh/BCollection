"""
CIC National Credit Information Microservice (Port 8093)
Cung cấp các API:
- Báo cáo quan hệ tín dụng toàn ngành CIC
- Điểm tín dụng và nhóm nợ xấu nhất tại các TCTD khác
"""

from typing import Dict, Any
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from .generators import generate_cic_report

app = FastAPI(
    title="CIC Credit Information Service (Mock)",
    description="Cổng Thông tin Tín dụng Quốc gia CIC (Port 8093) — Lịch sử quan hệ tín dụng toàn ngành",
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
    return {"status": "HEALTHY", "service": "cic-gateway", "port": 8093}


@app.get("/api/cic/v1/reports")
def get_cic_report_endpoint(cif: str = Query(..., description="Mã CIF của khách hàng"), national_id: str = ""):
    return generate_cic_report(cif, national_id)


def run():
    import uvicorn
    uvicorn.run("legacy_servers.cic_server:app", host="127.0.0.1", port=8093, reload=False)


if __name__ == "__main__":
    run()
