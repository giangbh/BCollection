import hashlib
from typing import Dict, Any

class HoldoutManager:
    """
    Quản lý phân bổ ngẫu nhiên có kiểm soát (Deterministic Hashing with Salt).
    Đảm bảo 10% khách hàng cố định thuộc nhóm Control (Holdout) và 90% thuộc nhóm Treated.
    """
    def __init__(self, experiment_id: str = "EXP_B1_2026_Q4", salt: str = "BIDV_BCOLLECTION_SALT_v1", control_pct: int = 10):
        self.experiment_id = experiment_id
        self.salt = salt
        self.control_pct = control_pct

    def assign_arm(self, debtor_cif: str) -> str:
        """
        Băm CIF để trả về cố định 'CONTROL' hoặc 'TREATED'.
        """
        if not debtor_cif:
            return "CONTROL"
            
        payload = f"{debtor_cif.strip()}:{self.experiment_id}:{self.salt}".encode('utf-8')
        hash_val = int(hashlib.md5(payload).hexdigest(), 16)
        bucket = hash_val % 100  # 0 đến 99
        
        if bucket < self.control_pct:
            return "CONTROL"
        return "TREATED"

    def is_holdout(self, debtor_cif: str) -> bool:
        return self.assign_arm(debtor_cif) == "CONTROL"
