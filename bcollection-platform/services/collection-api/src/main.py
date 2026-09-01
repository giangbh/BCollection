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

app = FastAPI(
    title="B.Collection Platform Core API",
    description="Core Decision & Case Management API for Collector Workspace",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo repositories & orchestrator dùng chung trong API
obl_repo = InMemoryObligationRepository()
cnt_repo = InMemoryCounterRepository()
aud_repo = HashChainAuditRepository()
orchestrator = GuardrailOrchestrator(obl_repo, cnt_repo, aud_repo)
holdout_mgr = HoldoutManager()

# Khởi tạo mock data 20 cases
mock_cases_db: Dict[str, Dict[str, Any]] = {}
raw_cases = generate_synthetic_delinquent_cases(20)

for c in raw_cases:
    case_id = c["case_id"]
    cif = c["debtor_cif"]
    loan_id = c["loan_id"]
    
    # Gán vào bảng obligation
    obl_repo.add_obligation(loan_id=loan_id, party_id=cif, edge_type="BORROWED", contact_eligible="YES")
    # Thêm 1 người bảo lãnh mẫu cho case
    obl_repo.add_obligation(loan_id=loan_id, party_id=f"{cif}_GUARANTOR", edge_type="GUARANTEES", contact_eligible="YES")
    
    arm = holdout_mgr.assign_arm(cif)
    c["experiment_arm"] = arm
    c["status"] = "IN_TREATMENT" if c["dpd"] > 5 else "ASSIGNED"
    c["guarantor_id"] = f"{cif}_GUARANTOR"
    mock_cases_db[case_id] = c


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "bcollection-platform-api"}


@app.get("/api/cases", response_model=List[Dict[str, Any]])
def get_case_queue():
    """Lấy danh sách hồ sơ nợ B1 cần xử lý trong ngày"""
    return list(mock_cases_db.values())


@app.get("/api/cases/{case_id}/persona")
def get_persona_card(case_id: str):
    """Lấy chi tiết Debtor Persona Card 7 trục phục vụ đọc trong 15 giây"""
    case = mock_cases_db.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    dpd = case["dpd"]
    # Tính toán các điểm số mẫu
    ability_val = max(20, min(95, 100 - dpd * 2))
    willingness_val = 75 if dpd < 15 else 45
    contactability_val = 82

    return {
        "case_id": case_id,
        "loan_id": case["loan_id"],
        "debtor_cif": case["debtor_cif"],
        "full_name": case["full_name"],
        "phone_e164": case["phone_e164"],
        "dpd": dpd,
        "product_code": case["product_code"],
        "overdue_amount": case["overdue_amount"],
        "experiment_arm": case["experiment_arm"],
        "status": case["status"],
        "scores": {
            "ability": {"value": ability_val, "coverage": 0.85, "top_drivers": ["Dòng tiền lương ổn định ngày 10", "DTI 42%"]},
            "willingness": {"value": willingness_val, "coverage": 0.78, "top_drivers": ["Lịch sử giữ cam kết PTP 80%", "Nghe máy khi gọi"]},
            "contactability": {"value": contactability_val, "coverage": 0.90, "top_drivers": ["Số di động chính chủ", "Khung giờ nghe máy 18h-20h"]}
        },
        "segment_cell": "S3" if ability_val < 60 and willingness_val >= 50 else "S1",
        "root_cause": {
            "primary": "CASHFLOW_TIMING",
            "confidence": 4,
            "description": "Lệch chu kỳ dòng tiền: Lương về ngày 10, kỳ trả nợ ngày 05."
        },
        "recommended_playbook": {
            "best_channel": "VOICE",
            "best_time_window": "18:00 - 20:00",
            "suggested_action": "Gọi điện thoại đề xuất đổi ngày trả nợ sang ngày 12 và miễn 30% lãi phạt nếu thanh toán tuần này.",
            "top_levers": ["ACCRUING_PENALTY_COST", "EARLY_SETTLEMENT_DISCOUNT"],
            "success_rate_estimate": "82% (Dựa trên 5 case tương đồng)"
        },
        "mandatory_guardrail_notes": [
            f"Chỉ được liên hệ: Chính chủ ({case['full_name']}) hoặc Bên bảo lãnh.",
            "TUYỆT ĐỐI KHÔNG liên hệ người thân, đồng nghiệp không bảo lãnh.",
            "Khung giờ hợp lệ: 07:00 – 21:00 (Hôm nay đã liên hệ 0/3 lần)."
        ]
    }


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

    return {
        "status": "SAVED",
        "case_id": case_id,
        "new_case_status": case["status"],
        "committed": True
    }
