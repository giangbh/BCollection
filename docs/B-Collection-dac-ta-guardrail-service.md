# B.COLLECTION — ĐẶC TẢ COMPLIANCE GUARDRAIL SERVICE
**Phiên bản:** v1.0 | **Ngày:** 01/09/2026
**Tài liệu liên quan:** Kiến trúc tổng thể (Mục 11.1) · Collection Graph (Mục 7) · Persona Model & Manual Enrichment (Phần B5)

> **Trạng thái:** Bản đặc tả kỹ thuật để thẩm định. Các nội dung pháp lý được tra cứu qua nguồn thứ cấp và **phải được Khối Pháp chế đối chiếu bản gốc trên Công báo trước khi hiện thực hóa**. Các hạng mục chờ chốt được đánh dấu 🔶 và tổng hợp ở Mục 17.

---

## 1. Phạm vi & vị trí kiến trúc

Guardrail Service là tầng L6 — chạy **cắt ngang** giữa tầng Quyết định (L5: NBA Engine, Strategy Engine) và tầng Thực thi (L7: Workflow, Dialer, SMS, Field App, Legal). Không có đường đi từ L5 sang L7 mà không qua L6.

```
   L5 DECISIONING                     L7 EXECUTION
   ┌──────────────┐                   ┌──────────────────┐
   │ NBA Engine   │──── intent ──┐    │ Dialer / IVR     │
   │ Strategy     │              │    │ SMS / Zalo ZNS   │
   │ Collector UI │              ▼    │ Field App        │
   └──────────────┘   ┌────────────────────┐  │ Legal / Thu giữ │
                      │ GUARDRAIL SERVICE  │──┤ Bán nợ          │
   ┌──────────────┐   │  evaluate/commit   │  └──────────────────┘
   │ Graph        │──►│  deterministic     │
   │ Persona      │──►│  fail-closed       │──► Immutable Audit Log
   │ Policy Store │──►│  policy-as-code    │
   └──────────────┘   └────────────────────┘
```

**Guardrail chịu trách nhiệm:** quyết định một hành động cụ thể tới một đối tượng cụ thể, tại một thời điểm cụ thể, có được phép thực hiện hay không, và ghi lại bằng chứng của quyết định đó.

**Guardrail KHÔNG chịu trách nhiệm:** chọn hành động (đó là NBA), thực thi hành động (đó là L7), hay đánh giá hiệu quả (đó là Analytics).

---

## 2. Nguyên tắc thiết kế

| # | Nguyên tắc | Hiện thực hóa |
|---|---|---|
| **GR1** | **Fail-closed tuyệt đối** | Timeout, lỗi phụ thuộc, dữ liệu thiếu, policy không tải được → `BLOCK`. Không có chế độ "cho qua khi lỗi". |
| **GR2** | **Deterministic, không LLM** | Toàn bộ logic là rule engine + truy vấn. LLM chỉ được dùng trong Content Filter như một *bộ phân loại phụ trợ*, và chỉ có quyền làm quyết định **nghiêm ngặt hơn**, không bao giờ nới lỏng. |
| **GR3** | **Không có đường vòng** | L7 chỉ nhận lệnh có `guardrail_token` hợp lệ, chưa hết hạn, khớp chữ ký. Adapter kênh từ chối mọi lệnh không có token. |
| **GR4** | **Policy là dữ liệu, không phải code** | Chính sách nằm trong file YAML có version, ký số, phê duyệt bởi Compliance Officer. Đổi chính sách không cần deploy. |
| **GR5** | **Mọi quyết định đều để lại bằng chứng** | Cả `ALLOW` lẫn `BLOCK` đều ghi audit. Log `BLOCK` chính là bằng chứng tuân thủ khi thanh tra. |
| **GR6** | **Guardrail không sửa dữ liệu nghiệp vụ** | Chỉ đọc. Trạng thái duy nhất nó sở hữu là bộ đếm tần suất và audit log. |
| **GR7** | **Chặn ở nơi gần hành động nhất** | Kiểm tra tại thời điểm *thực thi*, không phải thời điểm *lập kế hoạch*. Một chiến dịch lập lúc 2h sáng phải được kiểm tra lại khi gửi lúc 19h. |

---

## 3. Cơ sở pháp lý — ma trận ánh xạ

| Mã | Control | Văn bản | Tình trạng áp dụng với Ngân hàng |
|---|---|---|---|
| G01 | Tính hợp lệ của khoản nợ | Bộ luật Dân sự 2015, TT 39/2016/TT-NHNN | **Bắt buộc** |
| G02 | Đối tượng được liên hệ | NĐ 117/2018/NĐ-CP (bí mật thông tin KH); TT 43/2016 sđ bởi TT 18/2019 | NĐ 117 **bắt buộc**; TT 18 **tự áp** 🔶 |
| G03 | Đồng ý & DNC | Luật BVDLCN 91/2025/QH15; NĐ 356/2025/NĐ-CP | **Bắt buộc** từ 01/01/2026 |
| G04 | Giới hạn tần suất | TT 18/2019 (5 lần/ngày) | **Tự áp** 🔶 — TT 39 không hạn chế biện pháp thu nợ với TCTD |
| G05 | Khung giờ liên hệ | TT 18/2019 (7h–21h) | **Tự áp** 🔶 |
| G06 | Nội dung liên hệ | TT 18/2019 (cấm đe dọa); NĐ 117/2018; BLHS (Đ.155, Đ.170) | Cấm đe dọa/xúc phạm **bắt buộc** theo pháp luật hình sự & dân sự |
| G07 | Khách hàng dễ tổn thương | Chưa có quy định trực tiếp tại VN | **Tự áp** — chuẩn mực quốc tế (FCA CONC 7) |
| G08 | Tranh chấp / tạm dừng | Luật BVQLNTD 19/2023/QH15 | **Bắt buộc** 🔶 (cần trích dẫn chính xác điều khoản) |
| G09 | **Thu giữ TSBĐ** | Luật 96/2025/QH15 (Đ.198a–198c, hiệu lực 15/10/2025); **NĐ 304/2025/NĐ-CP (hiệu lực 01/12/2025)** | **Bắt buộc** |
| G10 | Bảo vệ dữ liệu cá nhân | Luật 91/2025/QH15; NĐ 356/2025/NĐ-CP | **Bắt buộc** |
| G11 | Hành động không đảo ngược | Luật 96/2025 (quy định nội bộ về trình tự thu giữ, kể cả khi ủy quyền bên thứ ba) | **Bắt buộc** |
| G12 | Nhật ký & lưu trữ | NĐ 356/2025 (hồ sơ vi phạm lưu tối thiểu 5 năm) | **Bắt buộc** |
| — | Cấm dịch vụ đòi nợ thuê | Luật Đầu tư 2020 | **Bắt buộc** — ràng buộc ở tầng mô hình vận hành, không phải runtime |

