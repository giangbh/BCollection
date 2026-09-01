import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../bcollection-guardrail')))

from base import MockSMSChannelAdapter, MockZNSChannelAdapter
from src.guardrail.api.token import generate_guardrail_token

def test_sms_adapter_success_with_valid_token():
    adapter = MockSMSChannelAdapter()
    token = generate_guardrail_token(
        request_id="REQ-SMS-001",
        loan_id="LOAN-001",
        target_party_id="CIF-001",
        channel="SMS"
    )

    res = adapter.send_message({
        "guardrail_token": token,
        "recipient_phone_e164": "+84912345678",
        "template_id": "SMS_B1_STD"
    })

    assert res["status"] == "SENT"
    assert res["channel"] == "SMS"

def test_sms_adapter_rejects_missing_token():
    adapter = MockSMSChannelAdapter()
    with pytest.raises(PermissionError) as exc:
        adapter.send_message({
            "recipient_phone_e164": "+84912345678"
        })
    assert "Thiếu Guardrail Token" in str(exc.value)

def test_sms_adapter_rejects_wrong_channel_token():
    adapter = MockSMSChannelAdapter()
    # Token cấp cho VOICE nhưng cố tình dùng để gửi SMS
    token = generate_guardrail_token(
        request_id="REQ-VOICE-001",
        loan_id="LOAN-001",
        target_party_id="CIF-001",
        channel="VOICE"
    )

    with pytest.raises(PermissionError) as exc:
        adapter.send_message({
            "guardrail_token": token,
            "recipient_phone_e164": "+84912345678"
        })
    assert "không thể dùng cho SMS" in str(exc.value)
