# B.COLLECTION — ĐỀ XUẤT KIẾN TRÚC TỔNG THỂ
### Hệ thống Quản lý & Tối ưu Thu hồi nợ trên nền Big Data – Graph – AI
**Góc nhìn:** Enterprise Architect | **Phạm vi:** BIDV (bán lẻ + KHDN) | **Phiên bản:** v0.1 (bản đề xuất kiến trúc)

---

## 0. Tóm tắt cho lãnh đạo (Executive Summary)

B.Collection không nên được xây như "một phần mềm quản lý danh sách nợ quá hạn". Bản chất bài toán là **tối ưu hoá phân bổ nguồn lực thu hồi trên một tập nợ có xác suất thu hồi rất khác nhau** — cùng một đồng chi phí thu hồi bỏ vào khách hàng A cho ra 3 đồng, bỏ vào khách hàng B cho ra 0 đồng. Giá trị lớn nhất của hệ thống nằm ở ba năng lực:

1. **Chân dung nợ (Debtor 360 + Graph)** — hiểu *ai đang nợ, họ đang ở đâu trong mạng lưới quan hệ – tài sản – dòng tiền, và vì sao họ chưa trả*.
2. **Bộ máy quyết định chiến lược (Decision & Strategy Engine)** — từ chân dung sinh ra **Next Best Action**: ai gọi, gọi lúc nào, kênh nào, đề xuất phương án gì (cơ cấu / miễn giảm lãi / thu giữ TSBĐ / khởi kiện / bán nợ).
3. **Vòng lặp học từ case thành công (Case-Based Reference Engine)** — mỗi lần thu hồi thành công trở thành một "reference case" được vector hoá và tự động gợi ý cho khách hàng có chân dung tương đồng.

**Ràng buộc thiết kế bắt buộc:** kiến trúc phải đặt **Compliance & Ethics Guardrail là một tầng kiến trúc độc lập, chạy xác định (deterministic), fail-closed**, không phải một mục trong tài liệu chính sách. Lý do ở Mục 2. Đây là điểm khác biệt sống còn giữa một hệ thống collection đẳng cấp ngân hàng và một hệ thống bị "tuýt còi" sau 6 tháng vận hành.

---

## 1. Mục tiêu & Chỉ số thành công

### 1.1 Mục tiêu nghiệp vụ
| # | Mục tiêu | Chỉ số đo (KPI) | Baseline → Target (gợi ý 18 tháng) |
|---|---|---|---|
| M1 | Tăng tỷ lệ tự khỏi nợ ở nhóm sớm | Cure rate B1 (DPD 1–30) | +8–12 điểm % |
| M2 | Giảm dịch chuyển nhóm nợ | Roll rate B1→B2, B2→B3 | −15–20% tương đối |
| M3 | Tăng hiệu suất thu hồi nợ xấu | Recovery rate NPL/XLRR | +10–15% tương đối |
| M4 | Giảm chi phí thu hồi | Cost-to-Collect (CTC / 1 đồng thu được) | −20–25% |
| M5 | Tăng chất lượng tiếp cận | Right Party Contact (RPC) rate | +25% tương đối |
| M6 | Tăng độ tin cậy cam kết | PTP Kept Rate (giữ đúng cam kết trả) | +15 điểm % |
| M7 | Rút ngắn chu kỳ xử lý | Time-to-Resolution theo bucket | −30% |
| M8 | Kiểm soát rủi ro danh tiếng | Số khiếu nại / 1.000 tương tác | Giảm và có trace 100% |

### 1.2 Nguyên tắc kiến trúc (Architecture Principles)
- **AP1 – Compliance by design, fail-closed.** Mọi hành động ra kênh (gọi, SMS, thăm hiện trường) phải đi qua Guardrail Service. Guardrail không phản hồi = chặn hành động.
- **AP2 – Data minimization & purpose limitation.** Chỉ thu thập – lưu trữ dữ liệu có mục đích thu hồi nợ đã đăng ký; mọi trường dữ liệu có TTL và chủ sở hữu.
- **AP3 – Provenance-first.** Mọi thuộc tính chân dung phải trả lời được: *nguồn nào, ai nhập, khi nào, độ tin cậy bao nhiêu, cơ sở pháp lý nào*.
- **AP4 – Human-in-the-loop cho quyết định trọng yếu.** AI đề xuất, con người quyết định với các hành động không thể đảo ngược (khởi kiện, thu giữ TSBĐ, miễn giảm lãi, bán nợ).
- **AP5 – Tách Decisioning khỏi Execution.** Bộ não (chiến lược) tách khỏi tay chân (workflow, dialer, SMS) để thay đổi chiến lược không cần đổi hệ thống thực thi.
- **AP6 – Explainability là bắt buộc.** Không dùng mô hình không giải thích được cho quyết định ảnh hưởng trực tiếp đến khách hàng.
- **AP7 – Tái sử dụng tài sản sẵn có.** Đặc biệt là graph nhóm khách hàng liên quan (KHLQ) và nền tảng dữ liệu hiện hữu — xem Mục 12.

---

## 2. Khung pháp lý & Ranh giới đạo đức (thiết kế vào kiến trúc, không phải phụ lục)

> **Lưu ý:** phần này là định hướng kiến trúc, cần Khối Pháp chế & Tuân thủ + DPO chốt lại bằng văn bản trước khi thiết kế chi tiết. Các văn bản dưới đây có thể đã được sửa đổi/bổ sung.

### 2.1 Các ràng buộc pháp lý cốt lõi tại Việt Nam
| Nhóm | Nội dung ràng buộc kiến trúc phải hiện thực hoá |
|---|---|
| **Cấm dịch vụ đòi nợ thuê** (Luật Đầu tư 2020) | Không thiết kế luồng "outsource đòi nợ" cho bên thứ ba dạng dịch vụ đòi nợ. Chỉ hợp tác qua các hình thức hợp pháp: uỷ quyền pháp lý, mua bán nợ (VAMC/AMC/DATC), dịch vụ pháp lý – tố tụng. |
| **Bảo vệ dữ liệu cá nhân** (NĐ 13/2023 và Luật BVDLCN 2025 — cần rà lại hiệu lực) | Bắt buộc: cơ sở pháp lý xử lý dữ liệu, hồ sơ đánh giá tác động (DPIA), quyền của chủ thể dữ liệu (truy cập / chỉnh sửa / xoá / rút đồng ý), giới hạn dữ liệu nhạy cảm, kiểm soát chuyển dữ liệu ra ngoài. |
| **Quy tắc nhắc nợ** (tinh thần TT 43/2016 & TT 18/2019 áp cho CTTC — nên tự áp làm chuẩn nội bộ) | Cấm đe doạ, xúc phạm; **không nhắc nợ với người không có nghĩa vụ trả nợ**; giới hạn số lần liên hệ/ngày; khung giờ liên hệ hợp lý (đề xuất 07:00–21:00). |
| **Bảo mật thông tin khách hàng** (Luật Các TCTD, NĐ về bí mật thông tin khách hàng) | Kiểm soát chặt việc lộ thông tin khoản nợ ra ngoài phạm vi bên có nghĩa vụ. |
| **Bộ luật Dân sự / Tố tụng dân sự / Luật Thi hành án** | Chuẩn hoá luồng khởi kiện, thi hành án, xử lý TSBĐ theo đúng trình tự. |