> **Ghi chú quan trọng về G04/G05:** Thông tư 43/2016 sửa đổi bởi Thông tư 18/2019 điều chỉnh hoạt động cho vay tiêu dùng của **công ty tài chính**, không áp trực tiếp cho ngân hàng thương mại. Thông tư 39/2016 — văn bản điều chỉnh hoạt động cho vay của TCTD — không hạn chế biện pháp, hình thức, cách thức thu nợ. Do đó ngưỡng tần suất và khung giờ trong đặc tả này là **chuẩn nội bộ Ngân hàng tự áp**. Khuyến nghị lấy TT 18/2019 làm sàn tối thiểu vì đây là mức mà cơ quan quản lý đã thể hiện quan điểm.
>
> **Ràng buộc kèm theo:** TT 18/2019 yêu cầu hình thức và thời gian nhắc nợ phải được **thỏa thuận trong hợp đồng**. Nếu Ngân hàng tự áp chuẩn này, phải bổ sung điều khoản tương ứng vào mẫu hợp đồng tín dụng. Đây là công việc của Pháp chế, cần khởi động song song với phát triển hệ thống — thời gian sửa mẫu biểu thường dài hơn thời gian code.

---

## 4. Mô hình quyết định

### 4.1 Bốn kết quả
| Kết quả | Nghĩa | Hành vi của L7 |
|---|---|---|
| `ALLOW` | Được phép, không điều kiện | Thực thi, kèm token |
| `ALLOW_WITH_CONDITIONS` | Được phép nhưng bị ràng buộc | Thực thi theo `conditions` (ví dụ: chỉ dùng kịch bản đã duyệt, chỉ kênh SMS, không nêu số dư) |
| `ESCALATE` | Cần phê duyệt của con người có thẩm quyền | Đưa vào hàng đợi phê duyệt, **không thực thi** |
| `BLOCK` | Không được phép | Từ chối, ghi lý do, thông báo cho người thao tác |

### 4.2 Thứ tự đánh giá và quy tắc ưu tiên

Các control chạy **theo thứ tự cố định**, dừng ngay khi gặp `BLOCK` đầu tiên (short-circuit), nhưng **vẫn ghi nhận toàn bộ control đã chạy** vào audit.

```
G01 Debt validity        ─┐
G02 Party eligibility     │  Nhóm CHẶN CỨNG
G03 Consent & DNC         │  BLOCK ở đây là tuyệt đối,
G07 Vulnerability         │  không có cơ chế ghi đè
G08 Dispute hold          │  bởi bất kỳ vai trò nào
G09 Collateral gate      ─┘
        ▼
G10 Data protection      ─┐  Nhóm CHẶN CÓ ĐIỀU KIỆN
G05 Time window           │  Có thể chuyển thành ESCALATE
G04 Frequency cap         │  nếu policy cho phép
G06 Content filter       ─┘
        ▼
G11 Irreversible action  ──  Nhóm LEO THANG (ESCALATE, không BLOCK)
        ▼
G12 Audit & token issue  ──  Luôn chạy, kể cả khi đã BLOCK
```

**Quy tắc ưu tiên:** `BLOCK` > `ESCALATE` > `ALLOW_WITH_CONDITIONS` > `ALLOW`. Kết quả cuối cùng là mức nghiêm ngặt nhất trong tất cả control đã chạy. Không có vai trò nào — kể cả Giám đốc chi nhánh hay Tổng giám đốc — có quyền ghi đè một `BLOCK` thuộc nhóm chặn cứng qua giao diện hệ thống; thay đổi chỉ có thể thực hiện bằng cách sửa policy, với quy trình phê duyệt ở Mục 14.

---

## 5. Đặc tả từng Control

### G01 — Debt Validity Gate
**Mục đích:** Không đòi một khoản nợ không tồn tại, không đúng chủ thể, hoặc đã hết hiệu lực.

| Kiểm tra | Nguồn dữ liệu | Kết quả nếu fail |
|---|---|---|
| Khoản vay tồn tại, trạng thái `ACTIVE`/`OVERDUE` | Core Banking | `BLOCK: DEBT_NOT_FOUND` |
| Số dư quá hạn > 0 tại thời điểm gọi | Core Banking (near-real-time) | `BLOCK: NO_OUTSTANDING` |
| Hợp đồng tín dụng hợp lệ, có `contract_ref` | LOS/CLMS | `BLOCK: CONTRACT_INVALID` |
| Khoản nợ chưa được bán/chuyển giao | Core + hệ thống bán nợ | `BLOCK: DEBT_TRANSFERRED` |
| Không trong thời gian ân hạn/cơ cấu đang hiệu lực | Core | `BLOCK: UNDER_RESTRUCTURE` |
| Thời hiệu khởi kiện (chỉ với action pháp lý) | Tính toán | `ESCALATE: STATUTE_REVIEW` |

> Kiểm tra "số dư quá hạn > 0 tại thời điểm gọi" quan trọng hơn vẻ ngoài của nó: khách hàng trả nợ lúc 16h mà 19h vẫn bị gọi nhắc là nguồn khiếu nại phổ biến nhất và hoàn toàn tránh được. Yêu cầu độ trễ dữ liệu ≤ 5 phút.

---

### G02 — Party Eligibility Gate
**Mục đích:** Chỉ liên hệ người có nghĩa vụ pháp lý với khoản nợ.

**Nguồn chân lý:** thuộc tính `contact_eligible` trên cạnh graph (xem tài liệu Collection Graph, Mục 7). Guardrail **không tự suy luận**, chỉ truy vấn.

**Whitelist cạnh được phép `YES`** (hard-coded, không cấu hình được qua UI):
`BORROWED`, `GUARANTEES`, `CO_BORROWER_WITH`, `LEGAL_REP_OF`

**Hai cạnh nâng lên `YES` tại runtime có điều kiện:**
- `REFERENCE_CONTACT_OF` — chỉ khi `consent_obtained = true` **và** có `consent_ref` lưu trữ được (yêu cầu của NĐ 356/2025, xem G03)
- `AUTHORIZED_BY` — chỉ trong phạm vi và thời hạn uỷ quyền còn hiệu lực

