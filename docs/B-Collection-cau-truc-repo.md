# B.COLLECTION — CẤU TRÚC REPOSITORY & QUY ƯỚC PHÁT TRIỂN
**Phiên bản:** v0.1 | **Ngày:** 01/09/2026 | **Phạm vi:** MVP, có tính đến đường tiến hoá GĐ2–3
**Liên quan:** Tech Stack MVP · Guardrail Service v1.0 · Kiến trúc tích hợp v0.1 · ADR-001

---

## 1. Quyết định nền tảng: 4 repo, không phải 1, cũng không phải 12

| Repo | Sở hữu | Nhịp release | Lý do tách |
|---|---|---|---|
| `bcollection-platform` | Đội phát triển | Liên tục | Monorepo cho ứng dụng — API, worker, frontend, thư viện dùng chung |
| `bcollection-guardrail` | Đội phát triển + **Compliance có quyền phủ quyết** | Chậm, có kiểm soát | **Ranh giới tiến trình và ranh giới quyền hạn** — xem Mục 2 |
| `bcollection-policy` | **Compliance Officer** | Theo nhu cầu chính sách | Chính sách là dữ liệu, đổi không cần deploy code; người duyệt là Compliance chứ không phải Tech Lead |
| `bcollection-data` | Đội Dữ liệu & ML | Theo chu kỳ mô hình | dbt + ML có governance riêng (Model Risk Management), reviewer khác, vòng đời khác |

**Vì sao không monorepo toàn bộ:** yêu cầu cốt lõi của kiến trúc là Guardrail có **quyền merge riêng** — Compliance Officer phải phê duyệt được thay đổi mà không phụ thuộc Tech Lead. Trong monorepo, CODEOWNERS làm được điều này về mặt kỹ thuật, nhưng khi thanh tra hỏi "ai có thể sửa logic kiểm soát tuân thủ", câu trả lời "một file CODEOWNERS trong repo mà đội phát triển toàn quyền" yếu hơn nhiều so với "một repo riêng mà đội phát triển không có quyền merge".

**Vì sao không tách nhỏ hơn:** 4 repo là đủ. Tách theo microservice ở MVP (persona-service, case-service, nba-service...) sẽ tạo ra chi phí điều phối lớn hơn giá trị, khi đội chỉ có 15 người và toàn bộ chạy trên một CSDL.

---

## 2. `bcollection-guardrail` — repo có kiểm soát đặc biệt

```
bcollection-guardrail/
├── CODEOWNERS                      # * @compliance-team @tech-lead (bắt buộc cả hai)
├── README.md
├── src/guardrail/
│   ├── api/
│   │   ├── routes.py               # evaluate, commit, batch-evaluate, dsr, evidence
│   │   ├── schemas.py              # Pydantic v2 — hợp đồng API
│   │   └── token.py                # ký/xác thực ES256, TTL 5 phút
│   ├── controls/                   # MỖI CONTROL MỘT FILE — dễ review, dễ audit
│   │   ├── base.py                 # giao diện Control, kết quả, thứ tự chạy
│   │   ├── g01_debt_validity.py
│   │   ├── g02_party_eligibility.py
│   │   ├── g03_consent_dnc.py
│   │   ├── g04_frequency_cap.py
│   │   ├── g05_time_window.py
│   │   ├── g06_content_filter.py
│   │   ├── g07_vulnerability.py
│   │   ├── g08_dispute_hold.py
│   │   ├── g09_collateral_enforcement.py
│   │   ├── g10_data_protection.py
│   │   ├── g11_irreversible_action.py
│   │   └── g12_audit.py
│   ├── engine/
│   │   ├── orchestrator.py         # thứ tự chạy, short-circuit, quy tắc ưu tiên
│   │   ├── precedence.py           # BLOCK > ESCALATE > CONDITIONS > ALLOW
│   │   └── failclosed.py           # xử lý timeout/lỗi phụ thuộc → BLOCK
│   ├── hardcoded/
│   │   └── eligibility_whitelist.py   # 4 cạnh + 2 cạnh có điều kiện
│   │                                  # KHÔNG cấu hình được qua policy file
│   ├── repositories/               # cổng ra ngoài, có interface
│   │   ├── obligation_repo.py      # ← điểm thay Postgres → Neo4j ở GĐ2
│   │   ├── persona_repo.py
│   │   ├── counter_repo.py         # Redis sorted set
│   │   └── audit_repo.py           # hash-chain
│   └── policy/
│       ├── loader.py               # tải + xác thực chữ ký policy
│       └── cache.py                # cache tối đa 1h, hết hạn → BLOCK
├── tests/
│   ├── unit/
│   ├── compliance/                 # BỘ TEST TUÂN THỦ — cổng chặn CI
│   │   ├── test_g02_eligibility.py      # ≥60 case
│   │   ├── test_g04_frequency.py        # ≥40 case, biên cửa sổ trượt
│   │   ├── test_g05_time_window.py      # ≥25 case
│   │   ├── test_g09_collateral.py       # ≥35 case
│   │   ├── test_g06_content_vi.py       # ≥200 mẫu tiếng Việt
│   │   ├── test_failclosed.py           # ≥20 case, tắt từng phụ thuộc
│   │   └── test_bypass_attempts.py      # ≥15 case — KHÔNG ĐƯỢC PHÉP FAIL
│   └── fixtures/
│       ├── eligibility_matrix.yaml
│       └── content_samples_vi.yaml      # bộ mẫu có version, do Compliance duyệt
├── docs/
│   ├── control-specs/              # đặc tả từng control
│   └── evidence-pack-format.md
└── .gitlab-ci.yml
```

