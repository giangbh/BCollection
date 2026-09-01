from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class PartyObligationDTO:
    loan_id: str
    party_id: str
    party_name: str
    party_type: str        # PERSON / ORG
    edge_type: str         # BORROWED, GUARANTEES, CO_BORROWER_WITH, LEGAL_REP_OF
    contact_eligible: str  # YES / NO / CONDITIONAL
    phone_e164: str
    source_system: str     # LOS, RLOS


class LOSAdapter(ABC):
    """
    Interface tích hợp hệ thống Khởi tạo Khoản vay (LOS / RLOS / CLOS) để lấy danh sách người có nghĩa vụ (IF-LOS-02).
    """
    @abstractmethod
    def get_loan_party_obligations(self, loan_id: str) -> List[PartyObligationDTO]:
        pass


class MockLOSAdapter(LOSAdapter):
    """Mock Service LOS phục vụ DEV/UAT"""
    def __init__(self):
        self._mock_data: Dict[str, List[PartyObligationDTO]] = {}

    def add_mock_obligation(self, dto: PartyObligationDTO):
        if dto.loan_id not in self._mock_data:
            self._mock_data[dto.loan_id] = []
        self._mock_data[dto.loan_id].append(dto)

    def get_loan_party_obligations(self, loan_id: str) -> List[PartyObligationDTO]:
        return self._mock_data.get(loan_id, [
            PartyObligationDTO(
                loan_id=loan_id,
                party_id="CIF_MOCK_BORROWER",
                party_name="NGUYỄN VĂN AN",
                party_type="PERSON",
                edge_type="BORROWED",
                contact_eligible="YES",
                phone_e164="+84912345678",
                source_system="LOS"
            )
        ])
