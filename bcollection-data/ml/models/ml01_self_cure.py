import math
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class SelfCurePrediction:
    debtor_cif: str
    self_cure_propensity: float  # Xác suất 0.0 - 1.0
    action_tier: str             # SELF_CURE_HIGH, SELF_CURE_MED, HIGH_RISK
    grace_period_days: int       # Số ngày hoãn liên hệ (0, 3, 5 ngày)
    top_reasons: List[str]


class ML01SelfCureModel:
    """
    Mô hình ML01: Dự báo khả năng khách hàng tự thanh toán (Self-Cure Propensity).
    Huấn luyện trên dữ liệu chu kỳ dòng tiền, lịch sử trả nợ các kỳ trước, và DTI.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        # Hệ số trọng số mặc định cho mô hình
        default_weights = {
            "historical_on_time_ratio": 0.40,  # Lịch sử trả đúng hạn
            "days_since_salary_day": -0.05,     # Số ngày cách ngày nhận lương (Payroll)
            "dpd": -0.03,                       # DPD càng cao xác suất tự trả càng giảm
            "prior_cure_count": 0.15,           # Số lần từng quá hạn nhưng tự trả trong 12 tháng
            "dti_ratio": -0.20,                 # Tỷ lệ nợ trên thu nhập
            "casa_buffer_weight": 0.25          # Trọng số số dư đệm CASA (Non-Payroll)
        }
        self.weights = {**default_weights, **cfg.get("weights", {})}
        self.base_intercept = cfg.get("base_intercept", 0.60)
        self.tiers = cfg.get("tiers", {
            "high_prob": 0.80, "high_grace_days": 5,
            "med_prob": 0.45, "med_grace_days": 3
        })

    def predict_propensity(self, features: Dict[str, Any]) -> float:
        """
        Tính xác suất qua hàm Sigmoid chuẩn math.exp.
        Hỗ trợ đa phân khúc:
        - Payroll BIDV: Tận dụng độ vênh ngày lương Core Banking
        - Non-Payroll (Tiểu thương/Lương bank khác/Tự do): Dùng CASA Buffer & Chu kỳ tiền về suy luận
        """
        dpd = features.get("dpd", 5)
        on_time_ratio = features.get("historical_on_time_ratio", 0.90)
        prior_cures = features.get("prior_cure_count", 2)
        dti = features.get("dti_ratio", 0.35)

        has_payroll = features.get("has_payroll_relationship", True)
        archetype = features.get("inflow_archetype", "PAYROLL_INTERNAL")
        casa_buffer = float(features.get("casa_buffer_ratio", 1.0))

        if has_payroll:
            # Nhánh 1: Khách chi lương qua BIDV
            days_to_salary = features.get("days_since_salary_day", 2)
            flow_signal = self.weights["days_since_salary_day"] * days_to_salary
        else:
            # Nhánh 2: Khách không chi lương qua BIDV (Surrogate Signals)
            if archetype == "MERCHANT_BUSINESS":
                # Tiểu thương: Số dư đệm thanh khoản CASA là tín hiệu mạnh nhất
                clamped_buffer = min(max(casa_buffer, 0.2), 4.0)
                flow_signal = self.weights["casa_buffer_weight"] * (clamped_buffer - 1.0)
            elif archetype == "NON_PAYROLL_SALARIED":
                # Nhận lương bank khác: Dùng chu kỳ suy luận từ LOS + CASA
                inferred_diff = abs(features.get("days_since_historical_pay_rhythm", 2))
                flow_signal = (0.18 * min(casa_buffer, 3.0)) - (0.03 * inferred_diff)
            else:
                # Lao động tự do
                flow_signal = 0.12 * (min(casa_buffer, 2.5) - 1.0)

        z = (self.base_intercept 
             + self.weights["historical_on_time_ratio"] * on_time_ratio
             + flow_signal
             + self.weights["dpd"] * dpd
             + self.weights["prior_cure_count"] * min(prior_cures, 5)
             + self.weights["dti_ratio"] * dti)

        prob = 1.0 / (1.0 + math.exp(-z))
        return max(0.05, min(0.98, prob))

    def evaluate_case(self, debtor_cif: str, features: Dict[str, Any]) -> SelfCurePrediction:
        prob = self.predict_propensity(features)
        has_payroll = features.get("has_payroll_relationship", True)
        archetype = features.get("inflow_archetype", "PAYROLL_INTERNAL")
        casa_buffer = float(features.get("casa_buffer_ratio", 1.0))
        bank_name = features.get("payroll_bank_name", "BIDV")

        reasons = []
        if features.get("historical_on_time_ratio", 0) >= 0.85:
            reasons.append("Lịch sử 12 tháng trước trả đúng hạn 85%+")
        if features.get("dpd", 0) <= 7:
            reasons.append("Quá hạn nhóm sớm dưới 7 ngày")

        # Diễn giải theo phân khúc dòng tiền thực tế
        if has_payroll:
            if features.get("days_since_salary_day", 0) <= 3:
                reasons.append("Gần ngày nhận lương tại BIDV")
        else:
            if archetype == "MERCHANT_BUSINESS":
                if casa_buffer >= 1.5:
                    reasons.append(f"Số dư CASA đệm thanh khoản tốt ({casa_buffer:.1f}x nghĩa vụ nợ)")
                reasons.append("Dòng tiền bán hàng VietQR/POS về rải rác hàng ngày")
            elif archetype == "NON_PAYROLL_SALARIED":
                reasons.append(f"Nhận lương tại {bank_name} (ước tính theo hồ sơ LOS)")
            else:
                reasons.append("Lao động tự do, theo dõi số dư bình quân CASA")

        high_prob = self.tiers.get("high_prob", 0.80)
        high_days = self.tiers.get("high_grace_days", 5)
        med_prob = self.tiers.get("med_prob", 0.45)
        med_days = self.tiers.get("med_grace_days", 3)

        if prob >= high_prob:
            return SelfCurePrediction(
                debtor_cif=debtor_cif,
                self_cure_propensity=round(prob, 3),
                action_tier="SELF_CURE_HIGH",
                grace_period_days=high_days,
                top_reasons=reasons or ["Hồ sơ tín dụng tốt, khả năng tự khỏi rất cao"]
            )
        elif prob >= med_prob:
            return SelfCurePrediction(
                debtor_cif=debtor_cif,
                self_cure_propensity=round(prob, 3),
                action_tier="SELF_CURE_MED",
                grace_period_days=med_days,
                top_reasons=reasons or ["Cần nhắc nhẹ qua Zalo/SMS kèm mã VietQR"]
            )
        else:
            return SelfCurePrediction(
                debtor_cif=debtor_cif,
                self_cure_propensity=round(prob, 3),
                action_tier="HIGH_RISK",
                grace_period_days=0,
                top_reasons=["Rủi ro cao, phân bổ chuyên viên gọi điện can thiệp sớm"]
            )
