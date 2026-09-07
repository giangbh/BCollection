"""
Core Banking ESB Microservice (Port 8091)
Cung cấp các API:
- Tra cứu số dư nợ quá hạn thời gian thực
- Tra cứu giao dịch nộp tiền trong 15 phút
- Tra cứu dòng tiền lương và số dư CASA
- Danh mục nợ B1
- API giả lập thanh toán tức thời (simulate/payment)
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .generators import generate_core_loan_balance, generate_core_cashflow, get_db_connection

app = FastAPI(
    title="Core Banking ESB Service (Mock)",
    description="Hệ thống Core Banking ESB Ngân hàng (Port 8091) — Tra cứu số dư, dòng tiền và thanh toán",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_simulated_payments: Dict[str, List[Dict[str, Any]]] = {}
_balance_overrides: Dict[str, Dict[str, Any]] = {}


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "core-banking-esb", "port": 8091}


@app.get("/api/core/v1/loans/{loan_id}/balance")
def get_loan_balance(loan_id: str):
    return generate_core_loan_balance(loan_id, overrides=_balance_overrides)


@app.get("/api/core/v1/loans/{loan_id}/payments")
def get_recent_payments(loan_id: str, lookback_minutes: int = 15):
    payments = _simulated_payments.get(loan_id, [])
    now = time.time()
    valid = []
    for p in payments:
        if (now - p.get("_created_timestamp", now)) <= (lookback_minutes * 60):
            valid.append({k: v for k, v in p.items() if not k.startswith("_")})
    return {"loan_id": loan_id, "payments": valid}


class PaymentSimulationRequest(BaseModel):
    loan_id: str
    debtor_cif: str
    amount_paid: float
    channel: str = "VIETQR"


@app.post("/api/core/v1/simulate/payment")
def simulate_payment(payload: PaymentSimulationRequest):
    event_id = f"PAY-SIM-{int(time.time()*1000)}"
    record = {
        "event_id": event_id,
        "loan_id": payload.loan_id,
        "debtor_cif": payload.debtor_cif,
        "amount_paid": payload.amount_paid,
        "paid_at": datetime.now(timezone.utc).isoformat(),
        "channel": payload.channel,
        "_created_timestamp": time.time()
    }
    if payload.loan_id not in _simulated_payments:
        _simulated_payments[payload.loan_id] = []
    _simulated_payments[payload.loan_id].append(record)

    # Đưa số dư nợ quá hạn về 0 để demo chống đòi nợ oan
    _balance_overrides[payload.loan_id] = {
        "loan_id": payload.loan_id,
        "debtor_cif": payload.debtor_cif,
        "outstanding_principal": 15000000.0,
        "outstanding_interest": 0.0,
        "overdue_amount": 0.0,
        "dpd": 0,
        "days_past_due": 0,
        "loan_status": "ACTIVE",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source_version": 2
    }
    return {
        "status": "SUCCESS",
        "payment": record,
        "message": "Số dư nợ quá hạn đã được cập nhật thành 0. Hủy nhắc nợ tự động."
    }


@app.get("/api/core/v1/customers/{debtor_cif}/cashflows")
def get_customer_cashflows(debtor_cif: str, months: int = 3):
    return generate_core_cashflow(debtor_cif)


@app.get("/api/core/v1/portfolio/delinquent")
def get_delinquent_portfolio(max_dpd: int = 30):
    conn = get_db_connection()
    loans = []
    if conn:
        try:
            rows = conn.execute("SELECT * FROM cases WHERE dpd <= ? LIMIT 50", (max_dpd,)).fetchall()
            for r in rows:
                loans.append(dict(r))
        finally:
            conn.close()
    return {"loans": loans, "total": len(loans)}


def run():
    import uvicorn
    uvicorn.run("legacy_servers.core_server:app", host="127.0.0.1", port=8091, reload=False)


if __name__ == "__main__":
    run()
