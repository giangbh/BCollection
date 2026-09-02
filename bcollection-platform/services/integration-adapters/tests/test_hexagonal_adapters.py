import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from core_banking.adapter import CoreBankingAdapter
from core_banking.mock_client import MockCoreBankingApiClient
from los.adapter import LOSAdapter
from los.mock_client import MockLOSApiClient
from messaging.adapter import MessagingGatewayAdapter
from messaging.mock_client import MockMessagingApiClient
from cic.adapter import CICAdapter
from cic.mock_client import MockCICApiClient

def test_core_banking_adapter_delegates_to_client():
    mock_client = MockCoreBankingApiClient()
    mock_client.set_mock_loan({
        "loan_id": "LOAN-TEST-HEX",
        "debtor_cif": "CIF999",
        "outstanding_principal": 100000000.0,
        "outstanding_interest": 5000000.0,
        "overdue_amount": 5000000.0,
        "dpd": 15,
        "loan_status": "OVERDUE"
    })

    # Adapter được khởi tạo với mock_client (không sửa logic Adapter)
    adapter = CoreBankingAdapter(api_client=mock_client)
    snapshot = adapter.get_realtime_balance("LOAN-TEST-HEX")

    assert snapshot.loan_id == "LOAN-TEST-HEX"
    assert snapshot.debtor_cif == "CIF999"
    assert snapshot.overdue_amount == 5000000.0
    assert snapshot.days_past_due == 15
    assert not snapshot.is_fully_paid

    # Giả lập trả nợ
    mock_client.simulate_incoming_payment("LOAN-TEST-HEX", "CIF999", 5000000.0)
    new_snapshot = adapter.get_realtime_balance("LOAN-TEST-HEX")
    assert new_snapshot.is_fully_paid
    assert new_snapshot.overdue_amount == 0.0

    # Kiểm tra sự kiện thanh toán
    payment_ev = adapter.check_recent_payment("LOAN-TEST-HEX", lookback_minutes=15)
    assert payment_ev is not None
    assert payment_ev.amount_paid == 5000000.0

def test_los_adapter_delegates_to_client():
    mock_los_client = MockLOSApiClient()
    mock_los_client.add_mock_party_obligation("LOAN-TEST-HEX", {
        "loan_id": "LOAN-TEST-HEX",
        "party_id": "CIF-GUARANTOR-99",
        "party_name": "NGUYỄN VĂN BẢO LÃNH",
        "party_type": "PERSON",
        "edge_type": "GUARANTEES",
        "contact_eligible": "YES",
        "phone_e164": "+84912999888",
        "source_system": "LOS"
    })

    adapter = LOSAdapter(api_client=mock_los_client)
    parties = adapter.get_loan_party_obligations("LOAN-TEST-HEX")

    assert len(parties) >= 1
    guarantor = [p for p in parties if p.party_id == "CIF-GUARANTOR-99"][0]
    assert guarantor.edge_type == "GUARANTEES"
    assert guarantor.contact_eligible == "YES"

def test_messaging_gateway_adapter_enforces_token_and_delegates():
    mock_msg_client = MockMessagingApiClient()
    adapter = MessagingGatewayAdapter(api_client=mock_msg_client)

    # 1. Chặn nếu thiếu Guardrail Token
    with pytest.raises(ValueError, match="LỖI PHÁP CHẾ L6"):
        adapter.send_sms_notification(
            phone_e164="+84912345678",
            message="Nhac no",
            guardrail_token=""
        )

    # 2. Thành công nếu có Guardrail Token hợp lệ
    res = adapter.send_sms_notification(
        phone_e164="+84912345678",
        message="BIDV tran trong thong bao",
        guardrail_token="eyJhbGciOiJFUzI1NiJ9.test"
    )
    assert res["status"] == "SUCCESS"
    assert len(mock_msg_client.sent_messages) == 1
    assert mock_msg_client.sent_messages[0]["channel"] == "SMS"

def test_cic_adapter_delegates_to_client():
    mock_cic_client = MockCICApiClient()
    adapter = CICAdapter(api_client=mock_cic_client)

    report = adapter.get_credit_report(debtor_cif="CIF100001", national_id="001099012345")
    assert report.debtor_cif == "CIF100001"
    assert report.credit_score == 620
    assert report.worst_group_other_banks in (1, 2)