**Truy vấn (Cypher):**
```cypher
MATCH (l:Loan {loan_id: $loan_id})
MATCH (p) WHERE p.person_id = $target_id OR p.org_id = $target_id
OPTIONAL MATCH (p)-[r]->(l)
  WHERE type(r) IN ['BORROWED','GUARANTEES','CO_BORROWER_WITH']
    AND r.status='ACTIVE' AND (r.valid_to IS NULL OR r.valid_to > date())
OPTIONAL MATCH (p)-[lr:LEGAL_REP_OF]->(:Organization)-[:BORROWED]->(l)
  WHERE lr.is_current = true
OPTIONAL MATCH (p)-[cr:REFERENCE_CONTACT_OF|AUTHORIZED_BY]->()-[:BORROWED]->(l)
  WHERE coalesce(cr.consent_obtained,false)=true
    AND cr.consent_ref IS NOT NULL
    AND (cr.expiry IS NULL OR cr.expiry > date())
RETURN
  CASE
    WHEN p.deceased_flag THEN 'BLOCK_DECEASED'
    WHEN r IS NOT NULL   THEN 'ALLOW_OBLIGATED'
    WHEN lr IS NOT NULL  THEN 'ALLOW_LEGAL_REP'
    WHEN cr IS NOT NULL  THEN 'ALLOW_CONSENTED'
    ELSE 'BLOCK_NO_LEGAL_BASIS'
  END AS decision,
  coalesce(type(r), type(lr), type(cr)) AS basis_edge;
```

**Fail-closed:** truy vấn không trả về bản ghi, hoặc Neo4j không phản hồi trong 300ms → `BLOCK: ELIGIBILITY_UNVERIFIABLE`.

**Chặn bổ sung:** nếu `er_ambiguity_flag = true` trên node đích (entity resolution chưa được duyệt), kết quả tối đa là `ALLOW_WITH_CONDITIONS` với `conditions: ["no_debt_disclosure"]` — được liên hệ để xác minh danh tính nhưng **không được tiết lộ thông tin khoản nợ**. Đây là biện pháp chống rủi ro liên hệ nhầm người, đồng thời phù hợp nghĩa vụ bí mật thông tin khách hàng theo NĐ 117/2018.

---

### G03 — Consent & Do-Not-Contact Gate
**Mục đích:** Tôn trọng quyền của chủ thể dữ liệu theo Luật BVDLCN 91/2025 và NĐ 356/2025.

| Kiểm tra | Kết quả |
|---|---|
| `dnc_flag = true` trên node đích | `BLOCK: DNC_ACTIVE` |
| `dnc_scope` giới hạn theo kênh (ví dụ: từ chối gọi điện nhưng chấp nhận SMS) | Chặn đúng kênh bị từ chối |
| Khách hàng có luật sư đại diện (`has_legal_counsel`) | `BLOCK: CONTACT_VIA_COUNSEL` + chuyển hướng tới kênh luật sư |
| Yêu cầu rút đồng ý đang xử lý | `BLOCK: CONSENT_WITHDRAWAL_PENDING` |
| Với cạnh `REFERENCE_CONTACT_OF`: `consent_ref` có tồn tại và truy xuất được bằng chứng không | `BLOCK: CONSENT_EVIDENCE_MISSING` |

**Yêu cầu mới từ NĐ 356/2025 — bắt buộc hiện thực hóa:**
1. **Cấm mặc định đồng ý.** Trường `consent_obtained` không được có giá trị mặc định `true` ở bất kỳ đâu trong hệ thống. DB constraint: `DEFAULT false NOT NULL`.
2. **Phải lưu trữ được sự đồng ý.** `consent_ref` phải trỏ tới một bản ghi có: thời điểm, phương thức thu thập (văn bản/ghi âm/eKYC), nội dung đã được đồng ý, và định danh người đồng ý. Guardrail **xác minh bản ghi này thực sự tồn tại và đọc được**, không chỉ kiểm tra cờ boolean.
3. **SLA phản hồi yêu cầu của chủ thể dữ liệu.** Guardrail phát sinh sự kiện `DSR_RECEIVED` khi phát hiện yêu cầu truy cập/chỉnh sửa/xoá, gắn hạn xử lý theo NĐ 356 🔶 (cần Pháp chế xác nhận số ngày cụ thể).

---

### G04 — Frequency Cap Gate
**Mục đích:** Không tạo áp lực bằng tần suất.

**Mô hình cửa sổ trượt hai tầng:**

```yaml
frequency_policy:
  scope: per_loan_per_party      # tính theo từng khoản nợ và từng đối tượng
  windows:
    - id: daily_reminder
      basis: TT18_2019_self_adopted
      unit: rolling_24h
      max_attempts: 5             # sàn theo TT 18/2019
      counted_channels: [VOICE, SMS, ZALO, EMAIL, IVR]
    - id: weekly_voice
      basis: international_benchmark
      unit: rolling_7d
      max_attempts: 7             # theo chuẩn Regulation F
      counted_channels: [VOICE, IVR]
    - id: post_rpc_cooldown
      basis: international_benchmark
      trigger: last_rpc_at
      cooldown_hours: 168         # 7 ngày sau khi đã nói chuyện được
      applies_to: [VOICE, IVR]
      exception_if: ptp_broken OR customer_initiated
```

**Quy tắc đếm** (khác biệt quan trọng, học từ Regulation F):
- Cửa sổ là **trượt liên tục**, không reset theo ngày lịch hay tuần lịch.
- Đếm theo **từng khoản nợ**, không phải từng khách hàng. Khách hàng có 3 khoản nợ thì mỗi khoản có bộ đếm riêng — nhưng xem cảnh báo tích luỹ bên dưới.
- **Cuộc gọi vào hộp thư thoại vẫn tính là một lần gọi.**
- Cuộc gọi không kết nối (máy bận, không đổ chuông, thuê bao không tồn tại) **không tính**.
- Khách hàng chủ động gọi đến **không tính**.

**Cảnh báo tích luỹ đa khoản nợ:** khi một khách hàng có nhiều khoản nợ và tổng số lần liên hệ trong 24h vượt `max_attempts × 1.5`, Guardrail trả `ESCALATE: CUMULATIVE_PRESSURE` bất kể từng khoản riêng lẻ đều hợp lệ. Đây là điểm mà cách đếm "theo từng khoản nợ" tạo ra kẽ hở, và cần bịt lại — bản chất khách hàng vẫn là một người nhận cuộc gọi.

**Hiện thực:** Redis sorted set, key `freq:{loan_id}:{party_id}:{channel}`, member = `attempt_id`, score = epoch ms. Đếm bằng `ZCOUNT` trong khoảng `[now - window, now]`. TTL tự động dọn.

