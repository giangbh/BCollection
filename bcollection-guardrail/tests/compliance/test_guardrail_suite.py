import pytest
import sys
import os
from datetime import datetime

# Thêm root của guardrail vào path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.guardrail.api.schemas import EvaluateRequest, TargetParty, ActionIntentPayload, ChannelType, GuardrailDecision
from src.guardrail.repositories.obligation_repo import InMemoryObligationRepository
from src.guardrail.repositories.counter_repo import InMemoryCounterRepository
from src.guardrail.repositories.audit_repo import HashChainAuditRepository
from src.guardrail.engine.orchestrator import GuardrailOrchestrator
from src.guardrail.api.token import verify_guardrail_token


@pytest.fixture
def setup_guardrail():
    obl_repo = InMemoryObligationRepository()
    cnt_repo = InMemoryCounterRepository()
    aud_repo = HashChainAuditRepository()
    
    # Nạp dữ liệu mẫu hợp lệ
    obl_repo.add_obligation(loan_id="LOAN-001", party_id="CIF-CHINH-CHU", edge_type="BORROWED", contact_eligible="YES")
    obl_repo.add_obligation(loan_id="LOAN-001", party_id="CIF-BAO-LANH", edge_type="GUARANTEES", contact_eligible="YES")
    obl_repo.add_obligation(loan_id="LOAN-001", party_id="CIF-NGUOI-THAN", edge_type="FAMILY_OF", contact_eligible="NO")
    
    orchestrator = GuardrailOrchestrator(obl_repo, cnt_repo, aud_repo)
    return orchestrator, obl_repo, cnt_repo, aud_repo


# --- 1. Test G01: Debt Validity ---
def test_g01_blocked_when_no_outstanding(setup_guardrail):
    orchestrator, _, _, _ = setup_guardrail
    req = EvaluateRequest(
        request_id="REQ-001",
        loan_id="LOAN-001",
        debtor_cif="CIF-CHINH-CHU",
        target_party=TargetParty(party_id="CIF-CHINH-CHU"),
        intent=ActionIntentPayload(action_type="SMS_REMINDER", channel=ChannelType.SMS, proposed_time=datetime(2026, 9, 1, 10, 0)),
        case_context={"overdue_amount": 0.0} # Đã hết nợ quá hạn
    )
    res = orchestrator.evaluate(req)
    assert res.decision == GuardrailDecision.BLOCK
    assert "G01_NO_OUTSTANDING" in res.blocking_reason


# --- 2. Test G02: Party Eligibility (Chặn liên hệ người thân không bảo lãnh) ---
def test_g02_blocked_when_contacting_family_member(setup_guardrail):
    orchestrator, _, _, _ = setup_guardrail
    req = EvaluateRequest(
        request_id="REQ-002",
        loan_id="LOAN-001",
        debtor_cif="CIF-CHINH-CHU",
        target_party=TargetParty(party_id="CIF-NGUOI-THAN"), # Người thân FAMILY_OF
        intent=ActionIntentPayload(action_type="VOICE_CALL", channel=ChannelType.VOICE, proposed_time=datetime(2026, 9, 1, 10, 0)),
        case_context={"overdue_amount": 5000000.0}
    )
    res = orchestrator.evaluate(req)
    assert res.decision == GuardrailDecision.BLOCK
    assert "G02_PROHIBITED_PARTY_RELATION" in res.blocking_reason


def test_g02_allowed_when_contacting_guarantor(setup_guardrail):
    orchestrator, _, _, _ = setup_guardrail
    req = EvaluateRequest(
        request_id="REQ-003",
        loan_id="LOAN-001",
        debtor_cif="CIF-CHINH-CHU",
        target_party=TargetParty(party_id="CIF-BAO-LANH"), # Bên bảo lãnh GUARANTEES
        intent=ActionIntentPayload(action_type="SMS_REMINDER", channel=ChannelType.SMS, proposed_time=datetime(2026, 9, 1, 10, 0)),
        case_context={"overdue_amount": 5000000.0}
    )
    res = orchestrator.evaluate(req)
    assert res.decision == GuardrailDecision.ALLOW
    assert res.guardrail_token is not None


