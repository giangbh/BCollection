"""
LOS / RLOS Loan Origination Microservice (Port 8092)
Cung cấp các API:
- Tra cứu danh sách các bên có nghĩa vụ tín dụng (IF-LOS-02)
- Tra cứu tài sản bảo đảm thế chấp và tỷ lệ LTV
"""

from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .generators import generate_los_parties, generate_los_collaterals

app = FastAPI(
    title="LOS Loan Origination Service (Mock)",
    description="Hệ thống Khởi tạo Khoản vay LOS / RLOS (Port 8092) — Các bên nghĩa vụ và tài sản thế chấp",
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
    return {"status": "HEALTHY", "service": "los-origination", "port": 8092}


@app.get("/api/los/v1/loans/{loan_id}/parties")
def get_loan_parties(loan_id: str):
    parties = generate_los_parties(loan_id)
    return {"loan_id": loan_id, "parties": parties}


@app.get("/api/los/v1/loans/{loan_id}/collaterals")
def get_loan_collaterals(loan_id: str):
    collaterals = generate_los_collaterals(loan_id)
    return {"loan_id": loan_id, "collaterals": collaterals}


def run():
    import uvicorn
    uvicorn.run("legacy_servers.los_server:app", host="127.0.0.1", port=8092, reload=False)


if __name__ == "__main__":
    run()