```python
def check_frequency(loan_id, party_id, channel, window_sec, max_attempts):
    key = f"freq:{loan_id}:{party_id}:{channel}"
    now = time.time()
    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, now - window_sec)   # dọn ngoài cửa sổ
    pipe.zcount(key, now - window_sec, now)
    _, count = pipe.execute()
    return count < max_attempts, count
```

**Fail-closed:** Redis không phản hồi → `BLOCK: FREQUENCY_UNVERIFIABLE`. Không dùng bộ đếm cục bộ dự phòng — bộ đếm sai còn nguy hiểm hơn không có bộ đếm.

---

### G05 — Time Window Gate

```yaml
time_policy:
  timezone: Asia/Ho_Chi_Minh
  allowed_window: "07:00-21:00"        # sàn theo TT 18/2019
  channels_subject_to_window: [VOICE, IVR, SMS, ZALO, FIELD_VISIT]
  channels_exempt: [EMAIL, IN_APP]      # 🔶 chờ Pháp chế xác nhận
  excluded_dates:
    - national_holidays
    - lunar_new_year_range              # từ 28 tháng Chạp đến mùng 6 Tết
  field_visit_window: "08:00-17:00"     # chặt hơn, do tính chất xâm phạm cao hơn
```

**Lưu ý:** khung giờ tính theo múi giờ Việt Nam; nếu khách hàng có `abroad_flag = true`, chuyển sang kênh không đồng bộ (email, in-app) và `BLOCK` kênh voice/SMS trừ khi khách hàng đã thỏa thuận khác.

Thăm hiện trường có khung giờ hẹp hơn liên hệ từ xa vì mức độ can thiệp vào đời sống riêng tư cao hơn hẳn — đây là chuẩn tự áp, không có quy định trực tiếp.

---

### G06 — Content Filter Gate
**Mục đích:** Không có nội dung đe dọa, xúc phạm, hoặc tiết lộ khoản nợ cho bên thứ ba.

**Áp dụng cho:** kịch bản SMS/ZNS, nội dung do LLM sinh (Collector Copilot), nội dung nhập tay trong Manual Enrichment, ghi chú tương tác.

**Ba tầng kiểm tra:**

| Tầng | Kỹ thuật | Hành vi |
|---|---|---|
| **1. Rule-based** | Từ điển cấm + regex (đe dọa, xúc phạm, ám chỉ pháp lý sai như "sẽ bị bắt", "truy tố hình sự" với nợ dân sự) | `BLOCK` ngay, không cần tầng sau |
| **2. Classifier** | Mô hình phân loại tiếng Việt: `THREATENING`, `ABUSIVE`, `THIRD_PARTY_DISCLOSURE`, `SENSITIVE_PII`, `FALSE_LEGAL_CLAIM` | `BLOCK` nếu score > ngưỡng; `ESCALATE` nếu ở vùng xám |
| **3. Template check** | Với kênh tự động: nội dung phải khớp template đã duyệt (allowlist), chỉ được thay thế biến | Lệch template → `BLOCK` |

**Quy tắc GR2 áp dụng ở đây:** mô hình phân loại chỉ có quyền **siết chặt**. Nếu tầng 1 đã `BLOCK` thì tầng 2 không thể nâng lên `ALLOW`. Nếu classifier không phản hồi trong 2s → với nội dung tự động: `BLOCK`; với nội dung nhập tay: `PENDING_REVIEW`.

**Kiểm tra tiết lộ bên thứ ba (theo NĐ 117/2018):** khi đối tượng liên hệ không phải bên vay (ví dụ bên bảo lãnh), nội dung được phép nêu nghĩa vụ bảo lãnh nhưng **không được nêu chi tiết tài chính của bên vay** vượt quá phạm vi nghĩa vụ bảo lãnh. Điều kiện này được truyền vào qua `conditions: ["limited_disclosure"]`.

---

### G07 — Vulnerability Gate

| Điều kiện | Kết quả |
|---|---|
| `vulnerability_flag = true` | `ALLOW_WITH_CONDITIONS` — chỉ kênh mềm, kịch bản hỗ trợ, cấm treatment cứng |
| `vulnerability_category = INCAPACITY` hoặc `BEREAVEMENT` | `ESCALATE` — chuyển bộ phận chuyên trách |
| `deceased_flag = true` | `BLOCK: DECEASED` — chuyển luồng xử lý thừa kế |
| `DISASTER_AFFECTED` (thiên tai, dịch bệnh theo công bố) | `ALLOW_WITH_CONDITIONS` + ưu tiên chào phương án cơ cấu |

**Nghĩa vụ khoan dung (forbearance-first):** với khách hàng có `root_cause_primary ∈ {INCOME_LOSS, BUSINESS_DOWNTURN, FORCE_MAJEURE, HEALTH_OR_FAMILY_EVENT}` **và** `ability_score < 40`, Guardrail trả `ALLOW_WITH_CONDITIONS` với `conditions: ["must_offer_forbearance_first"]`. Hệ thống chỉ cho phép chuyển sang treatment cứng (thu giữ, khởi kiện) sau khi có bản ghi chứng minh đã chào phương án cơ cấu và khách hàng từ chối hoặc không phản hồi.

Đây là chuẩn tự áp theo tinh thần FCA CONC 7 (Anh), chưa có quy định tương đương tại Việt Nam. Tôi khuyến nghị áp dụng vì đây là biện pháp phòng vệ danh tiếng rẻ nhất, và vì bằng chứng "đã chào phương án hỗ trợ trước khi cưỡng chế" có giá trị lớn khi có khiếu nại hoặc tranh tụng.

---

### G08 — Dispute & Hold Gate

| Điều kiện | Kết quả |
|---|---|
| `dispute_hold_active = true` | `BLOCK: DISPUTE_HOLD` |
| Khiếu nại đang xử lý trong SLA | `BLOCK: COMPLAINT_PENDING` |
| Khách hàng đã yêu cầu cung cấp bằng chứng khoản nợ, chưa cung cấp | `BLOCK: VALIDATION_PENDING` |
| Đang trong thời gian thỏa thuận cơ cấu chờ phê duyệt | `ALLOW_WITH_CONDITIONS: ["status_update_only"]` |

---

### G09 — Collateral Enforcement Gate 🆕
**Đây là control mới, bổ sung sau khi rà soát Luật 96/2025/QH15 và NĐ 304/2025/NĐ-CP.**

**Kích hoạt khi:** action thuộc `{PROPOSE_SEIZURE, INITIATE_SEIZURE, FIELD_SEIZURE_NOTICE}`.

