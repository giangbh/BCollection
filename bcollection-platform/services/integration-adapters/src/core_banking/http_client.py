import os
from urllib.parse import quote, urlencode
from .client import CoreBankingApiClient
from rest_transport import RestTransport, required_list
from rest_transport import AdapterError
from .contracts import CoreSnapshot
from pydantic import ValidationError


class HttpCoreBankingApiClient(CoreBankingApiClient):
    """Same read transport for synthetic REST and configured legacy REST."""
    def __init__(self, base_url=None, api_key=None, timeout_seconds=5):
        self.transport = RestTransport(base_url or os.getenv("CORE_BANKING_API_URL", ""),
                                       api_key or os.getenv("CORE_BANKING_API_KEY", ""), timeout_seconds)

    def fetch_loan_balance(self, loan_id):
        response = self.transport.get(f"loans/{quote(loan_id, safe='')}/balance")
        try:
            snapshot = CoreSnapshot.model_validate(response["data"])
            if response.get("status") != "SUCCESS" or snapshot.loan_id != loan_id:
                raise ValueError("Identity or status mismatch")
        except (KeyError, ValueError, ValidationError) as exc:
            raise AdapterError("INVALID_CONTRACT") from None
        return response

    def fetch_recent_payments(self, loan_id, lookback_minutes=15):
        response = self.transport.get(f"loans/{quote(loan_id, safe='')}/payments?" + urlencode({"lookback_minutes": lookback_minutes}))
        return required_list(response, "payments")

    def fetch_overdue_portfolio(self, max_dpd=30):
        return required_list(self.transport.get("portfolio/delinquent?" + urlencode({"max_dpd": max_dpd})), "loans")

    def fetch_customer_inflows(self, debtor_cif, months=3):
        return self.transport.get(f"customers/{quote(debtor_cif, safe='')}/cashflows?" + urlencode({"months": months}))
