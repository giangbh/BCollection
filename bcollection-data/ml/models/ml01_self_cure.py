import math
from typing import Dict, Any, List
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
    def __init__(self):
        # Hệ số trọng số mẫu cho MVP
        self.weights = {
            "historical_on_time_ratio": 0.40,  # Lịch sử trả đúng hạn
            "days_since_salary_day": -0.05,     # Số ngày cách ngày nhận lương
            "dpd": -0.03,                       # DPD càng cao xác suất tự trả càng giảm
            "prior_cure_count": 0.15,           # Số lần từng quá hạn nhưng tự trả trong 12 tháng
            "dti_ratio": -0.20                  # Tỷ lệ nợ trên thu nhập
        }
        self.base_intercept = 0.60

    def predict_propensity(self, features: Dict[str, Any]) -> float:
        """Tính xác suất qua hàm Sigmoid chuẩn math.exp"""
        dpd = features.get("dpd", 5)
        on_time_ratio = features.get("historical_on_time_ratio", 0.90)
        days_to_salary = features.get("days_since_salary_day", 2)
        prior_cures = features.get("prior_cure_count", 2)
        dti = features.get("dti_ratio", 0.35)

        z = (self.base_intercept 
             + self.weights["historical_on_time_ratio"] * on_time_ratio
             + self.weights["days_since_salary_day"] * days_to_salary
             + self.weights["dpd"] * dpd
             + self.weights["prior_cure_count"] * min(prior_cures, 5)
             + self.weights["dti_ratio"] * dti)

        prob = 1.0 / (1.0 + math.exp(-z))
        return max(0.05, min(0.98, prob))

    def evaluate_case(self, debtor_cif: str, features: Dict[str, Any]) -> SelfCurePrediction:
        prob = self.predict_propensity(features)
        
        reasons = []
        if features.get("historical_on_time_ratio", 0) >= 0.85:
            reasons.append("Lịch sử 12 tháng trước trả đúng hạn 85%+")
        if features.get("dpd", 0) <= 7:
            reasons.append("Quá hạn nhóm sớm dưới 7 ngày")
        if features.get("days_since_salary_day", 0) <= 3:
            reasons.append("Gần ngày nhận lương định kỳ")

        if prob >= 0.80:
            return SelfCurePrediction(
                debtor_cif=debtor_cif,
                self_cure_propensity=round(prob, 3),
                action_tier="SELF_CURE_HIGH",
                grace_period_days=5,
                top_reasons=reasons or ["Hồ sơ tín dụng tốt, khả năng tự khỏi rất cao"]
            )
        elif prob >= 0.45:
            return SelfCurePrediction(
                debtor_cif=debtor_cif,
                self_cure_propensity=round(prob, 3),
                action_tier="SELF_CURE_MED",
                grace_period_days=2,
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