**Quan trọng về thời điểm:** control này chạy **cả khi NBA Engine chỉ mới *đề xuất*** hành động thu giữ, không chỉ khi thực thi. Không được hiển thị cho cán bộ một khuyến nghị mà pháp luật không cho phép thực hiện.

| Kiểm tra | Nguồn | Kết quả |
|---|---|---|
| Khoản nợ có phải nợ xấu theo định nghĩa | Core (phân loại nợ) | `BLOCK: NOT_NPL` |
| Hợp đồng bảo đảm có thỏa thuận về quyền thu giữ | LOS/CLMS | `BLOCK: NO_SEIZURE_CLAUSE` |
| Đã đáp ứng điều kiện tại điểm a,b,c,d,e khoản 2 Điều 198a | Checklist có bằng chứng | `BLOCK: ART198A_CONDITIONS_UNMET` |
| **TSBĐ có phải chỗ ở duy nhất?** | `Collateral.is_sole_residence` | Nếu `true` → nhánh đặc biệt bên dưới |
| **TSBĐ có phải công cụ lao động chủ yếu/duy nhất?** | `Collateral.is_primary_work_tool` | Nếu `true` → nhánh đặc biệt bên dưới |
| Cả hai thuộc tính đều `NULL` (chưa xác minh) | | `BLOCK: SOLE_RESIDENCE_UNVERIFIED` |

**Nhánh đặc biệt — chỗ ở duy nhất / công cụ lao động duy nhất:**

Theo NĐ 304/2025, tài sản thuộc nhóm này chỉ được thu giữ khi đáp ứng các điều kiện tại Điều 198a **và** một trong các điều kiện bổ sung của Nghị định. Với trường hợp thu giữ chỗ ở duy nhất đã được xác nhận và chứng minh, bên nhận bảo đảm phải **trích một khoản tiền cho bên bảo đảm bằng 12 tháng lương tính theo mức lương tối thiểu**. Tinh thần của Nghị định là bảo đảm bên bảo đảm và gia đình duy trì được chi phí sinh hoạt tối thiểu.

```
IF is_sole_residence OR is_primary_work_tool THEN
    IF NOT has_borrower_confirmation_document THEN
        RETURN BLOCK: SOLE_RESIDENCE_NOT_CONFIRMED
    IF NOT compensation_amount_computed THEN
        RETURN BLOCK: COMPENSATION_NOT_PROVISIONED
    IF NOT internal_seizure_procedure_followed THEN
        RETURN BLOCK: INTERNAL_PROCEDURE_INCOMPLETE
    RETURN ESCALATE: SOLE_RESIDENCE_SEIZURE_APPROVAL
        (bắt buộc phê duyệt cấp Hội sở, không phân cấp chi nhánh)
END IF
```

**Bổ sung schema bắt buộc** cho node `:Collateral` trong Collection Graph:

| Thuộc tính mới | Kiểu | Nguồn | Ghi chú |
|---|---|---|---|
| `is_sole_residence` | BOOLEAN (nullable) | Cam kết/xác nhận của bên bảo đảm tại hợp đồng hoặc văn bản khác | `NULL` = chưa xác minh → chặn |
| `is_primary_work_tool` | BOOLEAN (nullable) | Như trên | |
| `sole_residence_evidence_ref` | STRING | Tham chiếu văn bản xác nhận | Bắt buộc khi `is_sole_residence = true` |
| `sole_residence_verified_at` | DATE | | Cần tái xác minh định kỳ |
| `compensation_provisioned` | BOOLEAN | Hệ thống kế toán | 12 tháng lương tối thiểu |

**Yêu cầu tổ chức đi kèm:** Luật 96/2025 yêu cầu TCTD ban hành quy định nội bộ về trình tự thu giữ TSBĐ, **kể cả khi ủy quyền cho bên thứ ba**. Guardrail kiểm tra `internal_procedure_version` của quy định nội bộ đang áp dụng và ghi vào audit — để khi thanh tra có thể chứng minh hành động được thực hiện theo quy trình nào, phiên bản nào.

---

### G10 — Data Protection Gate

| Kiểm tra | Cơ sở | Kết quả nếu fail |
|---|---|---|
| Mục đích xử lý dữ liệu khớp mục đích đã đăng ký trong hồ sơ DPIA | Luật 91/2025 | `BLOCK: PURPOSE_MISMATCH` |
| Trường dữ liệu dùng trong hành động nằm trong phạm vi đã khai báo | NĐ 356/2025 | `BLOCK: FIELD_OUT_OF_SCOPE` |
| Dữ liệu chưa quá `ttl_expiry` | Chính sách nội bộ | Loại trường quá hạn khỏi payload |
| **Dữ liệu về vợ/chồng** được xử lý đúng phạm vi | NĐ 356/2025 mở rộng dữ liệu cá nhân cơ bản, bổ sung thông tin về vợ/chồng (quy định cũ chỉ gồm cha, mẹ, con cái) | `BLOCK` nếu dùng ngoài phạm vi nghĩa vụ pháp lý |
| Với dữ liệu vị trí (Field App GPS) và sinh trắc học: cơ chế thông báo vi phạm sẵn sàng | NĐ 356/2025 yêu cầu thông báo chủ thể dữ liệu trong 72 giờ kể từ khi phát hiện vi phạm | Cấu hình bắt buộc, kiểm tra ở mức hệ thống |

**Tác động lên Collection Graph:** cạnh `FAMILY_OF` với `relation_type = SPOUSE` giờ chứa dữ liệu cá nhân cơ bản của người thứ ba theo quy định mới. Cạnh này vẫn giữ `contact_eligible = NO`, nhưng bổ sung ràng buộc: chỉ được **sử dụng** (kể cả để phân tích) khi phục vụ mục đích xác định tài sản chung trong quá trình xử lý TSBĐ — tức chỉ khi G09 đã kích hoạt. Ngoài bối cảnh đó, cạnh này bị ẩn khỏi mọi truy vấn của tầng NBA.

---

### G11 — Irreversible Action Gate

Các hành động không đảo ngược **luôn** trả `ESCALATE`, không bao giờ `ALLOW` tự động:

| Hành động | Cấp phê duyệt |
|---|---|
| Khởi kiện | Hội sở / Ban Pháp chế |
| Thu giữ TSBĐ thông thường | Giám đốc chi nhánh + Ban XLN |
| **Thu giữ chỗ ở duy nhất / công cụ lao động duy nhất** | **Hội sở, không phân cấp** |
| Miễn giảm lãi vượt ngưỡng | Theo phân cấp thẩm quyền |
| Bán nợ | Hội đồng XLN |
| Chuyển sang theo dõi ngoại bảng | Theo phân cấp |
| Áp nhãn `WILFUL_DEFAULT` lên hồ sơ | Kiểm soát viên (4 mắt) |

