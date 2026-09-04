# B.COLLECTION — THIẾT KẾ CHI TIẾT PERSONA MODEL & MANUAL ENRICHMENT
**Phiên bản:** v0.2 | **Tài liệu mẹ:** B-Collection-kien-truc-tong-the.md (Mục 5.1, 6) | **Liên quan:** B-Collection-schema-collection-graph.md
**Thay đổi chính so với v0.1:** chuyển `willingness_score` từ một điểm số duy nhất sang **ma trận điểm số có điều kiện theo treatment** (Mục A4.2), bổ sung `NO_ACTION` là một treatment hạng nhất — xem Mục A10.

---

# PHẦN A — PERSONA MODEL

## A1. Nguyên tắc thiết kế

| # | Nguyên tắc | Hệ quả |
|---|---|---|
| **P1** | **Persona là dữ liệu có phiên bản, không phải view động** | Mỗi lần NBA ra quyết định phải **đóng băng snapshot persona** đã dùng. Không có snapshot thì 6 tháng sau không ai giải thích được vì sao hệ thống khuyến nghị hành động đó. |
| **P2** | **Ba đối tượng tiêu thụ, ba định dạng** | Con người đọc Persona Card; mô hình dùng Persona Vector; lãnh đạo dùng Persona Cluster. Không ép một định dạng phục vụ cả ba. |
| **P3** | **Mọi điểm số phải truy ngược được về bằng chứng** | Mỗi score đi kèm top-3 driver và link tới nguồn. Không có "điểm số mồ côi". |
| **P4** | **Persona mô tả *tình huống nợ*, không mô tả *con người*** | Chỉ chứa thuộc tính có liên quan nhân quả tới khả năng và cách thức thu hồi. Đây vừa là ràng buộc pháp lý, vừa là kỷ luật thiết kế chống phình dữ liệu. |
| **P5** | **Thiếu dữ liệu là một trạng thái, không phải giá trị 0** | Mọi trục có `coverage_score`. Persona thiếu dữ liệu phải làm NBA hạ cấp xuống hành động an toàn, không phải đoán bừa. |
| **P6** | **Persona không chứa kết luận về nhân thân** | Không có trường kiểu "khách hàng gian dối", "khách hàng khó tính". Chỉ có sự kiện quan sát được và xác suất có hiệu chuẩn. |

---

## A2. Kiến trúc ba lớp đầu ra

```
                    ┌─────────────────────────────────┐
                    │      PERSONA CORE (canonical)   │
                    │   7 trục D1–D7, có provenance   │
                    │   persona_id + version + as_of  │
                    └────────────┬────────────────────┘
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
     ┌────────────────┐ ┌─────────────────┐ ┌──────────────────┐
     │ PERSONA CARD   │ │ PERSONA VECTOR  │ │ PERSONA CLUSTER  │
     │ Cho collector  │ │ Cho máy         │ │ Cho chiến lược   │
     │ đọc trong 15s  │ │ 192 chiều       │ │ 20–30 cụm        │
     │ + explainable  │ │ + CBR retrieval │ │ → ma trận 2×2    │
     └────────────────┘ └─────────────────┘ └──────────────────┘
```

---

## A3. Đặc tả chi tiết 7 trục

### D1 — Khả năng trả (Ability)

| Trường | Kiểu | Nguồn | Cách tính | Làm mới |
|---|---|---|---|---|
| `verified_inflow_3m` / `_6m` / `_12m` | DECIMAL | Core | Tổng tiền vào tài khoản, loại giao dịch nội bộ vòng tròn | Ngày |
| `inflow_stability` | FLOAT 0–1 | Core | `1 − CV(dòng tiền vào theo tháng)` | Ngày |
| `inflow_seasonality` | ENUM | Core | `STABLE`, `MONTHLY_SALARY`, `SEASONAL`, `IRREGULAR`, `NONE_12M` | Tuần |
| `peak_inflow_days` | INT[] | Core | Các ngày trong tháng có dòng tiền vào cao nhất | Tuần |
| `avg_balance_3m`, `min_balance_3m` | DECIMAL | Core | | Ngày |
| `total_obligation_all_banks` | DECIMAL | CIC | Tổng dư nợ toàn ngành | Tháng |
| `obligations_at_other_banks_count` | INT | CIC | | Tháng |
| `worst_group_other_banks` | INT 1–5 | CIC | Nhóm nợ xấu nhất tại TCTD khác | Tháng |
| `debt_service_ratio_actual` | FLOAT | Tính toán | Tổng nghĩa vụ trả nợ tháng / dòng tiền vào xác thực | Ngày |
| `net_collateral_value` | DECIMAL | Graph | Từ `OWNS`/`PLEDGES`, trừ nghĩa vụ ưu tiên trước | Tuần |
| `unencumbered_asset_value` | DECIMAL | Graph | Tài sản chưa thế chấp — quan trọng cho ML7 | Tuần |
| `business_operating_status` | ENUM | ĐKKD/Graph | KHDN: `ACTIVE`/`SUSPENDED`/`DISSOLVED` | Tuần |
| `income_disruption_flag` | BOOLEAN | Suy diễn + nhập tay | Dòng tiền vào giảm >50% so với 12 tháng trước | Ngày |
| **`ability_score`** | FLOAT 0–100 | Mô hình | Công thức A4.1 | Ngày |
| `ability_coverage` | FLOAT 0–1 | | Tỷ lệ trường có dữ liệu, trọng số theo tầm quan trọng | Ngày |

### D2 — Thiện chí trả (Willingness)

| Trường | Kiểu | Nguồn | Ghi chú |
|---|---|---|---|
| `historical_dpd_max_24m`, `dpd_count_over_30_24m` | INT | Core | |
| `self_cure_count_24m` | INT | Core | Số lần tự trả không cần can thiệp |
| `ptp_made_count`, `ptp_kept_count`, `ptp_kept_rate` | INT/FLOAT | Collection | **Chỉ báo mạnh nhất của thiện chí** |
| `ptp_partial_rate` | FLOAT | Collection | Trả một phần cũng là tín hiệu tích cực |
| `avg_days_to_respond` | FLOAT | Collection | |
| `refusal_count`, `avoidance_pattern` | INT/ENUM | Collection | `NONE`, `PASSIVE` (không nghe máy), `ACTIVE` (đổi số, từ chối) |
| `paying_other_banks_while_overdue` | BOOLEAN | CIC | **Tín hiệu chọn lọc ưu tiên trả** — rất mạnh cho phân loại S2 |
| `proactive_contact_count` | INT | Collection | Khách hàng chủ động liên hệ ngân hàng |
| `dispute_raised` | BOOLEAN | Collection | Có tranh chấp về khoản nợ |
| `first_payment_default` | BOOLEAN | Core | Cờ nghi ngờ gian lận từ đầu |
| **`willingness_matrix`** | MAP<treatment, FLOAT 0–1> | Mô hình | **A4.2 — xác suất có điều kiện theo từng treatment, gồm cả `NO_ACTION`. Đây là trường NBA Engine đọc** |
| `willingness_score` | FLOAT 0–100 | Dẫn xuất | Điểm tổng hợp cho con người đọc; **không dùng cho quyết định tự động** |
| `best_treatment` | ENUM | Dẫn xuất | `argmax` của ma trận, trừ `NO_ACTION` |
| `matrix_confidence` | MAP<treatment, FLOAT> | Mô hình | Độ tin cậy từng ô — thấp khi treatment ít dữ liệu lịch sử |
| `willingness_coverage` | FLOAT | | Khách hàng mới quá hạn lần đầu → coverage thấp |

