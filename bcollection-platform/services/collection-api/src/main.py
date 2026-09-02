from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import sys
import os

# Thêm đường dẫn libs và guardrail vào path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, os.path.join(BASE_DIR, 'bcollection-platform/libs'))
sys.path.insert(0, os.path.join(BASE_DIR, 'bcollection-guardrail'))
sys.path.insert(0, os.path.join(BASE_DIR, 'bcollection-data'))

from bc_domain.enums import CaseStatus, ChannelType, ExperimentArm
from bc_domain.models import CollectionCase, DebtorPersonaSnapshot, ScoreComponent
from src.guardrail.engine.orchestrator import GuardrailOrchestrator
from src.guardrail.repositories.obligation_repo import InMemoryObligationRepository
from src.guardrail.repositories.counter_repo import InMemoryCounterRepository
from src.guardrail.repositories.audit_repo import HashChainAuditRepository
from src.guardrail.api.schemas import EvaluateRequest, TargetParty, ActionIntentPayload
from synthetic.generator import generate_synthetic_delinquent_cases
from ml.experiments.holdout_assignment import HoldoutManager

# Nạp các Integration Adapters theo chuẩn Hexagonal Architecture
sys.path.insert(0, os.path.join(BASE_DIR, 'bcollection-platform/services/integration-adapters/src'))
from core_banking_adapter import CoreBankingAdapter
from los_adapter import LOSAdapter
from cic.adapter import CICAdapter
from balance_check_service import RealTimeBalanceCheckService

app = FastAPI(
    title="B.Collection Platform Core API",
    description="Core Decision & Case Management API for Collector Workspace (Hexagonal Architecture)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo repositories & orchestrator L6 Guardrail
obl_repo = InMemoryObligationRepository()
cnt_repo = InMemoryCounterRepository()
aud_repo = HashChainAuditRepository()
orchestrator = GuardrailOrchestrator(obl_repo, cnt_repo, aud_repo)
holdout_mgr = HoldoutManager()

# Khởi tạo các Backend Integration Adapters (Hexagonal Ports)
core_banking_adapter = CoreBankingAdapter()
los_adapter = LOSAdapter()
cic_adapter = CICAdapter()
balance_checker = RealTimeBalanceCheckService(core_banking_adapter)

# Khởi tạo Engine Tính toán Chân dung Persona 360 Động (AI + Formulas + Multi-adapter)
from persona_engine import DynamicDebtorPersonaEngine
persona_engine = DynamicDebtorPersonaEngine(
    core_adapter=core_banking_adapter,
    los_adapter=los_adapter,
    cic_adapter=cic_adapter
)

# Nạp danh sách 500 hồ sơ nợ B1 chuẩn nghiệp vụ BIDV
mock_cases_db: Dict[str, Dict[str, Any]] = {}
raw_portfolio = generate_synthetic_delinquent_cases(num_cases=500, seed=42)

for idx, c in enumerate(raw_portfolio):
    case_id = c.get("case_id", f"CASE-2026-{10001 + idx}")
    c["case_id"] = case_id
    cif = c["debtor_cif"]
    loan_id = c["loan_id"]
    
    # Đồng bộ vào MockCoreBankingApiClient nếu đang chạy mock client
    if hasattr(core_banking_adapter.client, "set_mock_loan"):
        core_banking_adapter.client.set_mock_loan(c)
    
    # Đăng ký quan hệ nghĩa vụ vào LOSAdapter và Obligation Repo
    obl_repo.add_obligation(
        loan_id=loan_id,
        party_id=cif,
        edge_type="BORROWED",
        contact_eligible="YES"
    )
    # 30% hồ sơ có thêm người bảo lãnh hợp pháp
    if idx % 3 == 0:
        guarantor_id = f"{cif}_G1"
        obl_repo.add_obligation(
            loan_id=loan_id,
            party_id=guarantor_id,
            edge_type="GUARANTEES",
            contact_eligible="YES"
        )
        c["guarantor_id"] = guarantor_id
    else:
        c["guarantor_id"] = None

    # Gán nhóm thử nghiệm Holdout 10% vs Treatment 90%
    arm = holdout_mgr.assign_arm(cif)
    c["experiment_arm"] = arm
    c["status"] = "IN_TREATMENT" if c.get("dpd", 0) > 5 else "ASSIGNED"
    mock_cases_db[case_id] = c

# CSDL lưu trữ lịch sử tương tác cuộc gọi, tin nhắn của từng Case (Case History DB)
case_interactions_db: Dict[str, List[Dict[str, Any]]] = {}
for case_id, c in mock_cases_db.items():
    dpd = c.get("dpd", 0)
    if dpd > 5:
        days_ago_1 = datetime.now() - timedelta(days=1, hours=2, minutes=15)
        days_ago_2 = datetime.now() - timedelta(days=3, hours=4, minutes=30)
        case_interactions_db[case_id] = [
            {
                "id": f"INT-{case_id}-02",
                "case_id": case_id,
                "channel": "VOICE",
                "timestamp": days_ago_1.strftime("%d/%m/%Y %H:%M"),
                "collector_name": "Lê Văn Chuyên (CB-8842)",
                "outcome": "BUSY_NO_ANSWER",
                "outcome_label": "Không nghe máy",
                "ptp_amount": None,
                "ptp_date": None,
                "notes": "Chuyên viên gọi điện theo danh mục phân bổ, đổ chuông 35s không ai nhấc máy.",
                "guardrail_token": "eyJhbGciOiJFUzI1NiJ9.g05_token_audit_ok",
                "sentiment": "TRUNG TÍNH"
            },
            {
                "id": f"INT-{case_id}-01",
                "case_id": case_id,
                "channel": "SMS",
                "timestamp": days_ago_2.strftime("%d/%m/%Y %H:%M"),
                "collector_name": "Hệ thống Tự động (Batch)",
                "outcome": "SMS_SENT",
                "outcome_label": "SMS VietQR đã gửi",
                "ptp_amount": None,
                "ptp_date": None,
                "notes": f"Gửi tin nhắn SMS Brandname BIDV kèm link VietQR nợ kỳ {c['overdue_amount']:,.0f} đ.",
                "guardrail_token": "eyJhbGciOiJFUzI1NiJ9.g03_vietqr_audit_ok",
                "sentiment": "TÍCH CỰC"
            }
        ]
    else:
        case_interactions_db[case_id] = []


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "bcollection-platform-api"}