Guardrail chỉ tạo yêu cầu phê duyệt và ghi nhận; việc phê duyệt diễn ra ở Workflow Engine với đầy đủ audit.

---

### G12 — Audit & Evidence

**Mọi lượt gọi Guardrail đều ghi một bản ghi bất biến**, kể cả khi kết quả là `ALLOW`.

```json
{
  "audit_id": "GA-2026-09-01-00184423",
  "ts": "2026-09-01T19:04:12.338+07:00",
  "request": {
    "intent_id": "NBA-2026-0912847",
    "case_id": "C-2026-88213",
    "loan_id": "L-0099213",
    "target_party_id": "P-8891234",
    "action": "VOICE_CALL",
    "channel": "VOICE",
    "initiated_by": "EMP-4471",
    "source_system": "COLLECTOR_UI"
  },
  "policy_version": "gp-2026.09.01-r3",
  "internal_procedure_version": "QTNB-XLN-2026-02",
  "controls": [
    {"id":"G01","result":"PASS","detail":{"outstanding":245000000}},
    {"id":"G02","result":"PASS","basis_edge":"BORROWED"},
    {"id":"G03","result":"PASS"},
    {"id":"G07","result":"PASS"},
    {"id":"G08","result":"PASS"},
    {"id":"G10","result":"PASS"},
    {"id":"G05","result":"PASS","window":"07:00-21:00","local_time":"19:04"},
    {"id":"G04","result":"PASS","counts":{"rolling_24h":1,"rolling_7d":3}},
    {"id":"G06","result":"PASS","template_id":"TPL-VOICE-B2-014"}
  ],
  "decision": "ALLOW",
  "conditions": [],
  "token": "gt_01J9X...",
  "token_expires_at": "2026-09-01T19:09:12+07:00",
  "prev_hash": "a83f...",
  "hash": "9c17..."
}
```

**Yêu cầu lưu trữ:**
- Audit log: **tối thiểu 5 năm**, WORM storage, hash-chain liên kết để chống sửa.
- Hồ sơ vi phạm dữ liệu cá nhân: NĐ 356/2025 yêu cầu lưu **tối thiểu 5 năm sau khi khắc phục**.
- Bản ghi `BLOCK` không được xoá trước hạn — đây là bằng chứng có giá trị cao nhất khi chứng minh tuân thủ.

---

## 6. Hợp đồng API

### 6.1 Mô hình hai pha (evaluate → commit)

Bộ đếm tần suất chỉ được tăng khi hành động **thực sự xảy ra**, không phải khi được phép. Nếu tăng ở bước evaluate, một chiến dịch bị huỷ giữa chừng sẽ đốt hết quota của khách hàng.

```
L5/UI ──evaluate──► Guardrail ──► ALLOW + token (TTL 5 phút, có reservation)
                                        │
L7 thực thi hành động ◄─────────────────┘
     │
     └──commit(token, outcome)──► Guardrail ──► tăng bộ đếm + chốt audit
     
Nếu không commit trong TTL → reservation tự huỷ, bộ đếm không tăng.
```

### 6.2 `POST /v1/guardrail/evaluate`

**Request:**
```json
{
  "intent_id": "NBA-2026-0912847",
  "case_id": "C-2026-88213",
  "loan_id": "L-0099213",
  "target": {"type": "PERSON", "id": "P-8891234"},
  "action": "VOICE_CALL",
  "channel": "VOICE",
  "scheduled_at": "2026-09-01T19:04:00+07:00",
  "content": {"template_id": "TPL-VOICE-B2-014", "rendered_text": null},
  "initiated_by": "EMP-4471",
  "source_system": "COLLECTOR_UI"
}
```

**Response — cho phép:**
```json
{
  "decision": "ALLOW",
  "token": "gt_01J9X...",
  "expires_at": "2026-09-01T19:09:12+07:00",
  "conditions": [],
  "remaining": {"rolling_24h": 4, "rolling_7d": 4},
  "audit_id": "GA-2026-09-01-00184423"
}
```

**Response — chặn:**
```json
{
  "decision": "BLOCK",
  "reason_code": "G02_NO_LEGAL_BASIS",
  "reason_message_vi": "Đối tượng này không có nghĩa vụ trả nợ đối với khoản vay. Không được liên hệ về khoản nợ.",
  "remediation": "Kiểm tra lại danh sách bên có nghĩa vụ trên hồ sơ, hoặc bổ sung bằng chứng bảo lãnh nếu có.",
  "overridable": false,
  "audit_id": "GA-2026-09-01-00184424"
}
```

**Nguyên tắc thông điệp:** `reason_message_vi` viết cho cán bộ đọc, giải thích *tại sao* chứ không chỉ *cái gì*. `remediation` chỉ ra việc cần làm. Một Guardrail chỉ nói "bị chặn" sẽ bị người dùng tìm cách lách; một Guardrail giải thích được sẽ dạy người dùng làm đúng.

### 6.3 `POST /v1/guardrail/commit`
```json
{"token": "gt_01J9X...", "outcome": "RPC", "duration_sec": 214, "recording_ref": "REC-..."}
```
Ghi nhận kết quả, tăng bộ đếm, cập nhật `last_rpc_at` (kích hoạt cooldown 7 ngày ở G04).

### 6.4 Các endpoint khác
| Endpoint | Mục đích |
|---|---|
| `POST /v1/guardrail/batch-evaluate` | Lọc trước danh sách chiến dịch (tối đa 10.000 intent/lượt) |
| `GET /v1/guardrail/policy/current` | Trả version policy đang áp dụng |
| `POST /v1/guardrail/dsr` | Ghi nhận yêu cầu của chủ thể dữ liệu, khởi tạo SLA |
| `GET /v1/guardrail/evidence/{case_id}` | Xuất gói bằng chứng cho khiếu nại/thanh tra |

> `batch-evaluate` chỉ dùng để **lọc trước**, kết quả không có giá trị cho phép thực thi. Mỗi hành động vẫn phải gọi `evaluate` tại thời điểm gửi (nguyên tắc GR7).

---

## 7. Policy-as-code

Toàn bộ chính sách nằm trong repository Git riêng, có ký số, CI kiểm tra, và quy trình phê duyệt.

