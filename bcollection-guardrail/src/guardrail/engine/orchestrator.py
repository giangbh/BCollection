from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import yaml

from ..api.schemas import (
    EvaluateRequest, EvaluateResponse, GuardrailDecision, ControlResult
)
from ..api.token import generate_guardrail_token
from ..controls.g01_debt_validity import G01DebtValidityControl
from ..controls.g02_party_eligibility import G02PartyEligibilityControl
from ..controls.g03_g05_g07_g12 import (
    G03ConsentDNCControl, G04FrequencyCapControl, G05TimeWindowControl,
    G07VulnerabilityControl, G12AuditControl
)

class GuardrailOrchestrator:
    def __init__(self, obligation_repo, counter_repo, audit_repo, policy_path: Optional[str] = None):
        self.obligation_repo = obligation_repo
        self.counter_repo = counter_repo
        self.audit_repo = audit_repo
        self.policy = self._load_policy(policy_path)
        
        # Danh sách 6 controls thứ tự thực thi
        self.controls = [
            G01DebtValidityControl(),
            G02PartyEligibilityControl(self.obligation_repo),
            G03ConsentDNCControl(),
            G07VulnerabilityControl(),
            G05TimeWindowControl(),
            G04FrequencyCapControl(self.counter_repo),
            G12AuditControl(self.audit_repo)
        ]

    def _load_policy(self, path: Optional[str]) -> Dict[str, Any]:
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            except Exception:
                pass
        # Default fallback policy v1.0
        return {
            "policy_version": "gp-2026.09.01-r1",
            "controls": {
                "g04_frequency": {
                    "max_daily_attempts_total": 3,
                    "max_daily_attempts_per_channel": {"VOICE": 2, "SMS": 2, "ZALO": 2}
                },
                "g05_time_window": {
                    "start_hour": "07:00",
                    "end_hour": "21:00",
                    "allowed_days": ["MON", "TUE", "WED", "THU", "FRI", "SAT"]
                }
            }
        }

    def evaluate(self, request: EvaluateRequest) -> EvaluateResponse:
        """
        Thực hiện đánh giá tuần tự theo nguyên tắc Fail-Closed & Short-Circuit.
        """
        control_traces: List[ControlResult] = []
        final_decision = GuardrailDecision.ALLOW
        blocking_reason: Optional[str] = None
        conditions: List[str] = []
        context = request.case_context or {}

        try:
            for control in self.controls:
                res = control.evaluate(request, self.policy, context)
                control_traces.append(res)

                if res.status == GuardrailDecision.BLOCK:
                    final_decision = GuardrailDecision.BLOCK
                    blocking_reason = f"{res.control_id}: {res.reason_code} - {res.message}"
                    break  # Short-circuit on first BLOCK

                elif res.status == GuardrailDecision.ALLOW_WITH_CONDITIONS:
                    if final_decision != GuardrailDecision.BLOCK:
                        final_decision = GuardrailDecision.ALLOW_WITH_CONDITIONS
                        conditions.append(f"{res.control_id}: {res.message}")

        except Exception as e:
            # Nguyên tắc Fail-Closed tuyệt đối khi xảy ra lỗi hệ thống / timeout
            final_decision = GuardrailDecision.BLOCK
            blocking_reason = f"FAIL_CLOSED_SYSTEM_EXCEPTION: {str(e)}"

        # Ghi log Audit bất biến
        self.audit_repo.record_decision(
            request_id=request.request_id,
            request_payload=request.model_dump(mode="json"),
            decision=final_decision.value
        )

        # Sinh token nếu được phép
        guardrail_token = None
        expires_at = None
        if final_decision in (GuardrailDecision.ALLOW, GuardrailDecision.ALLOW_WITH_CONDITIONS):
            guardrail_token = generate_guardrail_token(
                request_id=request.request_id,
                loan_id=request.loan_id,
                target_party_id=request.target_party.party_id,
                channel=request.intent.channel.value,
                ttl_seconds=300
            )
            expires_at = datetime.now() + timedelta(seconds=300)

        return EvaluateResponse(
            request_id=request.request_id,
            decision=final_decision,
            guardrail_token=guardrail_token,
            token_expires_at=expires_at,
            policy_version=self.policy.get("policy_version", "gp-2026.09.01-r1"),
            blocking_reason=blocking_reason,
            conditions=conditions,
            control_trace=control_traces
        )
