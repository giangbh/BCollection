from fastapi import FastAPI, HTTPException, Header, Depends
from typing import Optional

from .schemas import EvaluateRequest, EvaluateResponse, CommitRequest
from .token import verify_guardrail_token
from ..repositories.obligation_repo import InMemoryObligationRepository
from ..repositories.counter_repo import InMemoryCounterRepository
from ..repositories.audit_repo import HashChainAuditRepository
from ..engine.orchestrator import GuardrailOrchestrator

app = FastAPI(
    title="B.Collection Compliance Guardrail Service",
    description="Layer 6 Compliance & Ethics Guardrail Engine (Deterministic, Fail-Closed)",
    version="1.0.0"
)

# Khởi tạo repositories & orchestrator dùng chung
obligation_repo = InMemoryObligationRepository()
counter_repo = InMemoryCounterRepository()
audit_repo = HashChainAuditRepository()
orchestrator = GuardrailOrchestrator(obligation_repo, counter_repo, audit_repo)


@app.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "bcollection-guardrail-l6",
        "audit_chain_integrity": audit_repo.verify_integrity(),
        "records_count": audit_repo.count()
    }


@app.post("/v1/guardrail/evaluate", response_model=EvaluateResponse)
def evaluate_action(request: EvaluateRequest):
    """
    Đánh giá tính hợp lệ của hành động đòi nợ trước khi thực thi.
    """
    return orchestrator.evaluate(request)


@app.post("/v1/guardrail/commit")
def commit_action(request: CommitRequest):
    """
    Xác nhận hành động đã thực thi thành công để tăng biến đếm tần suất 24h.
    Bắt buộc phải có guardrail_token hợp lệ.
    """
    payload = verify_guardrail_token(request.guardrail_token)
    if not payload:
        raise HTTPException(status_code=403, detail="INVALID_OR_EXPIRED_GUARDRAIL_TOKEN")

    loan_id = payload.get("loan_id")
    party_id = payload.get("party_id")
    channel = payload.get("chan")

    if request.delivery_status in ("DELIVERED", "ANSWERED"):
        counter_repo.increment_attempt(loan_id, party_id, channel)

    return {
        "status": "COMMITTED",
        "request_id": request.request_id,
        "loan_id": loan_id,
        "party_id": party_id,
        "recorded": True
    }


@app.get("/v1/guardrail/audit/verify")
def verify_audit_ledger():
    """Kiểm toán độc lập tính toàn vẹn của sổ cái hash-chain"""
    is_valid = audit_repo.verify_integrity()
    return {
        "integrity_verified": is_valid,
        "total_records": audit_repo.count(),
        "latest_hash": audit_repo.get_latest_hash()
    }