```yaml
# guardrail-policy-2026.09.01-r3.yaml
version: gp-2026.09.01-r3
effective_from: 2026-09-01T00:00:00+07:00
approved_by:
  compliance_officer: "NGUYEN VAN X"
  legal_head: "TRAN THI Y"
  approval_ref: "QD-2026-1142"
signature: "..."

eligibility:
  whitelist_edges: [BORROWED, GUARANTEES, CO_BORROWER_WITH, LEGAL_REP_OF]
  conditional_edges:
    REFERENCE_CONTACT_OF: {requires: [consent_obtained, consent_ref, not_expired]}
    AUTHORIZED_BY:        {requires: [poa_valid, within_scope]}
  # KHÔNG cho phép thêm cạnh vào whitelist qua file này —
  # whitelist được hard-code, mục này chỉ để đối chiếu và cảnh báo lệch.

frequency: {...}   # xem G04
time: {...}        # xem G05

collateral_enforcement:
  require_npl_status: true
  require_seizure_clause: true
  sole_residence:
    require_confirmation_document: true
    compensation_months: 12
    compensation_basis: statutory_minimum_wage
    approval_level: HEAD_OFFICE
    delegable: false

escalation_matrix: {...}
```

**Nguyên tắc:** whitelist của G02 và các gate thuộc nhóm chặn cứng **không cấu hình được qua policy file**. Chúng nằm trong code, có unit test, và thay đổi cần release. Policy file chỉ điều chỉnh ngưỡng, khung giờ, ma trận phê duyệt — những thứ mà business cần đổi nhanh mà không tạo được lỗ hổng.

---

## 8. Chế độ suy giảm (Degradation)

| Thành phần lỗi | Hành vi |
|---|---|
| Neo4j (G02) | `BLOCK` toàn bộ hành động ra kênh |
| Redis (G04) | `BLOCK` toàn bộ |
| Core Banking (G01) | `BLOCK` — không đòi nợ khi không biết dư nợ hiện tại |
| Persona Service (G07) | `BLOCK` — không biết khách hàng có dễ tổn thương hay không thì không liên hệ |
| Content Classifier (G06) | Nội dung tự động: `BLOCK`; nội dung nhập tay: `PENDING_REVIEW` |
| Policy Store | Dùng bản cache đã ký gần nhất, tối đa 1 giờ; sau đó `BLOCK` |
| Audit Log store | **`BLOCK`** — không ghi được bằng chứng thì không được hành động |

Mục cuối cùng gây tranh cãi nhiều nhất khi thiết kế, nhưng tôi giữ nguyên: một hành động thu hồi không có bằng chứng đã qua kiểm soát là hành động không bảo vệ được ngân hàng khi có khiếu nại. Chi phí của việc dừng dialer 20 phút thấp hơn nhiều so với chi phí của một sự cố không giải trình được.

---

## 9. Yêu cầu phi chức năng

| Chỉ tiêu | Mục tiêu |
|---|---|
| Latency `evaluate` | p50 < 80ms, p95 < 250ms, p99 < 400ms |
| Throughput | 2.000 TPS thường, 8.000 TPS đỉnh (chiến dịch sáng) |
| `batch-evaluate` | 10.000 intent < 30s |
| Khả dụng | 99,95% — Guardrail down = toàn bộ thu hồi ra kênh dừng |
| Triển khai | K8s multi-AZ, tối thiểu 6 replica, không có single point |
| Bảo mật | mTLS nội bộ, token ký ES256, rotate khoá qua KMS/HSM |
| Audit throughput | Ghi bất đồng bộ vào queue bền, nhưng **xác nhận nhận được** trước khi trả `ALLOW` |

---

## 10. Kiểm thử & bằng chứng tuân thủ

### 10.1 Bộ test bắt buộc trước khi go-live
| Nhóm | Số case tối thiểu | Nội dung |
|---|---|---|
| Party eligibility | 60 | Mọi tổ hợp loại cạnh × trạng thái × thời hạn |
| Frequency | 40 | Biên cửa sổ trượt, voicemail, cuộc gọi không kết nối, đa khoản nợ |
| Time window | 25 | Biên 07:00/21:00, lễ Tết, khách ở nước ngoài |
| Collateral G09 | 35 | Chỗ ở duy nhất, công cụ lao động, thiếu xác minh, thiếu trích lập |
| Content filter | 200+ | Bộ mẫu tiếng Việt gồm cả biến thể lách từ khoá |
| Fail-closed | 20 | Tắt từng phụ thuộc, xác nhận đều ra `BLOCK` |
| Bypass attempt | 15 | Gọi L7 trực tiếp không token, token hết hạn, token của case khác |

Nhóm cuối quan trọng nhất: **phải chứng minh được không tồn tại đường vòng**. Đề xuất thuê kiểm thử độc lập cho nhóm này.

### 10.2 Gói bằng chứng (Evidence Pack)
`GET /v1/guardrail/evidence/{case_id}` xuất một gói gồm: toàn bộ audit của case, phiên bản policy áp dụng tại từng thời điểm, phiên bản quy định nội bộ, danh sách các lần bị chặn, và bằng chứng đã chào phương án cơ cấu (nếu có). Đây là tài liệu nộp khi có khiếu nại hoặc thanh tra — thiết kế để **xuất trong vài phút, không phải vài ngày**.

---

## 11. Chỉ số giám sát chính Guardrail

| Chỉ số | Ý nghĩa | Ngưỡng cảnh báo |
|---|---|---|
| Block rate theo lý do | Phân bố nguyên nhân bị chặn | Tăng đột biến một mã lý do |
| `G02_NO_LEGAL_BASIS` rate | Cán bộ đang cố liên hệ người không có nghĩa vụ | **> 2% → đào tạo lại** |
| `G06` block rate theo cán bộ | Chất lượng nội dung | Cá nhân > 5% → rà soát |
| Bypass attempt count | Nỗ lực đi đường vòng | **> 0 → điều tra ngay** |
| Frequency near-cap ratio | Tỷ lệ case chạm 80% quota | Chỉ báo áp lực chỉ tiêu |
| ESCALATE backlog | Hàng đợi phê duyệt quá 48h | > 5% |
| p95 latency | | > 250ms |
| Fail-closed activation | Số lần chặn do lỗi hệ thống | Bất kỳ đợt nào > 5 phút |

Chỉ số `G02_NO_LEGAL_BASIS` là chỉ số văn hoá, không phải chỉ số kỹ thuật. Nó đo mức độ cán bộ đang cố làm điều mà pháp luật không cho phép — và nó phải giảm dần theo thời gian. Nếu không giảm, vấn đề nằm ở cơ chế giao chỉ tiêu, không nằm ở hệ thống.

---

## 12. Ma trận trách nhiệm

