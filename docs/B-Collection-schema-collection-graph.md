# B.COLLECTION — THIẾT KẾ CHI TIẾT COLLECTION GRAPH
### Property Graph Schema, Bộ quy tắc chấm điểm cạnh & Pipeline xây dựng
**Phiên bản:** v0.1 | **Tài liệu mẹ:** B-Collection-kien-truc-tong-the.md (Mục 5.2) | **Nền tảng kế thừa:** Graph nhóm khách hàng liên quan (KHLQ)

---

## 1. Nguyên tắc thiết kế

| # | Nguyên tắc | Hệ quả kiến trúc |
|---|---|---|
| **G1** | **Tách tầng danh tính khỏi tầng quan hệ** | Cạnh dùng để *hợp nhất định danh* (`SAME_AS`, `SHARES_PHONE`) không bao giờ được dùng làm *đường liên hệ*. Đây là lỗi phổ biến nhất khiến hệ thống collection gọi nhầm người thân. |
| **G2** | **Contact eligibility là thuộc tính hạng nhất** | Mỗi cạnh phải khai báo `contact_eligible` (true/false/conditional). Graph biết ai *liên quan*, nhưng chỉ Guardrail quyết định ai được *liên hệ* — và Guardrail đọc chính thuộc tính này. |
| **G3** | **Bitemporal** | Mọi cạnh có `valid_from/valid_to` (thời gian thực tế) và `recorded_at` (thời gian hệ thống biết). Bắt buộc để trả lời "tại thời điểm cấp tín dụng, quan hệ này đã tồn tại chưa" và để phát hiện tẩu tán tài sản. |
| **G4** | **Không xoá, chỉ vô hiệu hoá** | Đóng cạnh bằng `valid_to` + `status='closed'`. Kiểm toán yêu cầu tái dựng được trạng thái graph tại bất kỳ thời điểm nào. |
| **G5** | **Provenance đầy đủ trên mọi cạnh và mọi thuộc tính suy diễn** | `source`, `evidence_ref`, `confidence`, `created_by`. Cạnh không có provenance không được dùng cho quyết định. |
| **G6** | **Suy diễn tách khỏi sự kiện** | Cạnh sự thật (`GUARANTEES` từ hợp đồng) và cạnh suy diễn (`LIKELY_CONTROLS` từ thuật toán) nằm ở namespace khác nhau, `derived=true`, có `model_version`. |
| **G7** | **Graph phục vụ hai chế độ đọc** | (a) Truy vấn điều tra real-time trên Neo4j; (b) Graph Feature Store dạng bảng phẳng trong lakehouse cho ML. Không để mô hình ML query graph online. |

---

## 2. Tổng quan mô hình 5 lớp

