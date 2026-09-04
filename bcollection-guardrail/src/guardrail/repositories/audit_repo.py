import hashlib
import json
import time
import threading
from typing import Dict, Any, List

class AuditRecord:
    def __init__(self, audit_id: str, timestamp: float, request_payload: Dict[str, Any], decision: str, prev_hash: str):
        self.audit_id = audit_id
        self.timestamp = timestamp
        self.request_payload = request_payload
        self.decision = decision
        self.prev_hash = prev_hash
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload_str = json.dumps(self.request_payload, sort_keys=True, default=str)
        raw = f"{self.audit_id}:{self.timestamp}:{self.decision}:{self.prev_hash}:{payload_str}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp,
            "decision": self.decision,
            "prev_hash": self.prev_hash,
            "hash": self.hash
        }


class HashChainAuditRepository:
    """Sổ cái Audit bất biến theo chuỗi Hash (Hash-Chain Immutable Ledger - Thread-Safe)"""
    def __init__(self):
        self._records: List[AuditRecord] = []
        self._last_hash: str = "GENESIS_HASH_BCOLLECTION_2026"
        self._lock = threading.Lock()

    def record_decision(self, request_id: str, request_payload: Dict[str, Any], decision: str) -> AuditRecord:
        with self._lock:
            record = AuditRecord(
                audit_id=f"AUDIT-{request_id}",
                timestamp=time.time(),
                request_payload=request_payload,
                decision=decision,
                prev_hash=self._last_hash
            )
            self._records.append(record)
            self._last_hash = record.hash
            return record

    def verify_integrity(self) -> bool:
        """Kiểm tra tính toàn vẹn của toàn bộ sổ cái Audit"""
        current_prev = "GENESIS_HASH_BCOLLECTION_2026"
        for rec in self._records:
            if rec.prev_hash != current_prev:
                return False
            if rec.hash != rec._compute_hash():
                return False
            current_prev = rec.hash
        return True

    def get_latest_hash(self) -> str:
        return self._last_hash

    def count(self) -> int:
        return len(self._records)