**Ba quy tắc bắt buộc của repo này:**

1. **Mỗi control một file.** Không gộp. Khi Compliance review, họ review một file 150 dòng có tên rõ ràng, không phải một hàm 800 dòng.
2. **`hardcoded/eligibility_whitelist.py` không có đường cấu hình.** Thay đổi file này cần release, cần Compliance duyệt, và có test khẳng định danh sách đúng bằng đúng 4 phần tử.
3. **`test_bypass_attempts.py` là cổng chặn tuyệt đối.** Một test fail ở đây chặn toàn bộ pipeline, không có `--skip`, không có ngoại lệ cho hotfix.

---

## 3. `bcollection-policy` — chính sách là dữ liệu

```
bcollection-policy/
├── CODEOWNERS                      # * @compliance-officer (chỉ Compliance merge)
├── policies/
│   ├── current -> versions/gp-2026.09.01-r3.yaml     # symlink
│   └── versions/
│       ├── gp-2026.09.01-r3.yaml
│       ├── gp-2026.09.01-r3.yaml.sig                 # chữ ký số
│       └── gp-2026.08.15-r2.yaml
├── schema/
│   └── policy.schema.json          # JSON Schema — CI validate mọi policy
├── approvals/
│   └── gp-2026.09.01-r3.md         # ai duyệt, số quyết định, ngày hiệu lực
├── impact-analysis/
│   └── gp-2026.09.01-r3.md         # mô phỏng trên 30 ngày dữ liệu lịch sử:
│                                   # bao nhiêu hành động bị chặn thêm/bớt
├── tests/
│   └── test_policy_valid.py        # schema, chữ ký, tính nhất quán ngưỡng
└── .gitlab-ci.yml                  # validate → ký → publish artifact
```

**Quy tắc bất đối xứng (từ đặc tả Guardrail Mục 14):** CI phát hiện thay đổi **nới lỏng** ngưỡng (tăng `max_attempts`, mở rộng khung giờ, hạ cấp phê duyệt) sẽ yêu cầu thêm một approver cấp cao hơn và bắt buộc có file `impact-analysis/`. Thay đổi **siết chặt** đi qua quy trình thường. Hệ thống phải dễ làm chặt và khó làm lỏng.

---

## 4. `bcollection-platform` — monorepo ứng dụng