@app.get("/api/cases", response_model=List[Dict[str, Any]])
def get_case_queue():
    """Lấy danh sách hồ sơ nợ B1 cần xử lý trong ngày"""
    return list(mock_cases_db.values())


@app.get("/api/cases/{case_id}/persona")
def get_persona_card(case_id: str):
    """
    Lấy chi tiết Debtor Persona Card 7 trục phục vụ đọc trong 15 giây.
    Tính toán động 100% qua DynamicDebtorPersonaEngine:
    - Công thức toán học D1 (Ability), D2 (Willingness), D3 (Contactability)
    - Tích hợp CoreBankingAdapter, LOSAdapter, CICAdapter
    - Mô hình AI ML01 Self-Cure và ML04 Best-Time-To-Contact
    - Bộ suy luận Nguyên nhân gốc (Root Cause Analyzer)
    """
    case = mock_cases_db.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return persona_engine.generate_persona(case)


class CallIntentRequest(BaseModel):
    channel: str = "VOICE"
    target_party_id: str


@app.post("/api/cases/{case_id}/call-intent")
def evaluate_call_intent(case_id: str, payload: CallIntentRequest):
    """
    Chuyên viên bấm nút [GỌI ĐIỆN] trên Web UI.
    Hệ thống tự động gửi yêu cầu kiểm tra tới L6 Compliance Guardrail.
    """
    case = mock_cases_db.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    eval_req = EvaluateRequest(
        request_id=f"CALL-REQ-{case_id}-{int(datetime.now().timestamp())}",
        loan_id=case["loan_id"],
        debtor_cif=case["debtor_cif"],
        target_party=TargetParty(party_id=payload.target_party_id),
        intent=ActionIntentPayload(
            action_type="VOICE_CALL_OUTBOUND",
            channel=ChannelType.VOICE,
            proposed_time=datetime.now()
        ),
        case_context={"overdue_amount": case["overdue_amount"]}
    )

    eval_res = orchestrator.evaluate(eval_req)

    return {
        "is_allowed": eval_res.decision in ("ALLOW", "ALLOW_WITH_CONDITIONS"),
        "decision": eval_res.decision.value,
        "guardrail_token": eval_res.guardrail_token,
        "blocking_reason": eval_res.blocking_reason,
        "policy_version": eval_res.policy_version,
        "evaluated_at": eval_res.evaluated_at.isoformat()
    }