### 2.2 Yêu cầu về "điểm tạo áp lực thu nợ" — làm rõ ngay từ đầu

Yêu cầu nghiệp vụ có nêu việc ghi nhận *"cái gì tạo ra áp lực thu nợ"*. Đây là một trường thông tin **hợp lệ và rất giá trị**, nhưng phải được mô hình hoá đúng, nếu không hệ thống sẽ vô tình trở thành công cụ hợp thức hoá hành vi bị cấm. Kiến trúc quy định trường này là **`negotiation_lever` (đòn bẩy đàm phán hợp pháp)** với danh mục đóng (closed vocabulary), không phải trường text tự do:

**Được phép (đưa vào enum hệ thống):**
- Ảnh hưởng lịch sử tín dụng CIC và khả năng vay vốn tương lai
- Rủi ro mất quyền sử dụng / bị xử lý tài sản bảo đảm theo hợp đồng
- Chi phí lãi phạt tích luỹ theo thời gian (minh hoạ định lượng cho khách hàng)
- Chi phí và thời gian nếu chuyển sang tố tụng
- Ảnh hưởng đến hạn mức/quan hệ tín dụng của **chính pháp nhân đi vay** (KHDN)
- Cơ hội: ưu đãi miễn giảm lãi có thời hạn, phương án cơ cấu, chiết khấu tất toán sớm
- Thời điểm khách hàng có dòng tiền (lương, thu hoạch mùa vụ, quyết toán công nợ, thưởng Tết)

**Bị chặn ở tầng Guardrail (không cho nhập, không cho AI sinh ra, log lại nếu có nỗ lực nhập):**
- Mọi thông tin nhằm gây áp lực qua người thân, đồng nghiệp, đối tác không có nghĩa vụ trả nợ
- Thông tin đời tư nhạy cảm: sức khoẻ, tôn giáo, quan điểm chính trị, đời sống tình cảm, xu hướng tính dục
- Thông tin về con cái, trường học của con, nơi ở của người thân
- Bất kỳ nội dung nào mang tính đe doạ, bôi nhọ, "bêu tên" trên mạng xã hội

**Cơ chế kỹ thuật:** trường `negotiation_lever` là enum + `lever_evidence` (dẫn chứng). Một **PII/Sensitive Content Classifier** chạy trên mọi nội dung nhập tay và mọi nội dung do AI sinh ra; vi phạm → chặn + cảnh báo tới Compliance. Đây là điểm khác biệt lớn nhất giữa B.Collection và các hệ thống collection thông thường.

### 2.3 Cờ khách hàng dễ tổn thương (Vulnerability Flag)
Bắt buộc có. Khi khách hàng thuộc nhóm: đang điều trị bệnh nặng, mất khả năng lao động, thiên tai/dịch bệnh, người cao tuổi neo đơn, đang có tranh chấp pháp lý về khoản vay → hệ thống **tự động hạ cường độ tiếp cận**, chuyển sang luồng hỗ trợ/cơ cấu, và khoá các treatment cứng. Đây vừa là yêu cầu ESG, vừa là lá chắn rủi ro danh tiếng.

---

