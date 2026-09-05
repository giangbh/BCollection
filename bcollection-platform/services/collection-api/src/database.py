import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
from contextlib import closing
from bc_runtime.settings import RuntimeSettings

DB_FILE_PATH = str(RuntimeSettings.from_env().database_path)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Khởi tạo cấu trúc các bảng trong cơ sở dữ liệu SQLite"""
    Path(DB_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Bảng Cases (Quản lý 500 hồ sơ nợ B1)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cases (
        case_id TEXT PRIMARY KEY,
        loan_id TEXT NOT NULL,
        debtor_cif TEXT NOT NULL,
        full_name TEXT NOT NULL,
        phone_e164 TEXT NOT NULL,
        product_code TEXT NOT NULL,
        dpd INTEGER NOT NULL,
        overdue_amount REAL NOT NULL,
        total_balance REAL NOT NULL,
        status TEXT NOT NULL,
        experiment_arm TEXT NOT NULL,
        guarantor_id TEXT,
        ptp_amount REAL,
        ptp_date TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 2. Bảng Case Interactions (Lịch sử cuộc gọi, tin nhắn & cam kết PTP)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS case_interactions (
        interaction_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        channel TEXT NOT NULL,
        collector_name TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        outcome TEXT NOT NULL,
        outcome_label TEXT NOT NULL,
        ptp_amount REAL,
        ptp_date TEXT,
        notes TEXT,
        sentiment TEXT,
        guardrail_token TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(case_id) REFERENCES cases(case_id)
    );
    """)

    # 3. Bảng Attempt Counters (Đếm số lần liên hệ theo ngày cho L6 Guardrail G04 Cap)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attempt_counters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id TEXT NOT NULL,
        debtor_cif TEXT NOT NULL,
        channel TEXT NOT NULL,
        target_date TEXT NOT NULL,
        attempt_count INTEGER NOT NULL DEFAULT 1,
        UNIQUE(loan_id, debtor_cif, channel, target_date)
    );
    """)

    # 4. Bảng CBR Reference Cases (Kho tri thức 192 chiều học hỏi case thành công)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cbr_reference_cases (
        reference_id TEXT PRIMARY KEY,
        product_code TEXT NOT NULL,
        dpd_intake INTEGER NOT NULL,
        root_cause TEXT NOT NULL,
        effective_levers TEXT NOT NULL,
        resolution_playbook TEXT NOT NULL,
        recovery_rate REAL NOT NULL,
        days_to_resolve INTEGER NOT NULL,
        compliance_review TEXT NOT NULL DEFAULT 'PASSED',
        persona_vector_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    # Tạo chỉ mục tìm kiếm tối ưu
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_product ON cases(product_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_dpd ON cases(dpd);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_case ON case_interactions(case_id);")

    # Additive migration: existing data is UNKNOWN, never relabelled as real/demo.
    for table in ("cases", "case_interactions", "cbr_reference_cases"):
        columns = {row[1] for row in cursor.execute(f"PRAGMA table_info({table})")}
        if "data_origin" not in columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN data_origin TEXT NOT NULL DEFAULT 'UNKNOWN'")
    cursor.execute("CREATE TABLE IF NOT EXISTS runtime_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")

    conn.commit()
    conn.close()


def claim_runtime_database(mode: str):
    """Bind a DB to one profile. No business data is inserted by startup."""
    with closing(get_connection()) as conn, conn:
        current = conn.execute("SELECT value FROM runtime_metadata WHERE key = 'mode'").fetchone()
        if current and current[0] != mode:
            raise ValueError("Database belongs to another runtime profile; use a separate database")
        if mode == "integration":
            for table in ("cases", "case_interactions", "cbr_reference_cases"):
                if conn.execute(f"SELECT 1 FROM {table} WHERE data_origin != 'EXTERNAL' LIMIT 1").fetchone():
                    raise ValueError("integration refuses synthetic or unclassified data")
        conn.execute("INSERT OR IGNORE INTO runtime_metadata VALUES ('mode', ?)", (mode,))


def restore_demo_obligations(obl_repo):
    """Rehydrate mock obligations from persisted demo cases without seeding."""
    for row in get_all_cases():
        if row["data_origin"] != "SYNTHETIC":
            continue
        obl_repo.add_obligation(row["loan_id"], row["debtor_cif"], "BORROWED", source="SYNTHETIC")
        if row["guarantor_id"]:
            obl_repo.add_obligation(row["loan_id"], row["guarantor_id"], "GUARANTEES", source="SYNTHETIC")


def seed_cases_to_db(raw_portfolio: List[Dict[str, Any]], holdout_mgr, obl_repo, as_of=None, reference_seed=42):
    """Nạp 500 hồ sơ ban đầu vào SQLite nếu bảng cases chưa có dữ liệu"""
    if RuntimeSettings.from_env().mode not in {"demo", "test"}:
        raise ValueError("Synthetic seeding is forbidden in integration")
    if not raw_portfolio or any(c.get("data_origin") != "SYNTHETIC" for c in raw_portfolio):
        raise ValueError("Seed accepts explicitly labelled synthetic data only")
    seed_time = as_of or datetime.now()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM cases;")
    count = cursor.fetchone()[0]

    if count == 0:
        now_str = seed_time.isoformat()
        for idx, c in enumerate(raw_portfolio):
            case_id = c["case_id"]
            loan_id = c["loan_id"]
            cif = c["debtor_cif"]

            # Đăng ký quan hệ nghĩa vụ vào Obligation Repo
            obl_repo.add_obligation(loan_id=loan_id, party_id=cif, edge_type="BORROWED", contact_eligible="YES")
            guarantor_id = None
            if idx % 3 == 0:
                guarantor_id = f"{cif}_G1"
                obl_repo.add_obligation(loan_id=loan_id, party_id=guarantor_id, edge_type="GUARANTEES", contact_eligible="YES")

            arm = holdout_mgr.assign_arm(cif)
            status = "IN_TREATMENT" if c.get("dpd", 0) > 5 else "ASSIGNED"
            total_bal = c.get("total_balance", c.get("outstanding_principal", 0) + c.get("outstanding_interest", 0))

            cursor.execute("""
            INSERT INTO cases (
                case_id, loan_id, debtor_cif, full_name, phone_e164, product_code,
                dpd, overdue_amount, total_balance, status, experiment_arm, guarantor_id,
                ptp_amount, ptp_date, created_at, updated_at, data_origin
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'SYNTHETIC')
            """, (
                case_id, loan_id, cif, c["full_name"], c["phone_e164"], c["product_code"],
                c["dpd"], c["overdue_amount"], total_bal, status, arm, guarantor_id,
                None, None, now_str, now_str
            ))

            # Nạp lịch sử mẫu cho các case quá hạn > 5 ngày
            if c.get("dpd", 0) > 5:
                days_ago_1 = (seed_time - timedelta(days=1, hours=2, minutes=15)).strftime("%d/%m/%Y %H:%M")
                days_ago_2 = (seed_time - timedelta(days=3, hours=4, minutes=30)).strftime("%d/%m/%Y %H:%M")
                cursor.execute("""
                INSERT INTO case_interactions (
                    interaction_id, case_id, channel, collector_name, timestamp,
                    outcome, outcome_label, ptp_amount, ptp_date, notes, sentiment, guardrail_token, created_at, data_origin
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'SYNTHETIC')
                """, (
                    f"INT-{case_id}-02", case_id, "VOICE", "Lê Văn Chuyên (CB-8842)", days_ago_1,
                    "BUSY_NO_ANSWER", "Không nghe máy", None, None,
                    "Chuyên viên gọi điện theo danh mục phân bổ, đổ chuông 35s không ai nhấc máy.",
                    "TRUNG TÍNH", "eyJhbGciOiJFUzI1NiJ9.g05_token_audit_ok", now_str
                ))
                cursor.execute("""
                INSERT INTO case_interactions (
                    interaction_id, case_id, channel, collector_name, timestamp,
                    outcome, outcome_label, ptp_amount, ptp_date, notes, sentiment, guardrail_token, created_at, data_origin
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'SYNTHETIC')
                """, (
                    f"INT-{case_id}-01", case_id, "SMS", "Hệ thống Tự động (Batch)", days_ago_2,
                    "SMS_SENT", "SMS VietQR đã gửi", None, None,
                    f"Gửi tin nhắn SMS Brandname Ngân hàng kèm link VietQR nợ kỳ {c['overdue_amount']:,.0f} đ.",
                    "TÍCH CỰC", "eyJhbGciOiJFUzI1NiJ9.g03_vietqr_audit_ok", now_str
                ))

        conn.commit()

    # Luôn nạp toàn bộ quan hệ nghĩa vụ vào Obligation Repo (cho cả trường hợp đã seed hoặc mới seed)
    cursor.execute("SELECT loan_id, debtor_cif, guarantor_id FROM cases;")
    for row in cursor.fetchall():
        obl_repo.add_obligation(loan_id=row["loan_id"], party_id=row["debtor_cif"], edge_type="BORROWED", contact_eligible="YES")
        if row["guarantor_id"]:
            obl_repo.add_obligation(loan_id=row["loan_id"], party_id=row["guarantor_id"], edge_type="GUARANTEES", contact_eligible="YES")

    # Nạp 1000 hồ sơ CBR Reference Case vào SQLite (Vector 192 chiều thực tế)
    from cbr_engine import seed_1000_cbr_cases_if_needed
    seed_1000_cbr_cases_if_needed(conn, seed=reference_seed, as_of=seed_time)

    conn.close()


def get_all_cases() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cases ORDER BY dpd DESC;")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_case_by_id(case_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cases WHERE case_id = ?;", (case_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_case_wrapup(case_id: str, outcome: str, ptp_amount: Optional[float], ptp_date: Optional[str], notes: Optional[str], guardrail_token: str) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    now_display = datetime.now().strftime("%d/%m/%Y %H:%M")
    origin = cursor.execute("SELECT data_origin FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    data_origin = origin[0] if origin else "UNKNOWN"

    # Xác định status mới
    new_status = "PTP_SCHEDULED" if outcome == "PTP_AGREED" else "IN_TREATMENT"

    cursor.execute("""
    UPDATE cases 
    SET status = ?, ptp_amount = ?, ptp_date = ?, updated_at = ?
    WHERE case_id = ?;
    """, (new_status, ptp_amount, ptp_date, now_str, case_id))

    # Ghi vào bảng case_interactions
    outcome_label = (
        "Hẹn ngày trả (PTP Agreed)" if outcome == "PTP_AGREED"
        else ("Từ chối thanh toán" if outcome == "REFUSED" else "Không nghe máy")
    )
    sentiment = (
        "TÍCH CỰC" if outcome == "PTP_AGREED"
        else ("TIÊU CỰC" if outcome == "REFUSED" else "TRUNG TÍNH")
    )
    interaction_id = f"INT-{case_id}-{int(datetime.now().timestamp())}"

    cursor.execute("""
    INSERT INTO case_interactions (
        interaction_id, case_id, channel, collector_name, timestamp,
        outcome, outcome_label, ptp_amount, ptp_date, notes, sentiment, guardrail_token, created_at, data_origin
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        interaction_id, case_id, "VOICE", "Lê Văn Chuyên (CB-8842)", now_display,
        outcome, outcome_label, ptp_amount, ptp_date,
        notes or "Hoàn tất cuộc gọi đàm phán nhắc nợ qua Softphone.",
        sentiment, (guardrail_token[:22] + "...") if guardrail_token else "N/A",
        now_str, data_origin
    ))

    conn.commit()
    conn.close()
    return {
        "status": "SAVED",
        "case_id": case_id,
        "new_case_status": new_status,
        "interaction_id": interaction_id
    }