```
┌─ L-IDENT  Định danh & Hợp nhất ────────────────────────────────────┐
│  Person, Organization, IdentityDoc, PhoneNumber, EmailAddress,     │
│  Address, Device, BankAccountExt                                   │
│  Cạnh: HAS_IDENTITY, USES_PHONE, RESIDES_AT, USES_DEVICE, SAME_AS  │
├─ L-REL    Quan hệ pháp lý & xã hội ────────────────────────────────┤
│  Cạnh: FAMILY_OF, LEGAL_REP_OF, SHAREHOLDER_OF, EMPLOYED_BY,       │
│         GUARANTEES, CO_BORROWER_WITH, AUTHORIZED_BY, RELATED_PARTY │
├─ L-ASSET  Tài sản & Dòng tiền ─────────────────────────────────────┤
│  Collateral, Property, Vehicle, SecurityHolding, Account           │
│  Cạnh: OWNS, PLEDGES, CO_OWNS, TRANSFERRED_TO, TRANSACTS_WITH,     │
│         CASH_FLOW_TO                                               │
├─ L-CASE   Nghĩa vụ nợ & Thu hồi ───────────────────────────────────┤
│  Loan, CollectionCase, ContactAttempt, PTP, LegalCase, Employer    │
│  Cạnh: BORROWED, HAS_CASE, ATTEMPTED_CONTACT, MADE_PTP,            │
│         PARTY_TO_LEGAL_CASE                                        │
├─ L-DERIV  Suy diễn ────────────────────────────────────────────────┤
│  ConnectedGroup, PersonaCluster                                    │
│  Cạnh: MEMBER_OF_GROUP, SIMILAR_PERSONA_TO, LIKELY_CONTROLS,       │
│         LIKELY_SAME_HOUSEHOLD, SUSPECTED_DISSIPATION               │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3. Thuộc tính chuẩn dùng chung (Common Property Envelope)

Áp dụng cho **mọi cạnh** và mọi node suy diễn:

| Thuộc tính | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `edge_id` | STRING | ✓ | UUID / hash(src, dst, type, valid_from) |
| `source` | STRING | ✓ | Enum: `CORE`, `LOS`, `CIF`, `CIC`, `NDKKD`, `DKGDBD`, `COURT`, `MANUAL`, `OSINT_GREEN`, `DERIVED` |
| `source_ref` | STRING | ✓ | Số hợp đồng / mã bản ghi nguồn / `case_id` nếu nhập tay |
| `evidence_type` | STRING | ✓ | `CONTRACT`, `LEGAL_DOC`, `SYSTEM_RECORD`, `PUBLIC_REGISTRY`, `SELF_DECLARED`, `STAFF_OBSERVED`, `INFERRED` |
| `evidence_strength` | INT 1–5 | ✓ | Xem Mục 8.2 |
| `confidence` | FLOAT 0–1 | ✓ | Kết quả tính từ công thức Mục 8 |
| `weight` | FLOAT 0–1 | ✓ | Cường độ quan hệ (khác confidence — xem 8.1) |
| `contact_eligible` | STRING | ✓ | `YES` / `NO` / `CONDITIONAL` — Mục 7 |
| `valid_from` | DATE | ✓ | Thời điểm quan hệ bắt đầu có hiệu lực thực tế |
| `valid_to` | DATE | – | NULL = còn hiệu lực |
| `recorded_at` | DATETIME | ✓ | Thời điểm hệ thống ghi nhận |
| `status` | STRING | ✓ | `ACTIVE`, `CLOSED`, `DISPUTED`, `REJECTED` |
| `created_by` | STRING | ✓ | User ID hoặc `SYSTEM:<pipeline>` |
| `verified_by` | STRING | – | Bắt buộc với `source=MANUAL` và cạnh nhạy cảm (4 mắt) |
| `derived` | BOOLEAN | ✓ | true nếu do thuật toán sinh |
| `model_version` | STRING | – | Bắt buộc khi `derived=true` |
| `corroboration_count` | INT | ✓ | Số nguồn độc lập xác nhận cùng quan hệ |
| `legal_basis` | STRING | ✓ | Cơ sở pháp lý xử lý dữ liệu (`CONTRACT`, `LEGAL_OBLIGATION`, `LEGITIMATE_INTEREST`, `CONSENT`) |
| `ttl_expiry` | DATE | – | Ngày hết hạn lưu trữ theo chính sách dữ liệu |

> **Quy ước:** thuộc tính trên là *envelope*; các bảng cạnh ở Mục 6 chỉ liệt kê thuộc tính **đặc thù bổ sung**.

---

## 4. Danh mục Node

### 4.1 L-IDENT

**`:Person`** — cá nhân (khách hàng, người liên quan, người đại diện)
| Thuộc tính | Kiểu | Ghi chú |
|---|---|---|
| `person_id` | STRING | **Khoá duy nhất** — golden record ID sau entity resolution |
| `cif_no` | STRING[] | Danh sách CIF đã hợp nhất (có thể nhiều) |
| `full_name` | STRING | Có dấu, đã chuẩn hoá |
| `name_normalized` | STRING | Không dấu, lowercase, dùng cho blocking |
| `dob` | DATE | |
| `gender` | STRING | |
| `nationality` | STRING | |
| `is_customer` | BOOLEAN | Phân biệt khách hàng BIDV vs người liên quan bên ngoài |
| `is_debtor` | BOOLEAN | Đang có nghĩa vụ nợ quá hạn |
| `pep_flag` | BOOLEAN | Người có ảnh hưởng chính trị |
| `deceased_flag` | BOOLEAN | Ảnh hưởng trực tiếp tới chiến lược thu hồi |
| `vulnerability_flag` | BOOLEAN | Đồng bộ từ Guardrail; **khoá treatment cứng** |
| `dnc_flag` | BOOLEAN | Do-not-contact |
| `persona_cluster_id` | STRING | Từ ML10 |
| `er_status` | STRING | `RESOLVED`, `PENDING_REVIEW`, `SPLIT` |
| `data_class` | STRING | Luôn `PII_HIGH` |

**`:Organization`** — pháp nhân, hộ kinh doanh
| Thuộc tính | Ghi chú |
|---|---|
| `org_id` | Khoá duy nhất |
| `tax_code` | MST — định danh mạnh nhất tại VN |
| `enterprise_code` | Mã số doanh nghiệp |
| `legal_name`, `name_normalized`, `trade_name` | |
| `org_type` | `JSC`, `LLC`, `HOUSEHOLD_BIZ`, `COOP`, `FDI`, `STATE` |
| `industry_code` | VSIC cấp 4 |
| `charter_capital`, `established_date` | |
| `operating_status` | `ACTIVE`, `SUSPENDED`, `DISSOLVED`, `BANKRUPT` — cực quan trọng với thu hồi |
| `status_source`, `status_checked_at` | Nguồn & thời điểm kiểm tra trạng thái |
| `is_shell_suspected` | Cờ suy diễn (vốn nhỏ + nhiều thay đổi ĐDPL + không phát sinh thuế) |

**`:IdentityDoc`** — CCCD/CMND/hộ chiếu/GPKD
`doc_id` (hash), `doc_type`, `doc_number_token` (**tokenized, không lưu plaintext**), `issue_date`, `issue_place`, `status`

**`:PhoneNumber`**
| Thuộc tính | Ghi chú |
|---|---|
| `phone_id` | Hash của E.164 |
| `e164` | Chuẩn hoá +84… |
| `carrier`, `line_type` | `MOBILE`, `FIXED`, `VOIP` |
| `is_active` | Kết quả kiểm tra gần nhất |
| `contactability_score` | 0–1, cập nhật từ lịch sử liên hệ thực tế |
| `last_rpc_at` | Lần gần nhất gặp đúng người |
| `shared_degree` | Số Person/Org gắn với số này — **>3 là tín hiệu cảnh báo** (số tổng đài, số môi giới, hoặc số khai khống) |

**`:Address`**
`address_id`, `raw_text`, `normalized_text`, `admin_code` (mã ĐVHC hiện hành), `admin_code_history` (ánh xạ theo biến động địa giới), `geohash`, `address_type` (`RESIDENTIAL`, `BUSINESS`, `REGISTERED`, `CORRESPONDENCE`), `verified_flag`, `verified_at`, `verification_method`

**`:Device`** — chỉ từ kênh số của BIDV
`device_id`, `device_fingerprint_token`, `os`, `first_seen`, `last_seen`, `shared_degree`

**`:EmailAddress`**, **`:BankAccountExt`** (tài khoản tại TCTD khác, biết qua giao dịch chuyển tiền): `account_no_token`, `bank_code`, `holder_name_raw`

### 4.2 L-ASSET

**`:Collateral`** — TSBĐ đã đăng ký tại BIDV
| Thuộc tính | Ghi chú |
|---|---|
| `collateral_id`, `collateral_type` | `REAL_ESTATE`, `VEHICLE`, `MACHINERY`, `INVENTORY`, `RECEIVABLE`, `SECURITIES`, `DEPOSIT` |
| `appraised_value`, `appraisal_date`, `appraiser` | |
| `current_ltv`, `legal_status` | `CLEAN`, `DISPUTED`, `UNDER_ENFORCEMENT`, `SEIZED` |
| `registration_no` | Số đăng ký giao dịch bảo đảm |
| `liquidity_score` | 1–5, đầu vào cho ML3/ML7 |
| `physical_verified_at` | Lần kiểm tra thực địa gần nhất |

**`:Property`** / **`:Vehicle`** — bất động sản / phương tiện biết qua nguồn khác (không phải TSBĐ tại BIDV), phục vụ đánh giá khả năng trả và phát hiện tẩu tán.
`asset_id`, `identifier_token` (số GCN / biển số, tokenized), `estimated_value`, `source`, `encumbrance_flag` (đang thế chấp nơi khác)

**`:Account`** — tài khoản tại BIDV
`account_id`, `account_type`, `open_date`, `status`, `avg_balance_3m`, `inflow_3m`, `last_txn_date`, `is_salary_account`

### 4.3 L-CASE

**`:Loan`**
`loan_id`, `product_code`, `segment` (`RETAIL`/`SME`/`CORP`), `disbursed_amount`, `outstanding_principal`, `outstanding_interest`, `dpd`, `npl_group` (1–5), `origination_date`, `maturity_date`, `restructure_count`, `purpose_code`, `is_offbalance`

**`:CollectionCase`**
`case_id`, `loan_id`, `bucket`, `status`, `assigned_to`, `strategy_cell_id`, `opened_at`, `closed_at`, `outcome`, `recovery_amount`, `cost_to_collect`, `persona_vector_ref`, `compliance_review` (`PASSED`/`FLAGGED`/`FAILED`), `experiment_arm` (`CHAMPION`/`CHALLENGER`/`CONTROL`)

**`:ContactAttempt`** — node chứ không phải cạnh, vì có vòng đời và thuộc tính phong phú
`attempt_id`, `channel`, `attempted_at`, `outcome` (`RPC`, `WRONG_PARTY`, `NO_ANSWER`, `REFUSED`, `DISPUTED`), `duration_sec`, `guardrail_decision`, `recording_ref`, `sentiment_score`

**`:PTP`** (Promise to Pay)
`ptp_id`, `promised_amount`, `promised_date`, `kept` (BOOLEAN), `actual_paid`, `channel_agreed`

**`:LegalCase`**
`legal_case_id`, `court_code`, `case_no`, `filed_date`, `case_type`, `stage`, `judgment_date`, `enforcement_status`, `source` (`INTERNAL`/`COURT_PORTAL`)

**`:Employer`** — có thể là `:Organization` hoặc node độc lập nếu ngoài hệ thống
`employer_id`, `name_normalized`, `salary_cycle_day`, `source`

### 4.4 L-DERIV

**`:ConnectedGroup`** — kế thừa từ hệ thống KHLQ
`group_id`, `algorithm` (`LOUVAIN`/`WCC`/`RULE_BASED`), `run_id`, `member_count`, `total_exposure`, `total_overdue`, `central_node_id`, `group_risk_score`, `computed_at`, `model_version`

**`:PersonaCluster`**
`cluster_id`, `label`, `centroid_ref`, `member_count`, `avg_recovery_rate`, `dominant_root_cause`, `model_version`

---

## 5. Danh mục Cạnh — L-IDENT (tầng danh tính)

> **Cảnh báo thiết kế (G1):** toàn bộ cạnh trong tầng này có `contact_eligible = NO` theo mặc định. Chúng phục vụ *tìm kiếm và hợp nhất*, không phải *liên hệ*.

| Cạnh | Từ → Đến | Thuộc tính đặc thù | Dùng để |
|---|---|---|---|
| `HAS_IDENTITY` | Person → IdentityDoc | `is_primary` | Định danh mạnh |
| `USES_PHONE` | Person\|Organization → PhoneNumber | `phone_role` (`PRIMARY`,`SECONDARY`,`WORK`,`REFERENCE`), `declared_at`, `last_verified_at`, `verification_result` | Skip-tracing |
| `USES_EMAIL` | Person\|Organization → EmailAddress | `email_role` | |
| `RESIDES_AT` / `REGISTERED_AT` / `OPERATES_AT` | Person\|Org → Address | `since`, `residence_type` | Field visit, skip-tracing |
| `USES_DEVICE` | Person → Device | `first_seen`, `last_seen`, `session_count` | Phát hiện chung hộ / chung người dùng |
| `SAME_AS` | Person → Person, Org → Org | `match_score`, `match_rule`, `reviewed_by`, `decision` (`MERGE`,`REJECT`,`PENDING`) | **Entity resolution** — không bao giờ dùng làm đường liên hệ |
| `LINKED_ACCOUNT` | Person\|Org → BankAccountExt | `first_seen_txn`, `txn_count` | Truy vết tài khoản ngoại bank |

**Cạnh suy diễn từ tầng danh tính** (namespace riêng, `derived=true`):
| Cạnh | Sinh từ | Ý nghĩa |
|---|---|---|
| `SHARES_PHONE` | 2 node cùng trỏ 1 PhoneNumber có `shared_degree ≤ 3` | Gợi ý cùng hộ / cùng đơn vị |
| `SHARES_ADDRESS` | Cùng Address `RESIDENTIAL` đã verify | Gợi ý cùng hộ gia đình |
| `SHARES_DEVICE` | Cùng Device, session chồng lấn | Tín hiệu mạnh nhất trong 3 loại |
| `LIKELY_SAME_HOUSEHOLD` | Tổ hợp ≥2 tín hiệu trên | Phục vụ tìm lại khách hàng mất liên lạc |

> Với `shared_degree > 3`, PhoneNumber/Address bị đánh dấu `is_hub=true` và **không sinh cạnh suy diễn** — đây là cơ chế chống bùng nổ cạnh từ số tổng đài, địa chỉ chung cư, địa chỉ khu công nghiệp.

---

## 6. Danh mục Cạnh — L-REL, L-ASSET, L-CASE

### 6.1 L-REL — Quan hệ pháp lý & xã hội

| Cạnh | Từ → Đến | Thuộc tính đặc thù | `contact_eligible` mặc định |
|---|---|---|---|
| `GUARANTEES` | Person\|Org → Loan | `guarantee_type` (`PERSONAL`,`CORPORATE`,`ASSET`), `guarantee_amount`, `contract_no`, `is_joint_several` | **YES** — có nghĩa vụ pháp lý |
| `CO_BORROWER_WITH` | Person ↔ Person\|Org (trên Loan) | `share_pct`, `liability_type` | **YES** |
| `LEGAL_REP_OF` | Person → Organization | `title`, `appointment_date`, `is_current`, `change_count` | **YES** (khi liên hệ về nghĩa vụ của pháp nhân) |
| `AUTHORIZED_BY` | Person → Person\|Org | `power_of_attorney_no`, `scope`, `expiry` | **CONDITIONAL** — theo phạm vi uỷ quyền |
| `SHAREHOLDER_OF` | Person\|Org → Organization | `ownership_pct`, `is_beneficial_owner`, `as_of_date` | **CONDITIONAL** — chỉ khi có nghĩa vụ liên đới |
| `DIRECTOR_OF` / `CONTROLS` | Person → Organization | `role`, `control_type` | **CONDITIONAL** |
| `FAMILY_OF` | Person ↔ Person | `relation_type` (`SPOUSE`,`PARENT`,`CHILD`,`SIBLING`), `is_marital_property_regime` | **NO** (mặc định) / **CONDITIONAL** với vợ-chồng khi tài sản chung |
| `EMPLOYED_BY` | Person → Employer\|Organization | `since`, `salary_cycle_day`, `income_band` | **NO** — dùng để định thời điểm có dòng tiền, **không** để liên hệ nơi làm việc |
| `REFERENCE_CONTACT_OF` | Person → Person | `consent_obtained` (BOOLEAN), `consent_ref`, `declared_by_debtor` | **CONDITIONAL — chỉ YES khi `consent_obtained=true`** |
| `RELATED_PARTY_OF` | Person\|Org ↔ Person\|Org | `rule_code` (mã quy định), `basis` | **NO** — mục đích rủi ro tín dụng, không phải liên hệ |

> `FAMILY_OF` và `EMPLOYED_BY` là hai cạnh **nguy hiểm nhất** trong toàn schema. Chúng cực kỳ hữu ích để hiểu bối cảnh và định thời điểm dòng tiền, nhưng nếu bị dùng làm đường liên hệ thì vi phạm nguyên tắc "không nhắc nợ với người không có nghĩa vụ trả nợ". Vì vậy `contact_eligible=NO` được **hard-code ở tầng schema**, không cho phép ghi đè bằng cấu hình.

### 6.2 L-ASSET — Tài sản & Dòng tiền

| Cạnh | Từ → Đến | Thuộc tính đặc thù | Dùng để |
|---|---|---|---|
| `OWNS` | Person\|Org → Collateral\|Property\|Vehicle\|Account | `ownership_pct`, `acquired_date`, `title_doc_ref` | Xác định tài sản có thể xử lý |
| `CO_OWNS` | Person ↔ Person (qua Asset) | `co_owner_type`, `consent_required` | Cảnh báo: xử lý TSBĐ cần đồng thuận đồng sở hữu |
| `PLEDGES` | Person\|Org → Collateral | `loan_id`, `pledge_rank`, `registered_at` | Thứ tự ưu tiên thanh toán |
| `PLEDGED_TO_EXTERNAL` | Asset → Organization(TCTD khác) | `registry_ref`, `registered_at` | Tài sản đã thế chấp nơi khác |
| `TRANSFERRED_TO` | Person\|Org → Person\|Org | `asset_id`, `transfer_date`, `declared_value`, `days_before_default`, `is_related_party` | **Phát hiện tẩu tán tài sản** |
| `TRANSACTS_WITH` | Account\|Org → Account\|BankAccountExt | `total_amount_12m`, `txn_count_12m`, `avg_amount`, `direction`, `first_txn`, `last_txn`, `regularity_score` | Dòng tiền thực, tài khoản ẩn |
| `CASH_FLOW_TO` | Organization → Organization | `net_amount_12m`, `dependency_ratio` | Nhận diện đối tác lớn của KHDN — nguồn thu hồi tiềm năng qua thoả thuận ba bên |

**Quy tắc chống nhiễu cho `TRANSACTS_WITH`:** chỉ tạo cạnh khi `total_amount_12m ≥ ngưỡng theo phân khúc` **và** `txn_count_12m ≥ 3`; loại trừ counterparty là node `is_hub=true` (ví điện tử, cổng thanh toán, kho bạc, tài khoản thuế). Không có bộ lọc này, graph sẽ có hàng tỷ cạnh vô nghĩa.

### 6.3 L-CASE — Nghĩa vụ & Thu hồi

| Cạnh | Từ → Đến | Thuộc tính đặc thù |
|---|---|---|
| `BORROWED` | Person\|Org → Loan | `role` (`PRIMARY`,`CO`), `share_pct` |
| `SECURED_BY` | Loan → Collateral | `coverage_ratio`, `pledge_rank` |
| `HAS_CASE` | Loan → CollectionCase | |
| `TARGETS` | CollectionCase → Person\|Org | `party_role` (`DEBTOR`,`GUARANTOR`,`CO_BORROWER`) |
| `ATTEMPTED_CONTACT` | CollectionCase → PhoneNumber\|Address\|EmailAddress | `attempt_id`, `outcome`, `attempted_at`, `guardrail_decision` |
| `MADE_PTP` | Person\|Org → PTP | |
| `PTP_FOR` | PTP → CollectionCase | |
| `PARTY_TO_LEGAL_CASE` | Person\|Org → LegalCase | `party_role` (`PLAINTIFF`,`DEFENDANT`,`THIRD_PARTY`) |
| `SIMILAR_CASE_TO` | CollectionCase ↔ CollectionCase | `similarity`, `vector_model_version` — nền tảng Case Reference Engine |

### 6.4 L-DERIV

| Cạnh | Ý nghĩa | Điều kiện sinh |
|---|---|---|
| `MEMBER_OF_GROUP` | Person\|Org → ConnectedGroup | Louvain / WCC trên subgraph có `weight ≥ θ` |
| `IN_PERSONA_CLUSTER` | Person\|Org → PersonaCluster | Từ ML10 |
| `SIMILAR_PERSONA_TO` | Person ↔ Person | cosine(persona_vector) ≥ 0.85, cùng phân khúc |
| `LIKELY_CONTROLS` | Person → Organization | Tổ hợp: sở hữu gián tiếp, đồng ĐDPL, kiểm soát dòng tiền, chung địa chỉ |
| `SUSPECTED_DISSIPATION` | Person\|Org → Person\|Org | `TRANSFERRED_TO` với `days_before_default ∈ [-365, 0]` và `is_related_party=true` và `declared_value < market_estimate × 0.7` |

---

## 7. Mô hình Contact Eligibility (điểm tuân thủ cốt lõi)

Guardrail Service không tự suy luận ai được liên hệ — nó **truy vấn graph**. Vì vậy quy tắc phải nằm trong schema.

### 7.1 Ba mức
| Giá trị | Nghĩa | Ví dụ |
|---|---|---|
| `YES` | Có nghĩa vụ pháp lý trực tiếp với khoản nợ | Bên vay, đồng vay, bên bảo lãnh, ĐDPL của pháp nhân vay |
| `CONDITIONAL` | Được liên hệ khi thoả điều kiện kiểm tra runtime | Người tham chiếu có `consent_obtained=true`; vợ/chồng khi tài sản là tài sản chung và đang xử lý TSBĐ; người được uỷ quyền trong phạm vi uỷ quyền còn hiệu lực |
| `NO` | Không được liên hệ về nghĩa vụ nợ trong mọi trường hợp | Người thân không có nghĩa vụ, đồng nghiệp, nơi làm việc, đối tác kinh doanh, hàng xóm, node phát hiện qua `SHARES_*` |

### 7.2 Truy vấn chuẩn của Guardrail
```cypher
// Kiểm tra: có được liên hệ target_party về case này không?
MATCH (c:CollectionCase {case_id: $case_id})-[:HAS_CASE]-(l:Loan)
MATCH (p) WHERE p.person_id = $target_id OR p.org_id = $target_id
OPTIONAL MATCH path = (p)-[r]->(l)
WHERE type(r) IN ['BORROWED','GUARANTEES']
  AND r.status = 'ACTIVE'
  AND (r.valid_to IS NULL OR r.valid_to > date())