## 3. Kiến trúc tổng thể (Logical Architecture)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ L8. TRẢI NGHIỆM & KÊNH        Collector Workspace │ Field App │ Portal KH │ Chatbot│
├──────────────────────────────────────────────────────────────────────────────────┤
│ L7. THỰC THI (Execution)      Case Workflow (BPM) │ Dialer/IVR │ SMS/OTT/Email    │
│                               │ Legal & Enforcement │ Bán nợ/AMC │ Field Visit    │
├──────────────────────────────────────────────────────────────────────────────────┤
│ ⛨ L6. COMPLIANCE GUARDRAIL (deterministic, fail-closed, cắt ngang L5↔L7)          │
│    Contact Policy Engine │ Consent & Legal Basis │ Content Filter │ Vulnerability │
│    Rate Limiter │ Do-Not-Contact │ Immutable Audit Log                            │
├──────────────────────────────────────────────────────────────────────────────────┤
│ L5. QUYẾT ĐỊNH (Decisioning)  Segmentation │ Strategy/Rule Engine │ NBA Engine     │
│                               Champion–Challenger │ Case Reference Engine (CBR)   │
├──────────────────────────────────────────────────────────────────────────────────┤
│ L4. TRÍ TUỆ (AI/ML/LLM)       Model Portfolio │ Feature Store │ LLM Gateway        │
│                               Vector Store │ MLOps/Model Risk Mgmt                │
├──────────────────────────────────────────────────────────────────────────────────┤
│ L3. TRI THỨC (Knowledge)      Debtor 360 │ Collection Graph (Neo4j/TigerGraph)     │
│                               Entity Resolution │ Manual Enrichment Store          │
├──────────────────────────────────────────────────────────────────────────────────┤
│ L2. DỮ LIỆU (Lakehouse)       Bronze → Silver → Gold │ Iceberg/Delta │ Spark/Flink │
│                               Data Catalog │ Lineage │ Quality │ Masking          │
├──────────────────────────────────────────────────────────────────────────────────┤
│ L1. THU THẬP (Ingestion)      CDC (Debezium) │ Batch │ Streaming (Kafka) │ API     │
│                               OSINT Collector (có kiểm soát) │ IDP/OCR            │
├──────────────────────────────────────────────────────────────────────────────────┤
│ L0. NGUỒN  Core Banking │ LOS/CLMS │ Thẻ │ CIF │ CIC │ Collateral │ CRM │ Call    │
│            Center │ Kênh số │ Nguồn công khai │ Nhập liệu thủ công                │
└──────────────────────────────────────────────────────────────────────────────────┘
```

**Nguyên tắc tách tầng quan trọng nhất:** L5 (quyết định) **không được** gọi trực tiếp L7 (thực thi). Mọi lệnh hành động đi qua L6. Điều này cho phép: (a) thay đổi chính sách tuân thủ ở một nơi duy nhất, (b) chứng minh với thanh tra rằng không có đường vòng, (c) chạy mô hình AI mạnh dạn hơn vì luôn có phanh cứng phía sau.

---

## 4. Tầng dữ liệu (L1–L2)

### 4.1 Nguồn dữ liệu
**Nội bộ (bắt buộc, ưu tiên P0):**
- Core Banking: dư nợ, lịch trả nợ, ngày quá hạn (DPD), nhóm nợ, lãi/phí, giao dịch tài khoản, số dư CASA, dòng tiền vào/ra
- LOS/CLMS: hồ sơ vay, mục đích vay, thu nhập khai báo, phương án kinh doanh, thẩm định ban đầu
- Hệ thống TSBĐ: loại tài sản, định giá, tình trạng pháp lý, đồng bảo đảm
- CIF/eKYC: định danh, địa chỉ, số điện thoại, người liên quan đã khai
- CRM & Call Center: lịch sử tương tác, ghi âm, ticket, khiếu nại
- Thẻ / kênh số: hành vi giao dịch, tần suất đăng nhập app (tín hiệu "còn hoạt động")
- Lịch sử thu hồi: mọi hành động collection trong quá khứ và kết quả

**Bên ngoài (P1, phải có cơ sở pháp lý rõ ràng cho từng nguồn):**
- CIC: quan hệ tín dụng toàn ngành, tổng dư nợ, nhóm nợ tại TCTD khác
- Cổng thông tin quốc gia về đăng ký doanh nghiệp: cơ cấu sở hữu, người đại diện, thay đổi vốn
- Cổng công bố bản án / Cổng thi hành án dân sự: tranh chấp, án đang thi hành
- Cổng đấu thầu quốc gia: hợp đồng trúng thầu → dòng tiền tương lai của KHDN
- Đăng ký giao dịch bảo đảm: tài sản đã thế chấp ở đâu
- Báo chí chính thống, công bố thông tin của công ty đại chúng (HNX/HOSE)
- Dữ liệu địa lý / vệ tinh (cho nông nghiệp, bất động sản dự án)

### 4.2 Kiến trúc Lakehouse
- **Bronze:** raw, immutable, giữ nguyên format nguồn, có `ingest_ts`, `source_system`, `batch_id`
- **Silver:** chuẩn hoá, entity-resolved, đã áp masking/tokenization, chuẩn hoá số điện thoại/địa chỉ (rất quan trọng cho skip-tracing)
- **Gold:** data mart cho collection: `dm_debtor_360`, `dm_case`, `dm_contact_history`, `dm_treatment_outcome`, `dm_collateral`
- **Định dạng:** Apache Iceberg (ưu tiên, hỗ trợ time travel + schema evolution — cần cho audit) trên HDFS/S3-compatible
- **Xử lý:** Spark (batch, nightly), Flink hoặc Spark Structured Streaming (near-real-time cho tín hiệu: khách hàng vừa có tiền về tài khoản → trigger liên hệ ngay)
- **CDC:** Debezium → Kafka cho các bảng nóng (giao dịch, trạng thái khoản vay)

### 4.3 Điểm cần chú ý về chất lượng dữ liệu
Kinh nghiệm cho thấy **60–70% giá trị ban đầu của một hệ thống collection đến từ việc làm sạch dữ liệu liên hệ**, không phải từ mô hình AI. Bắt buộc có:
- Phone Normalization & Validation Service (chuẩn E.164, phát hiện số rác/số ảo, ping HLR nếu được phép)
- Address Standardization (chuẩn hoá về mã đơn vị hành chính hiện hành — lưu ý biến động địa giới hành chính, cần bảng ánh xạ lịch sử)
- Deduplication & Golden Record cho khách hàng
- **Contactability Score** cho từng số điện thoại/địa chỉ, cập nhật liên tục theo kết quả liên hệ thực tế

---

## 5. Tầng tri thức: Chân dung nợ & Graph (L3)

### 5.1 Mô hình Chân dung nợ (Debtor Persona Model)
Chân dung không phải là "một bản mô tả", mà là một **vector đặc trưng có cấu trúc theo 7 trục**, phục vụ cả con người đọc lẫn máy so khớp:

| Trục | Nội dung | Nguồn chính |
|---|---|---|
| **D1. Khả năng trả (Ability)** | Dòng tiền vào tài khoản 6–12 tháng, thu nhập ước lượng, tổng nghĩa vụ nợ toàn ngành (CIC), DTI thực tế, giá trị TSBĐ ròng | Core, CIC, TSBĐ |
| **D2. Thiện chí trả (Willingness)** | Lịch sử trả nợ, tỷ lệ giữ cam kết PTP, phản ứng khi được liên hệ, có né tránh không, có nợ nơi khác vẫn trả không | Lịch sử collection, CIC |
| **D3. Khả năng tiếp cận (Contactability)** | Số điện thoại còn hoạt động, kênh phản hồi tốt nhất, khung giờ tối ưu, địa chỉ xác thực, có đang ở nước ngoài không | Call center, kênh số |
| **D4. Bối cảnh nguyên nhân (Root cause)** | Mất việc / giảm thu nhập / bệnh tật / thiên tai / kinh doanh khó khăn / tranh chấp / cố tình chây ì / bị lừa đảo | Nhập liệu + NLP từ ghi âm |
| **D5. Mạng lưới (Network)** | Nhóm KHLQ, đồng sở hữu tài sản, bảo lãnh, quan hệ sở hữu doanh nghiệp, nhà cung cấp/khách hàng lớn (KHDN) | **Collection Graph** |
| **D6. Đòn bẩy đàm phán hợp pháp** | `negotiation_lever` enum (Mục 2.2) + thời điểm có dòng tiền | Nhập liệu + phân tích dòng tiền |
| **D7. Rủi ro & nhạy cảm** | Vulnerability flag, rủi ro khiếu nại, rủi ro truyền thông, dấu hiệu gian lận (first-payment default, giả mạo hồ sơ) | Guardrail + mô hình fraud |

**Đầu ra chân dung** gồm 3 lớp:
1. **Persona Card** (cho collector đọc trong 15 giây): 1 màn hình — ai, nợ bao nhiêu, vì sao chưa trả, nên nói gì, gọi lúc nào, tuyệt đối tránh gì.
2. **Persona Vector** (cho máy): embedding ~128–256 chiều để so khớp tương đồng.
3. **Persona Cluster** (cho chiến lược): mã cụm, ví dụ `P-07: Hộ kinh doanh, dòng tiền mùa vụ, thiện chí cao, khả năng thấp`.

### 5.2 Collection Graph — thiết kế đồ thị

> **Tái sử dụng:** kế thừa trực tiếp schema và bộ chấm điểm cạnh từ hệ thống **phát hiện nhóm khách hàng liên quan (KHLQ)** đã có. B.Collection bổ sung thêm các loại node/edge đặc thù thu hồi. Không xây graph mới từ đầu.

**Node types:**
`Person`, `Organization`, `Account`, `Loan`, `Collateral`, `PhoneNumber`, `Address`, `Device`, `BankAccount(ngoại bank)`, `LegalCase`, `CollectionCase`, `Employer`, `Guarantor`

**Edge types (kèm thuộc tính `weight`, `confidence`, `valid_from/to`, `source`):**
| Cạnh | Ý nghĩa với thu hồi nợ |
|---|---|
| `OWNS` / `CONTROLS` | Truy vết tài sản thực có thể xử lý |
| `GUARANTEES` | Bên bảo lãnh — có nghĩa vụ pháp lý, được phép liên hệ |
| `CO_BORROWER` / `CO_OWNS_COLLATERAL` | Đồng nghĩa vụ, đồng sở hữu tài sản |
| `SHARES_PHONE` / `SHARES_ADDRESS` / `SHARES_DEVICE` | **Skip-tracing**: tìm lại khách hàng mất liên lạc |
| `TRANSACTS_WITH` (có trọng số theo giá trị/tần suất) | Dòng tiền thực, phát hiện tài khoản "ẩn" của KHDN |
| `RELATED_PARTY_OF` | Kế thừa từ hệ thống KHLQ |
| `SAME_LEGAL_REP` / `SAME_SHAREHOLDER` | Phát hiện "công ty vỏ", chuyển tài sản |
| `TRANSFERRED_ASSET_TO` | **Cảnh báo tẩu tán tài sản** trước khi xử lý nợ |
| `SIMILAR_PERSONA_TO` | Cạnh suy diễn từ Persona Vector — nền tảng cho Case Reference Engine |

**Các thuật toán graph triển khai:**
- **Connected Components / Louvain** → gom cụm nợ liên đới: một khách hàng vỡ nợ có thể kéo theo cả nhóm. Cho phép **chuyển từ chiến lược đơn khoản sang chiến lược đàm phán cả nhóm** — đây là nơi tạo ra giá trị thu hồi lớn nhất với KHDN.
- **PageRank / Betweenness** → xác định "nút trung tâm" thực sự kiểm soát dòng tiền của nhóm (thường không phải người đứng tên vay).
- **Shortest Path** → tìm đường liên hệ hợp pháp gần nhất (qua bên bảo lãnh, đồng vay — **không qua bên thứ ba không có nghĩa vụ**).
- **Temporal graph analysis** → phát hiện chuỗi chuyển nhượng tài sản bất thường trong 6–12 tháng trước khi quá hạn.
- **Link prediction** → gợi ý số điện thoại/địa chỉ có khả năng đúng cho case mất liên lạc.

**Công nghệ:** Neo4j Enterprise (nếu ưu tiên hệ sinh thái Cypher + GDS trưởng thành) hoặc TigerGraph (nếu quy mô cạnh > 5 tỷ). Xây dựng graph bằng PySpark như cách đã làm ở hệ thống KHLQ, ghi vào graph DB qua bulk loader; giữ **Graph Feature Store** dạng bảng phẳng trong lakehouse để phục vụ ML mà không phải query graph real-time.

### 5.3 Entity Resolution
Đây là "móng nhà". Thiết kế 3 tầng: blocking (theo CCCD/MST/số điện thoại chuẩn hoá) → scoring (fuzzy name Vietnamese-aware, có xử lý dấu, tên đệm, biến thể) → clustering + **human review queue** cho các cặp ở vùng xám (score 0.7–0.9). Mỗi quyết định merge/split đều được lưu vết và có thể rollback.

---

## 6. Tính năng làm giàu thông tin thủ công (Manual Enrichment)

Đây là yêu cầu nghiệp vụ then chốt và cũng là nơi dễ thất bại nhất — kinh nghiệm cho thấy nếu thiết kế như một ô "ghi chú" tự do, sau 1 năm sẽ có 2 triệu dòng text vô giá trị và một rủi ro tuân thủ khổng lồ.

### 6.1 Nguyên tắc thiết kế
1. **Structured-first:** nhập theo schema có kiểm soát, không phải free-text. Free-text chỉ là trường bổ trợ và luôn đi qua Content Filter.
2. **Provenance bắt buộc:** mỗi fact có `source_type` (khách hàng tự khai / cán bộ quan sát / bên bảo lãnh cung cấp / nguồn công khai), `collected_by`, `collected_at`, `legal_basis`, `confidence` (1–5), `expiry_date`.
3. **Bốn mắt cho thông tin nhạy cảm hoặc ảnh hưởng chiến lược:** cán bộ nhập → kiểm soát viên duyệt → mới có hiệu lực vào Persona.
4. **Confidence decay:** thông tin không được xác nhận lại sẽ tự động giảm độ tin cậy theo thời gian và bị loại khỏi Persona sau TTL (đề xuất 12 tháng cho thông tin hành vi, 6 tháng cho thông tin liên hệ).
5. **Không cho phép ghi đè im lặng:** mỗi cập nhật là một bản ghi mới (event sourcing), giữ toàn bộ lịch sử.

### 6.2 Schema các nhóm thông tin làm giàu
| Nhóm | Trường (ví dụ) | Kiểm soát |
|---|---|---|
| **Liên hệ** | Số điện thoại phụ, địa chỉ thực tế đang ở, khung giờ dễ gặp, kênh ưa thích | Tự do nhập, verify tự động |
| **Quan hệ có nghĩa vụ** | Bên bảo lãnh, đồng vay, người đại diện pháp luật, đồng sở hữu TSBĐ | Enum quan hệ, bắt buộc dẫn chứng pháp lý |
| **Quan hệ tham chiếu** | Người khách hàng tự khai làm đầu mối liên hệ (**có sự đồng ý của người đó**) | Bắt buộc cờ `consent_obtained` |
| **Nghề nghiệp & dòng tiền** | Nơi làm việc, chu kỳ lương, mùa vụ kinh doanh, đối tác thanh toán lớn | Enum + ngày |
| **Nguyên nhân chậm trả** | Enum D4 (Mục 5.1) + mô tả ngắn | Enum bắt buộc |
| **Đòn bẩy đàm phán** | `negotiation_lever` enum (Mục 2.2) | **Enum đóng, có Content Filter** |
| **Thói quen / sở thích liên quan trực tiếp đến khả năng liên hệ và trả nợ** | Ví dụ: "chỉ nghe máy sau 18h", "ưu tiên trao đổi qua Zalo", "thường ra khỏi nhà buổi sáng" | Enum + free-text qua filter |
| **Cờ nhạy cảm** | Vulnerability flag, đang tranh chấp, có luật sư đại diện, yêu cầu không liên hệ | Bắt buộc leo thang lên Compliance |

> **Ranh giới về "sở thích, thói quen":** hệ thống chỉ ghi nhận các đặc điểm **có liên quan trực tiếp tới việc liên hệ và khả năng trả nợ**. Các thông tin đời tư không phục vụ mục đích này (sức khoẻ chi tiết, tôn giáo, quan hệ tình cảm, con cái) bị chặn ở tầng nhập liệu — vừa để tuân thủ pháp luật về dữ liệu cá nhân, vừa để bảo vệ chính cán bộ ngân hàng khỏi rủi ro cá nhân.

### 6.3 Cơ chế khuyến khích chất lượng nhập liệu
- **Enrichment Contribution Score** cho từng cán bộ: đo bằng *thông tin bạn nhập có dẫn tới kết quả thu hồi không*, không đo bằng số dòng nhập.
- Hiển thị ngay trên Persona Card: "Thông tin do anh/chị X bổ sung 3 tháng trước đã giúp thu hồi thành công 2 case tương tự."
- Gamification nhẹ + đưa vào KPI mềm của cán bộ thu hồi.

---

## 7. Thu thập thông tin từ nguồn mở (OSINT) — có kiểm soát

Đây là hạng mục **rủi ro cao nhất** trong toàn bộ đề xuất. Khuyến nghị của tôi: **triển khai ở Giai đoạn 2, sau khi có DPIA và ý kiến pháp chế bằng văn bản**, và giới hạn phạm vi rõ ràng.

### 7.1 Phân tầng nguồn theo mức độ rủi ro
| Tầng | Nguồn | Trạng thái |
|---|---|---|
| **Xanh** — tự động hoá được | Cổng ĐKKD quốc gia, cổng đấu thầu, công bố thông tin HOSE/HNX, cổng bản án, đăng ký giao dịch bảo đảm, báo chí chính thống | Cho phép crawl/API, tôn trọng robots.txt & ToS |
| **Vàng** — bán tự động, có người duyệt | Website doanh nghiệp, sàn TMĐT (với hộ kinh doanh), thông tin công khai về hoạt động kinh doanh | Thu thập → hàng đợi thẩm định → cán bộ xác nhận mới vào Persona |
| **Đỏ** — chỉ thủ công, có phê duyệt cấp cao, ghi log | Mạng xã hội cá nhân | Xem Mục 7.2 |
| **Cấm tuyệt đối** | Mua dữ liệu từ nguồn không rõ nguồn gốc; dùng tài khoản giả để kết bạn/thâm nhập; lấy dữ liệu sau tường đăng nhập; thu thập dữ liệu về người thân không có nghĩa vụ | Chặn ở kiến trúc, không có API để làm |

### 7.2 Về mạng xã hội — khuyến nghị thẳng thắn
Việc tự động quét mạng xã hội cá nhân để phục vụ thu hồi nợ có 4 vấn đề mà tôi khuyến nghị BIDV không đánh đổi:
1. **Pháp lý:** dữ liệu cá nhân trên mạng xã hội, dù công khai, vẫn là dữ liệu cá nhân theo pháp luật hiện hành; xử lý cần cơ sở pháp lý, mà "công khai" không đương nhiên là cơ sở đó.
2. **Danh tiếng:** một bài đăng "BIDV theo dõi Facebook con nợ" đủ tạo khủng hoảng truyền thông vượt xa giá trị thu hồi.
3. **Chất lượng:** tỷ lệ khớp sai định danh trên mạng xã hội Việt Nam rất cao (trùng tên phổ biến) → dẫn tới liên hệ nhầm người, là rủi ro nghiêm trọng nhất trong collection.
4. **ROI:** giá trị gia tăng thực tế thấp hơn nhiều so với việc làm sạch dữ liệu liên hệ nội bộ (Mục 4.3).

**Thiết kế đề xuất nếu vẫn triển khai:** chỉ dùng để **xác minh thông tin đã có** (ví dụ xác nhận doanh nghiệp còn hoạt động, xác nhận địa điểm kinh doanh), thao tác thủ công bởi bộ phận chuyên trách, mỗi lượt tra cứu phải có `case_id` + lý do + phê duyệt, ghi log bất biến, và **cấm tuyệt đối lưu ảnh/nội dung cá nhân vào hệ thống**. Chỉ lưu kết luận đã chuẩn hoá (ví dụ: `business_status = active`, `confidence = 3`, `verified_by = X`).

### 7.3 Kiến trúc kỹ thuật OSINT Collector
```
Scheduler → Source Adapter (per-source, rate-limited, ToS-aware)
         → Raw Store (WORM, TTL ngắn)
         → Entity Matcher (khớp với CIF, ngưỡng cao, từ chối nếu mơ hồ)
         → PII Minimizer (chỉ trích xuất trường đã khai báo trong DPIA)
         → Human Verification Queue (tầng Vàng/Đỏ)
         → Enrichment Store (có provenance đầy đủ)
