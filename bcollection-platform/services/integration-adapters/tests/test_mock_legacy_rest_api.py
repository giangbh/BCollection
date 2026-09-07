import os
import sys
import pytest
from starlette.testclient import TestClient

# Thêm đường dẫn src vào sys.path
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src'))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mock_legacy_server import app as legacy_app
from cti.adapter import CTITelephonyAdapter
from cti.mock_client import MockCTIApiClient
from speech_ai.adapter import SpeechAIAdapter
from speech_ai.mock_client import MockSpeechAIApiClient
from core_banking.adapter import CoreBankingAdapter
from core_banking.mock_client import MockCoreBankingApiClient


@pytest.fixture
def client():
    return TestClient(legacy_app)


def test_mock_legacy_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "HEALTHY"
    assert res.json()["service"] == "bcollection-mock-legacy-server"


def test_core_banking_rest_endpoints(client):
    loan_id = "LOAN-UN-20001"
    # 1. Tra cứu số dư
    bal_res = client.get(f"/legacy/core/v1/loans/{loan_id}/balance")
    assert bal_res.status_code == 200
    data = bal_res.json()
    assert data["loan_id"] == loan_id
    assert "outstanding_principal" in data
    assert "overdue_amount" in data
    assert data["source_version"] >= 1

    # 2. Tra cứu dòng tiền CASA / Inflow
    cif = data.get("debtor_cif", "CIF100001")
    flow_res = client.get(f"/legacy/core/v1/customers/{cif}/cashflows")
    assert flow_res.status_code == 200
    flow = flow_res.json()
    assert flow["debtor_cif"] == cif
    assert flow["verified_inflow_avg_monthly"] > 0
    assert flow["inflow_archetype"] == "PAYROLL_INTERNAL"

    # 3. Mô phỏng thanh toán tức thời (Anti-wrongful collection)
    pay_res = client.post("/legacy/core/v1/simulate/payment", json={
        "loan_id": loan_id,
        "debtor_cif": cif,
        "amount_paid": float(data["overdue_amount"]),
        "channel": "VIETQR"
    })
    assert pay_res.status_code == 200
    assert pay_res.json()["status"] == "SUCCESS"

    # 4. Kiểm tra số dư sau khi thanh toán đã về 0
    updated_bal = client.get(f"/legacy/core/v1/loans/{loan_id}/balance").json()
    assert updated_bal["overdue_amount"] == 0.0
    assert updated_bal["loan_status"] == "ACTIVE"

    # 5. Tra cứu thanh toán trong 15 phút gần nhất
    recent_res = client.get(f"/legacy/core/v1/loans/{loan_id}/payments?lookback_minutes=15")
    assert recent_res.status_code == 200
    assert len(recent_res.json()["payments"]) >= 1
    assert recent_res.json()["payments"][-1]["amount_paid"] == float(data["overdue_amount"])


def test_los_rest_endpoints(client):
    loan_id = "LOAN-UN-20001"
    # Tra cứu các bên có nghĩa vụ
    party_res = client.get(f"/legacy/los/v1/loans/{loan_id}/parties")
    assert party_res.status_code == 200
    parties = party_res.json()["parties"]
    assert len(parties) >= 1
    assert any(p["edge_type"] == "BORROWED" for p in parties)

    # Tra cứu tài sản thế chấp
    collat_res = client.get(f"/legacy/los/v1/loans/{loan_id}/collaterals")
    assert collat_res.status_code == 200
    assert "collaterals" in collat_res.json()


def test_cic_rest_endpoints(client):
    res = client.get("/legacy/cic/v1/reports?cif=CIF100001&national_id=001090012345")
    assert res.status_code == 200
    report = res.json()
    assert report["debtor_cif"] == "CIF100001"
    assert report["credit_score"] >= 300
    assert 1 <= report["worst_group_other_banks"] <= 5


def test_cti_rest_endpoints(client):
    # 1. Khởi tạo cuộc gọi
    orig_res = client.post("/legacy/cti/v1/calls/originate", json={
        "agent_id": "COLLECTOR_01",
        "agent_extension": "1001",
        "destination_phone": "+84946913810",
        "case_id": "CASE-2026-10001",
        "guardrail_token": "eyJhbGciOi..."
    })
    assert orig_res.status_code == 200
    call_id = orig_res.json()["call_id"]
    assert orig_res.json()["status"] == "ANSWERED"

    # 2. Tra cứu trạng thái
    status_res = client.get(f"/legacy/cti/v1/calls/{call_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["call_id"] == call_id

    # 3. Kết thúc cuộc gọi
    hangup_res = client.post(f"/legacy/cti/v1/calls/{call_id}/hangup")
    assert hangup_res.status_code == 200
    assert hangup_res.json()["status"] == "HUNGUP"


def test_speech_ai_rest_endpoints(client):
    res = client.post("/legacy/speech-ai/v1/analyze-call", json={
        "case_id": "CASE-2026-10001",
        "call_duration_seconds": 45
    })
    assert res.status_code == 200
    data = res.json()
    assert len(data["transcript"]) >= 2
    assert data["extracted_outcome"] in ("PTP_AGREED", "REFUSED")
    assert "sentiment" in data
    assert data["compliance_audit"]["status"] == "PASSED"


def test_messaging_rest_endpoints(client):
    sms_res = client.post("/legacy/messaging/v1/sms/send", json={
        "phone_e164": "+84946913810",
        "message": "Nop tien nhanh tai vietqr.bank.vn",
        "brandname": "BANK"
    })
    assert sms_res.status_code == 200
    assert sms_res.json()["status"] == "SENT"

    zns_res = client.post("/legacy/messaging/v1/zns/send", json={
        "phone_e164": "+84946913810",
        "template_id": "ZNS_VIETQR",
        "template_data": {"amount": 3330000}
    })
    assert zns_res.status_code == 200
    assert zns_res.json()["status"] == "SENT"


def test_cti_telephony_adapter_guardrail_check():
    mock_client = MockCTIApiClient()
    adapter = CTITelephonyAdapter(api_client=mock_client)

    # 1. Chặn khi không có token hợp lệ
    with pytest.raises(ValueError, match="Không có Guardrail Token hợp lệ"):
        adapter.originate_call("AG01", "1001", "+84946913810", "CASE-01", "")

    # 2. Thành công khi có token hợp lệ
    session = adapter.originate_call("AG01", "1001", "+84946913810", "CASE-01", "eyJhbGciOi...")
    assert session.status == "ANSWERED"
    assert session.destination_phone == "+84946913810"

    # 3. Tra cứu và gác máy
    st = adapter.get_call_status(session.call_id)
    assert st["status"] == "ANSWERED"
    hungup = adapter.hangup_call(session.call_id)
    assert hungup["status"] == "HUNGUP"


def test_speech_ai_adapter_logic():
    mock_client = MockSpeechAIApiClient()
    adapter = SpeechAIAdapter(api_client=mock_client)

    result = adapter.analyze_call("CASE-2026-10001", call_duration_seconds=50, context={
        "dpd": 5, "full_name": "NGUYỄN VĂN A", "loan_id": "L1", "overdue_amount": 2000000
    })
    assert result.extracted_outcome == "PTP_AGREED"
    assert result.extracted_ptp_amount == 2000000
    assert result.sentiment["label"] == "TÍCH CỰC"
    assert result.compliance_audit["status"] == "PASSED"
