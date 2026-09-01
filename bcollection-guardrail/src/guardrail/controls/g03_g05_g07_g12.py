from typing import Dict, Any
from .base import BaseControl
from ..api.schemas import EvaluateRequest, ControlResult, GuardrailDecision

class G03ConsentDNCControl(BaseControl):
    def __init__(self):
        super().__init__("G03", "Consent & Do-Not-Contact Gate")

    def evaluate(self, request: EvaluateRequest, policy: Dict[str, Any], context: Dict[str, Any]) -> ControlResult:
        is_dnc = context.get("dnc_flag", False)
        consent_withdrawn = context.get("consent_withdrawn", False)
        has_legal_counsel = context.get("has_legal_counsel", False)

        if is_dnc:
            return ControlResult(
                control_id=self.control_id,
                status=GuardrailDecision.BLOCK,
                reason_code="G03_DO_NOT_CONTACT_ACTIVE",
                message="Khách hàng nằm trong danh sách không liên hệ (DNC)."
            )

        if consent_withdrawn:
            return ControlResult(
                control_id=self.control_id,
                status=GuardrailDecision.BLOCK,
                reason_code="G03_CONSENT_WITHDRAWN",
                message="Khách hàng đã chính thức rút lại đồng ý xử lý dữ liệu cho mục đích này."
            )

        if has_legal_counsel:
            return ControlResult(
                control_id=self.control_id,
                status=GuardrailDecision.BLOCK,
                reason_code="G03_LEGAL_COUNSEL_REPRESENTED",
                message="Khách hàng có luật sư đại diện hợp pháp. Mọi liên hệ phải chuyển qua luật sư."
            )

        return ControlResult(
            control_id=self.control_id,
            status=GuardrailDecision.ALLOW,
            message="Đạt điều kiện về sự đồng ý và không thuộc danh sách DNC."
        )


class G04FrequencyCapControl(BaseControl):
    def __init__(self, counter_repo):
        super().__init__("G04", "Frequency Cap Gate")
        self.counter_repo = counter_repo

    def evaluate(self, request: EvaluateRequest, policy: Dict[str, Any], context: Dict[str, Any]) -> ControlResult:
        loan_id = request.loan_id
        party_id = request.target_party.party_id
        channel = request.intent.channel.value

        freq_policy = policy.get("controls", {}).get("g04_frequency", {})
        max_daily_total = freq_policy.get("max_daily_attempts_total", 3)
        max_channel_attempts = freq_policy.get("max_daily_attempts_per_channel", {}).get(channel, 2)

        current_total = self.counter_repo.get_daily_attempts(loan_id, party_id, channel)
        current_channel = self.counter_repo.get_daily_channel_attempts(loan_id, party_id, channel)

        if current_total >= max_daily_total:
            return ControlResult(
                control_id=self.control_id,
                status=GuardrailDecision.BLOCK,
                reason_code="G04_DAILY_TOTAL_LIMIT_EXCEEDED",
                message=f"Đã vượt quá hạn mức liên lạc tối đa trong ngày ({current_total}/{max_daily_total} lần)."
            )

        if current_channel >= max_channel_attempts:
            return ControlResult(
                control_id=self.control_id,
                status=GuardrailDecision.BLOCK,
                reason_code="G04_CHANNEL_LIMIT_EXCEEDED",
                message=f"Đã vượt quá hạn mức liên lạc qua kênh {channel} ({current_channel}/{max_channel_attempts} lần)."
            )

        return ControlResult(
            control_id=self.control_id,
            status=GuardrailDecision.ALLOW,
            message=f"Hạn mức liên lạc hợp lệ ({current_total + 1}/{max_daily_total} lượt hôm nay)."
        )


class G05TimeWindowControl(BaseControl):
    def __init__(self):
        super().__init__("G05", "Time Window Gate")

    def evaluate(self, request: EvaluateRequest, policy: Dict[str, Any], context: Dict[str, Any]) -> ControlResult:
        time_policy = policy.get("controls", {}).get("g05_time_window", {})
        start_hour_str = time_policy.get("start_hour", "07:00")
        end_hour_str = time_policy.get("end_hour", "21:00")
        allowed_days = time_policy.get("allowed_days", ["MON", "TUE", "WED", "THU", "FRI", "SAT"])

        req_time = request.intent.proposed_time
        day_map = {0: "MON", 1: "TUE", 2: "WED", 3: "THU", 4: "FRI", 5: "SAT", 6: "SUN"}
        req_day = day_map.get(req_time.weekday())

        if req_day not in allowed_days:
            return ControlResult(
                control_id=self.control_id,
                status=GuardrailDecision.BLOCK,
                reason_code="G05_DISALLOWED_DAY",
                message=f"Ngày {req_day} không nằm trong danh mục ngày được phép liên hệ nhắc nợ."
            )

        # Kiểm tra giờ
        req_time_str = req_time.strftime("%H:%M")
        if not (start_hour_str <= req_time_str <= end_hour_str):
            return ControlResult(
                control_id=self.control_id,
                status=GuardrailDecision.BLOCK,
                reason_code="G05_OUTSIDE_PERMITTED_HOURS",
                message=f"Thời gian {req_time_str} nằm ngoài khung giờ cho phép ({start_hour_str} - {end_hour_str})."
            )

        return ControlResult(
            control_id=self.control_id,
            status=GuardrailDecision.ALLOW,
            message=f"Thời gian liên hệ {req_time_str} ({req_day}) nằm trong khung giờ hợp lệ."
        )


class G07VulnerabilityControl(BaseControl):
    def __init__(self):
        super().__init__("G07", "Vulnerability Gate")

    def evaluate(self, request: EvaluateRequest, policy: Dict[str, Any], context: Dict[str, Any]) -> ControlResult:
        is_vulnerable = context.get("vulnerability_flag", False)
        vuln_category = context.get("vulnerability_category")

        if is_vulnerable:
            return ControlResult(
                control_id=self.control_id,
                status=GuardrailDecision.BLOCK,
                reason_code="G07_VULNERABLE_CUSTOMER_PROTECTION",
                message=f"Khách hàng thuộc diện dễ tổn thương ({vuln_category}). Khóa toàn bộ biện pháp nhắc nợ cứng, chuyển luồng hỗ trợ."
            )

        return ControlResult(
            control_id=self.control_id,
            status=GuardrailDecision.ALLOW,
            message="Khách hàng không thuộc diện dễ tổn thương."
        )


class G12AuditControl(BaseControl):
    def __init__(self, audit_repo):
        super().__init__("G12", "Immutable Audit Gate")
        self.audit_repo = audit_repo

    def evaluate(self, request: EvaluateRequest, policy: Dict[str, Any], context: Dict[str, Any]) -> ControlResult:
        return ControlResult(
            control_id=self.control_id,
            status=GuardrailDecision.ALLOW,
            message="Audit control sẵn sàng ghi nhận."
        )