```
Toàn bộ pipeline chạy trong network zone riêng, không có đường ghi trực tiếp vào Persona.

---

## 8. Tầng AI/ML (L4)

### 8.1 Danh mục mô hình
| # | Mô hình | Đầu ra | Dùng ở đâu | Loại |
|---|---|---|---|---|
| ML1 | **Self-cure propensity** | P(tự trả trong 7 ngày không cần can thiệp) | Bỏ qua nhóm sớm → tiết kiệm chi phí lớn | GBM |
| ML2 | **Roll-rate / PD ngắn hạn** | P(chuyển nhóm nợ xấu hơn trong 30 ngày) | Ưu tiên hoá hàng đợi | GBM/Survival |
| ML3 | **Recovery amount forecast** | Số tiền kỳ vọng thu được (EAD × LGD động) | Xếp hạng giá trị kinh tế của case | Regression |
| ML4 | **Contactability & Best-Time-to-Call** | Kênh + khung giờ tối ưu cho từng số | Dialer, chiến dịch | Multiclass |
| ML5 | **PTP keeping propensity** | P(giữ đúng cam kết trả) | Quyết định có tin cam kết hay leo thang | GBM |
| ML6 | **Settlement / haircut optimization** | Mức miễn giảm tối thiểu để đạt thoả thuận | Đàm phán cơ cấu | Uplift/Optimization |
| ML7 | **Litigation worthiness** | NPV(khởi kiện) so với NPV(thương lượng) / NPV(bán nợ) | Quyết định chuyển pháp lý | Decision model |
| ML8 | **Asset dissipation alert** | Cảnh báo tẩu tán tài sản | Ưu tiên biện pháp bảo đảm khẩn | Graph + rules |
| ML9 | **Uplift model cho treatment** | Δ hiệu quả của mỗi treatment trên từng khách | Trái tim của NBA Engine | Causal/Uplift |
| ML10 | **Persona clustering & embedding** | Persona Vector + Cluster ID | Case Reference Engine | Autoencoder/UMAP+HDBSCAN |
| ML11 | **Fraud / first-payment-default** | Cờ nghi ngờ gian lận ngay từ đầu | Tách luồng xử lý riêng | Graph + GBM |

**Điểm kiến trúc quan trọng — ML9 (Uplift):** hầu hết hệ thống collection thất bại vì dùng mô hình *dự báo* (ai sẽ trả) thay vì mô hình *nhân quả* (hành động nào làm tăng khả năng trả). Kết quả là ngân hàng dồn nguồn lực vào nhóm dù sao cũng tự trả. Bắt buộc phải có **holdout group (control) 5–10%** không can thiệp hoặc can thiệp tối thiểu, duy trì liên tục, để đo uplift thực. Đây là điều kiện tiên quyết để chứng minh ROI của cả hệ thống.

### 8.2 LLM & GenAI — dùng đúng chỗ
| Use case | Giá trị | Rủi ro & kiểm soát |
|---|---|---|
| **Tóm tắt & trích xuất từ ghi âm cuộc gọi** (ASR tiếng Việt + LLM) | Tự động trích: cam kết trả, số tiền, ngày, nguyên nhân, cảm xúc → giảm 80% thời gian ghi chép | Không dùng làm bằng chứng pháp lý; luôn có bản gốc |
| **Persona Narrative Generator** | Sinh mô tả chân dung dạng văn xuôi từ dữ liệu có cấu trúc | **Chỉ được dùng dữ liệu có trong Persona**, chống bịa; bắt buộc dẫn nguồn từng câu |
| **Collector Copilot** | Gợi ý kịch bản đàm phán, trả lời phản đối, tính toán phương án cơ cấu tại chỗ | Toàn bộ output qua Content Filter; kịch bản lấy từ thư viện đã duyệt, LLM chỉ cá nhân hoá |
| **Quality Assurance tự động** | Rà 100% cuộc gọi tìm vi phạm quy tắc ứng xử (thay vì mẫu 2%) | Giá trị tuân thủ cực lớn — nên làm sớm |
| **Complaint & risk early warning** | Phát hiện khách hàng có nguy cơ khiếu nại/lên báo | Leo thang tự động |
| **Trợ lý truy vấn dữ liệu (NL→SQL/Cypher)** | Cán bộ hỏi bằng tiếng Việt về danh mục nợ | Read-only, giới hạn theo RBAC |

**LLM Gateway bắt buộc** (kế thừa mô hình đã thiết kế trong dự án CreditAgent): PII redaction trước khi gửi prompt, schema validation đầu ra (Pydantic), semantic cache, model tiering, log toàn bộ prompt/response, kill-switch.

### 8.3 Model Risk Management
Đây là ngân hàng — mọi mô hình ảnh hưởng tới khách hàng phải nằm trong khung MRM: model inventory, validation độc lập, backtesting định kỳ, giám sát drift (PSI/CSI), **fairness testing** (kiểm tra mô hình không tạo phân biệt đối xử theo vùng miền, giới tính, độ tuổi), tài liệu hoá, và quy trình phê duyệt trước khi lên production.

---

## 9. Tầng quyết định & chiến lược (L5)

### 9.1 Ma trận phân khúc gốc: Khả năng × Thiện chí
| | **Thiện chí CAO** | **Thiện chí THẤP** |
|---|---|---|
| **Khả năng CAO** | **S1 – Quên/Vướng thủ tục**<br>→ Nhắc nhẹ đa kênh, tự phục vụ, không tốn nguồn lực người. Chi phí thấp nhất, cure cao nhất. | **S2 – Chây ì có chủ đích**<br>→ Leo thang nhanh, biện pháp pháp lý, xử lý TSBĐ, cảnh báo tẩu tán tài sản (ML8). Đây là nhóm cần graph nhiều nhất. |
| **Khả năng THẤP** | **S3 – Khó khăn thực sự**<br>→ Cơ cấu nợ, giãn kỳ hạn, miễn giảm lãi, gói phục hồi. Đây là nhóm tạo giá trị dài hạn và bảo vệ danh tiếng. | **S4 – Mất khả năng / mất liên lạc**<br>→ Skip-tracing (graph), đánh giá NPV: bán nợ / khởi kiện / xoá sổ theo dõi ngoại bảng. |

Ma trận này là *khung tư duy*; phân khúc vận hành thực tế do ML10 (clustering) sinh ra, thường 15–30 cụm, được ánh xạ về 4 ô này để lãnh đạo dễ theo dõi.

### 9.2 Treatment Ladder theo DPD bucket
```
DPD 1-15  (B1a) → Digital-first: SMS/Zalo/app notification, IVR nhắc nhở
                  Lọc bằng ML1: ai self-cure cao → KHÔNG can thiệp (tiết kiệm & giữ trải nghiệm)