OPTIONAL MATCH (p)-[cr:REFERENCE_CONTACT_OF|AUTHORIZED_BY]->(:Person)-[:BORROWED]->(l)
WHERE cr.contact_eligible = 'CONDITIONAL'
  AND coalesce(cr.consent_obtained, false) = true
  AND (cr.expiry IS NULL OR cr.expiry > date())
RETURN
  CASE
    WHEN p.dnc_flag = true THEN 'BLOCK_DNC'
    WHEN p.vulnerability_flag = true THEN 'ESCALATE_VULNERABLE'
    WHEN p.deceased_flag = true THEN 'BLOCK_DECEASED'
    WHEN path IS NOT NULL THEN 'ALLOW_OBLIGATED'
    WHEN cr IS NOT NULL THEN 'ALLOW_CONSENTED'
    ELSE 'BLOCK_NO_LEGAL_BASIS'
  END AS decision,
  r.contact_eligible AS basis;
```
**Fail-closed:** truy vấn không trả kết quả rõ ràng → `BLOCK_NO_LEGAL_BASIS`. Mọi lần trả về `BLOCK_*` đều ghi audit log.

### 7.3 Quy tắc bất biến
`contact_eligible` **không phải trường tự do**. Nó được gán bởi bảng ánh xạ cứng theo `edge_type` trong pipeline build, và chỉ có 2 cạnh cho phép nâng lên `YES` tại runtime: `REFERENCE_CONTACT_OF` (khi có consent) và `AUTHORIZED_BY` (trong phạm vi uỷ quyền). Mọi thay đổi bảng ánh xạ này cần phê duyệt của Compliance Officer và được version-control.

---

## 8. Bộ quy tắc chấm điểm cạnh

### 8.1 Phân biệt `weight` và `confidence`
- **`confidence`** = *quan hệ này có thật không?* (0–1)
- **`weight`** = *quan hệ này mạnh đến mức nào?* (0–1)

Ví dụ: cạnh `SHAREHOLDER_OF` với 2% cổ phần lấy từ đăng ký kinh doanh có `confidence=0.95` (chắc chắn có thật) nhưng `weight=0.10` (ảnh hưởng yếu). Ngược lại, `SHARES_DEVICE` suy diễn có `confidence=0.6` nhưng nếu đúng thì `weight=0.8`. **Gộp hai chỉ số này là sai lầm thiết kế phổ biến** — nó khiến thuật toán cộng đồng cho ra kết quả vô nghĩa.

### 8.2 Công thức `confidence`
```
confidence = clip( w_base(evidence_type)
                   × decay(age_days, half_life(edge_type))
                   × corroboration_factor(n)
                   × source_reliability(source),
                 0.05, 0.99 )
