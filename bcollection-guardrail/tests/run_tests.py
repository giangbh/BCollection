import unittest
import sys
import os
from datetime import datetime

# Thêm đường dẫn src vào PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.guardrail.api.schemas import EvaluateRequest, TargetParty, ActionIntentPayload, ChannelType, GuardrailDecision
from src.guardrail.repositories.obligation_repo import InMemoryObligationRepository
from src.guardrail.repositories.counter_repo import InMemoryCounterRepository
from src.guardrail.repositories.audit_repo import HashChainAuditRepository
from src.guardrail.engine.orchestrator import GuardrailOrchestrator
from src.guardrail.api.token import verify_guardrail_token


class TestGuardrailComplianceSuite(unittest.TestCase):
    def setUp(self):
        self.obl_repo = InMemoryObligationRepository()
        self.cnt_repo = InMemoryCounterRepository()
        self.aud_repo = HashChainAuditRepository()
        
        self.obl_repo.add_obligation(loan_id="LOAN-001", party_id="CIF-CHINH-CHU", edge_type="BORROWED", contact_eligible="YES")
        self.obl_repo.add_obligation(loan_id="LOAN-001", party_id="CIF-BAO-LANH", edge_type="GUARANTEES", contact_eligible="YES")
        self.obl_repo.add_obligation(loan_id="LOAN-001", party_id="CIF-NGUOI-THAN", edge_type="FAMILY_OF", contact_eligible="NO")
        
        self.orchestrator = GuardrailOrchestrator(self.obl_repo, self.cnt_repo, self.aud_repo)

    def test_g01_blocked_when_no_outstanding(self):
        req = EvaluateRequest(
            request_id="REQ-001",
            loan_id="LOAN-001",
            debtor_cif="CIF-CHINH-CHU",
            target_party=TargetParty(party_id="CIF-CHINH-CHU"),
            intent=ActionIntentPayload(action_type="SMS_REMINDER", channel=ChannelType.SMS, proposed_time=datetime(2026, 9, 1, 10, 0)),
            case_context={"overdue_amount": 0.0}
        )
        res = self.orchestrator.evaluate(req)
        self.assertEqual(res.decision, GuardrailDecision.BLOCK)
        self.assertIn("G01_NO_OUTSTANDING", res.blocking_reason)

    def test_g02_blocked_when_contacting_family_member(self):
        req = EvaluateRequest(
            request_id="REQ-002",
            loan_id="LOAN-001",
            debtor_cif="CIF-CHINH-CHU",
            target_party=TargetParty(party_id="CIF-NGUOI-THAN"),
            intent=ActionIntentPayload(action_type="VOICE_CALL", channel=ChannelType.VOICE, proposed_time=datetime(2026, 9, 1, 10, 0)),
            case_context={"overdue_amount": 5000000.0}
        )
        res = self.orchestrator.evaluate(req)
        self.assertEqual(res.decision, GuardrailDecision.BLOCK)
        self.assertIn("G02_PROHIBITED_PARTY_RELATION", res.blocking_reason)

    def test_g02_allowed_when_contacting_guarantor(self):
        req = EvaluateRequest(
            request_id="REQ-003",
            loan_id="LOAN-001",
            debtor_cif="CIF-CHINH-CHU",
            target_party=TargetParty(party_id="CIF-BAO-LANH"),
            intent=ActionIntentPayload(action_type="SMS_REMINDER", channel=ChannelType.SMS, proposed_time=datetime(2026, 9, 1, 10, 0)),
            case_context={"overdue_amount": 5000000.0}
        )
        res = self.orchestrator.evaluate(req)
        self.assertEqual(res.decision, GuardrailDecision.ALLOW)
        self.assertIsNotNone(res.guardrail_token)
        # Kiểm tra tính hợp lệ của token
        token_payload = verify_guardrail_token(res.guardrail_token)
        self.assertIsNotNone(token_payload)
        self.assertEqual(token_payload.get("loan_id"), "LOAN-001")

    def test_g05_blocked_outside_hours_night(self):
        req = EvaluateRequest(
            request_id="REQ-004",
            loan_id="LOAN-001",
            debtor_cif="CIF-CHINH-CHU",
            target_party=TargetParty(party_id="CIF-CHINH-CHU"),
            intent=ActionIntentPayload(action_type="SMS_REMINDER", channel=ChannelType.SMS, proposed_time=datetime(2026, 9, 1, 21, 30)),
            case_context={"overdue_amount": 5000000.0}
        )
        res = self.orchestrator.evaluate(req)
        self.assertEqual(res.decision, GuardrailDecision.BLOCK)
        self.assertIn("G05_OUTSIDE_PERMITTED_HOURS", res.blocking_reason)

    def test_g04_blocked_when_exceeding_daily_cap(self):
        self.cnt_repo.increment_attempt("LOAN-001", "CIF-CHINH-CHU", "SMS")
        self.cnt_repo.increment_attempt("LOAN-001", "CIF-CHINH-CHU", "SMS")
        self.cnt_repo.increment_attempt("LOAN-001", "CIF-CHINH-CHU", "VOICE")
        
        req = EvaluateRequest(
            request_id="REQ-005",
            loan_id="LOAN-001",
            debtor_cif="CIF-CHINH-CHU",
            target_party=TargetParty(party_id="CIF-CHINH-CHU"),
            intent=ActionIntentPayload(action_type="VOICE_CALL", channel=ChannelType.VOICE, proposed_time=datetime(2026, 9, 1, 14, 0)),
            case_context={"overdue_amount": 5000000.0}
        )
        res = self.orchestrator.evaluate(req)
        self.assertEqual(res.decision, GuardrailDecision.BLOCK)
        self.assertIn("G04_DAILY_TOTAL_LIMIT_EXCEEDED", res.blocking_reason)

    def test_g07_blocked_when_customer_vulnerable(self):
        req = EvaluateRequest(
            request_id="REQ-006",
            loan_id="LOAN-001",
            debtor_cif="CIF-CHINH-CHU",
            target_party=TargetParty(party_id="CIF-CHINH-CHU"),
            intent=ActionIntentPayload(action_type="SMS_REMINDER", channel=ChannelType.SMS, proposed_time=datetime(2026, 9, 1, 10, 0)),
            case_context={"overdue_amount": 5000000.0, "vulnerability_flag": True, "vulnerability_category": "MEDICAL_TREATMENT"}
        )
        res = self.orchestrator.evaluate(req)
        self.assertEqual(res.decision, GuardrailDecision.BLOCK)
        self.assertIn("G07_VULNERABLE_CUSTOMER_PROTECTION", res.blocking_reason)

    def test_g12_audit_chain_integrity(self):
        for i in range(3):
            req = EvaluateRequest(
                request_id=f"REQ-AUD-{i}",
                loan_id="LOAN-001",
                debtor_cif="CIF-CHINH-CHU",
                target_party=TargetParty(party_id="CIF-CHINH-CHU"),
                intent=ActionIntentPayload(action_type="SMS_REMINDER", channel=ChannelType.SMS, proposed_time=datetime(2026, 9, 1, 10, 0)),
                case_context={"overdue_amount": 5000000.0}
            )
            self.orchestrator.evaluate(req)
        
        self.assertEqual(self.aud_repo.count(), 3)
        self.assertTrue(self.aud_repo.verify_integrity())


if __name__ == '__main__':
    unittest.main()
