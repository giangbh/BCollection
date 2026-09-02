from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .client import CoreBankingApiClient

class MockCoreBankingApiClient(CoreBankingApiClient):
    """
    Mock Service giả lập Backend API của Core Banking BIDV (SIBS / B-Connect ESB).
    Trả về dữ liệu thô (Raw JSON Response) chuẩn hợp đồng IF-CORE-01 và IF-CORE-04.
    """
    def __init__(self):
        self._loans: Dict[str, Dict[str, Any]] = {
            "LOAN-MO-20001": {
                "loan_id": "LOAN-MO-20001",
                "debtor_cif": "CIF100001",
                "full_name": "VŨ THỊ TRANG",
                "phone_e164": "+84932753329",
                "product_code": "MORTGAGE",
                "dpd": 11,
                "outstanding_principal": 320000000.0,
                "outstanding_interest": 16000000.0,
                "overdue_amount": 16000000.0,
                "loan_status": "OVERDUE",
                "batch_date": datetime.now().strftime("%Y-%m-%d")
            },
            "LOAN-AL-20002": {
                "loan_id": "LOAN-AL-20002",
                "debtor_cif": "CIF100002",
                "full_name": "NGÔ VĂN HOÀNG",
                "phone_e164": "+84988456123",
                "product_code": "AUTO_LOAN",
                "dpd": 23,
                "outstanding_principal": 450000000.0,
                "outstanding_interest": 22500000.0,
                "overdue_amount": 22500000.0,
                "loan_status": "OVERDUE",
                "batch_date": datetime.now().strftime("%Y-%m-%d")
            },
            "LOAN-CC-20003": {
                "loan_id": "LOAN-CC-20003",
                "debtor_cif": "CIF100003",
                "full_name": "TRẦN THỊ MAI",
                "phone_e164": "+84912345678",
                "product_code": "CREDIT_CARD",
                "dpd": 5,
                "outstanding_principal": 45000000.0,
                "outstanding_interest": 2250000.0,
                "overdue_amount": 2250000.0,
                "loan_status": "OVERDUE",
                "batch_date": datetime.now().strftime("%Y-%m-%d")
            }
        }
        self._payments: Dict[str, List[Dict[str, Any]]] = {}

    def set_mock_loan(self, loan_data: Dict[str, Any]):
        """Cấu hình thêm/sửa khoản vay phục vụ test"""
        self._loans[loan_data["loan_id"]] = loan_data

    def simulate_incoming_payment(self, loan_id: str, debtor_cif: str, amount: float, channel: str = "VIETQR"):
        """Giả lập có giao dịch chuyển tiền thanh toán vào Core Banking"""
        if loan_id in self._loans:
            self._loans[loan_id]["overdue_amount"] = 0.0
            self._loans[loan_id]["dpd"] = 0
            self._loans[loan_id]["loan_status"] = "ACTIVE"

        payment_record = {
            "event_id": f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "loan_id": loan_id,
            "debtor_cif": debtor_cif,
            "amount_paid": amount,
            "paid_at": datetime.now().isoformat(),
            "channel": channel
        }
        if loan_id not in self._payments:
            self._payments[loan_id] = []
        self._payments[loan_id].append(payment_record)
        return payment_record

    def fetch_loan_balance(self, loan_id: str) -> Dict[str, Any]:
        """Giả lập phản hồi endpoint GET /core/v1/loans/{loan_id}/balance"""
        if loan_id in self._loans:
            l = self._loans[loan_id]
            return {
                "status": "SUCCESS",
                "data": {
                    "loan_id": loan_id,
                    "debtor_cif": l["debtor_cif"],
                    "outstanding_principal": l["outstanding_principal"],
                    "outstanding_interest": l["outstanding_interest"],
                    "overdue_amount": l["overdue_amount"],
                    "dpd": l["dpd"],
                    "is_fully_paid": (l["overdue_amount"] <= 0),
                    "as_of": datetime.now().isoformat()
                }
            }
        # Mặc định cho case chưa khai báo
        return {
            "status": "SUCCESS",
            "data": {
                "loan_id": loan_id,
                "debtor_cif": "CIF_DEFAULT",
                "outstanding_principal": 50000000.0,
                "outstanding_interest": 2500000.0,
                "overdue_amount": 5000000.0,
                "dpd": 12,
                "is_fully_paid": False,
                "as_of": datetime.now().isoformat()
            }
        }

    def fetch_recent_payments(self, loan_id: str, lookback_minutes: int = 15) -> List[Dict[str, Any]]:
        """Giả lập phản hồi endpoint GET /core/v1/loans/{loan_id}/payments?lookback=X"""
        events = self._payments.get(loan_id, [])
        if not events:
            return []
        cutoff = datetime.now() - timedelta(minutes=lookback_minutes)
        results = []
        for ev in reversed(events):
            ev_time = datetime.fromisoformat(ev["paid_at"])
            if ev_time >= cutoff:
                results.append(ev)
        return results

    def fetch_overdue_portfolio(self, max_dpd: int = 30) -> List[Dict[str, Any]]:
        """Giả lập phản hồi endpoint GET /core/v1/portfolio/delinquent"""
        return list(self._loans.values())

    def fetch_customer_inflows(self, debtor_cif: str, months: int = 3) -> Dict[str, Any]:
        """Giả lập phản hồi endpoint GET /core/v1/customers/{cif}/cashflows"""
        return {
            "status": "SUCCESS",
            "data": {
                "debtor_cif": debtor_cif,
                "verified_inflow_avg_monthly": 28500000.0,
                "casa_balance": 15400000.0,
                "salary_day_of_month": 10,
                "stability_coefficient": 0.88
            }
        }