```

**`w_base` theo `evidence_strength` / `evidence_type`:**
| evidence_type | strength | w_base |
|---|---|---|
| `CONTRACT` (hợp đồng BIDV ký) | 5 | 1.00 |
| `LEGAL_DOC` (bản án, công chứng, ĐKGDBĐ) | 5 | 0.98 |
| `PUBLIC_REGISTRY` (ĐKKD, CIC) | 4 | 0.92 |
| `SYSTEM_RECORD` (giao dịch core, log kênh số) | 4 | 0.90 |
| `STAFF_OBSERVED` (cán bộ xác minh thực địa, đã duyệt 4 mắt) | 3 | 0.75 |
| `SELF_DECLARED` (khách hàng tự khai) | 2 | 0.55 |
| `OSINT_GREEN` (nguồn công khai chính thống, đã verify) | 2 | 0.50 |
| `INFERRED` (thuật toán) | 1 | 0.40 × model_precision |

**`decay` — suy giảm theo thời gian:**
```
decay = 0.5 ^ (age_days / half_life)
```
| Nhóm cạnh | half_life (ngày) | Lý do |
|---|---|---|
| Cạnh pháp lý (`GUARANTEES`, `CO_BORROWER_WITH`, `PLEDGES`) | ∞ (không decay) | Hiệu lực đến khi đóng bằng `valid_to` |
| Sở hữu (`OWNS`, `SHAREHOLDER_OF`) | 1095 (3 năm) | Cần tái xác minh định kỳ |
| Vai trò (`LEGAL_REP_OF`, `EMPLOYED_BY`) | 540 | Biến động vừa phải |
| Liên hệ (`USES_PHONE`, `RESIDES_AT`) | **180** | Số điện thoại/địa chỉ VN thay đổi nhanh |
| Giao dịch (`TRANSACTS_WITH`) | 365 | Dùng cửa sổ trượt 12 tháng |
| Suy diễn (`SHARES_*`, `LIKELY_*`) | 270 | Phải tái tính mỗi chu kỳ |

**`corroboration_factor`** (n = số nguồn độc lập):
```
n=1 → 1.00 ;  n=2 → 1.12 ;  n=3 → 1.20 ;  n≥4 → 1.25
```

**`source_reliability`:** `CORE/LOS`=1.0, `CIC`=0.98, `NDKKD/DKGDBD/COURT`=0.95, `MANUAL` đã duyệt=0.9, `MANUAL` chưa duyệt=0.6, `OSINT_GREEN`=0.7.

### 8.3 Công thức `weight` theo nhóm cạnh

| Cạnh | Công thức `weight` |
|---|---|
| `GUARANTEES` | `min(1, guarantee_amount / outstanding)` × (1.0 nếu `is_joint_several` else 0.8) |
| `CO_BORROWER_WITH` | `share_pct` (tối thiểu 0.5 nếu liên đới) |
| `SHAREHOLDER_OF` | `min(1, ownership_pct / 0.5)`; +0.3 nếu `is_beneficial_owner` |
| `LEGAL_REP_OF` | 0.9; giảm còn 0.5 nếu `is_current=false` |
| `OWNS` | `ownership_pct` × normalize(`asset_value`) |
| `TRANSACTS_WITH` | `0.5×norm(log(total_amount)) + 0.3×regularity_score + 0.2×norm(txn_count)` |
| `CASH_FLOW_TO` | `dependency_ratio` (tỷ trọng đối tác trong tổng dòng tiền) |
| `FAMILY_OF` | `SPOUSE`=0.9, `PARENT/CHILD`=0.7, `SIBLING`=0.5 |
| `SHARES_PHONE` | `0.8 / shared_degree` |
| `SHARES_ADDRESS` | `0.6 / shared_degree` × (1.5 nếu `verified_flag` và `RESIDENTIAL`) |
| `SHARES_DEVICE` | `0.85 × min(1, session_overlap_days / 30)` |
| `TRANSFERRED_TO` | `min(1, declared_value / total_exposure)` |

**Trọng số hiệu dụng dùng cho thuật toán đồ thị:**
```
effective_weight = confidence × weight
```
Ngưỡng mặc định để đưa cạnh vào phân cụm: `effective_weight ≥ 0.35`. Ngưỡng này là **tham số cấu hình được**, không hard-code — nó cần tinh chỉnh theo phân khúc (KHDN chặt hơn bán lẻ).

### 8.4 Chấm điểm nhóm (`group_risk_score`)
```
group_risk_score = 0.30 × norm(total_overdue)
                 + 0.20 × norm(max_dpd_in_group)
                 + 0.20 × contagion_index      // tỷ lệ thành viên có nợ quá hạn
                 + 0.15 × dissipation_signal   // số cạnh SUSPECTED_DISSIPATION
                 + 0.15 × opacity_index        // shell suspected, đổi ĐDPL nhiều, sở hữu vòng
