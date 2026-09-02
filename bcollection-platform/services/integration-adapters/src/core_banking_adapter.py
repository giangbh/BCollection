try:
    from .core_banking.adapter import (
        CoreBankingAdapter,
        LoanBalanceSnapshot,
        PaymentEvent,
        CustomerInflowProfile
    )
    from .core_banking.client import CoreBankingApiClient
    from .core_banking.mock_client import MockCoreBankingApiClient
    from .core_banking.http_client import HttpCoreBankingApiClient
except ImportError:
    from core_banking.adapter import (
        CoreBankingAdapter,
        LoanBalanceSnapshot,
        PaymentEvent,
        CustomerInflowProfile
    )
    from core_banking.client import CoreBankingApiClient
    from core_banking.mock_client import MockCoreBankingApiClient
    from core_banking.http_client import HttpCoreBankingApiClient

class MockCoreBankingAdapter(CoreBankingAdapter):
    """
    Tiện ích khởi tạo nhanh CoreBankingAdapter chạy trên Mock API Client phục vụ Unit Test / DEV.
    Vẫn đảm bảo sử dụng cùng một Adapter logic duy nhất.
    """
    def __init__(self, mock_client: MockCoreBankingApiClient = None):
        super().__init__(api_client=mock_client or MockCoreBankingApiClient())

    def set_mock_balance(self, loan_id: str, debtor_cif: str, overdue_amount: float, dpd: int):
        if isinstance(self.client, MockCoreBankingApiClient):
            self.client.set_mock_loan({
                "loan_id": loan_id,
                "debtor_cif": debtor_cif,
                "overdue_amount": overdue_amount,
                "dpd": dpd,
                "outstanding_principal": overdue_amount * 10,
                "outstanding_interest": overdue_amount * 0.05,
                "loan_status": "OVERDUE" if overdue_amount > 0 else "SETTLED"
            })

    def simulate_payment(self, loan_id: str, debtor_cif: str, amount: float, channel: str = "VIETQR"):
        if isinstance(self.client, MockCoreBankingApiClient):
            ev = self.client.simulate_incoming_payment(loan_id, debtor_cif, amount, channel)
            return PaymentEvent(
                event_id=ev["event_id"],
                loan_id=loan_id,
                debtor_cif=debtor_cif,
                amount_paid=amount,
                paid_at=self.check_recent_payment(loan_id).paid_at if self.check_recent_payment(loan_id) else None,
                channel=channel
            )
