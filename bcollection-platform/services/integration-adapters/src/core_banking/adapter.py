import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from .client import CoreBankingApiClient
from .mock_client import MockCoreBankingApiClient
from .http_client import HttpCoreBankingApiClient

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


@dataclass
class CustomerInflowProfile:
    debtor_cif: str
    verified_inflow_avg_monthly: float
    casa_balance: float
    salary_day_of_month: int
    stability_coefficient: float
    has_payroll_relationship: bool = True
    inflow_archetype: str = "PAYROLL_INTERNAL"  # PAYROLL_INTERNAL, MERCHANT_BUSINESS, NON_PAYROLL_SALARIED, GIG_FREELANCE
    casa_buffer_ratio: float = 1.0              # Tỷ lệ đệm thanh khoản CASA / Nghĩa vụ trả nợ
    inferred_pay_day_of_month: Optional[int] = None # Ngày chu kỳ tiền về suy luận từ LOS/Lịch sử
    payroll_bank_name: str = "BIDV"


class CoreBankingAdapter:
    """
    Adapter Duy nhất kết nối Hệ thống Core Banking của Ngân hàng.
    Tuân thủ Kiến trúc Hexagonal (Port & Adapter):
    - Đóng gói toàn bộ logic nghiệp vụ (DTO transformation, Contract validation, Error handling).
    - Ủy nhiệm việc gọi mạng cho ApiClient (Mặc định gọi MockApiClient; khi Go-Live chỉ cần cấu hình CORE_BANKING_MODE=http).
    - TUYỆT ĐỐI KHÔNG CẦN SỬA ĐỔI ADAPTER NÀY KHI CHUYỂN TỪ MOCK SANG HỆ THỐNG THẬT.
    """
    def __init__(self, api_client: Optional[CoreBankingApiClient] = None):
        if api_client is not None:
            self._client = api_client
        else:
            mode = os.getenv("CORE_BANKING_MODE", "mock").lower()
            if mode == "http":
                self._client = HttpCoreBankingApiClient()
            else:
                self._client = MockCoreBankingApiClient()

    @property
    def client(self) -> CoreBankingApiClient:
        return self._client

    def get_realtime_balance(self, loan_id: str) -> LoanBalanceSnapshot:
        """
        Kiểm tra số dư nợ quá hạn thời gian thực (IF-CORE-04 / IF-CORE-01).
        Chuyển đổi raw payload từ Backend API thành domain snapshot.
        """
        raw_res = self._client.fetch_loan_balance(loan_id)
        data = raw_res.get("data", raw_res)
        
        as_of_val = data.get("as_of")
        if isinstance(as_of_val, str):
            try:
                as_of_dt = datetime.fromisoformat(as_of_val)
            except Exception:
                as_of_dt = datetime.now()
        else:
            as_of_dt = datetime.now()

        overdue = float(data.get("overdue_amount", 0.0))
        return LoanBalanceSnapshot(
            loan_id=data.get("loan_id", loan_id),
            debtor_cif=data.get("debtor_cif", "CIF_UNKNOWN"),
            outstanding_principal=float(data.get("outstanding_principal", 0.0)),
            outstanding_interest=float(data.get("outstanding_interest", 0.0)),
            overdue_amount=overdue,
            days_past_due=int(data.get("dpd", 0)),
            is_fully_paid=(overdue <= 0),
            as_of=as_of_dt
        )

    def check_recent_payment(self, loan_id: str, lookback_minutes: int = 15) -> Optional[PaymentEvent]:
        """
        Kiểm tra sự kiện thanh toán vừa phát sinh trong X phút gần nhất.
        """
        raw_payments = self._client.fetch_recent_payments(loan_id, lookback_minutes)
        if not raw_payments:
            return None
        
        latest = raw_payments[-1]
        paid_at_str = latest.get("paid_at")
        try:
            paid_at_dt = datetime.fromisoformat(paid_at_str) if paid_at_str else datetime.now()
        except Exception:
            paid_at_dt = datetime.now()

        return PaymentEvent(
            event_id=latest.get("event_id", "PAY-UNKNOWN"),
            loan_id=latest.get("loan_id", loan_id),
            debtor_cif=latest.get("debtor_cif", ""),
            amount_paid=float(latest.get("amount_paid", 0.0)),
            paid_at=paid_at_dt,
            channel=latest.get("channel", "VIETQR")
        )

    def get_overdue_portfolio(self, max_dpd: int = 30) -> List[Dict[str, Any]]:
        """
        Lấy danh sách danh mục nợ B1 (IF-CORE-01) phục vụ nạp vào Case Queue.
        """
        raw_loans = self._client.fetch_overdue_portfolio(max_dpd)
        return raw_loans

    def get_customer_inflow_profile(self, debtor_cif: str) -> CustomerInflowProfile:
        """
        Lấy thông tin dòng tiền và lương phục vụ Persona 360 (D1 Ability Score).
        """
        raw_inflow = self._client.fetch_customer_inflows(debtor_cif)
        data = raw_inflow.get("data", raw_inflow)
        return CustomerInflowProfile(
            debtor_cif=debtor_cif,
            verified_inflow_avg_monthly=float(data.get("verified_inflow_avg_monthly", 20000000.0)),
            casa_balance=float(data.get("casa_balance", 0.0)),
            salary_day_of_month=int(data.get("salary_day_of_month", 10)),
            stability_coefficient=float(data.get("stability_coefficient", 0.85)),
            has_payroll_relationship=bool(data.get("has_payroll_relationship", True)),
            inflow_archetype=str(data.get("inflow_archetype", "PAYROLL_INTERNAL")),
            casa_buffer_ratio=float(data.get("casa_buffer_ratio", 1.0)),
            inferred_pay_day_of_month=data.get("inferred_pay_day_of_month"),
            payroll_bank_name=str(data.get("payroll_bank_name", "BIDV"))
        )