### D3 — Khả năng tiếp cận (Contactability)

| Trường | Kiểu | Nguồn |
|---|---|---|
| `active_phone_count`, `best_phone_e164` | INT/STRING | Graph + Core |
| `best_phone_contactability` | FLOAT 0–1 | Lịch sử liên hệ |
| `best_channel` | ENUM | ML4 — `VOICE`, `SMS`, `ZALO`, `EMAIL`, `APP`, `FIELD` |
| `best_time_window` | ENUM[] | ML4 — khung giờ, luôn trong 07:00–21:00 |
| `rpc_rate_90d` | FLOAT | Collection |
| `last_rpc_at`, `days_since_last_rpc` | DATE/INT | Collection |
| `address_verified_flag`, `address_verified_at` | BOOLEAN/DATE | Enrichment |
| `digital_engagement_score` | FLOAT | Kênh số — tần suất đăng nhập app (tín hiệu "còn hoạt động" rất rẻ và chính xác) |
| `lost_contact_flag` | BOOLEAN | Suy diễn — 0 RPC trong 60 ngày dù ≥8 lần thử |
| `skip_trace_candidates` | INT | Graph — số manh mối tìm lại |
| `abroad_flag` | BOOLEAN | Nhập tay / dấu hiệu giao dịch |
| **`contactability_score`** | FLOAT 0–100 | A4.3 |

### D4 — Bối cảnh nguyên nhân (Root Cause)

| Trường | Kiểu | Nguồn |
|---|---|---|
| `root_cause_primary` | ENUM (bắt buộc) | Nhập tay / trích từ cuộc gọi (có xác nhận) |
| `root_cause_secondary` | ENUM[] | |
| `root_cause_confidence` | INT 1–5 | |
| `root_cause_evidence` | TEXT (≤500 ký tự, qua Content Filter) | |
| `expected_recovery_timeline` | ENUM | `<1M`, `1-3M`, `3-6M`, `>6M`, `UNKNOWN` |

**Enum `root_cause_primary`** (danh mục đóng):
```
FORGOT_OR_ADMIN        — quên lịch, sai tài khoản trích nợ, lỗi thủ tục
CASHFLOW_TIMING        — có tiền nhưng lệch kỳ (lương chậm, công nợ chậm về)
INCOME_LOSS            — mất/giảm việc làm, giảm thu nhập
BUSINESS_DOWNTURN      — kinh doanh khó khăn, mất đơn hàng, mất đối tác lớn
OVER_INDEBTED          — vay nhiều nơi, mất cân đối nghĩa vụ
FORCE_MAJEURE          — thiên tai, dịch bệnh, hoả hoạn
HEALTH_OR_FAMILY_EVENT — biến cố lớn (**chỉ ghi nhận ở mức phân loại, không ghi chi tiết**)
DISPUTE                — tranh chấp về khoản vay, phí, lãi
FRAUD_VICTIM           — khách hàng bị lừa đảo
COLLATERAL_ISSUE       — vướng mắc pháp lý tài sản
WILFUL_DEFAULT         — có khả năng nhưng không trả (**cần bằng chứng: `paying_other_banks_while_overdue` hoặc `avoidance_pattern=ACTIVE`**)
UNREACHABLE            — chưa xác định được vì mất liên lạc
UNKNOWN
```

> `HEALTH_OR_FAMILY_EVENT` chỉ được lưu ở mức nhãn phân loại để hệ thống biết cần chuyển sang luồng hỗ trợ. **Không có trường nào lưu chi tiết bệnh tật, tình trạng sức khoẻ, hay biến cố gia đình cụ thể.** Chi tiết y tế/đời tư nằm ngoài phạm vi mục đích thu hồi nợ và bị Content Filter chặn ở tầng nhập liệu.
>
> `WILFUL_DEFAULT` là nhãn nặng nhất, ảnh hưởng trực tiếp tới quyết định leo thang pháp lý. Vì vậy hệ thống **bắt buộc yêu cầu bằng chứng định lượng** trước khi cho phép gán, và cần duyệt 4 mắt.

### D5 — Mạng lưới (Network) — lấy từ Collection Graph

| Trường | Nguồn (Graph Feature Store) |
|---|---|
| `guarantor_count`, `guarantor_coverage_ratio` | `GUARANTEES` |
| `co_borrower_count` | `CO_BORROWER_WITH` |
| `contactable_party_count` | Số bên có `contact_eligible=YES` |
| `group_id`, `group_size`, `group_overdue_ratio`, `group_risk_score` | ConnectedGroup |
| `is_central_node`, `pagerank_in_group` | GDS |
| `dissipation_alert_count`, `days_since_last_transfer` | `SUSPECTED_DISSIPATION` |
| `external_pledge_count` | `PLEDGED_TO_EXTERNAL` |
| `cashflow_partner_count`, `max_dependency_ratio` | `CASH_FLOW_TO` (KHDN) |
| `shell_org_in_network_count` | Suy diễn |
| `er_ambiguity_flag` | ER vùng xám → **hạ cấp tự động hoá** |

### D6 — Đòn bẩy đàm phán hợp pháp (Negotiation Levers)

| Trường | Kiểu | Nguồn |
|---|---|---|
| `applicable_levers` | ENUM[] | Suy diễn + nhập tay (xem B4) |
| `lever_ranked` | ENUM[] | Xếp hạng bởi CBR — đòn bẩy nào hiệu quả với cụm persona này |
| `cash_availability_windows` | STRUCT[] | `{day_of_month, source_type, confidence}` — thời điểm khách hàng có tiền |
| `acceptable_settlement_range` | STRUCT | `{min_pct, max_pct}` từ ML6 |
| `restructure_eligibility` | ENUM | `ELIGIBLE`, `CONDITIONAL`, `NOT_ELIGIBLE` theo chính sách |
| `prior_offers_made` | STRUCT[] | Phương án đã chào và phản ứng |

### D7 — Rủi ro & Nhạy cảm (Risk & Sensitivity)

