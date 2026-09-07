"""
Module sinh dữ liệu nghiệp vụ ngân hàng Việt Nam động và ngữ cảnh (Dynamic Contextual Generators).
Đảm bảo:
1. Nhất quán theo định danh (Deterministic Hash Seeding): Cùng 1 ID luôn cho ra dữ liệu tương tự.
2. Tương thích với 500 hồ sơ synthetic trong CSDL SQLite.
3. Sinh thông tin thực tế, tự nhiên, phong phú cho Core Banking, LOS, CIC, CTI, Speech AI, Messaging.
"""

import hashlib
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

ROOT_DIR = Path(__file__).resolve().parents[5]
DB_PATH = ROOT_DIR / ".runtime" / "demo" / "bcollection.sqlite3"


def get_db_connection() -> Optional[sqlite3.Connection]:
    if DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn
    return None


def get_case_from_db(loan_id: Optional[str] = None, debtor_cif: Optional[str] = None, case_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    if not conn:
        return None
    try:
        if case_id:
            row = conn.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
            if row:
                return dict(row)
        if loan_id:
            row = conn.execute("SELECT * FROM cases WHERE loan_id=?", (loan_id,)).fetchone()
            if row:
                return dict(row)
        if debtor_cif:
            row = conn.execute("SELECT * FROM cases WHERE debtor_cif=?", (debtor_cif,)).fetchone()
            if row:
                return dict(row)
    finally:
        conn.close()
    return None


def id_hash(seed_str: str) -> int:
    """Tạo số nguyên băm ổn định từ chuỗi ký tự."""
    return int(hashlib.sha256(seed_str.encode("utf-8")).hexdigest()[:8], 16)


# ---------------------------------------------------------------------------
# 1. CORE BANKING GENERATOR
# ---------------------------------------------------------------------------

VIETNAMESE_BANKS = ["BIDV", "Vietcombank", "VietinBank", "Techcombank", "MB", "VPBank", "ACB"]
EMPLOYERS = [
    ("Công ty CP Công nghệ FPT", "Hà Nội"),
    ("Tập đoàn Công nghiệp Viễn thông Viettel", "Hà Nội"),
    ("Công ty CP Tập đoàn Masan", "TP. Hồ Chí Minh"),
    ("Công ty TNHH Samsung Electronics Việt Nam", "Bắc Ninh"),
    ("Trường THPT Chu Văn An", "Hà Nội"),
    ("Bệnh viện Đa khoa Quốc tế Vinmec", "Hà Nội"),
    ("Hộ kinh doanh Đại lý Tạp hóa Hoàng Long", "Đà Nẵng"),
    ("Công ty TNHH Vận tải & Logistics Miền Nam", "Bình Dương"),
    ("Công ty CP Xây dựng Coteccons", "TP. Hồ Chí Minh")
]

BRANCHES = [
    "Chi nhánh Ba Đình - Hà Nội", "Chi nhánh Sở Giao dịch 1", "Chi nhánh Thăng Long",
    "Chi nhánh Bến Thành - TP.HCM", "Chi nhánh Chợ Lớn", "Chi nhánh Sông Hàn - Đà Nẵng",
    "Chi nhánh Cần Thơ", "Chi nhánh Hải Phòng", "Chi nhánh Bình Dương"
]


def generate_core_loan_balance(loan_id: str, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if overrides and loan_id in overrides:
        return overrides[loan_id]

    case = get_case_from_db(loan_id=loan_id)
    h = id_hash(loan_id)

    if case:
        debtor_cif = case["debtor_cif"]
        overdue_amt = float(case["overdue_amount"] or 0)
        dpd = int(case["dpd"] or 0)
        product_code = case.get("product_code", "UNSECURED_LOAN")
    else:
        debtor_cif = f"CIF{100000 + (h % 90000)}"
        overdue_amt = float(2000000 + (h % 30) * 500000)
        dpd = 3 + (h % 25)
        product_code = "SECURED_AUTO" if "SE" in loan_id else "UNSECURED_LOAN"

    multiplier = 2.0 + (h % 4) * 0.5
    principal = round(overdue_amt * multiplier, -5)
    interest_rate = 8.5 + (h % 12) * 0.5
    interest = round(overdue_amt * 0.08, -4)
    account_no = f"104{h % 1000000000:09d}"
    branch = BRANCHES[h % len(BRANCHES)]

    return {
        "loan_id": loan_id,
        "debtor_cif": debtor_cif,
        "account_no": account_no,
        "branch_name": branch,
        "product_code": product_code,
        "annual_interest_rate_pct": interest_rate,
        "outstanding_principal": principal,
        "outstanding_interest": interest,
        "overdue_amount": overdue_amt,
        "days_past_due": dpd,
        "dpd": dpd,
        "loan_status": "OVERDUE" if overdue_amt > 0 else "ACTIVE",
        "next_due_date": f"2026-09-{(h % 20) + 5:02d}",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source_version": 1
    }


def generate_core_cashflow(debtor_cif: str) -> Dict[str, Any]:
    case = get_case_from_db(debtor_cif=debtor_cif)
    h = id_hash(debtor_cif)

    emp, city = EMPLOYERS[h % len(EMPLOYERS)]
    bank = VIETNAMESE_BANKS[h % len(VIETNAMESE_BANKS)]
    salary_day = [5, 7, 10, 15, 20, 25][h % 6]

    base_salary = 12000000.0 + (h % 35) * 1000000.0
    casa_balance = round(base_salary * (0.15 + (h % 5) * 0.2), -5)
    monthly_obligation = 3500000.0 + (h % 10) * 500000.0
    casa_buffer = round(casa_balance / max(1.0, monthly_obligation), 2)

    inflow_types = ["PAYROLL_INTERNAL", "NON_PAYROLL_SALARIED", "MERCHANT_BUSINESS", "GIG_FREELANCE"]
    archetype = inflow_types[h % len(inflow_types)]

    return {
        "debtor_cif": debtor_cif,
        "casa_account_no": f"001{h % 10000000000:010d}",
        "employer_name": emp,
        "employer_city": city,
        "payroll_bank_name": bank,
        "has_payroll_relationship": (archetype == "PAYROLL_INTERNAL"),
        "inflow_archetype": archetype,
        "salary_day_of_month": salary_day,
        "verified_inflow_avg_monthly": base_salary,
        "casa_balance": casa_balance,
        "casa_buffer_ratio": casa_buffer,
        "stability_coefficient": round(0.75 + (h % 25) * 0.01, 2),
        "inflow_transactions_count_last_90d": 18 + (h % 30),
        "as_of": datetime.now(timezone.utc).isoformat()
    }


# ---------------------------------------------------------------------------
# 2. LOS (LOAN ORIGINATION SYSTEM) GENERATOR
# ---------------------------------------------------------------------------

FIRST_NAMES = ["BÙI THỊ", "NGUYỄN VĂN", "TRẦN VĂN", "LÊ THỊ", "HOÀNG MINH", "PHẠM THU", "ĐẶNG KIM", "VŨ THỊ"]
LAST_NAMES = ["HẢI", "AN", "LONG", "TRANG", "PHƯƠNG", "HÀ", "LAN", "VIỆT", "DŨNG", "THẢO", "ĐỨC"]

STREETS = [
    "Đường Giải Phóng, Phường Đồng Tâm, Quận Hai Bà Trưng, Hà Nội",
    "Đường Nguyễn Trãi, Phường Thanh Xuân Trung, Quận Thanh Xuân, Hà Nội",
    "Đường Hoàng Hoa Thám, Phường Thụy Khuê, Quận Tây Hồ, Hà Nội",
    "Đường Lê Văn Sỹ, Phường 14, Quận 3, TP. Hồ Chí Minh",
    "Đường Nguyễn Thị Minh Khai, Phường Đa Kao, Quận 1, TP. Hồ Chí Minh",
    "Đường Nguyễn Văn Linh, Phường Tân Phong, Quận 7, TP. Hồ Chí Minh",
    "Đường Bạch Đằng, Phường Hải Châu 1, Quận Hải Châu, Đà Nẵng",
    "Khu đô thị Vinhomes Ocean Park, Huyện Gia Lâm, Hà Nội"
]


def generate_los_parties(loan_id: str) -> List[Dict[str, Any]]:
    case = get_case_from_db(loan_id=loan_id)
    h = id_hash(loan_id)

    if case:
        borrower_name = case.get("full_name", "KHÁCH HÀNG")
        borrower_cif = case.get("debtor_cif", "CIF100001")
        phone = case.get("phone_e164", "+84946913810")
    else:
        borrower_name = f"{FIRST_NAMES[h % len(FIRST_NAMES)]} {LAST_NAMES[(h // 2) % len(LAST_NAMES)]}"
        borrower_cif = f"CIF{100000 + (h % 90000)}"
        phone = f"+849{(h % 90000000) + 10000000}"

    co_borrower_name = f"{FIRST_NAMES[(h + 1) % len(FIRST_NAMES)]} {LAST_NAMES[(h + 3) % len(LAST_NAMES)]}"
    guarantor_name = f"{FIRST_NAMES[(h + 2) % len(FIRST_NAMES)]} {LAST_NAMES[(h + 4) % len(LAST_NAMES)]}"

    parties = [
        {
            "loan_id": loan_id,
            "party_id": borrower_cif,
            "party_name": borrower_name,
            "party_type": "PERSON",
            "edge_type": "BORROWED",
            "relationship": "CHÍNH CHỦ",
            "national_id": f"0010{h % 90000000:08d}",
            "contact_eligible": "YES",
            "phone_e164": phone,
            "registered_address": STREETS[h % len(STREETS)],
            "source_system": "LOS"
        },
        {
            "loan_id": loan_id,
            "party_id": f"{borrower_cif}_G1",
            "party_name": guarantor_name,
            "party_type": "PERSON",
            "edge_type": "GUARANTEES",
            "relationship": "BẢO LÃNH HỢP ĐỒNG",
            "national_id": f"0010{(h + 1000) % 90000000:08d}",
            "contact_eligible": "YES",
            "phone_e164": f"+849{((h + 12345) % 90000000) + 10000000}",
            "registered_address": STREETS[(h + 1) % len(STREETS)],
            "source_system": "LOS"
        }
    ]

    # Nếu hash chẵn thì có thêm người đồng vay (Vợ/Chồng)
    if h % 2 == 0:
        parties.append({
            "loan_id": loan_id,
            "party_id": f"{borrower_cif}_CO1",
            "party_name": co_borrower_name,
            "party_type": "PERSON",
            "edge_type": "CO_BORROWER_WITH",
            "relationship": "ĐỒNG VAY (VỢ/CHỒNG)",
            "national_id": f"0010{(h + 2000) % 90000000:08d}",
            "contact_eligible": "YES",
            "phone_e164": f"+849{((h + 54321) % 90000000) + 10000000}",
            "registered_address": STREETS[h % len(STREETS)],
            "source_system": "LOS"
        })

    return parties


def generate_los_collaterals(loan_id: str) -> List[Dict[str, Any]]:
    h = id_hash(loan_id)
    if "SE" in loan_id or (h % 3 == 0):
        val = float(1200000000 + (h % 40) * 100000000)
        return [
            {
                "collateral_id": f"COL-{loan_id[-5:]}",
                "collateral_type": "REAL_ESTATE" if (h % 2 == 0) else "VEHICLE",
                "collateral_name": "Quyền sử dụng đất và nhà ở gắn liền" if (h % 2 == 0) else "Xe ô tô du lịch 5 chỗ",
                "valuation_amount": val,
                "valuation_date": "2025-10-15",
                "address": STREETS[h % len(STREETS)],
                "ltv_ratio": round(0.55 + (h % 15) * 0.01, 2)
            }
        ]
    return []


# ---------------------------------------------------------------------------
# 3. CIC GATEWAY GENERATOR
# ---------------------------------------------------------------------------

def generate_cic_report(debtor_cif: str, national_id: str = "") -> Dict[str, Any]:
    h = id_hash(debtor_cif)
    score = 520 + (h % 230)
    worst_group = 1 if score >= 670 else (2 if score >= 580 else 3)
    num_banks = (h % 4) + 1

    facilities = []
    other_banks = [b for b in VIETNAMESE_BANKS if b != "BIDV"]
    for i in range(min(num_banks, len(other_banks))):
        bank_name = other_banks[(h + i) % len(other_banks)]
        amt = float(10000000 + ((h + i) % 15) * 5000000)
        facilities.append({
            "institution_name": bank_name,
            "facility_type": "THẺ TÍN DỤNG" if i == 0 else "CHO VAY TRẢ GÓP",
            "outstanding_vnd": amt,
            "debt_group": 1 if score > 600 else 2
        })

    return {
        "debtor_cif": debtor_cif,
        "national_id": national_id or f"0010{h % 90000000:08d}",
        "credit_score": score,
        "credit_grade": f"Hạng {10 - (score // 75)}",
        "worst_group_other_banks": worst_group,
        "obligations_at_other_banks_count": len(facilities),
        "total_obligation_other_banks": sum(f["outstanding_vnd"] for f in facilities),
        "facilities": facilities,
        "paying_other_banks_while_overdue": bool(score > 630 and worst_group == 1),
        "report_date": datetime.now(timezone.utc).isoformat()
    }


# ---------------------------------------------------------------------------
# 4. CTI TELEPHONY GENERATOR
# ---------------------------------------------------------------------------

def generate_cti_call_session(agent_id: str, agent_extension: str, destination_phone: str, case_id: str) -> Dict[str, Any]:
    h = id_hash(f"{agent_id}:{case_id}:{time.time()}")
    call_id = f"CALL-FS-{int(time.time()) % 1000000:06d}-{h % 1000:03d}"
    return {
        "call_id": call_id,
        "sip_call_id": f"sip-{h:08x}@freeswitch.bank.vn",
        "agent_id": agent_id,
        "agent_extension": agent_extension,
        "destination_phone": destination_phone,
        "case_id": case_id,
        "status": "ANSWERED",
        "mos_score": round(4.1 + (h % 8) * 0.05, 2),  # HD Voice Quality (4.1 - 4.5)
        "started_at": datetime.now(timezone.utc).isoformat(),
        "recording_url": f"https://mock-storage.bank.vn/recordings/20260907/{call_id}.wav",
        "gateway": "FREESWITCH"
    }


# ---------------------------------------------------------------------------
# 5. SPEECH AI & NLP GENERATOR
# ---------------------------------------------------------------------------

DIALOGUE_ARCHETYPES = {
    "CASHFLOW_TIMING": [
        ("RM", "Dạ em chào anh/chị {name}, em gọi từ Phòng Quản lý nợ Ngân hàng về khoản vay {loan_id} đang quá hạn {dpd} ngày với số tiền {amount:,.0f} VNĐ ạ."),
        ("CUSTOMER", "À chào em, đợt này công ty anh đổi ngày chi trả lương sang ngày {ptp_day} nên anh bị lệch mấy hôm. Đến hôm đó anh chuyển khoản đủ nhé em."),
        ("RM", "Dạ vâng ngân hàng ghi nhận hẹn thanh toán đúng ngày {ptp_day}/09 qua VietQR hoặc SmartBanking. Cảm ơn anh/chị nhiều ạ.")
    ],
    "FORGETFULNESS": [
        ("RM", "Dạ kính chào anh/chị {name}, ngân hàng liên hệ nhắc kỳ thanh toán của hợp đồng {loan_id} đang trễ hạn {dpd} ngày ạ."),
        ("CUSTOMER", "Ối giời mấy hôm vừa rồi anh đi công tác vùng cao bận quá nên quên mất! Cho anh xin lại link VietQR anh quét thanh toán luôn bây giờ."),
        ("RM", "Dạ vâng em gửi link thanh toán VietQR động qua tin nhắn Zalo ngay cho anh/chị ạ.")
    ],
    "BUSINESS_DOWNTURN": [
        ("RM", "Chào anh/chị {name}, em là chuyên viên phụ trách khoản vay {loan_id}. Hiện tại khoản nợ đã phát sinh chậm trả {dpd} ngày, em liên hệ để hỗ trợ phương án ạ."),
        ("CUSTOMER", "Đợt này hàng quán chậm khách, tiền hàng đọng chưa rút ra kịp em ơi. Ngày {ptp_day} này anh xoay trước khoảng {ptp_amount:,.0f} đồng nộp trước được không?"),
        ("RM", "Dạ được anh ạ, ngân hàng ghi nhận cam kết nộp trước đợt 1 và hỗ trợ hướng dẫn cơ cấu phần còn lại ạ.")
    ],
    "WILFUL_DEFAULT": [
        ("RM", "Thông báo tới anh/chị {name}, hợp đồng tín dụng {loan_id} đã quá hạn {dpd} ngày và chuẩn bị chuyển nhóm nợ xấu trên hệ thống CIC toàn quốc."),
        ("CUSTOMER", "Tôi đã nói đợt này tôi kẹt tiền không có khả năng nộp rồi! Khi nào có tiền tôi khắc tự chuyển, đừng gọi nữa!"),
        ("RM", "Dạ ngân hàng rất thấu hiểu khó khăn nhưng xin phép lưu nhận phản hồi và gửi thông báo nghĩa vụ bằng văn bản chính thức theo quy định ạ.")
    ]
}


def generate_speech_ai_analysis(case_id: str, call_duration_seconds: int = 45) -> Dict[str, Any]:
    case = get_case_from_db(case_id=case_id)
    h = id_hash(case_id)

    if case:
        full_name = case.get("full_name", "Khách hàng")
        loan_id = case.get("loan_id", "LOAN-UN-20001")
        overdue_amt = float(case.get("overdue_amount") or 3000000.0)
        dpd = int(case.get("dpd") or 8)
    else:
        full_name = f"{FIRST_NAMES[h % len(FIRST_NAMES)]} {LAST_NAMES[(h // 2) % len(LAST_NAMES)]}"
        loan_id = f"LOAN-UN-{20000 + (h % 500)}"
        overdue_amt = float(2500000 + (h % 20) * 500000)
        dpd = 4 + (h % 24)

    if dpd <= 8:
        arch = "FORGETFULNESS" if (h % 2 == 0) else "CASHFLOW_TIMING"
    elif dpd <= 18:
        arch = "BUSINESS_DOWNTURN" if (h % 3 != 0) else "CASHFLOW_TIMING"
    else:
        arch = "WILFUL_DEFAULT" if (h % 2 == 0) else "BUSINESS_DOWNTURN"

    ptp_day = (h % 15) + 10
    ptp_amount = overdue_amt if arch in ("CASHFLOW_TIMING", "FORGETFULNESS") else round(overdue_amt * 0.5, -4)
    raw_turns = DIALOGUE_ARCHETYPES[arch]

    transcript = []
    base_sec = 2
    for spk, text in raw_turns:
        formatted_text = text.format(
            name=full_name, loan_id=loan_id, dpd=dpd, amount=overdue_amt,
            ptp_day=ptp_day, ptp_amount=ptp_amount
        )
        time_str = f"00:{base_sec:02d}"
        transcript.append({"speaker": spk, "text": formatted_text, "timestamp": time_str})
        base_sec += 15

    if arch in ("CASHFLOW_TIMING", "FORGETFULNESS"):
        outcome = "PTP_AGREED"
        ptp_date = f"2026-09-{ptp_day:02d}"
        sentiment_label = "TÍCH CỰC"
        sentiment_score = 0.52
        sentiment_tone = "Thiện chí • Lịch sự • Hợp tác cao"
        root_cause = "CASHFLOW_TIMING"
        auto_notes = f"Khách {full_name} xác nhận chuyển đủ {overdue_amt:,.0f} VNĐ vào ngày {ptp_day}/09."
    elif arch == "BUSINESS_DOWNTURN":
        outcome = "PTP_AGREED"
        ptp_date = f"2026-09-{ptp_day:02d}"
        sentiment_label = "TRUNG TÍNH"
        sentiment_score = 0.08
        sentiment_tone = "Khó khăn dòng tiền • Thiện chí đàm phán"
        root_cause = "BUSINESS_DOWNTURN"
        auto_notes = f"Khách khó khăn dòng tiền kinh doanh, cam kết thanh toán trước {ptp_amount:,.0f} VNĐ vào ngày {ptp_day}/09."
    else:
        outcome = "REFUSED"
        ptp_amount = None
        ptp_date = None
        sentiment_label = "TIÊU CỰC"
        sentiment_score = -0.68
        sentiment_tone = "Căng thẳng • Né tránh nghĩa vụ"
        root_cause = "WILFUL_DEFAULT"
        auto_notes = "Khách hàng từ chối cam kết ngày trả cụ thể, phản ứng bức xúc khi bị nhắc nợ."

    return {
        "case_id": case_id,
        "call_duration_seconds": call_duration_seconds,
        "transcript": transcript,
        "extracted_outcome": outcome,
        "extracted_ptp_amount": ptp_amount,
        "extracted_ptp_date": ptp_date,
        "confidence": round(0.92 + (h % 7) * 0.01, 2),
        "detected_root_cause": root_cause,
        "sentiment": {
            "label": sentiment_label,
            "score": sentiment_score,
            "tone": sentiment_tone
        },
        "compliance_audit": {
            "status": "PASSED",
            "checks": [
                "Xưng danh chuyên viên chuẩn mực",
                "Không có từ ngữ đe dọa, xúc phạm hoặc bôi nhọ",
                "Đúng người có nghĩa vụ theo L6 Guardrail",
                "Tuân thủ Thông tư 18/2019/TT-NHNN"
            ],
            "prohibited_words_found": []
        },
        "auto_notes": auto_notes
    }


# ---------------------------------------------------------------------------
# 6. MESSAGING GENERATOR
# ---------------------------------------------------------------------------

def generate_messaging_result(channel: str, phone: str, brandname: str = "BANK") -> Dict[str, Any]:
    h = id_hash(f"{channel}:{phone}:{time.time()}")
    gw_id = f"{channel}-GW-{int(time.time()*1000) % 1000000000:09d}"
    return {
        "status": "SENT",
        "delivery_status": "DELIVERED_TO_HANDSET",
        "gateway_message_id": gw_id,
        "channel": channel,
        "recipient": phone,
        "brandname": brandname,
        "cost_vnd": 500 if channel == "SMS" else 300,
        "telco_carrier": ["VIETTEL", "VINAPHONE", "MOBIFONE"][h % 3],
        "sent_at": datetime.now(timezone.utc).isoformat()
    }
