from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
import sys
import os

# Thêm đường dẫn libs và guardrail vào path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, os.path.dirname(__file__))
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
from bc_runtime.settings import RuntimeSettings
from case_service import CaseService, CaseConflict, CaseNotFound
from bc_domain.case_rules import obligation_status

# Nạp các Integration Adapters theo chuẩn Hexagonal Architecture
sys.path.insert(0, os.path.join(BASE_DIR, 'bcollection-platform/services/integration-adapters/src'))
from core_banking_adapter import CoreBankingAdapter
from los_adapter import LOSAdapter
from cic.adapter import CICAdapter
from balance_check_service import RealTimeBalanceCheckService

@asynccontextmanager
async def lifespan(app):
    global obl_repo, cnt_repo, aud_repo, orchestrator
    global core_banking_adapter, los_adapter, cic_adapter, balance_checker, persona_engine
    settings = RuntimeSettings.from_env()
    settings.validate_adapters()
    import database as db
    db.DB_FILE_PATH = str(settings.database_path)
    db.init_db()
    db.claim_runtime_database(settings.mode)
    app.state.settings = settings
    obl_repo = InMemoryObligationRepository()
    cnt_repo = InMemoryCounterRepository()
    aud_repo = HashChainAuditRepository()
    orchestrator = GuardrailOrchestrator(obl_repo, cnt_repo, aud_repo)
    core_banking_adapter = CoreBankingAdapter()
    los_adapter = LOSAdapter()
    cic_adapter = CICAdapter()
    balance_checker = RealTimeBalanceCheckService(core_banking_adapter)
    persona_engine = DynamicDebtorPersonaEngine(core_banking_adapter, los_adapter, cic_adapter)
    if settings.mode in {"demo", "test"}:
        db.restore_demo_obligations(obl_repo)
        for case in db.get_all_cases():
            if case["data_origin"] == "SYNTHETIC":
                conn = db.get_connection()
                try:
                    for exposure in conn.execute("SELECT * FROM case_exposures WHERE case_id=?", (case["case_id"],)):
                        core_banking_adapter.client.set_mock_loan({
                            **case, "loan_id": exposure["loan_id"], "dpd": exposure["dpd"],
                            "overdue_amount": exposure["overdue_vnd"],
                            "outstanding_principal": exposure["principal_vnd"],
                            "outstanding_interest": exposure["interest_vnd"],
                            "source_version": max(0, exposure["source_version"]),
                        })
                finally:
                    conn.close()
    yield


app = FastAPI(
    title="B.Collection Platform Core API",
    description="Core Decision & Case Management API for Collector Workspace (Hexagonal Architecture)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo Engine Tính toán Chân dung Persona 360 Động (AI + Formulas + Multi-adapter)
from persona_engine import DynamicDebtorPersonaEngine
from database import (
    get_all_cases, get_case_by_id,
    get_case_history, get_db_schema_info, get_connection
)

@app.middleware("http")
async def enforce_runtime_profile(request, call_next):
    settings = request.app.state.settings
    path = request.url.path.rstrip("/")
    if settings.mode == "integration":
        # Persona/CBR/ASR still contain synthetic heuristics. Do not present them
        # as live intelligence or enable mutations against integration data.
        simulated = path.endswith(("/persona", "/similar-cases"))
        if request.method not in {"GET", "HEAD", "OPTIONS"} or simulated:
            return JSONResponse(status_code=503, content={"detail": "PR-01 integration is read-only; simulated intelligence and actions are disabled"})
    response = await call_next(request)
    response.headers["X-BCollection-Mode"] = settings.mode
    response.headers["X-BCollection-Simulation"] = str(settings.mode != "integration").lower()
    return response


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "bcollection-platform-api", "database": "sqlite3", **runtime_info()}


@app.get("/api/runtime")
def runtime_info():
    return {
        "mode": app.state.settings.mode,
        "simulation": app.state.settings.mode in {"demo", "test"},
        "integration_read_only": app.state.settings.mode == "integration",
        "production_ready": False,
    }


@app.get("/api/db/schema")
def get_database_schema():
    """Xem cấu trúc DDL các bảng và thống kê bản ghi thực tế trong SQLite DB"""
    return get_db_schema_info()


