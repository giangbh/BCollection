import os
from urllib.parse import urlencode
from .client import CICApiClient
from rest_transport import RestTransport


class HttpCICApiClient(CICApiClient):
    def __init__(self, base_url=None, api_key=None, timeout_seconds=5):
        self.transport = RestTransport(base_url or os.getenv("CIC_GATEWAY_URL", ""),
                                       api_key or os.getenv("CIC_GATEWAY_KEY", ""), timeout_seconds)

    def fetch_credit_score_and_obligations(self, debtor_cif, national_id):
        return self.transport.get("reports?" + urlencode({"cif": debtor_cif, "national_id": national_id}))
