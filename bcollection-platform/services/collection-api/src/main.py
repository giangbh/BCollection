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

    return {
        "status": "SAVED",
        "case_id": case_id,
        "new_case_status": case["status"],
        "committed": True
    }


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