```

---

## 9. Entity Resolution — tích hợp vào graph

### 9.1 Ba tầng
1. **Deterministic:** trùng MST / CCCD token / mã doanh nghiệp → merge tự động, `match_score=1.0`
2. **Probabilistic:** Fellegi–Sunter trên `name_normalized` (Jaro-Winkler có xử lý tiếng Việt: bỏ dấu, chuẩn hoá tên đệm, xử lý biến thể "Nguyễn Thị" vs "Nguyen Thi"), `dob`, `phone`, `address_admin_code`
3. **Graph-assisted:** hai node có ≥2 láng giềng chung mạnh → nâng match_score

### 9.2 Ngưỡng
| Score | Hành động |
|---|---|
| ≥ 0.95 | Auto-merge, tạo `SAME_AS` với `decision=MERGE` |
| 0.75 – 0.95 | **Human review queue** — `decision=PENDING`, không merge |
| < 0.75 | Không tạo cạnh |

Vùng xám 0.75–0.95 là nơi phát sinh rủi ro "liên hệ nhầm người" nghiêm trọng nhất. Bắt buộc có người duyệt, và **mọi merge đều reversible** (giữ `person_id` gốc, lưu `merge_log`, có thủ tục split).

---

## 10. DDL — Ràng buộc & Chỉ mục (Neo4j)

```cypher
// --- Uniqueness constraints ---
CREATE CONSTRAINT person_id IF NOT EXISTS
  FOR (p:Person) REQUIRE p.person_id IS UNIQUE;
