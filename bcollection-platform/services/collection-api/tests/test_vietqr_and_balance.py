import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../integration-adapters/src')))

from vietqr_service import VietQRService
from core_banking_adapter import MockCoreBankingAdapter
from los_adapter import MockLOSAdapter, PartyObligationDTO
from balance_check_service import RealTimeBalanceCheckService

def test_vietqr_generation():
    qr_svc = VietQRService()
    res = qr_svc.generate_payment_link(loan_id="LOAN-123456", debtor_cif="CIF-888999", amount=3500000)
    
    assert res["bank_bin"] == "970418"
    assert res["amount"] == 3500000
    assert res["short_url"].startswith("https://bidv.vn/c/")
    assert len(res["token"]) == 8
    assert "TT DUP LOAN-123456" in res["transfer_content"]

def test_balance_check_allows_when_overdue():
    mock_core = MockCoreBankingAdapter()
    mock_core.set_mock_balance(loan_id="LOAN-ACTIVE-1", debtor_cif="CIF-1", overdue_amount=4200000, dpd=10)
    
    check_svc = RealTimeBalanceCheckService(mock_core)
    res = check_svc.verify_action_eligibility(loan_id="LOAN-ACTIVE-1", debtor_cif="CIF-1")
    
    assert res["can_proceed"] is True
    assert res["reason"] == "OVERDUE_CONFIRMED"

def test_balance_check_blocks_when_recently_paid():
    mock_core = MockCoreBankingAdapter()
    mock_core.set_mock_balance(loan_id="LOAN-PAID-1", debtor_cif="CIF-2", overdue_amount=5000000, dpd=12)
    
    # Khách hàng vừa thanh toán qua VietQR
    mock_core.simulate_payment(loan_id="LOAN-PAID-1", debtor_cif="CIF-2", amount=5000000, channel="VIETQR")
    
    check_svc = RealTimeBalanceCheckService(mock_core)
    res = check_svc.verify_action_eligibility(loan_id="LOAN-PAID-1", debtor_cif="CIF-2")
    
    # Phải tự động CHẶN hành động đòi nợ
    assert res["can_proceed"] is False
    assert res["reason"] == "PAYMENT_RECENTLY_DETECTED"
    assert "vừa thanh toán" in res["message"]

def test_los_adapter_mock():
    los = MockLOSAdapter()
    obligations = los.get_loan_party_obligations("LOAN-001")
    assert len(obligations) >= 1
    assert obligations[0].edge_type == "BORROWED"
    assert obligations[0].contact_eligible == "YES"
