from typing import Dict, Any, Optional
from datetime import datetime
import sys
import os

# Thêm đường dẫn libs vào path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../libs')))

from bc_domain.enums import CaseStatus, ChannelType, ExperimentArm
from bc_domain.models import CollectionCase


class CaseWorkflowStateMachine:
    """
    Quản lý chuyển đổi trạng thái của Collection Case theo quy chuẩn nghiệp vụ Ngân hàng.
    """
    VALID_TRANSITIONS = {
        CaseStatus.CREATED: [CaseStatus.ASSIGNED, CaseStatus.IN_TREATMENT, CaseStatus.RESOLVED_CURED],
        CaseStatus.ASSIGNED: [CaseStatus.IN_TREATMENT, CaseStatus.RESOLVED_CURED],
        CaseStatus.IN_TREATMENT: [CaseStatus.PTP_SCHEDULED, CaseStatus.RESTRUCTURE_PENDING, CaseStatus.LEGAL_ESCALATED, CaseStatus.RESOLVED_CURED],
        CaseStatus.PTP_SCHEDULED: [CaseStatus.PTP_KEPT, CaseStatus.PTP_BROKEN, CaseStatus.RESOLVED_CURED],
        CaseStatus.PTP_KEPT: [CaseStatus.RESOLVED_CURED, CaseStatus.CLOSED],
        CaseStatus.PTP_BROKEN: [CaseStatus.IN_TREATMENT, CaseStatus.LEGAL_ESCALATED],
        CaseStatus.RESTRUCTURE_PENDING: [CaseStatus.RESTRUCTURE_APPROVED, CaseStatus.IN_TREATMENT],
        CaseStatus.RESTRUCTURE_APPROVED: [CaseStatus.RESOLVED_CURED, CaseStatus.IN_TREATMENT],
        CaseStatus.LEGAL_ESCALATED: [CaseStatus.SETTLED_WRITEOFF, CaseStatus.CLOSED, CaseStatus.RESOLVED_CURED],
        CaseStatus.RESOLVED_CURED: [CaseStatus.CLOSED],
        CaseStatus.SETTLED_WRITEOFF: [CaseStatus.CLOSED],
        CaseStatus.CLOSED: []
    }

    @classmethod
    def can_transition(cls, from_status: CaseStatus, to_status: CaseStatus) -> bool:
        allowed = cls.VALID_TRANSITIONS.get(from_status, [])
        return to_status in allowed

    @classmethod
    def transition(cls, case: CollectionCase, new_status: CaseStatus, context: Optional[Dict[str, Any]] = None) -> CollectionCase:
        raise ValueError("Direct workflow mutation retired in PR-02; use CaseService.execute with versioned financial evidence")
