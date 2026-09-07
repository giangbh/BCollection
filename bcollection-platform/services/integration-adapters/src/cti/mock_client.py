import time
from typing import Dict, Any, Optional
from .client import CTIApiClient


class MockCTIApiClient(CTIApiClient):
    """
    Mock In-Memory Client cho Tổng đài CTI phục vụ Unit Test và môi trường phát triển cục bộ.
    """

    def __init__(self):
        self._active_calls: Dict[str, Dict[str, Any]] = {}
        self._counter = 1000

    def originate_call(
        self,
        agent_id: str,
        agent_extension: str,
        destination_phone: str,
        case_id: str,
        guardrail_token: str
    ) -> Dict[str, Any]:
        self._counter += 1
        call_id = f"CALL-MOCK-{self._counter}"
        record = {
            "call_id": call_id,
            "agent_id": agent_id,
            "agent_extension": agent_extension,
            "destination_phone": destination_phone,
            "case_id": case_id,
            "guardrail_token": guardrail_token,
            "status": "ANSWERED",
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "recording_url": f"https://mock-storage.bank.vn/recordings/{call_id}.wav",
            "gateway": "MOCK_FREESWITCH"
        }
        self._active_calls[call_id] = record
        return record

    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        call = self._active_calls.get(call_id)
        if not call:
            return {"call_id": call_id, "status": "NOT_FOUND"}
        return call

    def hangup_call(self, call_id: str) -> Dict[str, Any]:
        call = self._active_calls.get(call_id)
        if not call:
            return {"call_id": call_id, "status": "NOT_FOUND"}
        call["status"] = "HUNGUP"
        call["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        call["duration_seconds"] = 45
        return call
