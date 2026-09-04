import os
import sys
import pytest

API_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
ADAPTERS_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../integration-adapters/src"))
ML_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../bcollection-data"))
sys.path.insert(0, API_SRC)
sys.path.insert(0, ADAPTERS_SRC)
sys.path.insert(0, ML_SRC)

from scoring_config_loader import ScoringConfigManager, get_scoring_config_manager
from persona_engine import D1AbilityEngine, D2WillingnessEngine, D3ContactabilityEngine
from core_banking.adapter import CustomerInflowProfile
from cic.mock_client import MockCICApiClient
from los.mock_client import MockLOSApiClient
from database import init_db, get_debtor_behavioral_metrics


def test_scoring_config_manager_loads_valid_config():
    mgr = get_scoring_config_manager()
    cfg = mgr.get_config()
    assert "d1_ability" in cfg
    assert "d2_willingness" in cfg
    assert "d3_contactability" in cfg
    assert "ml01_self_cure" in cfg

    # Kiểm tra các trọng số D1
    d1_cfg = mgr.get_d1_config()
    assert d1_cfg["weights"]["dsr"] == 0.35
    assert d1_cfg["dsr_thresholds"]["safe_max"] == 0.35
    assert d1_cfg["dsr_thresholds"]["insolvent_min"] == 0.80


def test_d1_ability_calculation_with_config():
    inflow = CustomerInflowProfile(
        debtor_cif="CIF100001",
        verified_inflow_avg_monthly=20_000_000.0,
        casa_balance=10_000_000.0,
        salary_day_of_month=10,
        stability_coefficient=0.85
    )
    # Nghĩa vụ 5 triệu / 20 triệu = 25% DSR (<= 35% -> S_DSR = 100)
    res = D1AbilityEngine.calculate(
        monthly_obligation=5_000_000.0,
        inflow_profile=inflow,
        cic_score=720,
        worst_group_other_banks=1,
        collateral_ltv=0.45
    )
    assert 10 <= res["value"] <= 98
    assert res["coverage"] == 0.88
    assert len(res["top_drivers"]) > 0


def test_d2_willingness_calculation():
    res = D2WillingnessEngine.calculate(
        dpd=5,
        cif_hash=1234,
        self_cure_propensity=0.85,
        paying_other_banks_while_overdue=False,
        actual_ptp_kept_rate=0.92
    )
    assert 15 <= res["value"] <= 95
    assert res["coverage"] == 0.82


def test_d3_contactability_calculation():
    res = D3ContactabilityEngine.calculate(
        expected_rpc_rate=0.75,
        cif_hash=5678,
        app_logins=12
    )
    assert 20 <= res["value"] <= 95
    assert "12 lần/tháng" in res["top_drivers"][1]


def test_mock_cic_client_distribution():
    client = MockCICApiClient()
    scores = []
    debts = []
    for i in range(1, 20):
        cif = f"CIF{100000 + i * 37}"
        data = client.fetch_credit_score_and_obligations(cif, f"001099{i:06d}")["data"]
        scores.append(data["credit_score"])
        debts.append(data["total_obligation_other_banks"])
        assert 450 <= data["credit_score"] <= 750
        assert data["worst_group_other_banks"] in (1, 2, 3)

    # Đảm bảo phân bổ điểm tín dụng không bị trùng chết một số duy nhất
    assert len(set(scores)) > 5
    assert min(scores) < max(scores)
    assert min(debts) < max(debts)


def test_mock_los_client_collaterals_by_product():
    client = MockLOSApiClient()

    # 1. Mortgage: Có BĐS, LTV 0.40 - 0.75
    mo_collat = client.fetch_collateral_details("LOAN-MO-30005")
    assert len(mo_collat) == 1
    assert mo_collat[0]["collateral_type"] == "REAL_ESTATE"
    assert 0.40 <= mo_collat[0]["ltv_ratio"] <= 0.75

    # 2. Auto loan: Có xe ô tô
    al_collat = client.fetch_collateral_details("LOAN-AL-40012")
    assert len(al_collat) == 1
    assert al_collat[0]["collateral_type"] == "VEHICLE"
    assert 0.55 <= al_collat[0]["ltv_ratio"] <= 0.80

    # 3. SME: Có quyền đòi nợ / thiết bị
    sm_collat = client.fetch_collateral_details("LOAN-SM-50020")
    assert len(sm_collat) == 1
    assert sm_collat[0]["collateral_type"] == "RECEIVABLES_EQUIPMENT"

    # 4. Credit Card / Unsecured: Không có TSBĐ
    cc_collat = client.fetch_collateral_details("LOAN-CC-60030")
    assert len(cc_collat) == 0

    un_collat = client.fetch_collateral_details("LOAN-UN-70040")
    assert len(un_collat) == 0


def test_database_debtor_behavioral_metrics():
    init_db()
    metrics = get_debtor_behavioral_metrics("CIF100001", "CASE-2026-10001")
    assert "historical_on_time_ratio" in metrics
    assert "prior_cure_count" in metrics
    assert "digital_interactions_count" in metrics
    assert "app_logins" in metrics
    assert 0.0 <= metrics["historical_on_time_ratio"] <= 1.0
