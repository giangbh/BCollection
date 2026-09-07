import os
import sys
import pytest
from starlette.testclient import TestClient

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src'))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from legacy_servers.gateway import app as gateway_app
from legacy_servers.core_server import app as core_app
from legacy_servers.los_server import app as los_app
from legacy_servers.cic_server import app as cic_app
from legacy_servers.cti_server import app as cti_app
from legacy_servers.speech_server import app as speech_app
from legacy_servers.messaging_server import app as messaging_app
from legacy_servers.generators import (
    generate_core_loan_balance, generate_core_cashflow,
    generate_los_parties, generate_cic_report, generate_speech_ai_analysis
)


@pytest.fixture
def gateway_client():
    return TestClient(gateway_app)


@pytest.fixture
def core_client():
    return TestClient(core_app)


@pytest.fixture
def los_client():
    return TestClient(los_app)


@pytest.fixture
def cic_client():
    return TestClient(cic_app)


@pytest.fixture
def cti_client():
    return TestClient(cti_app)


@pytest.fixture
def speech_client():
    return TestClient(speech_app)


@pytest.fixture
def messaging_client():
    return TestClient(messaging_app)


# ---------------------------------------------------------------------------
# 1. KIỂM THỬ API GATEWAY (PORT 8090) ĐIỀU HƯỚNG CẢ 6 HỆ THỐNG
# ---------------------------------------------------------------------------

def test_gateway_health_and_routing_map(gateway_client):
    res = gateway_client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert data["service"] == "legacy-api-gateway"
    assert "core_banking" in data["routed_services"]
    assert "speech_ai" in data["routed_services"]


def test_gateway_routes_to_core_banking(gateway_client):
    res = gateway_client.get("/legacy/core/v1/loans/LOAN-UN-20001/balance")
    assert res.status_code == 200
    data = res.json()
    assert data["loan_id"] == "LOAN-UN-20001"
    assert data["debtor_cif"] == "CIF100001"
    assert data["overdue_amount"] == 3330000.0


def test_gateway_routes_to_los(gateway_client):
    res = gateway_client.get("/legacy/los/v1/loans/LOAN-UN-20001/parties")
    assert res.status_code == 200
    parties = res.json()["parties"]
    assert len(parties) >= 2
    assert parties[0]["relationship"] == "CHÍNH CHỦ"


def test_gateway_routes_to_cic(gateway_client):
    res = gateway_client.get("/legacy/cic/v1/reports?cif=CIF100001")
    assert res.status_code == 200
    report = res.json()
    assert report["debtor_cif"] == "CIF100001"
    assert report["credit_score"] >= 400


def test_gateway_routes_to_cti(gateway_client):
    res = gateway_client.post("/legacy/cti/v1/calls/originate", json={
        "agent_id": "COLLECTOR_01",
        "agent_extension": "1001",
        "destination_phone": "+84946913810",
        "case_id": "CASE-2026-10001",
        "guardrail_token": "eyJhbGciOi..."
    })
    assert res.status_code == 200
    assert res.json()["status"] == "ANSWERED"
    assert res.json()["gateway"] == "FREESWITCH"


def test_gateway_routes_to_speech_ai(gateway_client):
    res = gateway_client.post("/legacy/speech-ai/v1/analyze-call", json={
        "case_id": "CASE-2026-10001",
        "call_duration_seconds": 45
    })
    assert res.status_code == 200
    data = res.json()
    assert data["detected_root_cause"] == "CASHFLOW_TIMING"
    assert data["extracted_outcome"] == "PTP_AGREED"


def test_gateway_routes_to_messaging(gateway_client):
    res = gateway_client.post("/legacy/messaging/v1/sms/send", json={
        "phone_e164": "+84946913810",
        "message": "Nop tien nhanh tai VietQR",
        "brandname": "BIDV"
    })
    assert res.status_code == 200
    assert res.json()["status"] == "SENT"


# ---------------------------------------------------------------------------
# 2. KIỂM THỬ TRỰC TIẾP TỪNG MICROSERVICE ĐỘC LẬP
# ---------------------------------------------------------------------------

def test_core_server_direct_and_simulate_payment(core_client):
    loan_id = "LOAN-UN-20001"
    # Giả lập thanh toán tức thời
    pay_res = core_client.post("/api/core/v1/simulate/payment", json={
        "loan_id": loan_id,
        "debtor_cif": "CIF100001",
        "amount_paid": 3330000,
        "channel": "VIETQR"
    })
    assert pay_res.status_code == 200
    assert pay_res.json()["status"] == "SUCCESS"

    # Kiểm tra số dư về 0
    bal = core_client.get(f"/api/core/v1/loans/{loan_id}/balance").json()
    assert bal["overdue_amount"] == 0.0
    assert bal["loan_status"] == "ACTIVE"


def test_los_server_direct(los_client):
    res = los_client.get("/api/los/v1/loans/LOAN-UN-20001/collaterals")
    assert res.status_code == 200
    assert "collaterals" in res.json()


def test_cic_server_direct(cic_client):
    res = cic_client.get("/api/cic/v1/reports?cif=CIF100002")
    assert res.status_code == 200
    assert res.json()["debtor_cif"] == "CIF100002"


def test_cti_server_guardrail_blocking(cti_client):
    # Chặn nếu không có Guardrail token
    res = cti_client.post("/api/cti/v1/calls/originate", json={
        "agent_id": "AG01",
        "agent_extension": "101",
        "destination_phone": "+84946913810",
        "case_id": "CASE-2026-10001",
        "guardrail_token": ""
    })
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# 3. KIỂM THỬ TÍNH ĐỘNG VÀ NGỮ CẢNH (DYNAMIC CONTEXTUAL RESPONSES)
# ---------------------------------------------------------------------------

def test_dynamic_generator_diversity():
    # 1. So sánh 2 khách hàng khác nhau: CIF100001 (Bùi Thị Hải) vs CIF100002
    cf1 = generate_core_cashflow("CIF100001")
    cf2 = generate_core_cashflow("CIF100002")
    assert cf1["debtor_cif"] != cf2["debtor_cif"]
    assert cf1["casa_account_no"] != cf2["casa_account_no"]

    # 2. Kiểm tra tính nhất quán (deterministic): Cùng 1 CIF sinh ra dữ liệu giống nhau
    cf1_repeat = generate_core_cashflow("CIF100001")
    assert cf1["verified_inflow_avg_monthly"] == cf1_repeat["verified_inflow_avg_monthly"]
    assert cf1["casa_account_no"] == cf1_repeat["casa_account_no"]

    # 3. So sánh 2 khoản nợ khác nhau: LOAN-UN-20001 vs LOAN-SE-20002
    p1 = generate_los_parties("LOAN-UN-20001")
    p2 = generate_los_parties("LOAN-SE-20002")
    assert p1[0]["party_name"] != p2[0]["party_name"]
    assert p1[0]["national_id"] != p2[0]["national_id"]

    # 4. Kiểm tra kịch bản hội thoại Speech AI đa dạng
    speech1 = generate_speech_ai_analysis("CASE-2026-10001") # DPD 8 -> CASHFLOW_TIMING
    assert speech1["detected_root_cause"] in ("CASHFLOW_TIMING", "FORGETFULNESS")
    assert speech1["extracted_outcome"] == "PTP_AGREED"
    assert len(speech1["transcript"]) >= 2