CREATE CONSTRAINT org_id IF NOT EXISTS
  FOR (o:Organization) REQUIRE o.org_id IS UNIQUE;
CREATE CONSTRAINT org_tax IF NOT EXISTS
  FOR (o:Organization) REQUIRE o.tax_code IS UNIQUE;
CREATE CONSTRAINT phone_id IF NOT EXISTS
  FOR (ph:PhoneNumber) REQUIRE ph.phone_id IS UNIQUE;
CREATE CONSTRAINT address_id IF NOT EXISTS
  FOR (a:Address) REQUIRE a.address_id IS UNIQUE;
CREATE CONSTRAINT loan_id IF NOT EXISTS
  FOR (l:Loan) REQUIRE l.loan_id IS UNIQUE;
CREATE CONSTRAINT case_id IF NOT EXISTS
  FOR (c:CollectionCase) REQUIRE c.case_id IS UNIQUE;
CREATE CONSTRAINT collateral_id IF NOT EXISTS
  FOR (cl:Collateral) REQUIRE cl.collateral_id IS UNIQUE;

// --- Existence constraints (Enterprise) ---
CREATE CONSTRAINT person_data_class IF NOT EXISTS
  FOR (p:Person) REQUIRE p.data_class IS NOT NULL;

// --- Indexes phục vụ truy vấn nóng ---
CREATE INDEX person_name_norm IF NOT EXISTS
  FOR (p:Person) ON (p.name_normalized);
CREATE INDEX person_debtor IF NOT EXISTS
  FOR (p:Person) ON (p.is_debtor);
CREATE INDEX loan_dpd IF NOT EXISTS
  FOR (l:Loan) ON (l.dpd);
CREATE INDEX case_bucket_status IF NOT EXISTS
  FOR (c:CollectionCase) ON (c.bucket, c.status);
CREATE INDEX addr_admin IF NOT EXISTS
  FOR (a:Address) ON (a.admin_code);

// --- Relationship property indexes (rất quan trọng cho lọc theo thời gian) ---
CREATE INDEX rel_guarantees_valid IF NOT EXISTS
  FOR ()-[r:GUARANTEES]-() ON (r.valid_to);
CREATE INDEX rel_transacts_amt IF NOT EXISTS
  FOR ()-[r:TRANSACTS_WITH]-() ON (r.total_amount_12m);
CREATE INDEX rel_transfer_date IF NOT EXISTS
  FOR ()-[r:TRANSFERRED_TO]-() ON (r.transfer_date);

// --- Full-text cho điều tra ---
CREATE FULLTEXT INDEX entity_search IF NOT EXISTS
  FOR (n:Person|Organization) ON EACH [n.full_name, n.legal_name, n.name_normalized];
```

---

## 11. Truy vấn nghiệp vụ mẫu

### 11.1 Skip-tracing — tìm lại khách hàng mất liên lạc
```cypher
MATCH (p:Person {person_id: $debtor_id})
MATCH (p)-[u:USES_PHONE|RESIDES_AT|USES_DEVICE]->(node)
MATCH (node)<-[u2:USES_PHONE|RESIDES_AT|USES_DEVICE]-(other)
WHERE other <> p
  AND coalesce(node.is_hub, false) = false
  AND u.confidence * u2.confidence > 0.4
OPTIONAL MATCH (other)-[:USES_PHONE]->(newPhone:PhoneNumber)
WHERE newPhone.is_active = true
  AND NOT (p)-[:USES_PHONE]->(newPhone)
RETURN other.person_id, labels(other) AS type,
       collect(DISTINCT newPhone.e164) AS candidate_phones,
       max(u.confidence * u2.confidence) AS link_strength,
       // BẮT BUỘC hiển thị: có được liên hệ hay không
       [(p)-[r]-(other) WHERE r.contact_eligible = 'YES' | type(r)] AS legal_basis
ORDER BY link_strength DESC LIMIT 20;
```
> **Lưu ý vận hành:** kết quả trả về là *manh mối điều tra*, không phải danh sách để gọi. Nếu `legal_basis` rỗng, số điện thoại tìm được **chỉ dùng để xác minh nơi khách hàng có thể đang ở**, và mọi liên hệ vẫn phải qua Guardrail.

### 11.2 Cảnh báo tẩu tán tài sản
```cypher
MATCH (d:Person|Organization)-[:BORROWED]->(l:Loan)
WHERE l.dpd > 0
MATCH (d)-[t:TRANSFERRED_TO]->(recipient)
WHERE t.transfer_date >= date(l.origination_date)
  AND duration.inDays(t.transfer_date, date()).days <= 730
