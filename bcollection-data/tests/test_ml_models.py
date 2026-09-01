import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ml.models.ml01_self_cure import ML01SelfCureModel
from ml.models.ml04_best_time import ML04BestTimeToContactModel

def test_ml01_self_cure_high_propensity():
    model = ML01SelfCureModel()
    # Khách hàng có lịch sử trả đúng hạn tốt, chỉ mới quá hạn 3 ngày, gần ngày nhận lương
    features = {
        "dpd": 3,
        "historical_on_time_ratio": 0.95,
        "days_since_salary_day": 1,
        "prior_cure_count": 4,
        "dti_ratio": 0.25
    }
    pred = model.evaluate_case("CIF_001", features)
    assert pred.self_cure_propensity >= 0.80
    assert pred.action_tier == "SELF_CURE_HIGH"
    assert pred.grace_period_days == 5

def test_ml01_self_cure_high_risk():
    model = ML01SelfCureModel()
    # Khách hàng có DTI cao, quá hạn 25 ngày, lịch sử trả nợ kém
    features = {
        "dpd": 25,
        "historical_on_time_ratio": 0.30,
        "days_since_salary_day": 15,
        "prior_cure_count": 0,
        "dti_ratio": 0.70
    }
    pred = model.evaluate_case("CIF_002", features)
    assert pred.self_cure_propensity < 0.45
    assert pred.action_tier == "HIGH_RISK"
    assert pred.grace_period_days == 0

def test_ml04_best_time_prediction():
    model = ML04BestTimeToContactModel()
    # Dân văn phòng -> ưu tiên gọi tối 18:00 - 20:30
    pred = model.predict_best_time("CIF_003", {"occupation": "OFFICE_WORKER", "age": 28})
    assert pred.best_time_window == "18:00-20:30"
    assert pred.best_channel == "VOICE"
    assert pred.expected_rpc_rate >= 0.70
