from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from bc_domain.case_rules import vnd
from .client import CoreBankingApiClient

class MockCoreBankingApiClient(CoreBankingApiClient):
    """
    Mock Service giả lập Backend API của Core Banking (SIBS / B-Connect ESB).
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
        amount = vnd(amount)
        if not amount or loan_id not in self._loans or self._loans[loan_id]["debtor_cif"] != debtor_cif:
            raise ValueError("Known loan, matching CIF and positive payment required")
        loan = self._loans[loan_id]
        loan["overdue_amount"] = max(0, loan["overdue_amount"] - amount)
        paid_interest = min(loan["outstanding_interest"], amount)
        loan["outstanding_interest"] -= paid_interest
        loan["outstanding_principal"] = max(0, loan["outstanding_principal"] - (amount - paid_interest))
        if loan["overdue_amount"] == 0:
            loan["dpd"] = 0
            loan["loan_status"] = "ACTIVE"

        payment_record = {
            "event_id": f"PAY-{uuid4()}",
            "loan_id": loan_id,
            "debtor_cif": debtor_cif,
            "amount_paid": amount,
            "paid_at": datetime.now(timezone.utc).isoformat(),
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
            l["source_version"] = l.get("source_version", 0) + 1
            return {
                "status": "SUCCESS",
                "data": {
                    "loan_id": loan_id,
                    "debtor_cif": l["debtor_cif"],
                    "outstanding_principal": l["outstanding_principal"],
                    "outstanding_interest": l["outstanding_interest"],
                    "overdue_amount": l["overdue_amount"],
                    "dpd": l["dpd"],
                    "is_fully_paid": (l["outstanding_principal"] + l["outstanding_interest"] == 0),
                    "as_of": datetime.now(timezone.utc).isoformat(),
                    "source_version": l["source_version"],
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
                "as_of": datetime.now(timezone.utc).isoformat(),
                "source_version": 0,
            }
        }

    def fetch_recent_payments(self, loan_id: str, lookback_minutes: int = 15) -> List[Dict[str, Any]]:
        """Giả lập phản hồi endpoint GET /core/v1/loans/{loan_id}/payments?lookback=X"""
        events = self._payments.get(loan_id, [])
        if not events:
            return []
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
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
        """
        Giả lập phản hồi endpoint GET /core/v1/customers/{cif}/cashflows.
        Phân loại thực tế theo 4 nhóm đối tượng:
        1. PAYROLL_INTERNAL (40%): Chi lương qua BIDV
        2. MERCHANT_BUSINESS (30%): Hộ kinh doanh/tiểu thương (dòng tiền VietQR/POS hàng ngày, CASA đệm cao)
        3. NON_PAYROLL_SALARIED (20%): Nhận lương ngân hàng khác (Vietcombank, Techcombank...)
        4. GIG_FREELANCE (10%): Lao động tự do, thu nhập không định kỳ
        """
        cif_hash = sum(ord(c) for c in debtor_cif)
        bucket = cif_hash % 10

        if bucket < 4:
            # Nhóm 1: Chi lương qua BIDV
            has_payroll = True
            archetype = "PAYROLL_INTERNAL"
            bank_name = "BIDV"
            salary_day = 5 + (cif_hash % 6)  # ngày 5 đến ngày 10
            inferred_day = salary_day
            inflow_avg = 22_000_000.0 + (cif_hash % 10) * 1_500_000.0
            casa = 4_500_000.0 + (cif_hash % 8) * 1_000_000.0
            buffer_ratio = round(casa / 5_000_000.0, 2)
            stability = 0.90
        elif bucket < 7:
            # Nhóm 2: Hộ kinh doanh / Tiểu thương
            has_payroll = False
            archetype = "MERCHANT_BUSINESS"
            bank_name = "NONE_MERCHANT"
            salary_day = 0  # Không có ngày lương
            inferred_day = 15  # Chu kỳ chốt sổ giữa tháng
            inflow_avg = 45_000_000.0 + (cif_hash % 15) * 3_000_000.0
            casa = 14_000_000.0 + (cif_hash % 20) * 1_500_000.0
            buffer_ratio = round(casa / 5_000_000.0, 2)  # Đệm thường > 2.5x
            stability = 0.75
        elif bucket < 9:
            # Nhóm 3: Nhận lương ngân hàng khác
            has_payroll = False
            archetype = "NON_PAYROLL_SALARIED"
            bank_name = "VIETCOMBANK" if (cif_hash % 2 == 0) else "TECHCOMBANK"
            salary_day = 0
            inferred_day = 10 + (cif_hash % 5)  # Suy luận từ LOS/sao kê thẩm định
            inflow_avg = 25_000_000.0 + (cif_hash % 8) * 2_000_000.0
            casa = 3_000_000.0 + (cif_hash % 6) * 1_000_000.0
            buffer_ratio = round(casa / 5_000_000.0, 2)
            stability = 0.85
        else:
            # Nhóm 4: Lao động tự do
            has_payroll = False
            archetype = "GIG_FREELANCE"
            bank_name = "FREELANCE"
            salary_day = 0
            inferred_day = None
            inflow_avg = 18_000_000.0 + (cif_hash % 6) * 1_000_000.0
            casa = 2_000_000.0 + (cif_hash % 4) * 800_000.0
            buffer_ratio = round(casa / 5_000_000.0, 2)
            stability = 0.60

        return {
            "status": "SUCCESS",
            "data": {
                "debtor_cif": debtor_cif,
                "verified_inflow_avg_monthly": inflow_avg,
                "casa_balance": casa,
                "salary_day_of_month": salary_day,
                "stability_coefficient": stability,
                "has_payroll_relationship": has_payroll,
                "inflow_archetype": archetype,
                "casa_buffer_ratio": buffer_ratio,
                "inferred_pay_day_of_month": inferred_day,
                "payroll_bank_name": bank_name
            }
        }