| Trường | Kiểu | Tác động |
|---|---|---|
| `vulnerability_flag` | BOOLEAN | **Khoá treatment cứng**, chuyển luồng hỗ trợ |
| `vulnerability_category` | ENUM | `ELDERLY_ALONE`, `INCAPACITY`, `DISASTER_AFFECTED`, `BEREAVEMENT`, `LEGAL_REPRESENTATION`, `OTHER` — nhãn phân loại, không lưu chi tiết |
| `dnc_flag`, `dnc_scope` | BOOLEAN/ENUM | |
| `deceased_flag` | BOOLEAN | Chuyển hoàn toàn sang luồng xử lý thừa kế |
| `has_legal_counsel` | BOOLEAN | Mọi liên hệ phải qua luật sư đại diện |
| `complaint_count_12m`, `escalation_risk_score` | INT/FLOAT | Từ NLP cuộc gọi |
| `media_risk_flag` | BOOLEAN | Người của công chúng, PEP, doanh nghiệp niêm yết |
| `fraud_suspicion_score` | FLOAT | ML11 → tách luồng xử lý riêng |
| `dispute_hold_active` | BOOLEAN | Tạm dừng thu hồi |

---

## A4. Công thức tính điểm

### A4.1 Ability Score
```
ability_raw = 0.30 × norm(verified_inflow_6m / monthly_obligation)
            + 0.20 × inflow_stability
            + 0.20 × norm(net_collateral_value / outstanding)
            + 0.15 × (1 − norm(debt_service_ratio_actual))
            + 0.10 × norm(unencumbered_asset_value / outstanding)
            + 0.05 × business_health_factor        // KHDN; bán lẻ = employment_stability

ability_score = 100 × ability_raw × ability_coverage^0.5
```
Nhân với `coverage^0.5` để **điểm thấp khi thiếu dữ liệu**, thay vì để mô hình đoán. Đây là lựa chọn có chủ đích: thiếu thông tin phải dẫn tới thận trọng, không dẫn tới lạc quan.

### A4.2 Willingness — ma trận điểm số có điều kiện

> **Thay đổi so với v0.1:** trước đây `willingness_score` là **một** con số. Đó là thiết kế sai. Thiện chí trả nợ không phải thuộc tính cố định của khách hàng — nó phụ thuộc vào việc ngân hàng làm gì. Một khách hàng có thể có thiện chí thấp với cuộc gọi lúc 9h sáng nhưng thiện chí cao với đề nghị giãn kỳ hạn. Gộp thành một điểm số làm mất chính thông tin mà NBA Engine cần.

**Mô hình mới:** thay vì `P(hợp tác)`, mô hình sinh ra **xác suất có điều kiện theo từng treatment**:

```
willingness_matrix[t] = P(hợp tác trả nợ trong 60 ngày | treatment = t, liên hệ được)
                        với t ∈ tập treatment khả dụng
```

| Treatment `t` | Ký hiệu | Có trong MVP |
|---|---|---|
| Nhắc nợ tự động (SMS/ZNS) | `DIGITAL_REMINDER` | ✓ |
| Gọi điện trong khung giờ tối ưu | `VOICE_OPTIMAL_WINDOW` | ✓ |
| Gọi điện ngoài khung giờ tối ưu | `VOICE_OTHER` | ✓ |
| Chào phương án giãn kỳ hạn | `RESTRUCTURE_OFFER` | GĐ2 |
| Chào miễn giảm lãi phạt | `INTEREST_WAIVER` | GĐ2 |
| Chào chiết khấu tất toán sớm | `EARLY_SETTLEMENT` | GĐ2 |
| Làm việc với bên bảo lãnh | `GUARANTOR_ENGAGEMENT` | GĐ2 |
| **Không can thiệp** | `NO_ACTION` | ✓ |

`NO_ACTION` là một cột đầy đủ trong ma trận, không phải trường hợp đặc biệt: `willingness_matrix[NO_ACTION]` chính là xác suất tự khỏi nợ (đầu ra của ML1). Đưa nó vào cùng ma trận cho phép NBA Engine so sánh trực tiếp "làm gì đó" với "không làm gì" trên cùng một thang đo.

**Kỹ thuật:** calibrated GBM đa đầu ra (một mô hình cho mỗi treatment, huấn luyện trên tập con tương ứng), hiệu chuẩn bằng isotonic regression. Với treatment ít dữ liệu lịch sử, dùng mô hình chung có `treatment` là biến đầu vào, chấp nhận độ chính xác thấp hơn và ghi `matrix_confidence` thấp.

**Điểm tổng hợp (giữ lại cho con người đọc):**
```
willingness_score = 100 × max(willingness_matrix[t]) với t ≠ NO_ACTION
best_treatment    = argmax(willingness_matrix[t]) với t ≠ NO_ACTION
```
Điểm tổng hợp chỉ dùng cho Persona Card và ma trận chiến lược A4.4. **NBA Engine phải đọc toàn bộ ma trận, không được đọc điểm tổng hợp** — nếu đọc điểm tổng hợp thì lại quay về bài toán cũ.

**Các driver quan trọng nhất** (chung cho mọi treatment):
1. `ptp_kept_rate` — mạnh nhất
2. `paying_other_banks_while_overdue` — tín hiệu chọn lọc ưu tiên
3. `self_cure_count_24m` — đặc biệt mạnh cho cột `NO_ACTION`
4. `avoidance_pattern`
5. `proactive_contact_count`

**Vì sao đây là bước đệm sang uplift model:** ma trận có điều kiện là dạng trung gian giữa mô hình dự báo và mô hình nhân quả. Khi có đủ dữ liệu thí nghiệm từ holdout và champion–challenger, uplift được tính trực tiếp từ ma trận:
```
uplift(t) = willingness_matrix[t] − willingness_matrix[NO_ACTION]
```
Nghĩa là GĐ2 **không phải xây lại**, chỉ cần thay cách ước lượng từng ô ma trận bằng phương pháp nhân quả (T-learner / X-learner). Đây là lý do nên đổi cấu trúc ngay từ MVP dù MVP chỉ có 4 cột.

### A4.3 Contactability Score
```
contactability = 100 × [ 0.35 × best_phone_contactability
                       + 0.25 × rpc_rate_90d
                       + 0.20 × digital_engagement_score
                       + 0.10 × address_verified_factor
                       + 0.10 × norm(active_phone_count, cap=3) ]
                × (0.3 if lost_contact_flag else 1.0)
```

### A4.4 Ánh xạ về ma trận chiến lược
| | Willingness ≥ 60 | Willingness < 60 |
|---|---|---|
| **Ability ≥ 60** | **S1** Quên/vướng thủ tục | **S2** Chây ì có chủ đích |
| **Ability < 60** | **S3** Khó khăn thực sự | **S4** Mất khả năng / mất liên lạc |

Ngưỡng 60 là giá trị khởi tạo, cần hiệu chỉnh theo phân khúc. Ô S2 và S4 **bắt buộc có người duyệt** trước khi áp treatment cứng — đây là hai ô có hậu quả không đảo ngược được.

