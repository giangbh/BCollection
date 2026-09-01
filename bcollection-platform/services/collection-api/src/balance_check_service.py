from typing import Dict, Any, Optional
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../integration-adapters/src')))
from core_banking_adapter import CoreBankingAdapter, LoanBalanceSnapshot, PaymentEvent


class RealTimeBalanceCheckService:
    """
    Cơ chế Chống Đòi nợ Nhầm (Anti-False-Delinquency Guard):
    Trước khi gửi tin nhắn hoặc gọi điện, hệ thống kiểm tra số dư tức thời với Core Banking.
    Nếu khách hàng đã thanh toán (overdue_amount <= 0 hoặc có sự kiện trả tiền trong 15 phút qua),
    hành động sẽ bị HỦY ngay lập tức và Case được cập nhật thành CURED.
    """
    def __init__(self, core_adapter: CoreBankingAdapter):
        self.core_adapter = core_adapter

    def verify_action_eligibility(self, loan_id: str, debtor_cif: str) -> Dict[str, Any]:
        """
        Kiểm tra tính hợp lệ về mặt số dư nợ trước khi nhắc nợ.
        """
        # 1. Kiểm tra sự kiện thanh toán vừa phát sinh trong 15 phút
        recent_payment = self.core_adapter.check_recent_payment(loan_id, lookback_minutes=15)
        if recent_payment:
            return {
                "can_proceed": False,
                "reason": "PAYMENT_RECENTLY_DETECTED",
                "message": f"Khách hàng vừa thanh toán {recent_payment.amount_paid:,.0f} VNĐ qua {recent_payment.channel} vào lúc {recent_payment.paid_at.strftime('%H:%M:%S')}. Hủy nhắc nợ.",
                "payment_event": recent_payment
            }

        # 2. Kiểm tra số dư nợ quá hạn thời gian thực
        snapshot = self.core_adapter.get_realtime_balance(loan_id)
        if snapshot.is_fully_paid or snapshot.overdue_amount <= 0:
            return {
                "can_proceed": False,
                "reason": "NO_OVERDUE_BALANCE",
                "message": f"Khoản vay {loan_id} hiện không còn dư nợ quá hạn (Số dư: {snapshot.overdue_amount:,.0f} VNĐ). Hủy nhắc nợ.",
                "balance_snapshot": snapshot
            }

        return {
            "can_proceed": True,
            "reason": "OVERDUE_CONFIRMED",
            "message": f"Xác nhận khoản vay đang quá hạn {snapshot.days_past_due} ngày với số tiền {snapshot.overdue_amount:,.0f} VNĐ.",
            "balance_snapshot": snapshot
        }
