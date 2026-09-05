import random
from typing import List, Dict, Any
from datetime import datetime, timedelta

def generate_synthetic_delinquent_cases(num_cases: int = 500, seed: int = 42, as_of=None) -> List[Dict[str, Any]]:
    """
    Sinh dữ liệu tổng hợp (Synthetic Data) giả lập chuẩn cho môi trường DEV/UAT.
    Hỗ trợ sinh 500+ hồ sơ nợ B1 đa dạng, chuẩn hoá format ngân hàng bán lẻ.
    Tuyệt đối không chứa PII thật.
    """
    rng = random.Random(seed)
    
    first_names = ["NGUYỄN", "TRẦN", "LÊ", "PHẠM", "HOÀNG", "HUỲNH", "PHAN", "VŨ", "VÕ", "ĐẶNG", "BÙI", "ĐỖ", "HỒ", "NGÔ", "DƯƠNG"]
    mid_names = ["VĂN", "THỊ", "HỮU", "ĐỨC", "MINH", "QUANG", "ANH", "TUẤN", "NGỌC", "THU", "KIM", "GIA", "BẢO", "XUÂN", "TIẾN"]
    last_names = ["HẢI", "NAM", "LONG", "PHÚC", "HÀ", "LINH", "TRANG", "DŨNG", "TUẤN", "SƠN", "KHÁNH", "HUY", "TÙNG", "THẢO", "LAN", "HƯƠNG", "CHI", "PHƯỢNG", "BÌNH", "VIỆT"]
    products = ["CREDIT_CARD", "UNSECURED_LOAN", "AUTO_LOAN", "MORTGAGE"]
    
    cases = []
    base_date = as_of or datetime.now()
    
    for i in range(1, num_cases + 1):
        cif = f"CIF{100000 + i:06d}"
        full_name = f"{rng.choice(first_names)} {rng.choice(mid_names)} {rng.choice(last_names)}"
        phone = f"+849{rng.randint(10000000, 99999999)}"
        product = rng.choice(products)
        dpd = rng.randint(1, 29)  # Nhóm B1 (1 - 29 ngày)
        
        if product == "CREDIT_CARD":
            principal = round(rng.uniform(5_000_000, 60_000_000), -4)
            overdue_amt = round(rng.uniform(1_500_000, principal * 0.5), -4)
            interest = round(overdue_amt * 0.05, -3)
        elif product == "UNSECURED_LOAN":
            principal = round(rng.uniform(15_000_000, 100_000_000), -4)
            overdue_amt = round(rng.uniform(2_000_000, 15_000_000), -4)
            interest = round(overdue_amt * 0.03, -3)
        elif product == "AUTO_LOAN":
            principal = round(rng.uniform(200_000_000, 650_000_000), -5)
            overdue_amt = round(rng.uniform(8_000_000, 35_000_000), -4)
            interest = round(overdue_amt * 0.02, -3)
        else:  # MORTGAGE
            principal = round(rng.uniform(500_000_000, 2_500_000_000), -6)
            overdue_amt = round(rng.uniform(12_000_000, 75_000_000), -4)
            interest = round(overdue_amt * 0.02, -3)
        
        cases.append({
            "data_origin": "SYNTHETIC",
            "case_id": f"CASE-2026-{10000 + i}",
            "loan_id": f"LOAN-{product[:2]}-{20000 + i}",
            "debtor_cif": cif,
            "full_name": full_name,
            "phone_e164": phone,
            "product_code": product,
            "dpd": dpd,
            "outstanding_principal": principal,
            "outstanding_interest": interest,
            "overdue_amount": overdue_amt,
            "opened_at": (base_date - timedelta(days=dpd)).isoformat()
        })
        
    return cases