**Lưu ý về mối quan hệ với ma trận A4.2:** ma trận 2×2 này dùng `willingness_score` (điểm tổng hợp), nên nó là **công cụ giao tiếp với lãnh đạo và định hướng chính sách**, không phải cơ chế ra quyết định. Quyết định thực tế cho từng khách hàng do NBA Engine đưa ra từ `willingness_matrix` đầy đủ. Hai người cùng rơi vào ô S3 vẫn có thể nhận hai treatment khác nhau — và đó là đúng.

**Một hệ quả đáng chú ý:** khách hàng có `willingness_matrix[NO_ACTION]` cao (khả năng tự khỏi nợ lớn) sẽ rơi vào ô S1 theo ma trận, nhưng hành động đúng với họ là *không làm gì*, không phải "nhắc nhẹ đa kênh". Ma trận 2×2 không diễn đạt được sự khác biệt này — thêm một lý do để không dùng nó làm cơ chế quyết định.

---

## A5. Persona Vector (192 chiều)

| Khối | Số chiều | Nội dung | Mã hoá |
|---|---|---|---|
| Ability | 24 | Các trường D1 số hoá | Standardize + quantile binning |
| Willingness | 20 | D2 | Standardize |
| Contactability | 16 | D3 | Standardize |
| Root cause | 16 | D4 enum | One-hot + confidence |
| Graph | 32 | D5 | Log-transform + standardize |
| Product & exposure | 16 | Sản phẩm, kỳ hạn, bucket, LTV, segment | One-hot + numeric |
| Behavioral sequence | 32 | Chuỗi hành động–kết quả 12 tháng | Sequence encoder (GRU/Transformer nhỏ) |
| Text embedding | 32 | Note đã lọc + tóm tắt cuộc gọi | Vietnamese sentence embedding, giảm chiều PCA |
| Coverage mask | 4 | Coverage của từng trục | Raw |

**Quy tắc bắt buộc:**
- Vector **không chứa** biến nhạy cảm hoặc biến proxy mạnh cho biến nhạy cảm (giới tính, dân tộc, tôn giáo, mã vùng thuần tuý). Có bài test proxy detection: huấn luyện mô hình phụ dự đoán biến nhạy cảm từ vector — nếu AUC > 0.65 thì phải loại bỏ feature gây rò rỉ.
- `vector_model_version` gắn kèm mọi vector. Khi đổi version, **không so sánh chéo** vector khác version; phải re-embed toàn bộ kho reference case.
- Chuẩn hoá L2 trước khi tính cosine similarity cho CBR.

---

## A6. Persona Clustering

- **Phương pháp:** UMAP (giảm còn 15 chiều) → HDBSCAN (min_cluster_size ≈ 0,5% danh mục)
- **Số cụm mục tiêu:** 20–30. Ít hơn thì mất độ phân giải; nhiều hơn thì đội chiến lược không quản lý nổi.
- **Chạy riêng theo phân khúc:** bán lẻ / SME / KHDN lớn có động lực học rất khác nhau, không nên gom chung.
- **Đặt tên cụm:** bắt buộc do người đặt, theo mẫu `P-{nn}: {phân khúc} | {đặc trưng ability} | {đặc trưng willingness} | {root cause chiếm ưu thế}`.
  Ví dụ: `P-07: Hộ kinh doanh | dòng tiền mùa vụ | thiện chí cao | CASHFLOW_TIMING`
- **Hồ sơ cụm (Cluster Profile Card)** cho đội chiến lược: quy mô, dư nợ, recovery rate lịch sử, playbook hiệu quả nhất, chi phí thu hồi trung bình, tỷ lệ khiếu nại.
- **Giám sát trôi cụm:** PSI trên phân bố cụm hằng tháng. PSI > 0,25 → cảnh báo, xem xét re-cluster. **Không tự động re-cluster** vì sẽ phá vỡ toàn bộ chiến lược đang chạy và làm gãy so sánh champion–challenger. Re-cluster là quyết định có kiểm soát, theo quý.

---

## A7. Persona Card — đặc tả UX

Mục tiêu: collector nắm được tình huống trong **15 giây** trước khi bấm gọi.

```
┌──────────────────────────────────────────────────────────────────────┐
│ NGUYỄN VĂN A · CIF 0012345 · Case #C-2026-88213      [S3] Khó khăn   │
│ Nợ 245.000.000 · DPD 47 · Nhóm 2 · Vay tiêu dùng có TSBĐ             │
├──────────────────────────────────────────────────────────────────────┤
│  Khả năng trả  ████████░░ 42/100     Tiếp cận  ████████████░ 68/100  │
│  Độ phủ dữ liệu: 82%                                                 │
├──────────────────────────────────────────────────────────────────────┤
│ KHẢ NĂNG HỢP TÁC THEO CÁCH TIẾP CẬN                                  │
│   Chào giãn kỳ hạn      ████████████████░ 83%  ◄ tốt nhất  (tin cậy ▲)│
│   Gọi khung 18–20h      ██████████████░░░ 71%             (tin cậy ▲)│
│   SMS/Zalo nhắc nợ      █████████░░░░░░░░ 44%                        │
│   Gọi ngoài khung giờ   ███████░░░░░░░░░░ 38%                        │
│   Không can thiệp       ████░░░░░░░░░░░░░ 21%                        │
├──────────────────────────────────────────────────────────────────────┤
│ ⚠  LƯU Ý BẮT BUỘC                                                    │
│   • Chỉ liên hệ: KH chính, bên bảo lãnh Trần Thị B (0912xxx)         │
│   • KHÔNG liên hệ: nơi làm việc, người thân khác                     │
│   • Khung giờ cho phép: 18:00–21:00 (đã dùng 1/3 lượt hôm nay)       │
├──────────────────────────────────────────────────────────────────────┤
│ VÌ SAO CHƯA TRẢ                                                      │
│   CASHFLOW_TIMING (tin cậy 4/5) — lương về ngày 10, kỳ trả nợ ngày 5 │
│   Nguồn: xác minh qua cuộc gọi 12/08, CB Lê Văn C · dòng tiền core   │
├──────────────────────────────────────────────────────────────────────┤
│ NÊN LÀM GÌ                        [Từ 5 case tương đồng, 4 thành công]│
│   1. Gọi 18:00–20:00, kênh Voice (RPC 74%)                           │
│   2. Chào đổi ngày trả nợ sang ngày 12 + giãn 3 kỳ                   │
│   3. Đòn bẩy hiệu quả: chi phí lãi phạt tích luỹ (minh hoạ số cụ thể)│
│   Thời gian xử lý TB của case tương đồng: 34 ngày                    │
├──────────────────────────────────────────────────────────────────────┤
│ VÌ SAO HỆ THỐNG NGHĨ VẬY  ▸ (mở rộng: top drivers + link bằng chứng) │
├──────────────────────────────────────────────────────────────────────┤
│ [Ghi nhận kết quả]  [Bổ sung thông tin]  [Không đồng ý khuyến nghị]  │
└──────────────────────────────────────────────────────────────────────┘
```

