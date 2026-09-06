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
    assert metrics["historical_on_time_ratio"] is None
    assert metrics["ptp_kept_rate"] is None


def test_d1_living_wage_floor_penalty_and_relative_cushion():
    # Case A: Thu nhập thấp 8 triệu, trả nợ 4 triệu (DSR 50%). Tiền còn lại 4 triệu < 5.5 triệu mức sống tối thiểu
    low_inflow = CustomerInflowProfile(
        debtor_cif="CIF_LOW_INC",
        verified_inflow_avg_monthly=8_000_000.0,
        casa_balance=500_000.0,
        salary_day_of_month=10,
        stability_coefficient=0.85
    )
    res_low = D1AbilityEngine.calculate(
        monthly_obligation=4_000_000.0,
        inflow_profile=low_inflow,
        cic_score=600,
        worst_group_other_banks=1,
        collateral_ltv=None,
        product_code="UNSECURED_LOAN"
    )
    # Bị cảnh báo kiệt quệ sinh tồn và điểm bị kéo xuống
    assert any("thấp hơn mức sống tối thiểu" in d for d in res_low["top_drivers"])
    assert res_low["value"] <= 50

    # Case B: Nghĩa vụ nợ lớn (80 triệu/tháng), thu nhập 95 triệu. Tiền còn lại 15 triệu
    # Đệm tiền dư 15tr chỉ bằng 18.75% (< 20%) nghĩa vụ nợ -> Cảnh báo đòn bẩy cao, không được thưởng
    overleveraged_inflow = CustomerInflowProfile(
        debtor_cif="CIF_OVERLEVERAGED",
        verified_inflow_avg_monthly=95_000_000.0,
        casa_balance=10_000_000.0,
        salary_day_of_month=10,
        stability_coefficient=0.90
    )
    res_overleveraged = D1AbilityEngine.calculate(
        monthly_obligation=80_000_000.0,
        inflow_profile=overleveraged_inflow,
        cic_score=700,
        worst_group_other_banks=1,
        collateral_ltv=0.60,
        product_code="MORTGAGE"
    )
    assert any("Cảnh báo đòn bẩy nợ cao" in d for d in res_overleveraged["top_drivers"])

    # Case C: Thu nhập cao 100 triệu, trả nợ 48 triệu (DSR 48% > 45% safe_max).
    # Tiền còn lại 52 triệu >= 48 triệu (cushion multiple 1.08x >= 1.0) và >= 11 triệu (2x mức sống)
    safe_cushion_inflow = CustomerInflowProfile(
        debtor_cif="CIF_HIGH_CUSHION",
        verified_inflow_avg_monthly=100_000_000.0,
        casa_balance=50_000_000.0,
        salary_day_of_month=10,
        stability_coefficient=0.95
    )
    res_high = D1AbilityEngine.calculate(
        monthly_obligation=48_000_000.0,
        inflow_profile=safe_cushion_inflow,
        cic_score=720,
        worst_group_other_banks=1,
        collateral_ltv=0.45,
        product_code="MORTGAGE"
    )
    # Được thưởng bảo vệ dòng tiền do đệm khả dụng >= 1.0x nghĩa vụ nợ
    assert any("Dòng tiền an toàn: Đệm khả dụng" in d for d in res_high["top_drivers"])
    assert res_high["value"] >= 65


def test_d1_product_dsr_threshold_differentiation():
    # Cùng mức DSR = 42% ở mức thu nhập trung bình (Thu nhập 25 triệu, trả nợ 10.5 triệu)
    inflow = CustomerInflowProfile(
        debtor_cif="CIF_COMPARE",
        verified_inflow_avg_monthly=25_000_000.0,
        casa_balance=5_000_000.0,
        salary_day_of_month=10,
        stability_coefficient=0.90
    )

    # 1. MORTGAGE (Ngưỡng an toàn đến 45%): DSR 42% vẫn nằm trong ngưỡng an toàn
    res_mo = D1AbilityEngine.calculate(
        monthly_obligation=10_500_000.0,
        inflow_profile=inflow,
        cic_score=700,
        worst_group_other_banks=1,
        collateral_ltv=0.45,
        product_code="MORTGAGE"
    )

    # 2. CREDIT_CARD (Ngưỡng an toàn chỉ 30%, kiệt quệ ở 50%): DSR 42% bị đánh giá là rủi ro cao
    res_cc = D1AbilityEngine.calculate(
        monthly_obligation=10_500_000.0,
        inflow_profile=inflow,
        cic_score=700,
        worst_group_other_banks=1,
        collateral_ltv=None,
        product_code="CREDIT_CARD"
    )

    # Điểm Ability của Mortgage phải cao hơn rõ rệt so với Thẻ tín dụng do được chấp nhận DSR cao hơn
    assert res_mo["value"] > res_cc["value"]
    assert any("vượt ngưỡng an toàn 30% của gói CREDIT_CARD" in d for d in res_cc["top_drivers"])