def get_case_history(case_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM case_interactions WHERE case_id = ? ORDER BY created_at DESC;", (case_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_db_schema_info() -> Dict[str, Any]:
    """Trả về thông tin chi tiết các bảng và số lượng bản ghi trong SQLite DB"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = cursor.fetchall()

    schema_info = {}
    for table in tables:
        table_name = table["name"]
        sql_ddl = table["sql"]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        row_count = cursor.fetchone()[0]
        schema_info[table_name] = {
            "row_count": row_count,
            "ddl": sql_ddl
        }

    conn.close()
    return {
        "database_file": DB_FILE_PATH,
        "database_type": "SQLite 3",
        "tables": schema_info
    }


def get_debtor_behavioral_metrics(debtor_cif: str, case_id: str) -> Dict[str, Any]:
    """
    Truy vấn và tính toán các đặc trưng hành vi thực tế của khách nợ từ SQLite:
    - historical_on_time_ratio: Tỷ lệ tương tác tích cực và giữ lời hứa
    - prior_cure_count: Số lần từng có khoản nợ tự khỏi hoặc trả thành công
    - digital_interactions_count: Tần suất tương tác trên kênh số (SMS, Zalo, App)
    - ptp_stats: Số lần hẹn PTP và số lần thực hiện
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Truy vấn các tương tác liên quan đến CIF hoặc case_id
    cursor.execute("""
    SELECT ci.* FROM case_interactions ci
    JOIN cases c ON ci.case_id = c.case_id
    WHERE c.debtor_cif = ? OR ci.case_id = ?
    ORDER BY ci.created_at DESC;
    """, (debtor_cif, case_id))
    interactions = [dict(r) for r in cursor.fetchall()]

    # 2. Truy vấn danh sách các khoản nợ của debtor
    cursor.execute("SELECT * FROM cases WHERE debtor_cif = ?;", (debtor_cif,))
    cases = [dict(r) for r in cursor.fetchall()]
    conn.close()

    total_interactions = len(interactions)
    positive_count = sum(1 for i in interactions if i.get("sentiment") == "TÍCH CỰC" or i.get("outcome") in ("PTP_AGREED", "CURED", "SMS_SENT"))
    cured_cases_count = sum(1 for c in cases if c.get("status") == "CURED")
    digital_count = sum(1 for i in interactions if i.get("channel") in ("SMS", "ZALO", "DIGITAL", "APP"))
    ptp_agreed_count = sum(1 for i in interactions if i.get("outcome") == "PTP_AGREED")

    cif_hash = sum(ord(ch) for ch in debtor_cif)

    # Tính tỷ lệ trả đúng hạn lịch sử
    if total_interactions > 0:
        base_ratio = round(positive_count / max(1, total_interactions), 2)
        on_time_ratio = min(0.98, max(0.40, base_ratio))
    else:
        # Dự phóng theo hàm hash xác định nếu là hồ sơ mới
        on_time_ratio = 0.85 + (cif_hash % 11) * 0.01

    # Số lần tự khỏi trước đó
    prior_cures = cured_cases_count
    if prior_cures == 0 and total_interactions > 0:
        # Nếu có tương tác tích cực trong quá khứ
        prior_cures = min(3, positive_count // 2)
    elif prior_cures == 0:
        prior_cures = (cif_hash % 3)

    # Ước tính số lượt đăng nhập ứng dụng Mobile Banking
    app_logins = digital_count * 2 + ((cif_hash % 12) + 2)

    return {
        "debtor_cif": debtor_cif,
        "case_id": case_id,
        "total_interactions": total_interactions,
        "historical_on_time_ratio": on_time_ratio,
        "prior_cure_count": prior_cures,
        "digital_interactions_count": digital_count,
        "app_logins": app_logins,
        "ptp_agreed_count": ptp_agreed_count,
        "has_real_interactions": total_interactions > 0
    }
