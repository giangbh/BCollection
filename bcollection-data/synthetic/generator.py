import random
from typing import List, Dict, Any
from datetime import datetime, timedelta

def generate_synthetic_delinquent_cases(num_cases: int = 100) -> List[Dict[str, Any]]:
    """
    Sinh dữ liệu tổng hợp (Synthetic Data) giả lập cho môi trường DEV.
    Tuyệt đối không chứa PII thật.
    """
    first_names = ["NGUYỄN", "TRẦN", "LÊ", "PHẠM", "HOÀNG", "HUỲNH", "PHAN", "VŨ", "VÕ", "ĐẶNG"]
    mid_names = ["VĂN", "THỊ", "HỮU", "ĐỨC", "MINH", "QUANG", "ANH", "TUẤN", "NGỌC", "THU"]
    last_names = ["HẢI", "NAM", "LONG", "PHÚC", "HÀ", "LINH", "TRANG", "DŨNG", "TUẤN", "SƠN"]
    products = ["CREDIT_CARD", "UNSECURED_LOAN", "AUTO_LOAN", "MORTGAGE"]
    
    cases = []
    base_date = datetime.now()
    
    for i in range(1, num_cases + 1):
        cif = f"CIF{100000 + i:06d}"
        full_name = f"{random.choice(first_names)} {random.choice(mid_names)} {random.choice(last_names)}"
        phone = f"+849{random.randint(10000000, 99999999)}"
        product = random.choice(products)
        dpd = random.randint(1, 29) # Nhóm B1
        
        principal = round(random.uniform(5_000_000, 150_000_000), -4)
        interest = round(principal * 0.02 * (dpd / 30.0), -3)
        overdue_amt = principal if product == "CREDIT_CARD" else round(principal * 0.1, -4) + interest
        
        cases.append({
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