OPTIONAL MATCH (d)-[rp:RELATED_PARTY_OF|FAMILY_OF|SHAREHOLDER_OF*1..2]-(recipient)
WITH d, l, t, recipient, count(rp) AS related_hops
WHERE related_hops > 0 OR t.declared_value < t.market_estimate * 0.7
RETURN d.person_id AS debtor, l.loan_id, recipient,
       t.asset_id, t.transfer_date, t.declared_value, t.market_estimate,
       related_hops,
       CASE WHEN related_hops > 0 AND t.declared_value < t.market_estimate * 0.7
            THEN 'HIGH' ELSE 'MEDIUM' END AS alert_level
ORDER BY alert_level, t.transfer_date DESC;
```

### 11.3 Nhóm nợ liên đới — chuyển sang đàm phán cả nhóm
```cypher
MATCH (g:ConnectedGroup)<-[:MEMBER_OF_GROUP]-(m)
MATCH (m)-[:BORROWED]->(l:Loan)
WITH g, collect(DISTINCT m) AS members,
     sum(l.outstanding_principal) AS total_exposure,
     sum(CASE WHEN l.dpd > 0 THEN l.outstanding_principal ELSE 0 END) AS overdue_exposure,
     count(DISTINCT CASE WHEN l.dpd > 0 THEN m END) AS overdue_members,
     count(DISTINCT m) AS total_members
WHERE overdue_exposure > $threshold
RETURN g.group_id, g.central_node_id, g.group_risk_score,
       total_members, overdue_members,
       toFloat(overdue_members)/total_members AS contagion_ratio,
       total_exposure, overdue_exposure
ORDER BY overdue_exposure DESC;
```

### 11.4 Xác định "nút kiểm soát thực" của nhóm KHDN
```cypher
CALL gds.graph.project.cypher(
  'ctrl_graph',
  'MATCH (n) WHERE n:Person OR n:Organization RETURN id(n) AS id',
  'MATCH (a)-[r:SHAREHOLDER_OF|LEGAL_REP_OF|CONTROLS|CASH_FLOW_TO]->(b)
   WHERE r.confidence * r.weight >= 0.35
   RETURN id(a) AS source, id(b) AS target, r.confidence * r.weight AS weight'
) YIELD graphName;

CALL gds.pageRank.stream('ctrl_graph', {relationshipWeightProperty:'weight'})
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS n, score
WHERE n.person_id IS NOT NULL
RETURN n.person_id, n.full_name, score
ORDER BY score DESC LIMIT 50;
```

### 11.5 Đường liên hệ hợp pháp gần nhất
```cypher
MATCH (l:Loan {loan_id: $loan_id})
MATCH (party)-[r]->(l)
WHERE r.contact_eligible = 'YES'
  AND r.status = 'ACTIVE'
  AND (r.valid_to IS NULL OR r.valid_to > date())
MATCH (party)-[up:USES_PHONE]->(ph:PhoneNumber)
WHERE ph.is_active = true AND coalesce(party.dnc_flag,false) = false
RETURN party, type(r) AS obligation_type, ph.e164,
       ph.contactability_score, ph.last_rpc_at
ORDER BY ph.contactability_score DESC;
```

---

## 12. Graph Feature Store — đầu ra cho ML

Tính bằng PySpark/GDS theo lô đêm, ghi ra bảng phẳng `gold.gft_debtor_graph_features`:

| Feature | Kiểu | Dùng cho mô hình |
|---|---|---|
| `degree_total`, `degree_legal`, `degree_asset` | INT | ML2, ML3 |
| `contactable_party_count` | INT | ML4 (contactability) |
| `active_phone_count`, `max_contactability_score` | INT/FLOAT | ML4 |
| `guarantor_count`, `guarantor_coverage_ratio` | INT/FLOAT | ML3, ML7 |
| `co_borrower_count` | INT | ML5 |
| `net_asset_value_graph` | DECIMAL | ML3 (recovery forecast) |
| `external_pledge_count` | INT | ML3 — tài sản đã thế chấp nơi khác |
| `group_id`, `group_size`, `group_total_exposure`, `group_overdue_ratio` | | ML2, ML9 |
| `contagion_ratio` | FLOAT | ML2 |
| `pagerank_in_group`, `betweenness_in_group` | FLOAT | ML7 — có phải nút then chốt |
| `is_central_node` | BOOLEAN | Chiến lược đàm phán |
| `dissipation_alert_count`, `days_since_last_transfer` | INT | ML8, ML7 |
| `shell_org_in_network_count` | INT | ML11 (fraud) |
| `cashflow_partner_count`, `max_dependency_ratio` | | ML3 với KHDN |
| `legal_case_count`, `active_enforcement_count` | INT | ML7 |
| `avg_neighbor_dpd`, `max_neighbor_dpd` | FLOAT/INT | ML2 — lây lan rủi ro |
| `er_ambiguity_flag` | BOOLEAN | **Chặn tự động hoá khi định danh chưa chắc chắn** |

`er_ambiguity_flag=true` phải làm NBA Engine **hạ cấp xuống hành động an toàn nhất** (chỉ SMS chung, không gọi) cho đến khi ER được duyệt.

---

## 13. Pipeline xây dựng (PySpark → Neo4j)

```
[1] EXTRACT      Core/LOS/CIF/CIC/ĐKKD/ĐKGDBĐ/Court/Manual/OSINT_GREEN
                 → Bronze (Iceberg, immutable)
[2] STANDARDIZE  Phone E.164 · Address admin_code · Name normalize (VN-aware)
                 · Tax code validate · Tokenize CCCD/số tài khoản
[3] ENTITY RES   Blocking → Scoring → Clustering → Human review queue
                 → golden_person / golden_org
[4] EDGE BUILD   Mỗi loại cạnh = 1 job Spark độc lập, idempotent, có unit test
                 Output: silver.edges_<type> (chuẩn Common Property Envelope)
[5] FILTER       Hub detection (shared_degree, is_hub) · ngưỡng giao dịch
                 · loại self-loop · loại cạnh trùng
[6] SCORE        Áp công thức Mục 8 → confidence, weight, effective_weight
[7] ELIGIBILITY  Ánh xạ contact_eligible theo bảng cứng (version-controlled)
                 → validate: không cạnh nào ngoài whitelist được YES
[8] LOAD         Bulk import Neo4j (neo4j-admin import cho full,
                 apoc.periodic.iterate cho delta)
[9] ALGO         GDS: WCC → Louvain → PageRank → Betweenness (trong group)
                 → ghi ngược thuộc tính node + tạo ConnectedGroup