**Quy tắc hiển thị:**
- Khối "LƯU Ý BẮT BUỘC" luôn ở trên khối "NÊN LÀM GÌ". Ràng buộc phải được đọc trước hành động.
- Mọi con số đều bấm được để xem nguồn (P3).
- Nút "Không đồng ý khuyến nghị" **bắt buộc chọn lý do từ danh mục** — dữ liệu này là đầu vào cho vòng lặp cải tiến, tương tự cơ chế Approver Quality trong CreditAgent.
- Khi `coverage < 50%` hoặc `er_ambiguity_flag=true`: banner cảnh báo, ẩn khuyến nghị hành động cứng, chỉ cho phép hành động an toàn.
- **Luôn hiển thị dòng "Không can thiệp"** trong khối ma trận, kể cả khi nó thấp. Cán bộ cần thấy rằng "không làm gì" là một lựa chọn được cân nhắc, không phải sự lười biếng. Khi `NO_ACTION` là ô cao nhất, Persona Card hiển thị thông điệp rõ ràng: *"Khách hàng này nhiều khả năng tự trả. Khuyến nghị: không liên hệ trong 7 ngày tới."*
- Ô có `confidence < 0.6` hiển thị mờ kèm dấu hiệu cảnh báo — cán bộ cần biết ô nào là ước lượng yếu do ít dữ liệu lịch sử.

---

## A8. Vòng đời & phiên bản Persona

| Sự kiện kích hoạt tính lại | Độ trễ |
|---|---|
| Batch đêm (toàn danh mục) | Hằng ngày |
| Có giao dịch tiền vào tài khoản ≥ ngưỡng | < 5 phút (streaming) |
| Kết thúc cuộc gọi (có ghi nhận kết quả) | < 1 phút |
| Enrichment fact mới được duyệt | < 1 phút |
| Cập nhật CIC | Theo chu kỳ nhận file |
| Thay đổi trạng thái case / DPD roll | Tức thì |
| Graph feature refresh | Hằng đêm |

**Snapshot bắt buộc (P1):** mỗi lần NBA Engine ra quyết định, ghi `persona_snapshot_id` vào `decision_log`. Snapshot lưu ở dạng nén trong lakehouse, giữ tối thiểu 5 năm theo yêu cầu kiểm toán.

---

## A9. Data contract — Persona object

```json
{
  "persona_id": "PSN-000123456",
  "subject": { "type": "PERSON", "person_id": "P-8891234", "cif_no": ["0012345"] },
  "as_of": "2026-09-01T02:15:00+07:00",
  "schema_version": "2.0",
  "model_versions": { "willingness": "wl-3.0", "vector": "pv-1.4", "cluster": "cl-2026Q3" },
  "scores": {
    "ability":       { "value": 42, "coverage": 0.85, "top_drivers": [
        {"feature":"debt_service_ratio_actual","contribution":-0.31,"evidence_ref":"CORE:TXN:..."},
        {"feature":"net_collateral_value","contribution":0.18,"evidence_ref":"GRAPH:COLL:..."} ] },
    "contactability":{ "value": 68, "coverage": 0.90, "top_drivers": [...] }
  },
  "willingness": {
    "matrix": {
      "NO_ACTION":            {"p": 0.21, "confidence": 0.88},
      "DIGITAL_REMINDER":     {"p": 0.44, "confidence": 0.85},
      "VOICE_OPTIMAL_WINDOW": {"p": 0.71, "confidence": 0.82},
      "VOICE_OTHER":          {"p": 0.38, "confidence": 0.79},
      "RESTRUCTURE_OFFER":    {"p": 0.83, "confidence": 0.54}
    },
    "score": 83,
    "best_treatment": "RESTRUCTURE_OFFER",
    "coverage": 0.78,
    "top_drivers": [...],
    "note": "NBA Engine đọc 'matrix'. 'score' và 'best_treatment' chỉ để hiển thị."
  },
  "segment_cell": "S3",
  "cluster": { "id": "P-07", "label": "Hộ kinh doanh | mùa vụ | thiện chí cao", "similarity": 0.88 },
  "root_cause": { "primary": "CASHFLOW_TIMING", "confidence": 4,
                  "source": "MANUAL_VERIFIED", "recorded_at": "2026-08-12" },
  "levers": { "applicable": ["ACCRUING_PENALTY_COST","EARLY_SETTLEMENT_DISCOUNT"],
              "cash_windows": [{"day_of_month":10,"source_type":"SALARY","confidence":4}] },
  "contact_policy": {
    "eligible_parties": [
      {"party_id":"P-8891234","basis":"BORROWED"},
      {"party_id":"P-5567788","basis":"GUARANTEES"}],
    "blocked_reason_if_any": null,
    "allowed_windows": ["18:00-21:00"],
    "remaining_attempts_today": 2
  },
  "risk": { "vulnerability_flag": false, "dnc_flag": false,
            "has_legal_counsel": false, "escalation_risk": 0.12 },
  "vector_ref": "s3://persona-vectors/pv-1.4/PSN-000123456.npy",
  "coverage_overall": 0.82,
  "snapshot_id": "SNP-2026-09-01-000123456-01"
}
```

---

## A10. Nhật ký thay đổi

### v0.2 — Ma trận điểm số có điều kiện

| Nội dung | v0.1 | v0.2 |
|---|---|---|
| Thiện chí trả | Một điểm số `willingness_score` 0–100 | **Ma trận** `willingness_matrix[treatment] → P(hợp tác)` kèm `confidence` từng ô |
| "Không can thiệp" | Không được mô hình hoá; ML1 (self-cure) là mô hình tách rời | `NO_ACTION` là **một cột trong ma trận**, so sánh trực tiếp với các treatment khác |
| Đầu vào của NBA | Ba điểm số | Ability + Contactability (điểm số) + Willingness (ma trận) |
| Đường tiến hoá sang uplift | Phải xây lại mô hình | `uplift(t) = matrix[t] − matrix[NO_ACTION]` — chỉ đổi phương pháp ước lượng, giữ nguyên cấu trúc |
| Ma trận chiến lược 2×2 | Cơ chế quyết định | Công cụ giao tiếp và định hướng chính sách; quyết định thực tế đọc từ ma trận đầy đủ |
| Persona Card | Hiển thị 3 thanh điểm | Thêm khối "Khả năng hợp tác theo cách tiếp cận", luôn có dòng "Không can thiệp" |

**Nguồn ý tưởng:** McKinsey, *The analytics-enabled collections model* (2018) — phần Value-at-risk assessment mô tả hướng đi trong đó mỗi người vay có nhiều điểm số tuỳ theo chiến lược liên hệ và phương án được chào, thay vì một điểm rủi ro duy nhất; và Exhibit 1 mô tả phân khúc "đãng trí" với can thiệp đề xuất là bỏ qua vì nhóm này nhiều khả năng tự khỏi nợ.

