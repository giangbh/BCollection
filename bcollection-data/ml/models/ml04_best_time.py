from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class BestTimePrediction:
    debtor_cif: str
    best_time_window: str    # "08:30-11:30", "14:00-17:00", "18:00-20:30"
    best_channel: str        # "VOICE", "ZALO", "SMS"
    expected_rpc_rate: float # Tỷ lệ nghe máy dự báo (ví dụ 0.72)


class ML04BestTimeToContactModel:
    """
    Mô hình ML04: Dự báo khung giờ vàng và kênh liên hệ có xác suất Right-Party-Contact (RPC) cao nhất.
    """
    def predict_best_time(self, debtor_cif: str, profile: Dict[str, Any]) -> BestTimePrediction:
        occupation = profile.get("occupation", "OFFICE_WORKER")
        age = profile.get("age", 35)
        past_calls = profile.get("past_answered_hours", [])

        # Nếu đã có lịch sử nghe máy trong quá khứ -> ưu tiên khung giờ đó
        if past_calls:
            avg_hour = sum(past_calls) / len(past_calls)
            if 18 <= avg_hour <= 21:
                return BestTimePrediction(debtor_cif, "18:00-20:30", "VOICE", 0.85)
            elif 8 <= avg_hour <= 12:
                return BestTimePrediction(debtor_cif, "08:30-11:30", "VOICE", 0.78)
            else:
                return BestTimePrediction(debtor_cif, "14:00-17:00", "VOICE", 0.72)

        # Suy luận theo nghề nghiệp
        if occupation in ("OFFICE_WORKER", "FACTORY_WORKER", "TEACHER"):
            return BestTimePrediction(debtor_cif, "18:00-20:30", "VOICE", 0.75)
        elif occupation in ("MERCHANT", "BUSINESS_OWNER", "SELF_EMPLOYED"):
            return BestTimePrediction(debtor_cif, "08:30-11:30", "VOICE", 0.68)
        else:
            return BestTimePrediction(debtor_cif, "14:00-17:00", "ZALO", 0.60)