# --- 3. Test G05: Time Window (Chặn ngoài giờ 07:00 - 21:00) ---
def test_g05_blocked_outside_hours_night(setup_guardrail):
    orchestrator, _, _, _ = setup_guardrail
    req = EvaluateRequest(
        request_id="REQ-004",
        loan_id="LOAN-001",
        debtor_cif="CIF-CHINH-CHU",
        target_party=TargetParty(party_id="CIF-CHINH-CHU"),
        intent=ActionIntentPayload(action_type="SMS_REMINDER", channel=ChannelType.SMS, proposed_time=datetime(2026, 9, 1, 21, 30)), # 21h30 đêm
        case_context={"overdue_amount": 5000000.0}
    )
    res = orchestrator.evaluate(req)
    assert res.decision == GuardrailDecision.BLOCK
    assert "G05_OUTSIDE_PERMITTED_HOURS" in res.blocking_reason


# --- 4. Test G04: Frequency Cap (Vượt quá 3 lần/ngày) ---
def test_g04_blocked_when_exceeding_daily_cap(setup_guardrail):
    orchestrator, _, cnt_repo, _ = setup_guardrail
    # Giả lập đã gọi 3 lần trong ngày
    cnt_repo.increment_attempt("LOAN-001", "CIF-CHINH-CHU", "SMS")
    cnt_repo.increment_attempt("LOAN-001", "CIF-CHINH-CHU", "SMS")
    cnt_repo.increment_attempt("LOAN-001", "CIF-CHINH-CHU", "VOICE")
    
    req = EvaluateRequest(
        request_id="REQ-005",
        loan_id="LOAN-001",
        debtor_cif="CIF-CHINH-CHU",
        target_party=TargetParty(party_id="CIF-CHINH-CHU"),
        intent=ActionIntentPayload(action_type="VOICE_CALL", channel=ChannelType.VOICE, proposed_time=datetime(2026, 9, 1, 14, 0)),
        case_context={"overdue_amount": 5000000.0}
    )
    res = orchestrator.evaluate(req)
    assert res.decision == GuardrailDecision.BLOCK
    assert "G04_DAILY_TOTAL_LIMIT_EXCEEDED" in res.blocking_reason


# --- 5. Test G07: Vulnerability Protection ---
def test_g07_blocked_when_customer_vulnerable(setup_guardrail):
    orchestrator, _, _, _ = setup_guardrail
    req = EvaluateRequest(
        request_id="REQ-006",
        loan_id="LOAN-001",
        debtor_cif="CIF-CHINH-CHU",
        target_party=TargetParty(party_id="CIF-CHINH-CHU"),
        intent=ActionIntentPayload(action_type="SMS_REMINDER", channel=ChannelType.SMS, proposed_time=datetime(2026, 9, 1, 10, 0)),
        case_context={"overdue_amount": 5000000.0, "vulnerability_flag": True, "vulnerability_category": "MEDICAL_TREATMENT"}
    )
    res = orchestrator.evaluate(req)
    assert res.decision == GuardrailDecision.BLOCK
    assert "G07_VULNERABLE_CUSTOMER_PROTECTION" in res.blocking_reason


# --- 6. Test G12: Hash-chain Audit Integrity ---
def test_g12_audit_chain_integrity(setup_guardrail):
    orchestrator, _, _, aud_repo = setup_guardrail
    # Chạy 3 requests
    for i in range(3):
        req = EvaluateRequest(
            request_id=f"REQ-AUD-{i}",
            loan_id="LOAN-001",
            debtor_cif="CIF-CHINH-CHU",
            target_party=TargetParty(party_id="CIF-CHINH-CHU"),
            intent=ActionIntentPayload(action_type="SMS_REMINDER", channel=ChannelType.SMS, proposed_time=datetime(2026, 9, 1, 10, 0)),
            case_context={"overdue_amount": 5000000.0}
        )
        orchestrator.evaluate(req)
    
    assert aud_repo.count() == 3
    assert aud_repo.verify_integrity() is True