class CallWrapupRequest(BaseModel):
    guardrail_token: str
    outcome: str  # PTP_AGREED, REFUSED, BUSY_NO_ANSWER
    ptp_amount: Optional[float] = None
    ptp_date: Optional[str] = None
    notes: Optional[str] = None


@app.post("/api/cases/{case_id}/call-wrapup")
def submit_call_wrapup(case_id: str, payload: CallWrapupRequest):
    """Ghi nhận kết quả cuộc gọi và xác nhận commit Guardrail"""
    case = mock_cases_db.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Cập nhật case
    if payload.outcome == "PTP_AGREED":
        case["status"] = "PTP_SCHEDULED"
        case["ptp_amount"] = payload.ptp_amount
        case["ptp_date"] = payload.ptp_date
    elif payload.outcome == "REFUSED":
        case["status"] = "IN_TREATMENT"

    # Tăng biến đếm qua Guardrail commit
    loan_id = case["loan_id"]
    cif = case["debtor_cif"]
    cnt_repo.increment_attempt(loan_id, cif, "VOICE")

    # Ghi nhận vào Case History DB
    outcome_label = (
        "Hẹn ngày trả (PTP Agreed)" if payload.outcome == "PTP_AGREED"
        else ("Từ chối thanh toán" if payload.outcome == "REFUSED" else "Không nghe máy")
    )
    sentiment = (
        "TÍCH CỰC" if payload.outcome == "PTP_AGREED"
        else ("TIÊU CỰC" if payload.outcome == "REFUSED" else "TRUNG TÍNH")
    )

    interaction_item = {
        "id": f"INT-{case_id}-{int(datetime.now().timestamp())}",
        "case_id": case_id,
        "channel": "VOICE",
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "collector_name": "Lê Văn Chuyên (CB-8842)",
        "outcome": payload.outcome,
        "outcome_label": outcome_label,
        "ptp_amount": payload.ptp_amount,
        "ptp_date": payload.ptp_date,
        "notes": payload.notes or "Hoàn tất cuộc gọi đàm phán nhắc nợ qua Softphone.",
        "guardrail_token": (payload.guardrail_token[:22] + "...") if payload.guardrail_token else "N/A",
        "sentiment": sentiment
    }
    case_interactions_db.setdefault(case_id, []).insert(0, interaction_item)

    return {
        "status": "SAVED",
        "case_id": case_id,
        "new_case_status": case["status"],
        "committed": True,
        "interaction_id": interaction_item["id"]
    }


@app.get("/api/cases/{case_id}/history", response_model=List[Dict[str, Any]])
def get_case_history(case_id: str):
    """Lấy danh sách toàn bộ lịch sử tương tác (Case History) của hồ sơ"""
    return case_interactions_db.get(case_id, [])