```
bcollection-platform/
├── CODEOWNERS
├── docs/
│   ├── architecture/               # 6 tài liệu kiến trúc đã có
│   ├── adr/
│   │   ├── ADR-001-cdp-vs-persona-rieng.md
│   │   ├── ADR-002-mvp-khong-dung-neo4j.md          # cần viết
│   │   └── ADR-003-tach-repo-guardrail.md           # cần viết
│   └── runbooks/
├── contracts/                      # HỢP ĐỒNG INTERFACE — nguồn chân lý
│   ├── inbound/
│   │   ├── IF-CORE-01.loan-portfolio.schema.json
│   │   ├── IF-CORE-04.payment-event.schema.json
│   │   ├── IF-LOS-02.party-obligation.schema.json   # rủi ro cao nhất
│   │   ├── IF-CDP-01.profile-allowlist.yaml         # allowlist tường minh
│   │   └── IF-CDP-02.identity.schema.json
│   ├── outbound/
│   │   ├── IF-MSG-01.message-send.schema.json
│   │   └── IF-DWH-03.collection-mart.schema.json
│   └── tests/                      # contract test chạy hằng ngày trên UAT
├── libs/                           # thư viện dùng chung
│   ├── bc-domain/                  # kiểu dữ liệu nghiệp vụ, không phụ thuộc hạ tầng
│   │   ├── case.py
│   │   ├── persona.py              # gồm willingness_matrix
│   │   ├── obligation.py
│   │   └── enums.py                # root_cause, negotiation_lever, treatment
│   ├── bc-guardrail-client/        # client gọi Guardrail, quản lý token
│   └── bc-observability/           # OpenTelemetry, logging chuẩn
├── services/
│   ├── collection-api/             # FastAPI — BFF cho Collector Workspace
│   │   ├── src/
│   │   │   ├── api/
│   │   │   ├── application/        # use case
│   │   │   ├── domain/
│   │   │   └── adapters/           # ← cổng ra hạ tầng
│   │   │       ├── postgres/
│   │   │       │   └── obligation_repository.py     # MVP
│   │   │       └── neo4j/
│   │   │           └── obligation_repository.py     # GĐ2, cùng interface
│   │   └── tests/
│   ├── case-workflow/              # Temporal workflow + activity
│   │   ├── src/workflows/
│   │   ├── src/activities/
│   │   └── tests/
│   ├── persona-builder/            # job tính Persona (batch + event-driven)
│   ├── channel-adapters/
│   │   ├── sms/
│   │   ├── zns/
│   │   └── base.py                 # TỪ CHỐI lệnh không có guardrail_token
│   └── enrichment-api/             # Manual Enrichment + content filter client
├── apps/
│   └── collector-workspace/        # React + TS + Vite
│       ├── src/
│       │   ├── features/
│       │   │   ├── persona-card/   # gồm khối ma trận willingness
│       │   │   ├── case-queue/
│       │   │   ├── enrichment/     # form có cấu trúc, không có textarea lớn
│       │   │   └── call-wrapup/
│       │   └── shared/
│       └── tests/
├── db/
│   └── migrations/                 # Alembic
├── deploy/
│   ├── helm/
│   └── env/{dev,uat,prod}/
├── Makefile
└── .gitlab-ci.yml
```

**Điểm thiết kế quan trọng:** cấu trúc `adapters/postgres/` và `adapters/neo4j/` cùng hiện thực `ObligationRepository` — đây là cách hiện thực hoá lời hứa trong tài liệu Tech Stack rằng MVP không dùng Neo4j nhưng không tạo nợ kỹ thuật. Thư mục `neo4j/` tồn tại từ MVP với một hiện thực rỗng và một bộ test dùng chung, để không ai quên.

**`channel-adapters/base.py`** chứa kiểm tra token bắt buộc. Mọi adapter kênh kế thừa từ đây; không adapter nào được tự viết đường gửi riêng.

---

## 5. `bcollection-data` — dữ liệu & mô hình

