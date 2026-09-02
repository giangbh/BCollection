from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class CoreBankingApiClient(ABC):
    """
    Interface cấp thấp kết nối trực tiếp với Backend API của Core Banking (ESB / API Gateway).
    Phân tách hoàn toàn khỏi Adapter nghiệp vụ.
    """
    @abstractmethod
    def fetch_loan_balance(self, loan_id: str) -> Dict[str, Any]:
        """Gọi API truy vấn số dư khoản nợ"""
        pass

    @abstractmethod
    def fetch_recent_payments(self, loan_id: str, lookback_minutes: int = 15) -> List[Dict[str, Any]]:
        """Gọi API tra cứu các giao dịch thanh toán gần nhất"""
        pass

    @abstractmethod
    def fetch_overdue_portfolio(self, max_dpd: int = 30) -> List[Dict[str, Any]]:
        """Gọi API trích xuất danh sách danh mục nợ B1 (IF-CORE-01)"""
        pass

    @abstractmethod
    def fetch_customer_inflows(self, debtor_cif: str, months: int = 3) -> Dict[str, Any]:
        """Gọi API tra cứu dòng tiền tài khoản thanh toán và CASA của CIF"""
        pass
