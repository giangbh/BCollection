from typing import Dict, Any
from .base import BaseControl
from ..api.schemas import EvaluateRequest, ControlResult, GuardrailDecision
from ..hardcoded.eligibility_whitelist import ELIGIBLE_OBLIGATION_EDGES, CONDITIONAL_EDGES, PROHIBITED_EDGES

class G02PartyEligibilityControl(BaseControl):
    def __init__(self, obligation_repo):
        super().__init__("G02", "Party Eligibility Gate")
        self.obligation_repo = obligation_repo

    def evaluate(self, request: EvaluateRequest, policy: Dict[str, Any], context: Dict[str, Any]) -> ControlResult:
        target_party_id = request.target_party.party_id
        loan_id = request.loan_id
        
        # Tra cứu quan hệ trong party_obligation
        obligation = self.obligation_repo.get_party_obligation(loan_id, target_party_id)
        
        if not obligation:
            return ControlResult(
                control_id=self.control_id,
                status=GuardrailDecision.BLOCK,
                reason_code="G02_INELIGIBLE_PARTY_NO_OBLIGATION",
                message=f"Đối tượng {target_party_id} không có nghĩa vụ pháp lý đối với khoản vay {loan_id}."
            )

        edge_type = obligation.get("edge_type")
        contact_eligible = obligation.get("contact_eligible", "NO")

        # Kiểm tra nếu thuộc danh mục cấm
        if edge_type in PROHIBITED_EDGES:
            return ControlResult(
                control_id=self.control_id,
                status=GuardrailDecision.BLOCK,
                reason_code="G02_PROHIBITED_PARTY_RELATION",
                message=f"Quan hệ {edge_type} ({PROHIBITED_EDGES[edge_type]}) bị cấm liên hệ đòi nợ theo quy định."
            )

        # Kiểm tra nếu thuộc danh mục hợp lệ
        if edge_type in ELIGIBLE_OBLIGATION_EDGES and contact_eligible == "YES":
            return ControlResult(
                control_id=self.control_id,
                status=GuardrailDecision.ALLOW,
                message=f"Đối tượng có nghĩa vụ hợp pháp: {ELIGIBLE_OBLIGATION_EDGES[edge_type]}."
            )

        # Kiểm tra nếu thuộc danh mục có điều kiện
        if edge_type in CONDITIONAL_EDGES:
            if edge_type == "REFERENCE_CONTACT_OF" and not context.get("consent_obtained", False):
                return ControlResult(
                    control_id=self.control_id,
                    status=GuardrailDecision.BLOCK,
                    reason_code="G02_REFERENCE_NO_CONSENT",
                    message="Người tham chiếu chưa có văn bản đồng ý cho phép liên hệ."
                )
            return ControlResult(
                control_id=self.control_id,
                status=GuardrailDecision.ALLOW_WITH_CONDITIONS,
                message=f"Đối tượng liên hệ có điều kiện: {CONDITIONAL_EDGES[edge_type]}."
            )

        return ControlResult(
            control_id=self.control_id,
            status=GuardrailDecision.BLOCK,
            reason_code="G02_CONTACT_NOT_ELIGIBLE",
            message=f"Tư cách đối tượng không đủ điều kiện liên hệ (edge={edge_type}, eligible={contact_eligible})."
        )