DPD 16-30 (B1b) → Outbound call ưu tiên theo ML3×ML9, chào phương án tự phục vụ
DPD 31-60 (B2)  → Chuyên viên phụ trách, đàm phán cơ cấu, PTP có theo dõi (ML5)
DPD 61-90 (B2b) → Field visit có chọn lọc (chi phí cao — chỉ khi ML3 đủ lớn), làm việc với bên bảo lãnh
DPD 91-180(B3-4)→ Thu giữ/xử lý TSBĐ, khởi kiện (ML7 quyết định), đàm phán tất toán có chiết khấu
DPD >180  (B5)  → Bán nợ (VAMC/AMC/DATC), thi hành án, theo dõi ngoại bảng
```
Mỗi ô trong ladder là một **strategy cell** có thể cấu hình bằng UI (business user tự sửa được, không cần dev) — đây là yêu cầu phi chức năng quan trọng vì chiến lược thu hồi thay đổi theo chu kỳ kinh tế.

### 9.3 Next Best Action Engine
```
Input:  Persona Vector + Case State + Ràng buộc nguồn lực + Kết quả ML1..ML11
        + Reference Cases tương đồng (Mục 10)
Logic:  Với mỗi action khả dĩ a ∈ A:
            Score(a) = Uplift(a|persona) × ExpectedRecovery − Cost(a) − RiskPenalty(a)
        Loại bỏ các action bị Guardrail chặn
        Áp ràng buộc tối ưu toàn cục (số collector, số line dialer, ngân sách field visit)
        → Bài toán assignment: tối đa hoá tổng thu hồi kỳ vọng
