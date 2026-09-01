import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ml.experiments.holdout_assignment import HoldoutManager
from synthetic.generator import generate_synthetic_delinquent_cases

def test_holdout_distribution():
    hm = HoldoutManager(control_pct=10)
    total_samples = 10000
    control_count = 0
    
    for i in range(total_samples):
        cif = f"CIF_TEST_{i:06d}"
        if hm.is_holdout(cif):
            control_count += 1
            
    pct = (control_count / total_samples) * 100
    # Kỳ vọng tỷ lệ rơi vào khoảng 10% ± 1.0% trên 10.000 mẫu
    assert 9.0 <= pct <= 11.0, f"Actual holdout percentage: {pct}%"

def test_holdout_determinism():
    hm = HoldoutManager()
    cif = "CIF_BIDV_998877"
    arm1 = hm.assign_arm(cif)
    arm2 = hm.assign_arm(cif)
    assert arm1 == arm2, "Holdout assignment must be strictly deterministic!"

def test_synthetic_data_generator():
    cases = generate_synthetic_delinquent_cases(num_cases=50)
    assert len(cases) == 50
    for c in cases:
        assert c["debtor_cif"].startswith("CIF")
        assert c["dpd"] >= 1 and c["dpd"] <= 30
        assert c["overdue_amount"] > 0
