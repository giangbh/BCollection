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


def derive_persona_profile(case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sinh Chân dung Debtor Persona 360 đa dạng và cá nhân hóa dựa trên:
    DPD, Loại sản phẩm vay, Dư nợ và Thuật toán phân loại nguyên nhân gốc.
    """
    dpd = case["dpd"]
    product = case["product_code"]
    cif = case["debtor_cif"]
    cif_hash = sum(ord(ch) for ch in cif)
    
    # 1. Phân loại Nguyên nhân gốc (Root Cause) & Kịch bản đề xuất động
    if dpd <= 5:
        root_cause_type = "FORGOT_OR_ADMIN"
        root_cause_desc = "Quên lịch trả nợ hoặc lỗi chuyển khoản online qua app ngân hàng."
        segment_cell = "S1"
        segment_name = "Tự khỏi cao / Nhắc nhẹ"
        suggested_action = "Gửi tin nhắn Zalo ZNS kèm link VietQR động hoặc gọi điện nhắc lịch thanh toán tiêu chuẩn."
        top_levers = ["CIC_CREDIT_RECORD", "EARLY_SETTLEMENT_DISCOUNT"]
        best_channel = "ZALO" if (cif_hash % 2 == 0) else "SMS"
        best_time = "08:30 - 11:30"
        success_rate = "92% (Tự khỏi trong 48h)"
        ability_val = 88 - (cif_hash % 8)
        willingness_val = 85 - (cif_hash % 10)
        contactability_val = 90 - (cif_hash % 6)
        drivers_ability = ["Thu nhập ổn định 25tr/tháng", "DTI an toàn 28%"]
        drivers_willing = ["Lịch sử 12 tháng trước chưa từng quá hạn", "Hợp tác cao"]

    elif 6 <= dpd <= 10:
        salary_day = (cif_hash % 5) + 10  # Ngày 10 đến 14
        root_cause_type = "CASHFLOW_TIMING"
        root_cause_desc = f"Lệch chu kỳ dòng tiền: Ngày nhận lương là ngày {salary_day}, kỳ trả nợ đến hạn ngày 05."
        segment_cell = "S2"
        segment_name = "Lệch dòng tiền / Cần hẹn ngày"
        suggested_action = f"Gọi điện thoại ghi nhận cam kết thanh toán (PTP) vào đúng ngày nhận lương ({salary_day})."
        top_levers = ["CASH_FLOW_TIMING", "ACCRUING_PENALTY_COST"]
        best_channel = "VOICE"
        best_time = "18:00 - 20:30"
        success_rate = "84% (Đã chốt hẹn lương về)"
        ability_val = 78 - (cif_hash % 8)
        willingness_val = 75 - (cif_hash % 10)
        contactability_val = 85 - (cif_hash % 6)
        drivers_ability = [f"Dòng tiền lương định kỳ ngày {salary_day}", "Có tài khoản tiết kiệm BIDV"]
        drivers_willing = ["Nghe máy khi gọi", "Chủ động báo ngày có lương"]

    elif 11 <= dpd <= 18:
        if product in ("MORTGAGE", "AUTO_LOAN"):
            root_cause_type = "BUSINESS_DOWNTURN"
            root_cause_desc = "Kinh doanh hộ gia đình chậm thu hồi công nợ / Tồn kho tạm thời."
            top_levers = ["COLLATERAL_ENFORCEMENT_RISK", "EARLY_SETTLEMENT_DISCOUNT"]
            suggested_action = "Đề xuất miễn 30% lãi phạt chậm trả nếu khách hàng thanh toán toàn bộ nợ gốc trong tuần này."
        else:
            root_cause_type = "INCOME_LOSS"
            root_cause_desc = "Giảm sút thu nhập / Chi phí sinh hoạt y tế phát sinh đột xuất."
            top_levers = ["INTEREST_WAIVER_OFFER", "ACCRUING_PENALTY_COST"]
            suggested_action = "Tư vấn gói miễn giảm lãi phạt và chia nhỏ kỳ thanh toán hỗ trợ vượt qua khó khăn."
            
        segment_cell = "S3"
        segment_name = "Khó khăn tạm thời / Cần đòn bẩy"
        best_channel = "VOICE"
        best_time = "14:00 - 17:00" if (cif_hash % 2 == 0) else "18:00 - 20:30"
        success_rate = "76% (Khi áp dụng miễn giảm lãi)"
        ability_val = 58 - (cif_hash % 8)
        willingness_val = 65 - (cif_hash % 10)
        contactability_val = 78 - (cif_hash % 6)
        drivers_ability = ["Nguồn thu giảm tạm thời 30%", "Có tài sản đảm bảo"]
        drivers_willing = ["Thiện chí trả nhưng thiếu tiền mặt", "Đang thu hồi nợ đối tác"]

    elif 19 <= dpd <= 25:
        root_cause_type = "OVER_INDEBTED"
        root_cause_desc = "Áp lực tài chính từ nhiều TCTD / Dư nợ thẻ và vay tiêu dùng vượt ngưỡng."
        segment_cell = "S3"
        segment_name = "Áp lực đa khoản vay"
        suggested_action = "Cảnh báo nguy cơ nhảy nhóm nợ 2 trên toàn hệ thống CIC; đề xuất phương án tái cơ cấu giãn nợ."
        top_levers = ["CIC_CREDIT_RECORD", "RESTRUCTURE_OPPORTUNITY", "LITIGATION_COST_TIME"]
        best_channel = "VOICE"
        best_time = "18:00 - 20:30"
        success_rate = "65% (Cần Trưởng nhóm duyệt cơ cấu)"
        ability_val = 42 - (cif_hash % 8)
        willingness_val = 50 - (cif_hash % 10)
        contactability_val = 70 - (cif_hash % 6)
        drivers_ability = ["DTI cao > 60%", "Nợ tại 3 ngân hàng khác"]
        drivers_willing = ["Lo sợ ảnh hưởng điểm tín nhiệm CIC", "Đang tìm nguồn vay thân nhân"]

    else:  # DPD 26 - 30
        root_cause_type = "WILFUL_DEFAULT"
        root_cause_desc = "Cố tình chây ỳ / Né tránh liên hệ nhắc nợ của ngân hàng."
        segment_cell = "S4"
        segment_name = "Nguy cơ cao / Chuẩn bị pháp lý"
        suggested_action = "Gửi công văn cảnh báo pháp lý và khởi động quy trình xử lý tài sản bảo đảm / chuyển pháp chế."
        top_levers = ["COLLATERAL_ENFORCEMENT_RISK", "LITIGATION_COST_TIME", "CIC_CREDIT_RECORD"]
        best_channel = "VOICE"
        best_time = "08:30 - 11:30"
        success_rate = "48% (Cần biện pháp răn đe mạnh)"
        ability_val = 35 - (cif_hash % 8)
        willingness_val = 25 - (cif_hash % 10)
        contactability_val = 55 - (cif_hash % 6)
        drivers_ability = ["Không chứng minh được thu nhập", "Nợ xấu cận kề"]
        drivers_willing = ["Thường xuyên ngắt máy / Hứa lèo", "Thiện chí rất thấp"]

    return {
        "case_id": case["case_id"],
        "loan_id": case["loan_id"],
        "debtor_cif": case["debtor_cif"],
        "full_name": case["full_name"],
        "phone_e164": case["phone_e164"],
        "dpd": dpd,
        "product_code": product,
        "overdue_amount": case["overdue_amount"],
        "experiment_arm": case["experiment_arm"],
        "status": case["status"],
        "scores": {
            "ability": {"value": max(15, ability_val), "coverage": 0.85, "top_drivers": drivers_ability},
            "willingness": {"value": max(15, willingness_val), "coverage": 0.78, "top_drivers": drivers_willing},
            "contactability": {"value": max(20, contactability_val), "coverage": 0.90, "top_drivers": ["Số di động chính chủ", f"Khung giờ nghe máy {best_time}"]}
        },
        "segment_cell": segment_cell,
        "segment_name": segment_name,
        "root_cause": {
            "primary": root_cause_type,
            "confidence": 4,
            "description": root_cause_desc
        },
        "recommended_playbook": {
            "best_channel": best_channel,
            "best_time_window": best_time,
            "suggested_action": suggested_action,
            "top_levers": top_levers,
            "success_rate_estimate": success_rate
        },
        "mandatory_guardrail_notes": [
            f"Chỉ được liên hệ: Chính chủ ({case['full_name']}) hoặc Bên bảo lãnh hợp pháp.",
            "TUYỆT ĐỐI KHÔNG liên hệ người thân, đồng nghiệp không bảo lãnh.",
            "Khung giờ hợp lệ: 07:00 – 21:00 (Hôm nay đã liên hệ 0/3 lần)."
        ]
    }


@app.get("/api/cases/{case_id}/persona")
def get_persona_card(case_id: str):
    """Lấy chi tiết Debtor Persona Card 7 trục phục vụ đọc trong 15 giây (Động theo DPD & Sản phẩm)"""
    case = mock_cases_db.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return derive_persona_profile(case)


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