**Lưu ý khi triển khai:** thay đổi này làm tăng đáng kể yêu cầu về dữ liệu huấn luyện — cần đủ quan sát cho từng cặp (treatment × phân khúc). Nếu dữ liệu lịch sử không đủ (xem hạng mục 4b ở Mục B10), MVP có thể khởi đầu với 3 cột (`NO_ACTION`, `DIGITAL_REMINDER`, `VOICE_OPTIMAL_WINDOW`) và mở rộng dần. Cấu trúc dữ liệu vẫn phải là ma trận ngay từ đầu, kể cả khi chỉ có 3 cột — đổi cấu trúc sau tốn kém hơn nhiều so với để trống cột.

---

# PHẦN B — MANUAL ENRICHMENT

## B1. Vấn đề cần tránh

Nếu thiết kế module này như một ô "Ghi chú" tự do, sau 12 tháng Ngân hàng sẽ có vài triệu dòng text không truy vấn được, chất lượng không kiểm soát được, và một khối rủi ro tuân thủ không rà soát nổi. Toàn bộ thiết kế dưới đây xoay quanh việc tránh kết cục đó.

**Nguyên tắc:** *người dùng chọn, hệ thống ghi* — không phải *người dùng viết, hệ thống lưu*.

---

## B2. Mô hình dữ liệu — Event Sourcing

Không cập nhật tại chỗ. Mỗi lần nhập là một **EnrichmentFact** bất biến; Persona đọc từ *view hiện hành* được tính lại từ chuỗi fact.

```json
{
  "fact_id": "EF-2026-0891234",
  "subject_ref": { "type": "PERSON", "id": "P-8891234" },
  "case_id": "C-2026-88213",
  "fact_type": "CONTACT_WINDOW",
  "payload": { "window": "18:00-21:00", "day_type": "WEEKDAY" },
  "provenance": {
    "source_type": "DEBTOR_DECLARED",
    "collected_by": "EMP-4471",
    "collected_at": "2026-08-12T18:42:00+07:00",
    "collection_channel": "CALL",
    "evidence_ref": "REC-2026-08-12-4471-003",
    "legal_basis": "CONTRACT"
  },
  "confidence": 4,
  "valid_from": "2026-08-12",
  "ttl_expiry": "2027-02-12",
  "state": "PUBLISHED",
  "review": { "required": false, "reviewed_by": null, "reviewed_at": null },
  "filter_result": { "status": "PASS", "flags": [] },
  "supersedes": "EF-2026-0774112",
  "outcome_link": { "contributed_to_recovery": null }
}
```

**State machine:**
```
DRAFT ──submit──► VALIDATING ──pass──► [cần duyệt?] ──no──► PUBLISHED
                       │                     │
                       │ fail                │ yes
                       ▼                     ▼
                   REJECTED            PENDING_REVIEW ──approve──► PUBLISHED
                                              │ reject
                                              ▼
                                          REJECTED
PUBLISHED ──fact mới cùng loại──► SUPERSEDED
PUBLISHED ──quá ttl_expiry──────► EXPIRED
PUBLISHED ──KH phản đối─────────► DISPUTED (loại khỏi Persona ngay)
```

---

## B3. Danh mục fact type

| Nhóm | `fact_type` | Payload | Duyệt 4 mắt | TTL |
|---|---|---|---|---|
| **Liên hệ** | `ALT_PHONE` | `{e164, relation_to_subject, verified}` | Không | 6 tháng |
| | `CURRENT_ADDRESS` | `{address_id, address_type, verified_method}` | Không | 12 tháng |
| | `CONTACT_WINDOW` | `{window, day_type}` | Không | 6 tháng |
| | `PREFERRED_CHANNEL` | `{channel}` | Không | 6 tháng |
| | `ABROAD_STATUS` | `{status, country, expected_return}` | Có | 12 tháng |
| **Quan hệ có nghĩa vụ** | `GUARANTOR_CONFIRMED` | `{party_id, contract_ref}` | **Có** | ∞ |
| | `LEGAL_REP_CHANGE` | `{party_id, effective_date, doc_ref}` | **Có** | ∞ |
| | `AUTHORIZED_PERSON` | `{party_id, poa_ref, scope, expiry}` | **Có** | Theo uỷ quyền |
| | `REFERENCE_CONTACT` | `{party_id, consent_obtained, consent_ref, consent_method}` | **Có** | 12 tháng |
| **Nghề nghiệp & dòng tiền** | `EMPLOYMENT` | `{employer_name, since, employment_type}` | Không | 12 tháng |
| | `SALARY_CYCLE` | `{day_of_month}` | Không | 12 tháng |
| | `BUSINESS_SEASONALITY` | `{peak_months[], revenue_cycle}` | Không | 18 tháng |
| | `EXPECTED_INFLOW` | `{amount_band, expected_date, source_type}` | Không | 3 tháng |
| | `BUSINESS_STATUS_OBSERVED` | `{status, observed_at, method}` | Có | 6 tháng |
| **Nguyên nhân** | `ROOT_CAUSE` | `{primary, secondary[], evidence_text}` | Có nếu `WILFUL_DEFAULT` | 12 tháng |
| **Đòn bẩy** | `NEGOTIATION_LEVER` | `{lever_code, evidence_text}` | **Có** | 12 tháng |
| | `CASH_AVAILABILITY_WINDOW` | `{day_of_month, source_type}` | Không | 12 tháng |
| **Tài sản** | `ASSET_OBSERVED` | `{asset_type, identifier_ref, estimated_value, source}` | **Có** | 12 tháng |
| | `ASSET_CONDITION` | `{collateral_id, condition, photo_ref, gps}` | Không | 6 tháng |
| | `ASSET_TRANSFER_SUSPECTED` | `{recipient_ref, transfer_date, evidence_ref}` | **Có** | ∞ |
| **Rủi ro & nhạy cảm** | `VULNERABILITY` | `{category}` (chỉ nhãn) | **Có** | 12 tháng |
| | `LEGAL_COUNSEL` | `{counsel_name, contact_via}` | **Có** | ∞ |
| | `DISPUTE_RAISED` | `{dispute_type, raised_at}` | **Có** | ∞ |
| | `DNC_REQUEST` | `{scope, requested_at, channel}` | **Có** | ∞ |
| | `DECEASED` | `{reported_by, doc_ref}` | **Có** | ∞ |
| **Tương tác** | `INTERACTION_NOTE` | `{summary}` ≤ 500 ký tự, qua Content Filter | Không | 12 tháng |

Lưu ý: **không có** fact type nào cho sức khoẻ chi tiết, tôn giáo, quan điểm chính trị, đời sống riêng tư, thông tin về con cái, hay quan hệ xã hội không có nghĩa vụ pháp lý. Đây là quyết định thiết kế có chủ đích — không có trường thì không thể nhập, và không thể nhập thì không thể lạm dụng.

