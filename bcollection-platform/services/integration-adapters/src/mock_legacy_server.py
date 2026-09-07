"""
B.Collection Mock Legacy REST API Server (Port 8090)
Cung cấp toàn bộ các REST API chuẩn của các hệ thống ngân hàng truyền thống (Legacy Banking Apps):
- Core Banking ESB (/legacy/core/v1/...)
- Loan Origination System (/legacy/los/v1/...)
- Credit Information Center (/legacy/cic/v1/...)
- CTI Telephony Gateway (/legacy/cti/v1/...)
- Speech AI & NLP Service (/legacy/speech-ai/v1/...)
- Messaging SMS/ZNS Gateway (/legacy/messaging/v1/...)
"""

import os
import sys
import time
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parents[4]
DB_PATH = ROOT_DIR / ".runtime" / "demo" / "bcollection.sqlite3"

app = FastAPI(
    title="B.Collection Mock Legacy Banking REST Server",
    description="Mock REST API Server giả lập các hệ thống Core Banking, LOS, CIC, CTI, Speech AI cho Demo",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory dynamic state overrides (cho phép mô phỏng thanh toán, đổi số dư tức thời)
_simulated_payments: Dict[str, List[Dict[str, Any]]] = {}
_balance_overrides: Dict[str, Dict[str, Any]] = {}
_active_calls: Dict[str, Dict[str, Any]] = {}
_call_seq = 5000


def get_db():
    if DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn
    return None


@app.get("/health")
def health():
    return {
        "status": "HEALTHY",
        "service": "bcollection-mock-legacy-server",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database_connected": DB_PATH.exists()
    }


# =====================================================================
# 1. CORE BANKING REST API
# =====================================================================

@app.get("/legacy/core/v1/loans/{loan_id}/balance")
def get_loan_balance(loan_id: str):
    if loan_id in _balance_overrides:
        return _balance_overrides[loan_id]

    conn = get_db()
    if conn:
        try:
            row = conn.execute("SELECT * FROM cases WHERE loan_id=?", (loan_id,)).fetchone()
            if row:
                overdue = float(row["overdue_amount"] or 0)
                dpd = int(row["dpd"] or 0)
                principal = float(overdue * 2.5)
                interest = float(overdue * 0.1)
                return {
                    "loan_id": loan_id,
                    "debtor_cif": row["debtor_cif"],
                    "outstanding_principal": principal,
                    "outstanding_interest": interest,
                    "overdue_amount": overdue,
                    "dpd": dpd,
                    "loan_status": "OVERDUE" if overdue > 0 else "ACTIVE",
                    "as_of": datetime.now(timezone.utc).isoformat(),
                    "source_version": 1
                }
        finally:
            conn.close()

    # Fallback cho loan_id bất kỳ
    return {
        "loan_id": loan_id,
        "debtor_cif": "CIF_DEFAULT",
        "outstanding_principal": 20000000.0,
        "outstanding_interest": 1000000.0,
        "overdue_amount": 3000000.0,
        "dpd": 10,
        "loan_status": "OVERDUE",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source_version": 1
    }


@app.get("/legacy/core/v1/loans/{loan_id}/payments")
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


@app.post("/legacy/core/v1/simulate/payment")
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

    # Đưa số dư nợ quá hạn về 0 để demo tình huống chống đòi nợ oan
    _balance_overrides[payload.loan_id] = {
        "loan_id": payload.loan_id,
        "debtor_cif": payload.debtor_cif,
        "outstanding_principal": 10000000.0,
        "outstanding_interest": 0.0,
        "overdue_amount": 0.0,
        "dpd": 0,
        "loan_status": "ACTIVE",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source_version": 2
    }
    return {"status": "SUCCESS", "payment": record, "message": "Số dư đã được cập nhật thành 0"}


@app.get("/legacy/core/v1/customers/{debtor_cif}/cashflows")
def get_customer_cashflows(debtor_cif: str, months: int = 3):
    cif_num = sum(ord(c) for c in debtor_cif)
    salary_day = (cif_num % 10) + 5  # ngày 5-15
    salary = 15000000.0 + (cif_num % 20) * 1000000.0
    casa = 3000000.0 + (cif_num % 15) * 500000.0
    return {
        "debtor_cif": debtor_cif,
        "verified_inflow_avg_monthly": salary,
        "casa_balance": casa,
        "salary_day_of_month": salary_day,
        "stability_coefficient": 0.88,
        "has_payroll_relationship": True,
        "inflow_archetype": "PAYROLL_INTERNAL",
        "casa_buffer_ratio": round(casa / 4000000.0, 2),
        "payroll_bank_name": "BIDV"
    }


@app.get("/legacy/core/v1/portfolio/delinquent")
def get_delinquent_portfolio(max_dpd: int = 30):
    conn = get_db()
    loans = []
    if conn:
        try:
            rows = conn.execute("SELECT * FROM cases WHERE dpd <= ? LIMIT 50", (max_dpd,)).fetchall()
            for r in rows:
                loans.append(dict(r))
        finally:
            conn.close()
    return {"loans": loans, "total": len(loans)}


# =====================================================================
# 2. LOS (LOAN ORIGINATION SYSTEM) REST API
# =====================================================================

@app.get("/legacy/los/v1/loans/{loan_id}/parties")
def get_loan_parties(loan_id: str):
    conn = get_db()
    full_name = "KHÁCH HÀNG"
    cif = "CIF100001"
    phone = "+84946913810"
    if conn:
        try:
            row = conn.execute("SELECT * FROM cases WHERE loan_id=?", (loan_id,)).fetchone()
            if row:
                full_name = row["full_name"]
                cif = row["debtor_cif"]
                phone = row["phone_e164"]
        finally:
            conn.close()

    return {
        "loan_id": loan_id,
        "parties": [
            {
                "loan_id": loan_id,
                "party_id": cif,
                "party_name": full_name,
                "party_type": "PERSON",
                "edge_type": "BORROWED",
                "contact_eligible": "YES",
                "phone_e164": phone,
                "source_system": "LOS"
            },
            {
                "loan_id": loan_id,
                "party_id": f"{cif}_G1",
                "party_name": f"NGUYỄN VĂN BẢO LÃNH ({full_name})",
                "party_type": "PERSON",
                "edge_type": "GUARANTEES",
                "contact_eligible": "YES",
                "phone_e164": "+84912999888",
                "source_system": "LOS"
            }
        ]
    }


@app.get("/legacy/los/v1/loans/{loan_id}/collaterals")
def get_loan_collaterals(loan_id: str):
    # Với khoản vay thế chấp (LOAN-SE-...)
    if "SE" in loan_id:
        return {
            "loan_id": loan_id,
            "collaterals": [
                {
                    "collateral_id": f"COL-{loan_id[-5:]}",
                    "collateral_type": "REAL_ESTATE",
                    "valuation_amount": 1500000000.0,
                    "address": "Số 45 Đường Giải Phóng, Hà Nội",
                    "ltv_ratio": 0.65
                }
            ]
        }
    return {"loan_id": loan_id, "collaterals": []}


# =====================================================================
# 3. CIC GATEWAY REST API
# =====================================================================

@app.get("/legacy/cic/v1/reports")
def get_cic_report(cif: str = Query(...), national_id: str = ""):
    cif_num = sum(ord(c) for c in cif)
    score = 620 + (cif_num % 120)
    worst_group = 1 if score > 680 else (2 if score > 630 else 3)
    return {
        "debtor_cif": cif,
        "national_id": national_id or "001090012345",
        "credit_score": score,
        "worst_group_other_banks": worst_group,
        "obligations_at_other_banks_count": (cif_num % 3),
        "total_obligation_other_banks": float((cif_num % 5) * 10000000),
        "paying_other_banks_while_overdue": bool(score > 660)
    }


# =====================================================================
# 4. CTI TELEPHONY REST API (FreeSWITCH / Avaya Gateway)
# =====================================================================

class OriginateCallRequest(BaseModel):
    agent_id: str
    agent_extension: str
    destination_phone: str
    case_id: str
    guardrail_token: str


@app.post("/legacy/cti/v1/calls/originate")
def originate_call(payload: OriginateCallRequest):
    global _call_seq
    _call_seq += 1
    call_id = f"CALL-FS-{_call_seq}"
    call_record = {
        "call_id": call_id,
        "agent_id": payload.agent_id,
        "agent_extension": payload.agent_extension,
        "destination_phone": payload.destination_phone,
        "case_id": payload.case_id,
        "status": "ANSWERED",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "recording_url": f"https://mock-storage.bank.vn/recordings/20260907/{call_id}.wav",
        "gateway": "FREESWITCH"
    }
    _active_calls[call_id] = call_record
    return call_record


@app.get("/legacy/cti/v1/calls/{call_id}/status")
def get_call_status(call_id: str):
    if call_id in _active_calls:
        return _active_calls[call_id]
    return {"call_id": call_id, "status": "COMPLETED"}


@app.post("/legacy/cti/v1/calls/{call_id}/hangup")
def hangup_call(call_id: str):
    if call_id in _active_calls:
        _active_calls[call_id]["status"] = "HUNGUP"
        _active_calls[call_id]["ended_at"] = datetime.now(timezone.utc).isoformat()
        return _active_calls[call_id]
    return {"call_id": call_id, "status": "HUNGUP"}


# =====================================================================
# 5. SPEECH AI & NLP REST API (Whisper + Qwen LLM)
# =====================================================================

class SpeechAnalysisRequest(BaseModel):
    case_id: str
    call_duration_seconds: int = 45
    recording_url: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@app.post("/legacy/speech-ai/v1/analyze-call")
def analyze_call(payload: SpeechAnalysisRequest):
    case_id = payload.case_id
    conn = get_db()
    full_name = "Khách hàng"
    loan_id = "LOAN-UN-20001"
    overdue_amt = 3330000.0
    dpd = 8

    if conn:
        try:
            row = conn.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
            if row:
                full_name = row["full_name"]
                loan_id = row["loan_id"]
                overdue_amt = float(row["overdue_amount"] or 0)
                dpd = int(row["dpd"] or 0)
        finally:
            conn.close()

    if dpd <= 10:
        transcript = [
            {"speaker": "RM", "text": f"Dạ em chào anh/chị {full_name}, em là chuyên viên quản lý nợ Ngân hàng liên hệ về hợp đồng {loan_id} đang quá hạn {dpd} ngày với số tiền {overdue_amt:,.0f} VNĐ ạ."},
            {"speaker": "CUSTOMER", "text": f"À chào em, mấy hôm vừa rồi anh đi công tác xa nên quên béng mất. Đến ngày 10 tới anh nhận lương sẽ chuyển khoản đủ {overdue_amt:,.0f} đồng qua SmartBanking nhé."},
            {"speaker": "RM", "text": "Dạ vâng em đã ghi nhận lịch hẹn thanh toán vào ngày 10 tới. Em cảm ơn anh/chị nhiều ạ."}
        ]
        outcome = "PTP_AGREED"
        ptp_amt = overdue_amt
        ptp_date = "2026-09-10"
        confidence = 0.98
        sentiment_label = "TÍCH CỰC"
        sentiment_score = 0.48
        sentiment_tone = "Hợp tác cao • Tôn trọng"
        root_cause = "CASHFLOW_TIMING"
        auto_notes = f"Khách xác nhận bận công tác quên lịch nộp, cam kết chuyển khoản đủ {overdue_amt:,.0f} VNĐ qua SmartBanking vào ngày nhận lương 10/09."
    elif dpd <= 20:
        half_amt = round(overdue_amt * 0.5, -4)
        transcript = [
            {"speaker": "RM", "text": f"Chào anh/chị {full_name}, Ngân hàng liên hệ về khoản vay {loan_id} đã quá hạn {dpd} ngày. Em gọi để trao đổi phương án hỗ trợ anh/chị thanh toán kỳ nợ này ạ."},
            {"speaker": "CUSTOMER", "text": f"Đợt này kinh doanh hàng họ chậm thu hồi tiền quá em ơi. Đến ngày 15 này anh gom được trước một nửa khoảng {half_amt:,.0f} đồng nộp trước được không em?"},
            {"speaker": "RM", "text": "Dạ được anh ạ, em ghi nhận cam kết nộp trước ngày 15, phần còn lại chi nhánh sẽ hướng dẫn cơ cấu giãn tiếp ạ."}
        ]
        outcome = "PTP_AGREED"
        ptp_amt = half_amt
        ptp_date = "2026-09-15"
        confidence = 0.93
        sentiment_label = "TRUNG TÍNH"
        sentiment_score = 0.05
        sentiment_tone = "Khó khăn dòng tiền • Thiện chí đàm phán"
        root_cause = "BUSINESS_DOWNTURN"
        auto_notes = f"Khách kinh doanh chậm thu hồi công nợ, cam kết thanh toán trước 50% ({half_amt:,.0f} VNĐ) vào ngày 15/09."
    else:
        transcript = [
            {"speaker": "RM", "text": f"Chào anh/chị {full_name}, Ngân hàng thông báo khoản vay {loan_id} đã quá hạn {dpd} ngày và có nguy cơ chuyển nhóm nợ xấu trên CIC toàn quốc ạ."},
            {"speaker": "CUSTOMER", "text": "Tôi đã bảo đợt này kẹt tiền không xoay kịp rồi mà cứ gọi giục suốt thế! Để cuối tháng xem thế nào rồi tính!"},
            {"speaker": "RM", "text": "Dạ ngân hàng rất thấu hiểu khó khăn của anh/chị, em xin phép lưu nhận thông tin và gửi văn bản hỗ trợ qua Zalo ạ."}
        ]
        outcome = "REFUSED"
        ptp_amt = None
        ptp_date = None
        confidence = 0.91
        sentiment_label = "TIÊU CỰC"
        sentiment_score = -0.65
        sentiment_tone = "Bực bội • Né tránh nghĩa vụ"
        root_cause = "WILFUL_DEFAULT"
        auto_notes = "Khách hàng từ chối cam kết ngày trả cụ thể, phản ứng bực bội khi bị nhắc nợ. Đề xuất chuyển biện pháp cảnh báo văn bản."

    return {
        "case_id": case_id,
        "call_duration_seconds": payload.call_duration_seconds,
        "transcript": transcript,
        "extracted_outcome": outcome,
        "extracted_ptp_amount": ptp_amt,
        "extracted_ptp_date": ptp_date,
        "confidence": confidence,
        "detected_root_cause": root_cause,
        "sentiment": {
            "label": sentiment_label,
            "score": sentiment_score,
            "tone": sentiment_tone
        },
        "compliance_audit": {
            "status": "PASSED",
            "checks": [
                "Xưng danh chuyên viên chuẩn mực",
                "Tuyệt đối không dùng lời lẽ đe dọa hoặc từ cấm",
                "Tuân thủ khung giờ nhắc nợ Thông tư 18/2019/TT-NHNN",
                "Đúng đối tượng được phép liên hệ theo phê duyệt L6"
            ],
            "prohibited_words_found": []
        },
        "auto_notes": auto_notes
    }


# =====================================================================
# 6. MESSAGING GATEWAY REST API (SMS Brandname / Zalo ZNS)
# =====================================================================

class SMSSendRequest(BaseModel):
    phone_e164: str
    message: str
    brandname: str = "BANK"


@app.post("/legacy/messaging/v1/sms/send")
def send_sms(payload: SMSSendRequest):
    return {
        "status": "SENT",
        "gateway_message_id": f"SMS-GW-{int(time.time()*1000)}",
        "channel": "SMS",
        "recipient": payload.phone_e164,
        "brandname": payload.brandname,
        "cost_vnd": 500,
        "sent_at": datetime.now(timezone.utc).isoformat()
    }


class ZNSSendRequest(BaseModel):
    phone_e164: str
    template_id: str
    template_data: Dict[str, Any]


@app.post("/legacy/messaging/v1/zns/send")
def send_zns(payload: ZNSSendRequest):
    return {
        "status": "SENT",
        "gateway_message_id": f"ZNS-GW-{int(time.time()*1000)}",
        "channel": "ZALO",
        "recipient": payload.phone_e164,
        "template_id": payload.template_id,
        "cost_vnd": 300,
        "sent_at": datetime.now(timezone.utc).isoformat()
    }


def main():
    import uvicorn
    port = int(os.getenv("MOCK_LEGACY_PORT", "8090"))
    uvicorn.run("mock_legacy_server:app", host="127.0.0.1", port=port, reload=False)


if __name__ == "__main__":
    main()