```
bcollection-data/
├── CODEOWNERS                      # @data-team @model-risk (mô hình cần MRM duyệt)
├── dbt/
│   ├── models/
│   │   ├── staging/                # stg_core_loan, stg_los_party, stg_cdp_profile
│   │   ├── intermediate/
│   │   │   ├── int_phone_normalized.sql        # ưu tiên số 1 của MVP
│   │   │   ├── int_address_standardized.sql
│   │   │   └── int_party_obligation.sql        # nền tảng Guardrail G02
│   │   └── marts/
│   │       ├── dm_debtor_360.sql
│   │       ├── dm_persona_features.sql
│   │       ├── dm_treatment_outcome.sql
│   │       └── dm_collection_result.sql        # → IF-DWH-03
│   ├── tests/                      # dbt test + test tuỳ chỉnh
│   └── macros/
├── ml/
│   ├── features/
│   ├── models/
│   │   ├── ml01_self_cure/
│   │   ├── ml04_best_time/
│   │   └── ml_willingness_matrix/  # đa đầu ra theo treatment
│   ├── evaluation/
│   │   ├── calibration.py
│   │   ├── fairness.py             # kiểm tra phân biệt đối xử
│   │   └── proxy_detection.py      # vector không rò rỉ biến nhạy cảm
│   ├── experiments/
│   │   ├── holdout_assignment.py   # PHẢI CÓ TỪ NGÀY ĐẦU
│   │   └── uplift_measurement.py
│   └── registry/                   # cấu hình MLflow
├── governance/
│   ├── model-cards/                # bắt buộc cho MRM
│   │   ├── ml01-self-cure.md
│   │   └── ml-willingness-matrix.md
│   └── data-dictionary.md
└── .gitlab-ci.yml
```

`holdout_assignment.py` nằm trong repo từ commit đầu tiên. Đây là biện pháp chống rủi ro R6 trong tài liệu Tech Stack: nếu để sau, sẽ không bao giờ có.

---

## 6. Quy ước phát triển

### 6.1 Nhánh và merge
| Repo | Chiến lược | Reviewer bắt buộc |
|---|---|---|
| `platform` | Trunk-based, nhánh ngắn < 2 ngày | 1 dev + owner theo thư mục |
| `guardrail` | Trunk-based, nhưng **2 approver: 1 dev + 1 Compliance** | Không có ngoại lệ, kể cả hotfix |
| `policy` | **Chỉ Compliance Officer merge** | + Ban Điều hành nếu nới lỏng |
| `data` | Trunk-based | 1 data eng + Model Risk cho thay đổi mô hình |

### 6.2 Quy ước đặt tên
- Nhánh: `feat/BC-123-mo-ta-ngan`, `fix/`, `chore/`
- Commit: Conventional Commits, bắt buộc mã ticket
- Interface: luôn dùng mã `IF-<HỆ THỐNG>-<số>` trong code, test và log
- Control: luôn dùng mã `G01`–`G12`
- Mô hình: `ML01`–`ML12` khớp danh mục trong tài liệu kiến trúc

Quy ước mã hoá này quan trọng hơn vẻ ngoài: khi có sự cố, `reason_code = G02_NO_LEGAL_BASIS` truy ngược thẳng tới file `g02_party_eligibility.py`, tới Mục 5 đặc tả Guardrail, và tới cơ sở pháp lý NĐ 117/2018 — không cần ai giải thích.

### 6.3 CI pipeline

**`bcollection-guardrail`:**
```
lint → unit test → COMPLIANCE TEST SUITE → contract test
     → build → deploy UAT → smoke test → [duyệt thủ công] → prod
                    ▲
                    └── FAIL = chặn tuyệt đối, không có bypass
```

**`bcollection-platform`:**
```
lint → unit test → integration test (testcontainers)
     → contract test (schema trong contracts/)
     → build → deploy UAT → e2e → [duyệt] → prod
```

**`bcollection-data`:**
```
sqlfluff → dbt compile → dbt test (dữ liệu mẫu)
        → model training test → fairness + proxy detection
        → [Model Risk duyệt] → publish MLflow
```

**Contract test chạy hằng ngày trên UAT ở cả 4 repo**, không chỉ khi có commit — vì Core Banking và LOS thay đổi theo nhịp riêng của chúng, không theo nhịp commit của đội.

### 6.4 Bí mật và cấu hình
- Không có bí mật trong repo. Vault/KMS, inject lúc chạy.
- Cấu hình theo môi trường trong `deploy/env/`, giá trị nhạy cảm là tham chiếu Vault.
- `.env.example` có trong repo; `.env` trong `.gitignore`.
- Pre-commit hook quét bí mật (gitleaks) — bắt buộc ở cả 4 repo.

---

## 7. Vấn đề: dữ liệu thật trong môi trường phát triển

Đây là hạng mục hay bị xử lý sơ sài và tạo rủi ro lớn nhất về dữ liệu cá nhân trong toàn dự án.