---

## B4. `NEGOTIATION_LEVER` — enum đóng

**Danh mục được phép:**
| `lever_code` | Nội dung | Bằng chứng yêu cầu |
|---|---|---|
| `CIC_CREDIT_RECORD` | Ảnh hưởng lịch sử tín dụng, khả năng vay vốn tương lai | Không |
| `ACCRUING_PENALTY_COST` | Chi phí lãi phạt tích luỹ theo thời gian | Bảng tính minh hoạ tự sinh |
| `COLLATERAL_ENFORCEMENT_RISK` | Rủi ro bị xử lý TSBĐ theo hợp đồng | `collateral_id` |
| `LITIGATION_COST_TIME` | Chi phí và thời gian nếu chuyển tố tụng | Không |
| `CORPORATE_CREDIT_RELATIONSHIP` | Ảnh hưởng hạn mức/quan hệ tín dụng của **chính pháp nhân vay** | Chỉ áp dụng KHDN |
| `EARLY_SETTLEMENT_DISCOUNT` | Ưu đãi chiết khấu tất toán sớm | Trong khung chính sách đã duyệt |
| `INTEREST_WAIVER_OFFER` | Miễn giảm lãi phạt có thời hạn | Trong khung chính sách |
| `RESTRUCTURE_OPPORTUNITY` | Phương án cơ cấu, giãn kỳ hạn | Trong khung chính sách |
| `CASH_FLOW_TIMING` | Đề xuất khớp kỳ trả nợ với thời điểm khách hàng có tiền | `CASH_AVAILABILITY_WINDOW` |
| `COLLATERAL_RELEASE_INCENTIVE` | Giải chấp tài sản sau khi tất toán | `collateral_id` |

**Bị chặn cứng — không có mã, không có ô nhập, và Content Filter chặn nếu xuất hiện trong text:**
- Bất kỳ nội dung nào hướng tới việc gây áp lực qua người thân, đồng nghiệp, hàng xóm, đối tác không có nghĩa vụ trả nợ
- Nơi làm việc, trường học của con, nơi ở của người thân
- Thông tin sức khoẻ, tôn giáo, quan điểm chính trị, đời sống tình cảm
- Ngôn ngữ đe doạ, xúc phạm, hoặc ám chỉ công khai khoản nợ với bên thứ ba

**Cơ chế:** `lever_code` là enum đóng ở tầng database (CHECK constraint) và tầng API. Trường `evidence_text` đi qua Content Filter. Mọi nỗ lực nhập nội dung thuộc nhóm bị chặn đều được **ghi log và gửi cảnh báo tới Compliance**, kể cả khi bị chặn thành công — vì đó là tín hiệu cần đào tạo lại, không phải sự cố kỹ thuật.

---

## B5. Pipeline kiểm duyệt đầu vào

```
[1] CLIENT           Form có cấu trúc, enum dropdown, ràng buộc kiểu dữ liệu
                     Không có textarea lớn; INTERACTION_NOTE giới hạn 500 ký tự
       ▼
[2] SCHEMA VALIDATE  JSON Schema theo fact_type; sai → trả về ngay
       ▼
[3] CONTENT FILTER   (a) PII detector: phát hiện CCCD/STK/địa chỉ lẫn vào text
                     (b) Sensitive category classifier: sức khoẻ, tôn giáo, chính trị,
                         đời tư, thông tin về bên thứ ba không nghĩa vụ
                     (c) Abusive/threatening language detector
                     → FAIL: chặn + log + cảnh báo Compliance
                     → WARN: cho qua nhưng đánh dấu để QA rà soát
       ▼
[4] CONSENT CHECK    REFERENCE_CONTACT bắt buộc consent_obtained=true + consent_ref
                     Không có → REJECTED
       ▼
[5] CONFLICT CHECK   Mâu thuẫn với fact PUBLISHED hiện có? → xem B6
       ▼
[6] GRAPH IMPACT     Fact tạo/sửa cạnh graph? → tính contact_eligible theo bảng cứng
                     Không fact nào được tự nâng contact_eligible lên YES ngoài
                     whitelist đã định (xem tài liệu Graph, Mục 7.3)
       ▼
[7] REVIEW GATE      Theo cột "Duyệt 4 mắt" ở B3 → PENDING_REVIEW hoặc PUBLISHED
       ▼
[8] PERSONA REFRESH  Trigger tính lại Persona (< 1 phút)
       ▼
[9] AUDIT            Ghi immutable log: ai nhập, nhập gì, filter kết quả, ai duyệt
```

**Fail-closed:** Content Filter không phản hồi trong 2s → fact chuyển `PENDING_REVIEW`, không tự động publish.

---

## B6. Độ tin cậy, suy giảm & xử lý mâu thuẫn

### B6.1 Confidence
| `source_type` | Confidence khởi tạo |
|---|---|
| `DOCUMENT_VERIFIED` (có chứng từ) | 5 |
| `STAFF_FIELD_VERIFIED` (cán bộ xác minh thực địa, có ảnh/GPS) | 4 |
| `DEBTOR_DECLARED` (khách hàng tự khai qua kênh chính thức) | 3 |
| `THIRD_PARTY_OBLIGATED` (bên bảo lãnh, đồng vay cung cấp) | 3 |
| `STAFF_INFERRED` (cán bộ suy đoán từ quan sát) | 2 |
| `OSINT_GREEN_VERIFIED` (nguồn công khai, đã đối chiếu) | 2 |

### B6.2 Suy giảm
```
effective_confidence = confidence × 0.5^(age_days / half_life)
```
| Nhóm fact | half_life |
|---|---|
| Liên hệ (`ALT_PHONE`, `CONTACT_WINDOW`) | 120 ngày |
| Nghề nghiệp, dòng tiền | 270 ngày |
| Nguyên nhân, đòn bẩy | 180 ngày |
| Tài sản quan sát | 365 ngày |
| Pháp lý (`GUARANTOR_CONFIRMED`, `DECEASED`, `DNC_REQUEST`) | Không suy giảm |

Fact rơi xuống `effective_confidence < 1.5` → tự động loại khỏi Persona, đưa vào hàng đợi "cần xác minh lại" hiển thị trên Persona Card.

### B6.3 Xử lý mâu thuẫn
| Tình huống | Xử lý |
|---|---|
| Fact mới cùng `fact_type`, confidence cao hơn | Fact cũ → `SUPERSEDED` |
| Confidence bằng nhau | Fact mới thắng, nhưng ghi `conflict_flag` |
| Mâu thuẫn với dữ liệu hệ thống (Core/CIC) | **Hệ thống thắng**; fact vào `PENDING_REVIEW` để cán bộ giải trình |
| Mâu thuẫn giữa 2 cán bộ khác nhau | Escalate lên kiểm soát viên; cả 2 fact tạm treo khỏi Persona |
| Khách hàng phản đối thông tin | `DISPUTED` — loại khỏi Persona **ngay lập tức**, không chờ duyệt |

