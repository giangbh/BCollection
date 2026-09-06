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

    assert CaseWorkflowStateMachine.can_transition(CaseStatus.CREATED, CaseStatus.IN_TREATMENT)
    with pytest.raises(ValueError, match="CaseService"):
        CaseWorkflowStateMachine.transition(case, CaseStatus.IN_TREATMENT)
    assert case.status == CaseStatus.CREATED

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