| Môi trường | Dữ liệu | Quy tắc |
|---|---|---|
| DEV | **Chỉ dữ liệu tổng hợp** (synthetic) | Sinh bằng script trong `bcollection-data/synthetic/`; không bao giờ có PII thật |
| UAT | Dữ liệu thật **đã ẩn danh/giả lập** | Tokenize CCCD, số tài khoản; số điện thoại thay bằng dải test; giữ nguyên phân bố thống kê |
| PROD | Dữ liệu thật | Truy cập theo RBAC, mọi truy vấn có audit |

Bộ test tuân thủ của Guardrail dùng **fixture tự viết**, không dùng dữ liệu khách hàng thật — vừa an toàn hơn, vừa cho phép kiểm soát chính xác từng tình huống biên.

---

## 8. Ánh xạ tài liệu → repo

| Tài liệu đã có | Nơi lưu |
|---|---|
| Kiến trúc tổng thể v0.2 | `platform/docs/architecture/` |
| Collection Graph | `platform/docs/architecture/` + schema trong `db/migrations/` |
| Persona Model v0.2 | `platform/docs/architecture/` + `libs/bc-domain/persona.py` |
| Guardrail Service v1.0 | `guardrail/docs/control-specs/` |
| Kiến trúc tích hợp | `platform/contracts/` + `docs/architecture/` |
| Tech Stack MVP | `platform/docs/architecture/` |
| ADR-001 (CDP) | `platform/docs/adr/` |

Nguyên tắc: **tài liệu nằm cùng repo với code mà nó mô tả**, để cùng version và cùng review. Tài liệu kiến trúc tổng thể nằm ở `platform` vì đó là repo trung tâm.

---

## 9. Lộ trình khởi tạo

| Tuần | Việc |
|---|---|
| 1 | Tạo 4 repo, CODEOWNERS, pre-commit, CI khung; đưa 7 tài liệu vào `docs/` |
| 1 | Dựng `contracts/` với schema của 19 interface P0 (kể cả khi chưa có dữ liệu) |
| 2 | `bc-domain` với kiểu dữ liệu cốt lõi; migration đầu tiên cho `party_obligation` |
| 2 | `bcollection-data`: dbt staging + `holdout_assignment.py` |
| 3 | Khung Guardrail: `base.py`, orchestrator, `test_bypass_attempts.py` (viết test trước) |
| 4 | `bcollection-policy` với policy v1 và pipeline ký số |

Viết `test_bypass_attempts.py` **trước khi** viết Guardrail là có chủ đích: nó ép định hình đúng ranh giới ngay từ đầu, thay vì bổ sung kiểm tra sau khi kiến trúc đã cho phép đường vòng.

---

## 10. Việc cần quyết

| # | Câu hỏi | Người quyết |
|---|---|---|
| 1 | Nền tảng Git của Ngân hàng (GitLab/GitHub Enterprise/Bitbucket) và cơ chế phân quyền repo | Khối CNTT |
| 2 | Compliance Officer có tài khoản Git và được đào tạo review MR không? | Compliance + CNTT |
| 3 | Cơ chế ký số policy file — dùng PKI nội bộ nào? | Bảo mật |
| 4 | Chính sách dữ liệu cho môi trường UAT — ai duyệt bộ dữ liệu ẩn danh? | DPO |
| 5 | Có yêu cầu quét mã nguồn (SAST/SCA) bắt buộc theo chuẩn nội bộ không? | Bảo mật |

Câu 2 quan trọng hơn vẻ ngoài. Toàn bộ thiết kế kiểm soát dựa trên giả định Compliance Officer thực sự review và phê duyệt merge request. Nếu vai trò đó không có tài khoản Git hoặc chỉ ký duyệt hình thức qua email, cơ chế kiểm soát trở thành hình thức — và khi đó cần thiết kế lại quy trình phê duyệt cho phù hợp thực tế, chứ không nên giả vờ rằng nó đang hoạt động.

---

*Đề xuất cấu trúc repo, phiên bản thảo luận. Cần đối chiếu với chuẩn phát triển phần mềm và quy định quản lý mã nguồn nội bộ của Ngân hàng.*
