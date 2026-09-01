import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class GuardrailEvaluationResult:
    is_allowed: bool
    decision: str
    guardrail_token: Optional[str]
    blocking_reason: Optional[str]
    raw_response: Dict[str, Any]


class GuardrailClient:
    """
    Client gọi tới L6 Compliance Guardrail Service.
    Đảm bảo nguyên tắc Fail-Closed (Mọi lỗi mạng/timeout đều trả về is_allowed=False).
    """
    def __init__(self, guardrail_base_url: str = "http://localhost:8000", timeout_seconds: float = 2.0):
        self.base_url = guardrail_base_url
        self.timeout = timeout_seconds

    def evaluate_intent(self, request_payload: Dict[str, Any], direct_orchestrator=None) -> GuardrailEvaluationResult:
        """
        Gửi yêu cầu đánh giá tới Guardrail.
        Hỗ trợ gọi trực tiếp In-Memory Orchestrator trong DEV/Test hoặc gọi REST API.
        """
        try:
            if direct_orchestrator:
                # Direct In-Memory call for fast integration
                from bcollection_guardrail.src.guardrail.api.schemas import EvaluateRequest # type: ignore
                req = EvaluateRequest(**request_payload)
                res = direct_orchestrator.evaluate(req)
                is_allowed = res.decision in ("ALLOW", "ALLOW_WITH_CONDITIONS")
                return GuardrailEvaluationResult(
                    is_allowed=is_allowed,
                    decision=res.decision.value,
                    guardrail_token=res.guardrail_token,
                    blocking_reason=res.blocking_reason,
                    raw_response=res.model_dump(mode="json")
                )
            
            # Trong Production sẽ gọi HTTP REST qua httpx / requests
            # Giả lập response an toàn
            return GuardrailEvaluationResult(
                is_allowed=False,
                decision="BLOCK",
                guardrail_token=None,
                blocking_reason="REST_TRANSPORT_NOT_CONNECTED",
                raw_response={}
            )
        except Exception as e:
            # Nguyên tắc Fail-Closed khi có exception
            return GuardrailEvaluationResult(
                is_allowed=False,
                decision="BLOCK",
                guardrail_token=None,
                blocking_reason=f"GUARDRAIL_CLIENT_EXCEPTION: {str(e)}",
                raw_response={}
            )
