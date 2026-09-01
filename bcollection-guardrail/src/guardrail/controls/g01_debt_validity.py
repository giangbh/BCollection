from typing import Dict, Any
from .base import BaseControl
from ..api.schemas import EvaluateRequest, ControlResult, GuardrailDecision

class G01DebtValidityControl(BaseControl):
    def __init__(self):
        super().__init__("G01", "Debt Validity Gate")

    def evaluate(self, request: EvaluateRequest, policy: Dict[str, Any], context: Dict[str, Any]) -> ControlResult:
        # Kiểm tra khoản nợ tồn tại và có số dư quá hạn
        loan_status = context.get("loan_status", "ACTIVE")
        overdue_amount = context.get("overdue_amount", 1000000.0)
        is_transferred = context.get("is_debt_sold_or_transferred", False)

        if loan_status not in ("ACTIVE", "OVERDUE"):
            return ControlResult(
                control_id=self.control_id,
                status=GuardrailDecision.BLOCK,
                reason_code="G01_DEBT_NOT_FOUND",
                message="Khoản vay không tồn tại hoặc đã tất toán."
            )

        if overdue_amount <= 0:
            return ControlResult(
                control_id=self.control_id,
                status=GuardrailDecision.BLOCK,
                reason_code="G01_NO_OUTSTANDING",
                message="Khoản vay không còn dư nợ quá hạn tại thời điểm liên hệ."
            )

        if is_transferred:
            return ControlResult(
                control_id=self.control_id,
                status=GuardrailDecision.BLOCK,
                reason_code="G01_DEBT_TRANSFERRED",
                message="Khoản nợ đã được bán hoặc chuyển giao cho bên thứ ba."
            )

        return ControlResult(
            control_id=self.control_id,
            status=GuardrailDecision.ALLOW,
            message="Khoản nợ hợp lệ và có dư nợ quá hạn."
        )