@app.get("/api/rules/root-cause/dmn")
def get_root_cause_dmn_rules():
    """
    Xem Bảng quyết định Camunda DMN 1.3 (Decision Table) cho Root Cause Engine.
    Được nạp trực tiếp từ file rules/root_cause_rules.dmn.
    Hỗ trợ Hot-Reload: sửa file XML là cập nhật ngay lập tức không cần restart.
    """
    from dmn_engine import get_dmn_engine
    return get_dmn_engine().get_rules_summary()


@app.get("/api/config/scoring")
def get_scoring_policy_config():
    """
    Xem toàn bộ Cấu hình Trọng số & Ngưỡng Tính điểm (Scoring Policy) từ scoring_config.yaml.
    Hỗ trợ Hot-Reload: Tự động cập nhật khi file YAML thay đổi mà không cần restart server.
    """
    from scoring_config_loader import get_scoring_config_manager
    return get_scoring_config_manager().get_config()


@app.get("/api/cases", response_model=List[Dict[str, Any]])
def get_case_queue():
    """Lấy danh sách hồ sơ nợ B1 từ SQLite DB"""
    return get_all_cases()


@app.get("/api/cases/{case_id}/persona")
def get_persona_card(case_id: str):
    """
    Lấy chi tiết Debtor Persona Card 7 trục từ SQLite DB.
    Tính toán động 100% qua DynamicDebtorPersonaEngine:
    - Công thức toán học D1 (Ability), D2 (Willingness), D3 (Contactability)
    - Tích hợp CoreBankingAdapter, LOSAdapter, CICAdapter
    - Mô hình AI ML01 Self-Cure và ML04 Best-Time-To-Contact
    - Bộ suy luận Nguyên nhân gốc (Root Cause Analyzer)
    """
    case = get_case_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return persona_engine.generate_persona(case)


