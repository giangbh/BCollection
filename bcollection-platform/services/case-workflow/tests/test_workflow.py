import pytest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../libs')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from bc_domain.enums import CaseStatus, ExperimentArm
from bc_domain.models import CollectionCase
from workflow import CaseWorkflowStateMachine

def test_valid_case_transitions():
    case = CollectionCase(
        case_id="CASE-001",
        loan_id="LOAN-001",
        debtor_cif="CIF-001",
        product_code="UNSECURED_LOAN",
        dpd=12,
        outstanding_principal=20000000,
        outstanding_interest=400000,
        overdue_amount=2400000,
        status=CaseStatus.CREATED
    )

    # CREATED -> IN_TREATMENT
    CaseWorkflowStateMachine.transition(case, CaseStatus.IN_TREATMENT)
    assert case.status == CaseStatus.IN_TREATMENT

    # IN_TREATMENT -> PTP_SCHEDULED
    CaseWorkflowStateMachine.transition(case, CaseStatus.PTP_SCHEDULED, {"ptp_amount": 2400000, "ptp_date": datetime(2026, 9, 10)})
    assert case.status == CaseStatus.PTP_SCHEDULED
    assert case.ptp_amount == 2400000

    # PTP_SCHEDULED -> PTP_KEPT
    CaseWorkflowStateMachine.transition(case, CaseStatus.PTP_KEPT)
    assert case.status == CaseStatus.PTP_KEPT

    # PTP_KEPT -> RESOLVED_CURED
    CaseWorkflowStateMachine.transition(case, CaseStatus.RESOLVED_CURED, {"recovery_amount": 2400000})
    assert case.status == CaseStatus.RESOLVED_CURED
    assert case.cure_flag is True

def test_invalid_case_transition_raises_error():
    case = CollectionCase(
        case_id="CASE-002",
        loan_id="LOAN-002",
        debtor_cif="CIF-002",
        product_code="CREDIT_CARD",
        dpd=5,
        outstanding_principal=10000000,
        outstanding_interest=200000,
        overdue_amount=10200000,
        status=CaseStatus.CREATED
    )

    # Không được nhảy cóc từ CREATED sang PTP_KEPT
    with pytest.raises(ValueError):
        CaseWorkflowStateMachine.transition(case, CaseStatus.PTP_KEPT)
