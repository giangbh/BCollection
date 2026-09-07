from typing import Dict, Any, Optional
from .client import SpeechAIApiClient


class MockSpeechAIApiClient(SpeechAIApiClient):
    """
    Mock In-Memory Client cho Speech AI phục vụ Unit Test và môi trường phát triển cục bộ.
    """

    def analyze_call(
        self,
        case_id: str,
        call_duration_seconds: int = 45,
        recording_url: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        dpd = (context or {}).get("dpd", 8)
        full_name = (context or {}).get("full_name", "Khách hàng")
        loan_id = (context or {}).get("loan_id", "LOAN-UN-20001")
        overdue_amt = float((context or {}).get("overdue_amount", 3330000.0))

        if dpd <= 10:
            transcript = [
                {"speaker": "RM", "text": f"Dạ em chào anh/chị {full_name}, em là chuyên viên quản lý nợ Ngân hàng liên hệ về hợp đồng {loan_id} đang quá hạn {dpd} ngày với số tiền {overdue_amt:,.0f} VNĐ ạ."},
                {"speaker": "CUSTOMER", "text": f"À chào em, mấy hôm vừa rồi anh đi công tác xa nên quên béng mất. Đến ngày 10 tới anh nhận lương sẽ chuyển khoản đủ {overdue_amt:,.0f} đồng qua SmartBanking nhé."},
                {"speaker": "RM", "text": "Dạ vâng em đã ghi nhận lịch hẹn thanh toán vào ngày 10 tới. Em cảm ơn anh/chị nhiều ạ."}
            ]
            outcome = "PTP_AGREED"
            ptp_amt = overdue_amt
            ptp_date = "2026-09-10"
            confidence = 0.98
            sentiment_label = "TÍCH CỰC"
            sentiment_score = 0.48
            sentiment_tone = "Hợp tác cao • Tôn trọng"
            root_cause = "CASHFLOW_TIMING"
            auto_notes = f"Khách xác nhận bận công tác quên lịch nộp, cam kết chuyển khoản đủ {overdue_amt:,.0f} VNĐ qua SmartBanking vào ngày nhận lương 10/09."
        elif dpd <= 20:
            half_amt = round(overdue_amt * 0.5, -4)
            transcript = [
                {"speaker": "RM", "text": f"Chào anh/chị {full_name}, Ngân hàng liên hệ về khoản vay {loan_id} đã quá hạn {dpd} ngày. Em gọi để trao đổi phương án hỗ trợ anh/chị thanh toán kỳ nợ này ạ."},
                {"speaker": "CUSTOMER", "text": f"Đợt này kinh doanh hàng họ chậm thu hồi tiền quá em ơi. Đến ngày 15 này anh gom được trước một nửa khoảng {half_amt:,.0f} đồng nộp trước được không em?"},
                {"speaker": "RM", "text": "Dạ được anh ạ, em ghi nhận cam kết nộp trước ngày 15, phần còn lại chi nhánh sẽ hướng dẫn cơ cấu giãn tiếp ạ."}
            ]
            outcome = "PTP_AGREED"
            ptp_amt = half_amt
            ptp_date = "2026-09-15"
            confidence = 0.93
            sentiment_label = "TRUNG TÍNH"
            sentiment_score = 0.05
            sentiment_tone = "Khó khăn dòng tiền • Thiện chí đàm phán"
            root_cause = "BUSINESS_DOWNTURN"
            auto_notes = f"Khách kinh doanh chậm thu hồi công nợ, cam kết thanh toán trước 50% ({half_amt:,.0f} VNĐ) vào ngày 15/09."
        else:
            transcript = [
                {"speaker": "RM", "text": f"Chào anh/chị {full_name}, Ngân hàng thông báo khoản vay {loan_id} đã quá hạn {dpd} ngày và có nguy cơ chuyển nhóm nợ xấu trên CIC toàn quốc ạ."},
                {"speaker": "CUSTOMER", "text": "Tôi đã bảo đợt này kẹt tiền không xoay kịp rồi mà cứ gọi giục suốt thế! Để cuối tháng xem thế nào rồi tính!"},
                {"speaker": "RM", "text": "Dạ ngân hàng rất thấu hiểu khó khăn của anh/chị, em xin phép lưu nhận thông tin và gửi văn bản hỗ trợ qua Zalo ạ."}
            ]
            outcome = "REFUSED"
            ptp_amt = None
            ptp_date = None
            confidence = 0.91
            sentiment_label = "TIÊU CỰC"
            sentiment_score = -0.65
            sentiment_tone = "Bực bội • Né tránh nghĩa vụ"
            root_cause = "WILFUL_DEFAULT"
            auto_notes = "Khách hàng từ chối cam kết ngày trả cụ thể, phản ứng bực bội khi bị nhắc nợ. Đề xuất chuyển biện pháp cảnh báo văn bản."

        return {
            "case_id": case_id,
            "call_duration_seconds": call_duration_seconds,
            "transcript": transcript,
            "extracted_outcome": outcome,
            "extracted_ptp_amount": ptp_amt,
            "extracted_ptp_date": ptp_date,
            "confidence": confidence,
            "detected_root_cause": root_cause,
            "sentiment": {
                "label": sentiment_label,
                "score": sentiment_score,
                "tone": sentiment_tone
            },
            "compliance_audit": {
                "status": "PASSED",
                "checks": [
                    "Xưng danh chuyên viên chuẩn mực",
                    "Tuyệt đối không dùng lời lẽ đe dọa hoặc từ cấm",
                    "Tuân thủ khung giờ nhắc nợ Thông tư 18/2019/TT-NHNN",
                    "Đúng đối tượng được phép liên hệ theo phê duyệt L6"
                ],
                "prohibited_words_found": []
            },
            "auto_notes": auto_notes
        }
