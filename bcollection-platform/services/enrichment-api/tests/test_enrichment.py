import pytest
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from service import ManualEnrichmentService, EnrichmentFact

def test_add_fact_and_confidence_decay():
    svc = ManualEnrichmentService()
    fact = svc.add_fact(
        debtor_cif="CIF_1001",
        case_id="CASE_1001",
        fact_type="CONTACT_WINDOW",
        payload={"window": "18:00-21:00"},
        collected_by="STAFF_001",
        initial_confidence=4.0
    )

    assert fact.fact_id.startswith("EF-")
    assert fact.state == "PUBLISHED"

    # Sau 120 ngày (1 half-life của CONTACT_WINDOW), confidence phải giảm về 50% (4.0 -> 2.0)
    future_time = fact.collected_at + timedelta(days=120)
    eff_conf = svc.calculate_effective_confidence(fact, as_of=future_time)
    assert eff_conf == 2.0

def test_prohibited_content_blocked():
    svc = ManualEnrichmentService()
    with pytest.raises(ValueError) as exc:
        svc.add_fact(
            debtor_cif="CIF_1002",
            case_id="CASE_1002",
            fact_type="ROOT_CAUSE",
            payload={"note": "Khách hàng nói sẽ đe dọa con cái"}, # Chứa từ bị cấm
            collected_by="STAFF_001"
        )
    assert "từ ngữ bị cấm" in str(exc.value)
