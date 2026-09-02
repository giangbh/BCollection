try:
    from .los.adapter import (
        LOSAdapter,
        PartyObligationDTO,
        CollateralDTO
    )
    from .los.client import LOSApiClient
    from .los.mock_client import MockLOSApiClient
    from .los.http_client import HttpLOSApiClient
except ImportError:
    from los.adapter import (
        LOSAdapter,
        PartyObligationDTO,
        CollateralDTO
    )
    from los.client import LOSApiClient
    from los.mock_client import MockLOSApiClient
    from los.http_client import HttpLOSApiClient

class MockLOSAdapter(LOSAdapter):
    """
    Tiện ích khởi tạo nhanh LOSAdapter chạy trên Mock API Client phục vụ Unit Test / DEV.
    Vẫn đảm bảo sử dụng cùng một Adapter logic duy nhất.
    """
    def __init__(self, mock_client: MockLOSApiClient = None):
        super().__init__(api_client=mock_client or MockLOSApiClient())

    def add_mock_obligation(self, dto: PartyObligationDTO):
        if isinstance(self.client, MockLOSApiClient):
            self.client.add_mock_party_obligation(dto.loan_id, {
                "loan_id": dto.loan_id,
                "party_id": dto.party_id,
                "party_name": dto.party_name,
                "party_type": dto.party_type,
                "edge_type": dto.edge_type,
                "contact_eligible": dto.contact_eligible,
                "phone_e164": dto.phone_e164,
                "source_system": dto.source_system
            })
