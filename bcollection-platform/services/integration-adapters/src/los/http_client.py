import os
from urllib.parse import quote
from .client import LOSApiClient
from rest_transport import RestTransport, required_list


class HttpLOSApiClient(LOSApiClient):
    def __init__(self, base_url=None, api_key=None, timeout_seconds=5):
        self.transport = RestTransport(base_url or os.getenv("LOS_API_URL", ""),
                                       api_key or os.getenv("LOS_API_KEY", ""), timeout_seconds)

    def fetch_party_obligations(self, loan_id):
        return required_list(self.transport.get(f"loans/{quote(loan_id, safe='')}/parties"), "parties")

    def fetch_collateral_details(self, loan_id):
        return required_list(self.transport.get(f"loans/{quote(loan_id, safe='')}/collaterals"), "collaterals")