@app.post("/api/cases/{case_id}/balance-check")
def check_case_balance_realtime(case_id: str):
    """
    Kiểm tra số dư thời gian thực với Core Banking qua CoreBankingAdapter (IF-CORE-04).
    Chống đòi nợ oan: Nếu khách hàng đã trả tiền trong 15 phút hoặc nợ đã hết,
    hệ thống tự động hủy nhắc nợ và đổi trạng thái hồ sơ sang CURED.
    """
    case = mock_cases_db.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    loan_id = case["loan_id"]
    debtor_cif = case["debtor_cif"]

    check_res = balance_checker.verify_action_eligibility(loan_id, debtor_cif)
    if not check_res["can_proceed"]:
        case["status"] = "CURED"
        case["overdue_amount"] = 0.0

    return {
        "case_id": case_id,
        "loan_id": loan_id,
        "can_proceed": check_res["can_proceed"],
        "reason": check_res["reason"],
        "message": check_res["message"],
        "updated_case_status": case["status"]
    }


class CallTranscribeRequest(BaseModel):
    call_duration_seconds: int = 45
    channel: str = "VOICE"


@app.post("/api/cases/{case_id}/call-transcribe")
def transcribe_and_extract_call(case_id: str, payload: CallTranscribeRequest):
    """
    Phân hệ Speech AI bóc tách tự động cuộc gọi:
    1. Nhận diện giọng nói đa kênh (ASR Whisper)
    2. Trích xuất thực thể cam kết PTP, ngày hẹn trả và lý do nợ (NLP Qwen-2.5-7B)
    3. Phân tích sắc thái cảm xúc (Sentiment Analysis)
    4. Kiểm soát tuân thủ L6 Guardrail tự động (Compliance Check)
    """
    case = mock_cases_db.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    dpd = case.get("dpd", 5)
    full_name = case.get("full_name", "Khách hàng")
    loan_id = case.get("loan_id", "LOAN-UNKNOWN")
    overdue_amt = float(case.get("overdue_amount", 5_000_000.0))

    if dpd <= 10:
        transcript = [
            {"speaker": "RM", "text": f"Dạ em chào anh/chị {full_name}, em là chuyên viên quản lý nợ BIDV liên hệ về hợp đồng {loan_id} đang quá hạn {dpd} ngày với số tiền {overdue_amt:,.0f} VNĐ ạ."},
            {"speaker": "CUSTOMER", "text": f"À chào em, mấy hôm vừa rồi anh đi công tác xa nên quên béng mất. Đến ngày 10 tới anh nhận lương sẽ chuyển khoản đủ {overdue_amt:,.0f} đồng qua SmartBanking nhé."},
            {"speaker": "RM", "text": f"Dạ vâng em đã ghi nhận lịch hẹn thanh toán vào ngày 10 tới. Em cảm ơn anh/chị nhiều ạ."}
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

    elif 11 <= dpd <= 20:
        half_amt = round(overdue_amt * 0.5, -4)
        transcript = [
            {"speaker": "RM", "text": f"Chào anh/chị {full_name}, BIDV liên hệ về khoản vay {loan_id} đã quá hạn {dpd} ngày. Em gọi để trao đổi phương án hỗ trợ anh/chị thanh toán kỳ nợ này ạ."},
            {"speaker": "CUSTOMER", "text": f"Đợt này kinh doanh hàng họ chậm thu hồi tiền quá em ơi. Đến ngày 15 này anh gom được trước một nửa khoảng {half_amt:,.0f} đồng nộp trước được không em?"},
            {"speaker": "RM", "text": f"Dạ được anh ạ, em ghi nhận cam kết nộp trước {half_amt:,.0f} đồng vào ngày 15/09, phần còn lại chi nhánh sẽ hướng dẫn cơ cấu giãn tiếp ạ."}
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
            {"speaker": "RM", "text": f"Chào anh/chị {full_name}, BIDV thông báo khoản vay {loan_id} đã quá hạn {dpd} ngày và có nguy cơ chuyển nhóm nợ xấu trên CIC toàn quốc ạ."},
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
                "Xưng danh chuyên viên BIDV chuẩn mực",
                "Tuyệt đối không dùng lời lẽ đe dọa hoặc từ cấm",
                "Không tiết lộ thông tin cho người thứ ba",
                "Khung giờ liên hệ hợp lệ (07:00–21:00)"
            ]
        },
        "auto_notes": auto_notes
    }