Output: Hành động + kênh + thời điểm + kịch bản + người thực hiện + lý do (explanation)
```
Giải bằng **constrained optimization** (không phải chỉ ranking) — vì nguồn lực thu hồi là hữu hạn và đây chính là chỗ tạo ra 20–25% cải thiện CTC.

### 9.4 Champion–Challenger
Bắt buộc có framework thử nghiệm: mọi chiến lược mới chạy trên 10–15% danh mục, so với champion, đo bằng chỉ số kinh tế (thu hồi ròng sau chi phí), tự động promote/rollback. Không có cơ chế này, sau 2 năm không ai biết hệ thống có thực sự hiệu quả hay không.

---

## 10. Case Reference Engine — học từ case thành công

Đây là yêu cầu đặc trưng của B.Collection và cũng là phần tạo khác biệt lớn nhất.

### 10.1 Kiến trúc CBR (Case-Based Reasoning) 4 bước
```
RETRIEVE → REUSE → REVISE → RETAIN
```

**1. RETAIN — Xây kho case:** mỗi CollectionCase khi đóng đều sinh một bản ghi chuẩn hoá:
```json
{
  "case_id": "...",
  "persona_vector": [ ... 256 dims ... ],
  "persona_cluster": "P-07",
  "context": { "dpd_at_start": 47, "outstanding": ..., "segment": "SME", "root_cause": "cash_flow_gap" },
  "action_sequence": [
    {"step":1,"action":"call","channel":"phone","time":"18:30","outcome":"RPC","note_embedding":[...]},
    {"step":2,"action":"offer_restructure","terms":{"tenor_ext":6,"interest_waiver_pct":30}},
    {"step":3,"action":"ptp","amount":...,"kept":true}
  ],
  "levers_used": ["cic_impact","early_settlement_discount"],
  "outcome": {"status":"recovered","recovery_pct":0.92,"days_to_resolve":38,"cost_to_collect":...},
  "counterfactual_flag": "treated | control",
  "compliance_review": "passed"
}
```

**2. RETRIEVE — Tìm case tương đồng:** vector search (HNSW trên Milvus/Qdrant/pgvector) trên `persona_vector`, kết hợp lọc cứng theo phân khúc + sản phẩm + bucket, và **kết hợp graph similarity** (`SIMILAR_PERSONA_TO`). Trả về top-K case (K=5–10) kèm độ tương đồng.

**3. REUSE — Chuyển thành khuyến nghị:** tổng hợp các chuỗi hành động của case thành công tương đồng → sinh **Recommended Playbook**. Hiển thị cho collector dạng:
> *"5 khách hàng có chân dung tương đồng (độ khớp 0.87–0.93). 4/5 thu hồi thành công. Mẫu hành động hiệu quả: gọi khung 18–20h → chào phương án giãn kỳ hạn 6 tháng + miễn 30% lãi phạt → chốt PTP theo kỳ lương ngày 10 hàng tháng. Thời gian xử lý trung bình 41 ngày. Đòn bẩy hiệu quả nhất: chiết khấu tất toán sớm."*

**4. REVISE — Cán bộ điều chỉnh & phản hồi:** cán bộ có thể chấp nhận/sửa/từ chối playbook, **bắt buộc ghi lý do khi từ chối**. Dữ liệu này quay lại huấn luyện mô hình (đây chính là cơ chế Approver Quality tương tự đã thiết kế trong CreditAgent).

### 10.2 Ba cạm bẫy phải xử lý ngay từ thiết kế
| Cạm bẫy | Hậu quả | Giải pháp kiến trúc |
|---|---|---|
| **Survivorship bias** | Chỉ học từ case thành công → tưởng playbook hiệu quả trong khi thực ra khách hàng đó dù sao cũng trả | Lưu **cả case thất bại**; luôn tính uplift với nhóm control; hiển thị cả "playbook này đã thất bại N lần" |
| **Feedback loop tự khẳng định** | Hệ thống chỉ gợi ý những gì nó từng gợi ý → không bao giờ khám phá chiến lược tốt hơn | Dành **5–10% ngân sách cho exploration** (multi-armed bandit / epsilon-greedy) |
| **Kế thừa hành vi sai** | Một case thành công nhờ cách làm không đúng chuẩn mực → được nhân bản ra toàn hệ thống | **Compliance review là điều kiện để một case được RETAIN.** Case có khiếu nại hoặc vi phạm QA tự động → loại khỏi kho reference vĩnh viễn |

Cạm bẫy thứ ba là nghiêm trọng nhất: một hệ thống học máy sẽ khuếch đại hành vi sai nhanh hơn con người rất nhiều. Cổng `compliance_review = passed` là bắt buộc, không phải tuỳ chọn.

---

## 11. Tầng Guardrail & Thực thi (L6–L7)

### 11.1 Compliance Guardrail Service (chạy trước MỌI hành động)
| Kiểm tra | Nội dung |
|---|---|
| **Legal basis check** | Khoản nợ có hợp đồng hợp lệ, đúng chủ thể, chưa hết thời hiệu |
| **Party eligibility** | Đối tượng liên hệ có nghĩa vụ pháp lý không? (bên vay / đồng vay / bảo lãnh / người đại diện). **Không có nghĩa vụ → chặn** |
| **Consent & DNC** | Kiểm tra danh sách không liên hệ, yêu cầu rút đồng ý, khách hàng có luật sư đại diện |
| **Frequency cap** | Số lần liên hệ/ngày, /tuần theo kênh (đề xuất ≤ 3–5 lần/ngày tổng các kênh) |
| **Time window** | 07:00–21:00 giờ địa phương; loại trừ ngày lễ, Tết |
| **Content filter** | Nội dung SMS/kịch bản/tin nhắn AI sinh ra: chặn từ ngữ đe doạ, xúc phạm, tiết lộ khoản nợ cho bên thứ ba |
| **Vulnerability gate** | Cờ dễ tổn thương → chuyển luồng hỗ trợ, khoá treatment cứng |
| **Dispute hold** | Khoản nợ đang tranh chấp/khiếu nại → tạm dừng thu hồi |
| **Audit** | Ghi log bất biến (hash-chain / WORM) mọi quyết định cho phép và mọi lần chặn |

**Fail-closed:** Guardrail timeout hoặc lỗi → hành động bị chặn, không "cho qua". Đây là khác biệt căn bản so với thiết kế thông thường.

### 11.2 Case Workflow (BPM)
- Vòng đời case: `Created → Assigned → In-Treatment → PTP → Kept/Broken → Escalated → Legal → Settled/Written-off → Closed`
- Engine: Camunda 8 hoặc Temporal (nếu muốn thống nhất với nền tảng đã dùng ở CreditAgent — khuyến nghị **Temporal** để tận dụng năng lực đội ngũ và durable execution đã có kinh nghiệm)
- SLA tracking, tự động leo thang, phân công theo kỹ năng (skill-based routing: collector mạnh đàm phán KHDN vs collector bán lẻ khối lượng lớn)

### 11.3 Kênh thực thi
- **Digital:** SMS, Zalo ZNS, email, in-app notification, IVR — chi phí thấp nhất, phải là lớp đầu tiên
- **Voice:** tích hợp Predictive/Progressive Dialer + CTI, screen-pop Persona Card, ghi âm → ASR
- **Self-service portal:** khách hàng tự xem dư nợ, tự chọn phương án cơ cấu trong khung đã duyệt, tự trả online. **Đây là kênh có ROI cao nhất mà nhiều ngân hàng bỏ quên** — nhiều khách hàng ngại nói chuyện với collector nhưng sẵn sàng trả nếu có kênh tự phục vụ.
- **Field:** app di động cho cán bộ đi hiện trường (định vị, chụp ảnh biên bản, ký số, offline-first)
- **Legal:** tích hợp quản lý hồ sơ tố tụng, theo dõi thi hành án
- **Bán nợ:** đóng gói danh mục, định giá dựa trên ML3, hồ sơ chuyển giao

---

## 12. Kiến trúc kỹ thuật & Tích hợp

### 12.1 Stack đề xuất (phương án on-premise, phù hợp ràng buộc dữ liệu ngân hàng VN)
| Tầng | Công nghệ |
|---|---|
| Ingestion | Debezium, Kafka, NiFi, Spark |
| Lakehouse | Apache Iceberg + MinIO/HDFS, Spark 3.5, Trino (ad-hoc query) |
| Graph | Neo4j Enterprise + GDS (xây bằng PySpark, bulk load) |
| Feature Store | Feast (offline: Iceberg, online: Redis) |
| Vector Store | Milvus hoặc pgvector (nếu quy mô < 50 triệu vector) |
| ML | Python, XGBoost/LightGBM, PyTorch, MLflow, Kubeflow/Airflow |
| LLM | LLM Gateway nội bộ + mô hình on-prem (tiếng Việt) cho dữ liệu nhạy cảm; API bên ngoài chỉ cho tác vụ không chứa PII |
| Rule/Decision | Drools hoặc engine tự xây; UI cấu hình cho business |
| Workflow | Temporal (khuyến nghị) hoặc Camunda 8 |
| Backend | Java Spring Boot / Python FastAPI, gRPC nội bộ, REST ra ngoài |
| Frontend | React + design system nội bộ BIDV |
| Hạ tầng | Kubernetes multi-AZ, service mesh, KMS/HSM |
| Observability | OpenTelemetry, Prometheus, Grafana, ELK |

### 12.2 Tích hợp hệ thống hiện hữu
| Hệ thống | Chiều | Cơ chế |
|---|---|---|
| Core Banking | Đọc | CDC + batch EOD |
| LOS/CLMS | Đọc/Ghi | API — cập nhật kết quả cơ cấu |
| Hệ thống TSBĐ | Đọc/Ghi | API |
| CIC | Đọc | Batch định kỳ theo hợp đồng |
| **Hệ thống KHLQ (đã có)** | Đọc | **Chia sẻ graph & entity resolution — không xây lại** |
| **CreditAgent (đang POC)** | Hai chiều | Chia sẻ LLM Gateway, Tool Gateway, khung audit hash-chain, kinh nghiệm Temporal |
| CRM / Call Center | Hai chiều | CTI, API |
| Kế toán / GL | Ghi | Hạch toán thu hồi, miễn giảm |
| Hệ thống báo cáo NHNN | Đọc | Phân loại nợ, trích lập DPRR |

### 12.3 Yêu cầu phi chức năng
| Nhóm | Yêu cầu |
|---|---|
| Hiệu năng | Persona Card load < 2s; NBA scoring cho toàn danh mục < 4h/đêm; API decisioning real-time < 300ms p95 |
| Quy mô | Thiết kế cho 3–5 triệu case active, 50–100 triệu node graph, 500 triệu–2 tỷ cạnh |
| Bảo mật | Mã hoá at-rest & in-transit, tokenization PII, RBAC + ABAC (cán bộ chỉ thấy case được phân công), data masking theo vai trò |
| Kiểm toán | Log bất biến, truy vết đầy đủ "ai xem dữ liệu gì, khi nào, vì sao" |
| Sẵn sàng | RTO ≤ 4h, RPO ≤ 15 phút, DR site |
| Lưu trữ | TTL theo loại dữ liệu; tự động xoá/ẩn danh khi hết mục đích |

---

## 13. Lộ trình triển khai

### Giai đoạn 1 — Nền móng & Quick win (Tháng 1–6)
- Data foundation: ingest nội bộ, lakehouse, **làm sạch dữ liệu liên hệ** (ưu tiên số 1)
- Debtor 360 cơ bản + Persona Card v1
- Case Workflow + Collector Workspace
- **Compliance Guardrail v1** (bắt buộc có trước khi ra kênh)
- 3 mô hình đầu: ML1 (self-cure), ML2 (roll rate), ML4 (best time to call)
- Digital-first cho bucket B1
- Manual Enrichment module (structured schema)
- **Thiết lập holdout group ngay từ ngày đầu**
- *Kỳ vọng: giảm 15–20% chi phí liên hệ ở bucket sớm, tăng RPC*

### Giai đoạn 2 — Trí tuệ & Graph (Tháng 7–14)
- Collection Graph trên nền KHLQ, skip-tracing, cảnh báo tẩu tán tài sản
- ML3, ML5, ML6, ML9 (uplift), ML10 (persona clustering)
- NBA Engine + Strategy Configuration UI
- **Case Reference Engine v1** (vector search + playbook)
- LLM: ASR + tóm tắt cuộc gọi, QA tự động 100%
- OSINT tầng Xanh (nguồn công khai chính thống), sau DPIA
- Self-service portal
- *Kỳ vọng: +10% recovery rate, −20% CTC*

### Giai đoạn 3 — Tối ưu & Mở rộng (Tháng 15–24)
- Constrained optimization toàn danh mục
- ML7 (litigation worthiness), ML8, ML11
- Collector Copilot, Champion–Challenger tự động hoá
- Tích hợp bán nợ, thi hành án
- Mở rộng KHDN lớn, nợ nhóm liên đới
- *Kỳ vọng: hệ thống tự học, đo được ROI bằng uplift thực*

---

## 14. Mô hình vận hành & Tổ chức

| Vai trò | Trách nhiệm |
|---|---|
| **Product Owner B.Collection** | Khối Xử lý nợ — sở hữu KPI kinh doanh |
| **Data Owner** | Từng domain dữ liệu có chủ sở hữu định danh |
| **DPO / Compliance Officer** | Phê duyệt DPIA, sở hữu Guardrail policy, review case vào kho reference |
| **Model Risk Committee** | Validate mô hình độc lập, phê duyệt lên production |
| **Collection Strategy Team** | Cấu hình strategy cell, chạy champion–challenger — **đây là vai trò mới cần thành lập** |
| **Data/ML Engineering** | Nền tảng, pipeline, MLOps |
| **QA & Ethics Review** | Rà soát chất lượng tương tác, xử lý cảnh báo từ QA tự động |

Khuyến nghị: thành lập **Collection Analytics CoE** ~12–18 người, đặt trong Khối Xử lý nợ nhưng báo cáo song song về Khối Dữ liệu.

---

## 15. Rủi ro chính & Biện pháp

| # | Rủi ro | Mức | Biện pháp |
|---|---|---|---|
| R1 | Vi phạm pháp luật về dữ liệu cá nhân, đặc biệt từ OSINT/social | **Cao** | DPIA trước, Guardrail fail-closed, hoãn OSINT sang GĐ2, cấm crawl mạng xã hội tự động |
| R2 | Khủng hoảng truyền thông từ hành vi thu hồi | **Cao** | QA tự động 100% cuộc gọi, vulnerability flag, đào tạo, kịch bản duyệt trước |
| R3 | Chất lượng dữ liệu liên hệ kém → mô hình vô dụng | Cao | Đầu tư GĐ1 vào data cleansing; đo Contactability Score làm KPI riêng |
| R4 | Không chứng minh được ROI | Cao | Holdout group từ ngày đầu, đo bằng uplift chứ không phải recovery tuyệt đối |
| R5 | AI khuếch đại hành vi sai qua Case Reference | Trung bình–Cao | `compliance_review = passed` là điều kiện RETAIN; exploration budget |
| R6 | Liên hệ nhầm người (nhất là từ social/graph) | Cao | Ngưỡng entity matching cao, human verification, quy trình xử lý sự cố |
| R7 | Cán bộ không dùng hệ thống (adoption) | Trung bình | UX 15 giây, Copilot thực sự hữu ích, gắn KPI, giải thích được khuyến nghị |
| R8 | Graph phình to, hiệu năng kém | Trung bình | Pre-compute graph features, tách batch/serving, phân vùng theo phân khúc |
| R9 | Phụ thuộc vendor | Trung bình | Chuẩn mở (Iceberg, Kafka, OpenTelemetry), tránh khoá cứng |

---

## 16. Khuyến nghị của EA — 6 điều nếu chỉ được chọn 6

1. **Làm sạch dữ liệu liên hệ trước khi làm AI.** Đây là nơi tạo ra giá trị nhanh nhất và rẻ nhất; bỏ qua bước này thì mọi mô hình phía sau đều vô nghĩa.
2. **Guardrail là tầng kiến trúc, không phải chính sách.** Nếu không đưa vào code với cơ chế fail-closed, nó sẽ không được tuân thủ khi có áp lực chỉ tiêu.
3. **Thiết lập holdout group ngay từ ngày đầu.** Không có nó, sau 2 năm sẽ không ai chứng minh được hệ thống mang lại giá trị gì.
4. **Ưu tiên self-service portal ngang với dialer.** Kênh rẻ nhất, ít rủi ro nhất, thường bị đánh giá thấp nhất.
5. **Tái sử dụng graph KHLQ và nền tảng CreditAgent** thay vì xây mới — tiết kiệm 6–9 tháng và giữ nhất quán về entity resolution trên toàn ngân hàng.
6. **Với mạng xã hội: nói không với tự động hoá.** Giá trị gia tăng thấp, rủi ro pháp lý và danh tiếng cao. Nếu cần, chỉ dùng thủ công để *xác minh* thông tin đã có, có phê duyệt và log đầy đủ.

---

## 17. Việc cần làm tiếp theo

| # | Hạng mục | Chủ trì | Thời gian |
|---|---|---|---|
| 1 | Workshop chốt phạm vi GĐ1 + đo baseline KPI hiện tại | PO + EA | 2 tuần |
| 2 | **Xin ý kiến pháp chế bằng văn bản** về phạm vi thu thập dữ liệu & DPIA | Pháp chế + DPO | 4–6 tuần |
| 3 | Đánh giá hiện trạng dữ liệu (data profiling) — đặc biệt dữ liệu liên hệ | Data team | 3 tuần |
| 4 | Thiết kế chi tiết schema Collection Graph (mở rộng từ schema KHLQ) | SA + Data Architect | 4 tuần |
| 5 | Thiết kế chi tiết Persona Model + Manual Enrichment schema | BA + SA | 4 tuần |
| 6 | PoC Case Reference Engine trên dữ liệu lịch sử 2 năm | ML team | 6 tuần |
| 7 | Lựa chọn công nghệ graph & vector store (PoC so sánh) | EA | 4 tuần |
| 8 | Đề xuất mô hình tổ chức Collection Analytics CoE | HR + Khối XLN | 4 tuần |

---

*Tài liệu này là bản đề xuất kiến trúc ở mức khái niệm/logic, phục vụ thảo luận và phê duyệt định hướng. Các nội dung pháp lý mang tính định hướng kiến trúc và cần được Khối Pháp chế & Tuân thủ xác nhận trước khi thiết kế chi tiết.*