[10] FEATURES    Xuất Graph Feature Store → gold.gft_debtor_graph_features
[11] VALIDATE    Data quality gates (Mục 15) → nếu fail: giữ snapshot cũ
[12] SNAPSHOT    Version graph theo run_id, giữ 90 ngày để audit & rollback
```

**Nhịp chạy:**
| Thành phần | Tần suất |
|---|---|
| Cạnh L-CASE (case, contact, PTP) | Near-real-time (Kafka → Neo4j) |
| Cạnh danh tính & liên hệ | Hằng ngày |
| Cạnh giao dịch, sở hữu | Hằng ngày (cửa sổ trượt) |
| ER full re-run | Hằng tuần |
| Louvain / PageRank / group scoring | Hằng tuần (delta hằng ngày cho nhóm có biến động) |
| Graph Feature Store | Hằng đêm |

**Nguyên tắc:** mỗi job build cạnh là **idempotent** và có thể chạy lại độc lập. Không có job nào "xây cả graph" — đây là điều kiện để vận hành được ở quy mô sản xuất.

---

## 14. Quy mô, phân vùng & hiệu năng

**Ước lượng (BIDV, cả bán lẻ + KHDN):**
| Thành phần | Ước lượng |
|---|---|
| Person + Organization | 20–25 triệu |
| PhoneNumber + Address + Device | 40–60 triệu |
| Loan + Account + Collateral | 30–40 triệu |
| **Tổng node** | ~120–150 triệu |
| Cạnh danh tính & quan hệ | ~400 triệu |
| Cạnh giao dịch (sau lọc) | ~800 triệu – 1,5 tỷ |
| **Tổng cạnh** | **~1,5–2 tỷ** |

**Chiến lược:**
- **Tách graph theo mục đích:** `graph_core` (danh tính + quan hệ pháp lý + tài sản, ~500 triệu cạnh) phục vụ truy vấn điều tra online; `graph_txn` (giao dịch) chỉ dùng cho batch analytics trên Spark GraphFrames, **không load hết vào Neo4j**.
- **Projection theo phân khúc/chi nhánh** cho thuật toán GDS thay vì chạy toàn graph.
- Pre-compute mọi feature dùng cho ML — không query graph trong đường serving.
- Giới hạn độ sâu traversal mặc định = 3 hop; >3 hop phải có phê duyệt (vừa vì hiệu năng, vừa vì độ sâu càng lớn thì quan hệ càng vô nghĩa và rủi ro liên hệ nhầm càng cao).

---

## 15. Kiểm soát chất lượng & Data Quality Gates

Pipeline **fail** nếu vi phạm bất kỳ gate nào:

| Gate | Ngưỡng |
|---|---|
| Tỷ lệ node thiếu provenance | 0% |
| Cạnh có `contact_eligible=YES` ngoài whitelist (`BORROWED`, `GUARANTEES`, `CO_BORROWER_WITH`, `LEGAL_REP_OF`) | 0 cạnh |
| Cạnh `derived=true` thiếu `model_version` | 0 |
| Biến động số cạnh so với run trước | ±20% (vượt → cảnh báo, chặn auto-promote) |
| Node có `degree > 10.000` | Phải được đánh dấu `is_hub` |
| Tỷ lệ ER ở vùng xám chưa duyệt | < 5% tổng khách hàng đang có case |
| PII plaintext trong thuộc tính node | 0 (quét tự động) |
| Cạnh `MANUAL` chưa `verified_by` được dùng cho quyết định | 0 |

---

## 16. Bảo mật & Tuân thủ trên tầng graph

| Yêu cầu | Cách hiện thực |
|---|---|
| **Least privilege** | Neo4j RBAC theo label & relationship type. Cán bộ thu hồi chỉ thấy subgraph 2-hop quanh case được phân công. Chỉ đội điều tra chuyên trách được truy vấn tự do. |
| **Không lưu PII thô** | CCCD, số tài khoản, số GCN đều tokenize; detokenize qua service riêng có log. |
| **Audit truy vấn** | Log mọi truy vấn Cypher kèm `user`, `case_id`, `purpose`. Truy vấn không kèm `case_id` bị từ chối ở tầng API. |
| **Quyền của chủ thể dữ liệu** | Thủ tục xoá/ẩn danh: đóng cạnh (`valid_to`), thay node bằng tombstone giữ `person_id`, xoá thuộc tính PII. Không xoá cứng vì phá vỡ audit trail. |
| **TTL** | Job hằng tháng ẩn danh cạnh quá `ttl_expiry`, đặc biệt cạnh từ `OSINT_GREEN` và `MANUAL`. |
| **Cách ly OSINT** | Cạnh `source=OSINT_GREEN` nằm ở namespace riêng, không tham gia thuật toán phân cụm cho tới khi được cán bộ xác nhận. |

---

## 17. Quản trị schema

- **Version schema** bằng file YAML trong Git: `graph-schema-v{n}.yaml` chứa toàn bộ node/edge/property/eligibility mapping. Pipeline đọc file này, không hard-code.
- **Migration** có script tiến/lùi, chạy trên môi trường staging với snapshot production trước khi lên prod.
- **Thay đổi bảng `contact_eligible`** yêu cầu phê duyệt Compliance Officer + ghi vào changelog — đây là thay đổi có rủi ro pháp lý cao nhất trong toàn hệ thống.
- **Contract testing:** mỗi consumer (Guardrail, NBA Engine, Feature Store) có bộ test khẳng định các cạnh/thuộc tính nó phụ thuộc vẫn tồn tại.

---

## 18. Việc cần làm tiếp

| # | Hạng mục | Ghi chú |
|---|---|---|
| 1 | Đối chiếu schema này với schema KHLQ hiện có, lập bảng ánh xạ & phần mở rộng | Tránh xây trùng; xác định cạnh nào tái dùng nguyên trạng |
| 2 | Chốt bảng `contact_eligible` với Pháp chế bằng văn bản | Điều kiện tiên quyết trước khi code Guardrail |
| 3 | Hiệu chỉnh tham số chấm điểm trên dữ liệu lịch sử 2 năm | Đặc biệt `half_life` liên hệ và ngưỡng `effective_weight` |
| 4 | PoC hiệu năng: Neo4j với 500 triệu cạnh `graph_core` | Xác nhận p95 truy vấn 3-hop < 2s |
| 5 | Thiết kế chi tiết Human Review Queue cho ER vùng xám | Rủi ro liên hệ nhầm người |
| 6 | Định nghĩa bộ Data Quality Gates dạng code (Great Expectations / Deequ) | |
| 7 | Đo baseline: hiện tại bao nhiêu % case mất liên lạc? Graph cải thiện được bao nhiêu? | Chứng minh giá trị của tầng graph |

---

*Tài liệu thiết kế chi tiết, phiên bản đề xuất. Các ngưỡng và trọng số là giá trị khởi tạo, cần hiệu chỉnh trên dữ liệu thực tế của BIDV.*