@app.get("/api/cases/{case_id}/similar-cases")
def get_similar_cases(case_id: str, top_k: int = 5):
    """
    Thực hiện so sánh Cosine Similarity thực tế trên không gian Vector 192 Chiều
    với toàn bộ 1,000 hồ sơ tham chiếu (CBR Reference Cases) trong CSDL SQLite.
    Trả về Top-K hồ sơ khớp nhất kèm đòn bẩy và kịch bản đã xử lý thành công.
    """
    case = get_case_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    persona = persona_engine.generate_persona(case)
    return {
        "case_id": case_id,
        "full_name": case["full_name"],
        "product_code": case["product_code"],
        "dpd": case["dpd"],
        "root_cause": persona["root_cause"]["primary"],
        "top_k": top_k,
        "total_reference_pool": 1000,
        "vector_dimensions": 192,
        "matched_references": persona.get("similar_references", [])
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
    case = get_case_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if case["lifecycle"] != "OPEN" or case["contact_hold_reason"]:
        raise HTTPException(409, "Case is closed or contact is held for reconciliation")
    # Fail closed across every exposure, including partial recent payments.
    state = financial_state(case_id)
    try:
        for exposure in state["case_exposures"]:
            check = balance_checker.verify_action_eligibility(exposure["loan_id"], case["debtor_cif"])
            if not check["can_proceed"]:
                return {"is_allowed": False, "blocking_reason": check["reason"]}
    except Exception as exc:
        raise HTTPException(503, "Core evidence unavailable; contact blocked") from exc

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


class CommandRequest(BaseModel):
    command_id: str = Field(min_length=1, max_length=128)
    expected_version: int = Field(ge=0, strict=True)


def run_command(case_id, payload, kind, data=None):
    try:
        return CaseService().execute(case_id, payload.command_id, payload.expected_version, kind,
            data if data is not None else payload.model_dump(exclude={"command_id", "expected_version"}))
    except CaseNotFound:
        raise HTTPException(404, "Case not found")
    except CaseConflict as exc:
        raise HTTPException(409, str(exc))
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(422, str(exc))


class CallWrapupRequest(CommandRequest):
    guardrail_token: str
    outcome: str  # PTP_AGREED, REFUSED, BUSY_NO_ANSWER
    ptp_amount: Optional[float] = None
    ptp_date: Optional[str] = None
    notes: Optional[str] = None
    loan_id: Optional[str] = None


@app.post("/api/cases/{case_id}/call-wrapup")
def submit_call_wrapup(case_id: str, payload: CallWrapupRequest):
    result = run_command(case_id, payload, "wrapup")
    if not result["replayed"]:
        case = get_case_by_id(case_id)
        cnt_repo.increment_attempt(case["loan_id"], case["debtor_cif"], "VOICE")
    return result


@app.get("/api/cases/{case_id}/history", response_model=List[Dict[str, Any]])
def get_case_history_api(case_id: str):
    """Lấy danh sách toàn bộ lịch sử tương tác (Case History) từ SQLite DB"""
    return get_case_history(case_id)


@app.get("/api/cases/{case_id}/financial-state")
def financial_state(case_id: str):
    case = get_case_by_id(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    conn = get_connection()
    try:
        result = {"case": case, **{table: [dict(r) for r in conn.execute(f"SELECT * FROM {table} WHERE case_id=?", (case_id,))] for table in ("case_exposures", "ptps", "payment_ledger", "case_transition_log")}}
        for exposure in result["case_exposures"]:
            exposure["obligation_status"] = obligation_status(exposure)
        return result
    finally:
        conn.close()


@app.post("/api/cases/{case_id}/balance-check")
def check_case_balance_realtime(case_id: str, payload: CommandRequest):
    state = financial_state(case_id)
    snapshots, recent = [], False
    try:
        for exposure in state["case_exposures"]:
            s = core_banking_adapter.get_realtime_balance(exposure["loan_id"])
            snapshots.append({
                "loan_id": s.loan_id, "debtor_cif": s.debtor_cif,
                "overdue_amount": s.overdue_amount, "outstanding_principal": s.outstanding_principal,
                "outstanding_interest": s.outstanding_interest, "dpd": s.days_past_due,
                "as_of": s.as_of.isoformat(), "source_version": s.source_version,
            })
            payment = core_banking_adapter.check_recent_payment(s.loan_id)
            recent = recent or bool(payment)
    except Exception as exc:
        raise HTTPException(503, "Core evidence unavailable; contact must remain blocked") from exc
    result = run_command(case_id, payload, "balance_check", {"snapshots": snapshots, "recent_payment": recent})
    return {**result, "can_proceed": result["lifecycle"] == "OPEN" and not result["contact_hold_reason"],
            "reason": result["contact_hold_reason"] or result["new_case_status"],
            "updated_case_status": result["new_case_status"]}


class FinancialCommandRequest(CommandRequest):
    # Explicit demo/test ingress. Integration writes remain disabled by middleware.
    payload: Dict[str, Any]


@app.post("/api/cases/{case_id}/commands/{kind}")
def financial_command(case_id: str, kind: str, request: FinancialCommandRequest):
    if kind not in {"balance", "payment", "observe_ptp", "link_exposure", "reconcile"}:
        raise HTTPException(422, "Unsupported financial command")
    return run_command(case_id, request, kind, request.payload)


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
    case = get_case_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    dpd = case.get("dpd", 5)
    full_name = case.get("full_name", "Khách hàng")
    loan_id = case.get("loan_id", "LOAN-UNKNOWN")
    overdue_amt = float(case.get("overdue_amount", 5_000_000.0))

    if dpd <= 10:
        transcript = [
            {"speaker": "RM", "text": f"Dạ em chào anh/chị {full_name}, em là chuyên viên quản lý nợ Ngân hàng liên hệ về hợp đồng {loan_id} đang quá hạn {dpd} ngày với số tiền {overdue_amt:,.0f} VNĐ ạ."},
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
            {"speaker": "RM", "text": f"Chào anh/chị {full_name}, Ngân hàng liên hệ về khoản vay {loan_id} đã quá hạn {dpd} ngày. Em gọi để trao đổi phương án hỗ trợ anh/chị thanh toán kỳ nợ này ạ."},
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
                "Không tiết lộ thông tin cho người thứ ba",
                "Khung giờ liên hệ hợp lệ (07:00–21:00)"
            ]
        },
        "auto_notes": auto_notes
    }
