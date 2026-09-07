from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class CTIApiClient(ABC):
    """
    Interface cấp thấp kết nối trực tiếp với Hệ thống Tổng đài CTI
    (FreeSWITCH, Avaya, Cisco Contact Center Gateway).
    """

    @abstractmethod
    def originate_call(
        self,
        agent_id: str,
        agent_extension: str,
        destination_phone: str,
        case_id: str,
        guardrail_token: str
    ) -> Dict[str, Any]:
        """Khởi tạo cuộc gọi click-to-call từ tổng đài CTI tới số khách hàng."""
        pass

    @abstractmethod
    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """Tra cứu trạng thái cuộc gọi thời gian thực (RINGING, ANSWERED, HUNGUP, BUSY)."""
        pass

    @abstractmethod
    def hangup_call(self, call_id: str) -> Dict[str, Any]:
        """Chủ động kết thúc cuộc gọi trên tổng đài và nhận URL ghi âm."""
        pass
