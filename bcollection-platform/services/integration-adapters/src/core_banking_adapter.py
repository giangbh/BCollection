from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import os

@dataclass
class LoanBalanceSnapshot:
    loan_id: str
    debtor_cif: str
    outstanding_principal: float
    outstanding_interest: float
    overdue_amount: float
    days_past_due: int
    is_fully_paid: bool
    as_of: datetime


@dataclass
class PaymentEvent:
    event_id: str
    loan_id: str
    debtor_cif: str
    amount_paid: float
    paid_at: datetime
    channel: str  # SMARTBANKING, VIETQR, COUNTER


class CoreBankingAdapter(ABC):
    """
    Interface chuẩn hóa kết nối với Core Banking (SIBS/Signature/Finacle/B-Connect).
    """
    @abstractmethod
    def get_realtime_balance(self, loan_id: str) -> LoanBalanceSnapshot:
        """Kiểm tra số dư nợ quá hạn thời gian thực (IF-CORE-01 / IF-CORE-04)"""
        pass

    @abstractmethod
    def check_recent_payment(self, loan_id: str, lookback_minutes: int = 15) -> Optional[PaymentEvent]:
        """Kiểm tra sự kiện thanh toán vừa phát sinh trong X phút gần nhất"""
        pass


class MockCoreBankingAdapter(CoreBankingAdapter):
    """
    Mock Service phục vụ kiểm thử, phát triển DEV/UAT trước khi đấu nối API thật của Core Banking.
    """
    def __init__(self):
        self._mock_balances: Dict[str, Dict[str, Any]] = {}
        self._mock_payments: Dict[str, List[PaymentEvent]] = {}

    def set_mock_balance(self, loan_id: str, debtor_cif: str, overdue_amount: float, dpd: int):
        self._mock_balances[loan_id] = {
            "debtor_cif": debtor_cif,
            "overdue_amount": overdue_amount,
            "dpd": dpd,
            "outstanding_principal": overdue_amount * 10,
            "outstanding_interest": overdue_amount * 0.05
        }

    def simulate_payment(self, loan_id: str, debtor_cif: str, amount: float, channel: str = "VIETQR"):
        """Giả lập khách hàng vừa thanh toán thành công qua VietQR/SmartBanking"""
        # Cập nhật số dư về 0
        if loan_id in self._mock_balances:
            self._mock_balances[loan_id]["overdue_amount"] = 0.0
            self._mock_balances[loan_id]["dpd"] = 0

        event = PaymentEvent(
            event_id=f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            loan_id=loan_id,
            debtor_cif=debtor_cif,
            amount_paid=amount,
            paid_at=datetime.now(),
            channel=channel
        )
        if loan_id not in self._mock_payments:
            self._mock_payments[loan_id] = []
        self._mock_payments[loan_id].append(event)
        return event

    def get_realtime_balance(self, loan_id: str) -> LoanBalanceSnapshot:
        data = self._mock_balances.get(loan_id, {
            "debtor_cif": "CIF_DEFAULT",
            "overdue_amount": 5000000.0,
            "dpd": 12,
            "outstanding_principal": 50000000.0,
            "outstanding_interest": 250000.0
        })
        overdue = data["overdue_amount"]
        return LoanBalanceSnapshot(
            loan_id=loan_id,
            debtor_cif=data["debtor_cif"],
            outstanding_principal=data["outstanding_principal"],
            outstanding_interest=data["outstanding_interest"],
            overdue_amount=overdue,
            days_past_due=data["dpd"],
            is_fully_paid=(overdue <= 0),
            as_of=datetime.now()
        )

    def check_recent_payment(self, loan_id: str, lookback_minutes: int = 15) -> Optional[PaymentEvent]:
        events = self._mock_payments.get(loan_id, [])
        if not events:
            return None
        now = datetime.now()
        for ev in reversed(events):
            if now - ev.paid_at <= timedelta(minutes=lookback_minutes):
                return ev
        return None


class HttpCoreBankingAdapter(CoreBankingAdapter):
    """
    Adapter gọi REST API thật tới Core Banking qua Enterprise Service Bus (ESB/API Gateway).
    Cấu hình URL qua biến môi trường CORE_BANKING_API_URL.
    """
    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        self.api_url = api_url or os.getenv("CORE_BANKING_API_URL", "https://api-internal.bidv.vn/core/v1")
        self.api_key = api_key or os.getenv("CORE_BANKING_API_KEY", "")

    def get_realtime_balance(self, loan_id: str) -> LoanBalanceSnapshot:
        # Trong tương lai sẽ gọi HTTP requests / httpx tới self.api_url
        raise NotImplementedError("API Thật sẽ được tích hợp khi hạ tầng ESB/Core Banking sẵn sàng.")

    def check_recent_payment(self, loan_id: str, lookback_minutes: int = 15) -> Optional[PaymentEvent]:
        raise NotImplementedError("API Thật sẽ được tích hợp khi hạ tầng ESB/Core Banking sẵn sàng.")