Nguyên tắc: **khi có mâu thuẫn chưa giải quyết, Persona hiển thị trạng thái "không chắc chắn" thay vì chọn một bên.** NBA Engine hạ cấp tương ứng.

---

## B7. Trải nghiệm nhập liệu

Chất lượng dữ liệu làm giàu phụ thuộc gần như hoàn toàn vào việc nhập có **dễ hơn không nhập** hay không.

**B7.1 — Nhập tại điểm phát sinh (contextual capture).** Không có "màn hình nhập liệu" riêng. Form bổ sung thông tin bật ra ngay trong màn hình kết thúc cuộc gọi (call wrap-up), tối đa 3 trường được gợi ý sẵn theo ngữ cảnh.

**B7.2 — Gợi ý từ cuộc gọi, người xác nhận.** LLM đọc bản ASR, đề xuất fact có cấu trúc dạng chip bấm-để-xác-nhận:
> *"Ghi nhận: lương về ngày 10 hằng tháng?"* → [Đúng] [Sửa] [Bỏ qua]

Cán bộ bấm 1 lần thay vì gõ. Fact được tạo với `source_type=DEBTOR_DECLARED`, `collection_channel=CALL_ASR_CONFIRMED`. **LLM không bao giờ tự publish fact** — luôn cần một cú bấm xác nhận của con người.

**B7.3 — Field App.** Cán bộ đi hiện trường: chụp ảnh + GPS + chọn enum, hoạt động offline, đồng bộ khi có mạng. Đây là nguồn `STAFF_FIELD_VERIFIED` chất lượng cao nhất.

**B7.4 — Hiển thị giá trị ngược lại.** Trên Persona Card, cạnh mỗi fact hiển thị người đóng góp. Trong thông báo định kỳ: *"Thông tin về chu kỳ lương anh/chị bổ sung tháng 6 đã được dùng trong 14 case, góp phần thu hồi thành công 9 case."* Đây là động lực bền hơn mọi hình thức ép buộc.

---

## B8. Quản trị chất lượng

### B8.1 Enrichment Contribution Score (ECS)
```
ECS = 0.40 × utility_rate       // % fact được dùng trong quyết định NBA
    + 0.30 × outcome_lift       // uplift thu hồi của case có dùng fact do CB nhập
    + 0.20 × accuracy_rate      // % fact không bị mâu thuẫn/DISPUTED về sau
    − 0.30 × filter_violation_rate   // tỷ lệ bị Content Filter chặn
```
**Đo bằng kết quả, không đo bằng số dòng nhập.** Nếu đo bằng số lượng, sẽ có hàng nghìn fact rác trong tháng đầu tiên.

**Chống gaming:** phát hiện nhập hàng loạt fact giá trị thấp, nhập trùng lặp, nhập fact "an toàn" không có tác dụng. Trọng số phạt `filter_violation_rate` cao hơn các thành phần thưởng — cố tình nhập nội dung bị cấm phải lỗ, không được hoà.

### B8.2 QA lấy mẫu
- 100% fact `PENDING_REVIEW` được duyệt trước khi publish
- 5% fact tự động publish được lấy mẫu QA hằng tuần
- 100% fact có `filter_result.status = WARN` được rà soát
- Đối chiếu chéo: fact `STAFF_FIELD_VERIFIED` có GPS lệch bất thường → cảnh báo

### B8.3 Quản trị danh mục trường
Thêm một `fact_type` mới hoặc thêm giá trị enum là **thay đổi có kiểm soát**: đề xuất → đánh giá cần thiết & rủi ro pháp lý → phê duyệt bởi PO + DPO → cập nhật catalog (YAML trong Git) → migration. Không cho phép thêm trường tự phát ở cấp chi nhánh. Đây là cơ chế duy nhất giữ cho mô hình không trôi về free-text sau 2 năm.

---

## B9. Chỉ số theo dõi module

| Chỉ số | Ý nghĩa | Mục tiêu gợi ý |
|---|---|---|
| Enrichment coverage | % case có ≥1 fact `PUBLISHED` trong 90 ngày | > 70% |
| Persona coverage trung bình | Độ phủ dữ liệu trung bình toàn danh mục | > 75% |
| Fact utility rate | % fact được NBA thực sự sử dụng | > 40% |
| Time-to-publish | Từ nhập tới có hiệu lực trên Persona | p95 < 5 phút (không cần duyệt) |
| Review backlog | Số fact `PENDING_REVIEW` quá 48h | < 5% |
| Filter block rate | Tỷ lệ bị Content Filter chặn | Giảm dần theo thời gian (chỉ báo hiệu quả đào tạo) |
| Dispute rate | % fact bị khách hàng phản đối | < 0,5% |
| Stale fact ratio | % fact đã EXPIRED chưa được làm mới | < 20% |
| **Enrichment uplift** | Chênh lệch recovery giữa case có/không có enrichment (đã kiểm soát biến) | Đo bằng holdout |

Chỉ số cuối là chỉ số quan trọng nhất — nó trả lời câu hỏi *module này có đáng chi phí vận hành không*. Cần thiết kế đo lường từ ngày đầu, không phải sau khi triển khai.

---

## B10. Việc cần làm tiếp

| # | Hạng mục | Chủ trì |
|---|---|---|
| 1 | Chốt danh mục `fact_type` và toàn bộ enum với nghiệp vụ + DPO | BA + DPO |
| 2 | Chốt `NEGOTIATION_LEVER` enum với Pháp chế bằng văn bản | Pháp chế |
| 3 | Xây bộ dữ liệu huấn luyện cho Sensitive Content Classifier tiếng Việt | ML + Compliance |
| 4 | Hiệu chỉnh trọng số `ability_score` và ngưỡng ma trận 2×2 trên dữ liệu 2 năm | ML |
| 4b | **Kiểm tra tính khả thi của ma trận có điều kiện**: dữ liệu lịch sử có đủ quan sát cho từng cặp (treatment × phân khúc) không? Nếu một treatment có < 500 quan sát thì chưa ước lượng được ô đó | ML |
| 4c | **Thiết kế lại API Persona → NBA** để truyền cả ma trận, và bổ sung kiểm tra: NBA không được đọc `willingness.score` | SA |
| 5 | Proxy detection test cho Persona Vector | Model Validation |
| 6 | Thiết kế chi tiết UI Persona Card + call wrap-up form, test với 10 collector thật | UX + PO |
| 7 | Định nghĩa cơ chế snapshot & lưu trữ 5 năm | Data Eng |
| 8 | Baseline: hiện tại bao nhiêu % case có thông tin nguyên nhân chậm trả? | PO |

---

*Tài liệu thiết kế chi tiết, phiên bản đề xuất. Các trọng số, ngưỡng và TTL là giá trị khởi tạo, cần hiệu chỉnh trên dữ liệu thực tế của Ngân hàng.*
