from typing import Dict, Any
from .client import CICApiClient

class MockCICApiClient(CICApiClient):
    """
    Mock Service giả lập cổng dữ liệu Trung tâm Thông tin Tín dụng Quốc gia (CIC).
    Sinh dữ liệu tín dụng thực tế, đa dạng (Credit Score 450 - 750, tổng nợ 15M - 280M).
    """
    def fetch_credit_score_and_obligations(self, debtor_cif: str, national_id: str) -> Dict[str, Any]:
        cif_hash = sum(ord(ch) for ch in debtor_cif)

        # 1. Điểm tín dụng CIC phân bổ từ 450 đến 750
        # 450 - 579: Kém/Rủi ro cao (Poor)
        # 580 - 669: Trung bình (Fair)
        # 670 - 739: Tốt (Good)
        # 740 - 750+: Xuất sắc (Very Good)
        raw_score = 450 + (cif_hash % 270) + ((cif_hash * 7) % 31)
        credit_score = min(750, max(450, raw_score))

        # 2. Nhóm nợ xấu nhất tại các TCTD khác
        if credit_score >= 680:
            worst_group = 1
        elif credit_score >= 580:
            worst_group = 2 if (cif_hash % 4 == 0) else 1
        else:
            mod_g = cif_hash % 10
            worst_group = 3 if mod_g < 3 else (2 if mod_g < 7 else 1)

        # 3. Số lượng tổ chức tín dụng đang có quan hệ nợ (1 đến 4 TCTD)
        obligations_count = (cif_hash % 4) + 1

        # 4. Tổng nghĩa vụ nợ tại các TCTD khác (tương ứng với số TCTD)
        base_debt = 15_000_000.0 * obligations_count
        debt_variation = (cif_hash % 25) * 5_000_000.0
        total_debt = round(base_debt + debt_variation, -6)  # Làm tròn đến hàng triệu

        # 5. Tín hiệu vẫn trả nợ TCTD khác trong khi nợ ngân hàng ta
        # (Nếu ở bank khác vẫn nhóm 1 mà nợ ngân hàng ta quá hạn -> có dấu hiệu né tránh)
        paying_other = (worst_group == 1) and (cif_hash % 5 != 0)

        return {
            "status": "SUCCESS",
            "data": {
                "debtor_cif": debtor_cif,
                "national_id": national_id,
                "credit_score": credit_score,
                "worst_group_other_banks": worst_group,
                "obligations_at_other_banks_count": obligations_count,
                "total_obligation_other_banks": total_debt,
                "paying_other_banks_while_overdue": paying_other
            }
        }