| Hạng mục | Sở hữu | Phê duyệt thay đổi |
|---|---|---|
| Whitelist `contact_eligible` (code) | EA/SA | Compliance Officer + Pháp chế, kèm release |
| Ngưỡng tần suất, khung giờ (policy) | Collection Strategy Team | Compliance Officer |
| Ma trận phê duyệt G11 | Khối XLN | Ban Điều hành |
| Từ điển & mô hình Content Filter | Compliance + ML | Compliance Officer |
| Quy định nội bộ trình tự thu giữ | Ban XLN + Pháp chế | Ban Điều hành |
| Hồ sơ DPIA & phạm vi dữ liệu | DPO | DPO + Pháp chế |

---

## 13. Lộ trình

| Giai đoạn | Nội dung | Thời gian |
|---|---|---|
| **GR-P1** (bắt buộc trước mọi liên hệ ra kênh) | G01, G02, G03, G05, G12 + API evaluate/commit + audit hash-chain | Tháng 1–3 |
| **GR-P2** | G04 (cửa sổ trượt), G06 (rule-based + template), G08 | Tháng 3–5 |
| **GR-P3** | G07, G09 (collateral gate), G10, G11 | Tháng 5–8 |
| **GR-P4** | G06 tầng classifier, Evidence Pack tự động, giám sát nâng cao | Tháng 8–11 |

**Không được ra kênh trước khi hoàn thành GR-P1.** Đây là ràng buộc cứng của lộ trình dự án, không phải khuyến nghị.

---

## 14. Quy trình thay đổi chính sách

```
Đề xuất (Strategy Team / Pháp chế)
  → Đánh giá tác động (mô phỏng trên 30 ngày dữ liệu lịch sử:
     bao nhiêu hành động sẽ bị chặn thêm/bớt?)
  → Thẩm định pháp lý
  → Phê duyệt Compliance Officer (+ Ban Điều hành nếu nới lỏng)
  → Ký số policy file, merge vào Git
  → Triển khai canary 5% → 100% trong 48h
  → Theo dõi block rate 7 ngày
```

**Quy tắc bất đối xứng:** siết chặt chính sách có thể triển khai ngay. **Nới lỏng** bất kỳ ngưỡng nào đều cần phê duyệt cấp cao hơn một bậc và đánh giá tác động bắt buộc. Hệ thống nên dễ làm chặt và khó làm lỏng.

---

## 15. Rủi ro còn lại

| # | Rủi ro | Biện pháp |
|---|---|---|
| R1 | Cán bộ liên hệ ngoài hệ thống (điện thoại cá nhân) | Không giải quyết được bằng kỹ thuật. Cần: cấm trong quy chế, đối soát CDR tổng đài, xử lý kỷ luật, và **QA tự động 100% cuộc gọi qua hệ thống** để hệ thống chính thức luôn tiện hơn đường vòng |
| R2 | Chỗ ở duy nhất chưa được xác minh trên diện rộng | Chiến dịch xác minh có kế hoạch; trong lúc chờ, G09 chặn mặc định |
| R3 | Content Filter tiếng Việt thiếu dữ liệu huấn luyện | Bắt đầu bằng rule-based + template allowlist; classifier là tăng cường, không phải nền tảng |
| R4 | Áp lực chỉ tiêu tạo sức ép nới ngưỡng | Quy tắc bất đối xứng ở Mục 14 + báo cáo block rate lên Uỷ ban Rủi ro |
| R5 | Quy định pháp luật thay đổi | Rà soát định kỳ 6 tháng; policy-as-code cho phép cập nhật nhanh |

---

## 16. Điểm khác biệt so với bản trước

| Nội dung | v0.1 | v1.0 |
|---|---|---|
| Tần suất | 3–5 lần/ngày, cửa sổ ngày lịch | Cửa sổ trượt hai tầng: 5/24h + 7/7 ngày + cooldown 168h sau RPC; đếm theo khoản nợ + cảnh báo tích luỹ đa khoản |
| Cơ sở pháp lý | NĐ 13/2023 | Luật 91/2025 + NĐ 356/2025 (NĐ 13 đã hết hiệu lực từ 01/01/2026) |
| Consent | Cờ boolean | Bắt buộc bằng chứng lưu trữ được; cấm mặc định đồng ý; SLA phản hồi DSR |
| Thu giữ TSBĐ | Không có control | **G09 mới** theo Luật 96/2025 + NĐ 304/2025, gồm nhánh chỗ ở duy nhất |
| Forbearance | Không có | Điều kiện `must_offer_forbearance_first` |
| Dữ liệu vợ/chồng | Không xử lý riêng | Ràng buộc phạm vi sử dụng theo NĐ 356/2025 |
| Mô hình gọi | Một pha | Hai pha evaluate/commit để bộ đếm chính xác |

---

## 17. Hạng mục chờ Pháp chế chốt 🔶

| # | Câu hỏi | Ảnh hưởng |
|---|---|---|
| 1 | Ngân hàng có tự áp chuẩn TT 18/2019 không? Ở mức nào? | Ngưỡng G04, G05 |
| 2 | Nếu có, kế hoạch bổ sung điều khoản nhắc nợ vào mẫu hợp đồng tín dụng? | Điều kiện tiên quyết để G04/G05 có hiệu lực pháp lý |
| 3 | Email và in-app notification có thuộc phạm vi "nhắc nợ" cần giới hạn khung giờ không? | G05 |
| 4 | Số ngày SLA phản hồi yêu cầu chủ thể dữ liệu theo NĐ 356/2025? | G03 |
| 5 | Điều khoản cụ thể của Luật BVQLNTD 19/2023 về quấy rối người tiêu dùng? | G08, G06 |
| 6 | Mã `CIC_CREDIT_RECORD` trong danh mục đòn bẩy — cách diễn đạt an toàn để không bị coi là đe dọa? | G06, danh mục `negotiation_lever` |
| 7 | Phạm vi xác nhận "chỗ ở duy nhất": ai xác nhận, bằng văn bản gì, hiệu lực bao lâu? | G09 |
| 8 | Cơ sở pháp lý xử lý dữ liệu từ nguồn công khai (cổng ĐKKD, cổng bản án) — "thực hiện hợp đồng" hay "lợi ích hợp pháp"? | G10, OSINT Collector |

**Toàn bộ nội dung pháp lý trong tài liệu này được tra cứu qua nguồn thứ cấp (báo chí, trang tổng hợp pháp luật) và phải được đối chiếu với bản gốc trên Công báo trước khi hiện thực hóa.**

---

*Đặc tả kỹ thuật, phiên bản đề xuất. Các ngưỡng là giá trị khởi tạo, cần hiệu chỉnh trên dữ liệu thực tế và theo quyết định chính sách của Ngân hàng.*
