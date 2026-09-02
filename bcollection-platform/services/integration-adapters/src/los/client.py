from abc import ABC, abstractmethod
from typing import Dict, Any, List

class LOSApiClient(ABC):
    """
    Interface cấp thấp kết nối trực tiếp với Backend API của hệ thống Khởi tạo Khoản vay (LOS / RLOS / CLOS).
    """
    @abstractmethod
    def fetch_party_obligations(self, loan_id: str) -> List[Dict[str, Any]]:
        """Gọi API tra cứu các bên liên quan và nghĩa vụ khoản vay (IF-LOS-02)"""
        pass

    @abstractmethod
    def fetch_collateral_details(self, loan_id: str) -> List[Dict[str, Any]]:
        """Gọi API tra cứu tài sản bảo đảm thế chấp"""
        pass
