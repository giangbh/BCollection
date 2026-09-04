# ADR-001 — TẬN DỤNG CDP HAY XÂY PERSONA LAYER RIÊNG CHO B.COLLECTION
**Trạng thái:** Đề xuất | **Ngày:** 01/09/2026 | **Người đề xuất:** EA
**Liên quan:** Persona Model v0.2 · Guardrail Service v1.0 · Kiến trúc tích hợp v0.1

---

## 1. Bối cảnh

Ngân hàng đã có Customer Data Platform (CDP) đang vận hành. Câu hỏi: B.Collection nên dùng CDP làm nền tảng chân dung khách hàng nợ, hay xây persona layer riêng?

Đây không phải câu hỏi nhị phân. CDP là tập hợp của 6 năng lực riêng biệt, và câu trả lời **khác nhau cho từng năng lực**. Trả lời theo kiểu "dùng hết" hoặc "xây mới hết" đều dẫn tới kết cục xấu: dùng hết thì phá vỡ mô hình tuân thủ; xây mới hết thì tạo ra hệ thống định danh thứ hai trong ngân hàng — rủi ro nghiêm trọng hơn nhiều.

---

## 2. Quyết định

**Mô hình lai: CDP là nguồn thượng nguồn và là thẩm quyền định danh; B.Collection sở hữu tầng persona chuyên biệt cho thu hồi nợ.**

Phân rã theo từng năng lực:

| # | Năng lực CDP | Quyết định | Lý do ngắn |
|---|---|---|---|
| 1 | **Entity Resolution / Golden Record** | ✅ **Dùng, không xây lại** | Hai hệ thống định danh = hai câu trả lời về "ai là ai" = rủi ro liên hệ nhầm người |
| 2 | **Dữ liệu liên hệ** (SĐT, địa chỉ, kênh) | ⚠️ **Dùng làm nguồn, không làm thẩm quyền** | Xem Mục 4.1 — bẫy lớn nhất |
| 3 | **Sự kiện hành vi số** (đăng nhập app, mở email) | ✅ **Dùng** | Rẻ, sạch, không nhạy cảm |
| 4 | **Phân khúc / Audience** | ❌ **Không dùng** | Ontology marketing sai bản chất với thu hồi |
| 5 | **Lưu trữ profile** làm nơi chứa Persona | ❌ **Không dùng** | CDP lưu trạng thái hiện tại; Persona cần snapshot theo thời điểm + provenance từng fact |
| 6 | **Activation / Campaign orchestration** | ❌ **Cấm dùng cho thu hồi** | Xem Mục 4.2 — đây là điểm không thương lượng |

---

## 3. Kiến trúc kết quả

```
┌──────────────────────────────────────────────────────────────┐
│  CDP  (thẩm quyền định danh + hồ sơ khách hàng toàn hàng)     │
│  · Golden Record ID  · Contact points  · Digital events      │
│  · Marketing segments  · Consent (marketing)                 │
└────────────┬─────────────────────────────────────────────────┘
             │  IF-CDP-01: đồng bộ CÓ CHỌN LỌC (allowlist trường)
             │  IF-CDP-02: golden_customer_id (bắt buộc, một chiều)
             ▼
┌──────────────────────────────────────────────────────────────┐
│  B.COLLECTION — Collection Persona Layer                     │
│  · Kế thừa golden_customer_id, KHÔNG tự làm ER               │
│  · Bổ sung 7 trục D1–D7 (ability, willingness matrix, ...)   │
│  · Provenance từng fact + TTL + confidence decay             │
│  · Snapshot theo thời điểm quyết định (giữ 5 năm)            │
│  · party_obligation + contact_eligible  ← KHÔNG từ CDP       │
└────────────┬─────────────────────────────────────────────────┘
             │  Mọi hành động ra kênh
             ▼
┌──────────────────────────────────────────────────────────────┐
│  GUARDRAIL SERVICE  →  Channel Adapters                      │
└──────────────────────────────────────────────────────────────┘

        ✗ KHÔNG có đường: CDP Activation ──► Channel
          (với mục đích thu hồi nợ)
```

---

## 4. Lý do chi tiết cho ba quyết định quan trọng

### 4.1 Vì sao dữ liệu liên hệ từ CDP là "nguồn" chứ không phải "thẩm quyền"

Ba khác biệt căn bản mà nếu bỏ qua sẽ gây sự cố:

**(a) Khả năng tiếp cận marketing ≠ khả năng tiếp cận thu hồi.** CDP đánh giá một số điện thoại là "tốt" khi khách hàng mở tin nhắn khuyến mại. B.Collection cần `contactability_score` dựa trên **RPC thực tế** — có gặp đúng người và nói được chuyện về khoản nợ hay không. Hai chỉ số này tương quan yếu. Người mở tin khuyến mại đều đặn vẫn có thể không bao giờ nghe máy khi thấy số của bộ phận thu hồi.

**(b) Đồng ý marketing ≠ cơ sở pháp lý liên hệ thu hồi.** Đây là điểm quan trọng nhất. Theo Luật BVDLCN 91/2025 và NĐ 356/2025, dữ liệu thu thập cho mục đích marketing với sự đồng ý cho mục đích marketing **không tự động dùng được cho mục đích thu hồi nợ** — nguyên tắc giới hạn mục đích. Ngược lại, cơ sở pháp lý để liên hệ về khoản nợ thường là "thực hiện hợp đồng", mạnh hơn và không cần đồng ý, nhưng chỉ áp dụng cho **bên có nghĩa vụ**.

Hệ quả cụ thể: nếu đồng bộ toàn bộ contact point từ CDP vào B.Collection, hệ thống sẽ có số điện thoại của người thân, người tham chiếu, đầu mối liên hệ marketing — những người mà Guardrail G02 sẽ chặn liên hệ. Đồng bộ chúng vào chỉ tạo ra cám dỗ và rủi ro, không tạo ra giá trị.

**(c) `party_obligation` không thể lấy từ CDP.** Bảng nền tảng của Guardrail G02 được dựng từ LOS/LMS (hợp đồng bảo lãnh, đồng vay, người đại diện pháp luật), không phải từ hồ sơ khách hàng. CDP biết *quan hệ*, không biết *nghĩa vụ pháp lý*. Đây là hai khái niệm khác nhau và tuyệt đối không được lẫn.

### 4.2 Vì sao cấm dùng Activation của CDP cho thu hồi

**Đây là điểm không thương lượng.** Activation engine của CDP đẩy thẳng ra kênh (SMS, email, push, ads). Nếu chiến dịch thu hồi chạy qua đường này, nó **đi vòng qua Guardrail** — không có kiểm tra tần suất, khung giờ, đối tượng có nghĩa vụ, cờ dễ tổn thương, hay audit log.

Nguy hiểm hơn: đường đi này rất tiện. Khi đội vận hành cần chạy gấp một chiến dịch nhắc nợ và B.Collection đang chậm, CDP Activation là lối tắt hiển nhiên. Vì vậy cần biện pháp kỹ thuật chứ không chỉ quy chế:

- Channel Adapter (SMS/ZNS Gateway) **từ chối mọi lệnh không có `guardrail_token` hợp lệ** khi `purpose = DEBT_COLLECTION`
- CDP không được cấp quyền tạo audience có tiêu chí liên quan trạng thái nợ (xem 4.3)
- Giám sát: đối soát log gateway với audit log Guardrail hằng ngày; chênh lệch > 0 là sự cố phải điều tra

### 4.3 Vì sao chiều ngược lại cũng nguy hiểm

Không chỉ CDP → B.Collection cần kiểm soát. Chiều **B.Collection → CDP** có rủi ro riêng, và thường bị bỏ sót.

Nếu trạng thái nợ quá hạn chảy ngược vào CDP và trở thành thuộc tính profile, hệ quả:
- Bộ phận marketing có thể tạo audience theo trạng thái nợ → tiết lộ thông tin khoản nợ ra ngoài phạm vi cần biết, vi phạm nghĩa vụ bí mật thông tin khách hàng (NĐ 117/2018)
- Khách hàng đang nợ quá hạn vẫn nhận được chào mời vay thêm — hoặc ngược lại, bị loại khỏi mọi chương trình chăm sóc một cách âm thầm, tạo hiệu ứng phân biệt đối xử không được kiểm soát
- Dữ liệu thu hồi có mục đích xử lý riêng; đưa sang CDP là mở rộng mục đích, cần cơ sở pháp lý riêng

**Quyết định:** B.Collection **không** đẩy trạng thái nợ, điểm số persona, hay kết quả thu hồi sang CDP. Nếu marketing cần loại trừ khách hàng đang thu hồi khỏi chiến dịch, dùng một **danh sách loại trừ dạng cờ nhị phân, không nêu lý do**, cung cấp qua interface riêng có kiểm soát và có DPIA.

### 4.4 Vì sao không dùng CDP làm nơi lưu Persona

Bốn yêu cầu của Persona mà CDP thường không đáp ứng:

| Yêu cầu | CDP điển hình | Persona cần |
|---|---|---|
| Ảnh chụp theo thời điểm | Ghi đè, lưu trạng thái hiện tại | **Snapshot bất biến tại mỗi lần NBA ra quyết định, giữ 5 năm** |
| Provenance từng trường | Thường ở mức nguồn dữ liệu | Từng fact: ai nhập, khi nào, cơ sở pháp lý, độ tin cậy, TTL |
| Suy giảm độ tin cậy | Không có | `effective_confidence = confidence × 0.5^(age/half_life)` |
| Cấu trúc đầu ra | Thuộc tính phẳng | `willingness_matrix[treatment]` — ma trận có điều kiện |

Nguyên nhân sâu xa: CDP được thiết kế để trả lời *"khách hàng này hiện đang thế nào"*. Persona thu hồi phải trả lời *"tại thời điểm 19:04 ngày 01/9, hệ thống biết gì về khách hàng này, và vì sao nó khuyến nghị hành động đó"*. Yêu cầu thứ hai là yêu cầu kiểm toán, không phải yêu cầu marketing.

### 4.5 Rủi ro nhập lại chính những gì đã loại trừ

Persona Model (nguyên tắc P4) cố tình không có trường cho sở thích, lối sống, phân khúc tâm lý, hay thuộc tính suy diễn về nhân thân. CDP thì thường có đầy đủ những thứ đó — đó là công việc của nó.

Nếu đồng bộ profile theo kiểu "lấy hết cho đủ", B.Collection sẽ nhập lại chính xác những gì đã chủ động loại trừ, và toàn bộ kỷ luật thiết kế ở Persona Model trở nên vô nghĩa.

**Cơ chế bắt buộc:** `IF-CDP-01` dùng **allowlist trường được khai báo tường minh**, không phải blocklist, không phải đồng bộ toàn bộ. Thêm một trường vào allowlist là thay đổi có kiểm soát, cần DPO duyệt.

---

## 5. Đặc tả interface CDP ↔ B.Collection

### `IF-CDP-02` — Định danh (bắt buộc, P0)
| Trường | Ghi chú |
|---|---|
| `golden_customer_id` | **Khoá chính**, B.Collection kế thừa, không tự sinh |
| `cif_no[]` | Danh sách CIF đã hợp nhất |
| `er_confidence` | Độ tin cậy hợp nhất từ CDP |
| `er_status` | `RESOLVED` / `PENDING_REVIEW` — ánh xạ sang `er_ambiguity_flag` |

`er_status = PENDING_REVIEW` → `er_ambiguity_flag = true` → NBA hạ cấp xuống hành động an toàn nhất, Guardrail G02 trả `ALLOW_WITH_CONDITIONS: ["no_debt_disclosure"]`.

### `IF-CDP-01` — Allowlist trường (P0)
| Nhóm | Trường được phép | Không được phép |
|---|---|---|
| Định danh | `full_name`, `dob`, `gender`, `nationality` | — |
| Liên hệ | `phone[]`, `address[]`, `email[]` **kèm `source` và `consent_purpose`** | Contact point của bên thứ ba, đầu mối marketing |
| Hành vi số | `app_login_frequency_30d`, `last_digital_session`, `preferred_language` | Lịch sử duyệt web, tương tác quảng cáo |
| Sản phẩm | `product_holdings[]`, `relationship_tenure` | — |
| — | — | **Phân khúc marketing, điểm lifestyle, thuộc tính tâm lý, giá trị vòng đời khách hàng, xu hướng churn** |

Mỗi contact point từ CDP mang theo `consent_purpose`. B.Collection **chỉ dùng contact point để liên hệ khi cơ sở pháp lý là hợp đồng tín dụng** (bên có nghĩa vụ), bất kể CDP nói gì về đồng ý marketing.

### `IF-CDP-03` — Danh sách loại trừ (chiều ngược, GĐ2, có DPIA)
Chỉ một trường: `suppress_marketing = true/false`. **Không kèm lý do, không kèm trạng thái nợ.**

---

## 6. Hệ quả

**Tích cực:**
- Không xây hệ thống định danh thứ hai — loại bỏ rủi ro lớn nhất
- Tiết kiệm khoảng 6–8 tuần trong MVP (không phải xây ER từ đầu)
- Dữ liệu hành vi số có sẵn, chất lượng tốt, không nhạy cảm
- Nhất quán "một khách hàng, một định danh" trên toàn hàng

**Tiêu cực / chi phí:**
- Phụ thuộc vào SLA và chất lượng ER của CDP — nếu CDP sai, B.Collection sai theo
- Cần đàm phán và duy trì allowlist với chủ quản CDP; đây là công việc liên tục, không phải một lần
- Cần DPIA cho việc dùng dữ liệu CDP vào mục đích thu hồi (giới hạn mục đích)
- Phải xây và duy trì cơ chế giám sát chống đi vòng qua Activation

**Rủi ro cần theo dõi:**

| # | Rủi ro | Biện pháp |
|---|---|---|
| C1 | ER của CDP không đủ chính xác cho mục đích thu hồi | Đo tỷ lệ vùng xám; nếu `PENDING_REVIEW` > 5% ở nhóm có case, cần bổ sung human review queue riêng |
| C2 | Chiến dịch thu hồi chạy qua CDP Activation, đi vòng Guardrail | Gateway từ chối lệnh không có token + đối soát log hằng ngày |
| C3 | Allowlist bị nới dần theo thời gian ("thêm trường này cho tiện") | Mỗi lần thêm cần DPO duyệt; rà soát định kỳ 6 tháng |
| C4 | Trạng thái nợ rò rỉ sang marketing | `IF-CDP-03` chỉ có cờ nhị phân; kiểm tra schema trong contract test |
| C5 | CDP thay đổi schema profile | Contract test trong CI |

---

## 7. Bốn câu hỏi cần trả lời để xác nhận quyết định này

Quyết định trên giả định CDP của Ngân hàng có đặc điểm phổ biến. Cần kiểm chứng:

| # | Câu hỏi | Nếu câu trả lời khác thì sao |
|---|---|---|
| 1 | **CDP có làm entity resolution thật, hay chỉ hợp nhất theo CIF sẵn có?** | Nếu chỉ join theo CIF, nó không phải thẩm quyền định danh → B.Collection cần lớp ER bổ sung cho graph, cộng 4–6 tuần |
| 2 | **CDP có phục vụ được truy vấn ở độ trễ < 300ms không, hay chỉ batch?** | Nếu chỉ batch, B.Collection phải giữ bản sao cục bộ của các trường nóng — chấp nhận được, nhưng cần thiết kế đồng bộ |
| 3 | **Contact point trong CDP có gắn `consent_purpose` và nguồn gốc không?** | Nếu không phân biệt được nguồn gốc và mục đích đồng ý, **không được dùng contact point từ CDP** để liên hệ thu hồi; chỉ dùng từ CIF/LOS |
| 4 | **CDP có lưu dữ liệu về người không phải khách hàng không** (đầu mối, người tham chiếu)? | Nếu có, allowlist phải loại trừ tuyệt đối nhóm này — rủi ro liên hệ người không có nghĩa vụ |

Câu 3 là câu quan trọng nhất. Nếu CDP trộn contact point từ nhiều nguồn mà không giữ nguồn gốc, thì toàn bộ dữ liệu liên hệ từ CDP không dùng được cho thu hồi, và MVP phải lấy contact point trực tiếp từ CIF và LOS. Điều này không phá vỡ quyết định chung (vẫn dùng CDP làm thẩm quyền định danh), nhưng thay đổi phạm vi `IF-CDP-01`.

---

## 8. Các phương án đã cân nhắc và loại bỏ

**Phương án A — Xây persona layer hoàn toàn độc lập, không dùng CDP.**
Loại bỏ vì tạo ra hệ thống định danh thứ hai. Khi CDP và B.Collection bất đồng về "hai bản ghi này có phải một người không", không có cơ chế hoà giải, và hệ quả là liên hệ nhầm người — rủi ro nghiêm trọng nhất trong thu hồi nợ. Ngoài ra tốn thêm 6–8 tuần cho việc đã có sẵn.

**Phương án B — Dùng CDP làm nền tảng persona, B.Collection chỉ là lớp ứng dụng mỏng.**
Loại bỏ vì bốn lý do ở Mục 4.4 (không có snapshot, không có provenance từng fact, không có suy giảm độ tin cậy, không chứa được ma trận có điều kiện), cộng với rủi ro ở 4.2 và 4.5. Về bản chất: CDP tối ưu cho *tiếp cận khách hàng*, còn persona thu hồi tối ưu cho *quyết định có kiểm soát và giải trình được*. Đây là hai bài toán khác nhau, dùng chung nền tảng sẽ khiến một trong hai bị hy sinh — và trong bối cảnh pháp lý hiện tại, bên bị hy sinh sẽ là tuân thủ.

**Phương án C — Mô hình lai (được chọn).**

---

## 9. Việc cần làm tiếp

| # | Hạng mục | Chủ trì | Hạn |
|---|---|---|---|
| 1 | Trả lời 4 câu hỏi ở Mục 7 (workshop với chủ quản CDP) | EA + CDP Owner | Tuần 2 |
| 2 | Chốt allowlist trường `IF-CDP-01` | SA + DPO | Tuần 4 |
| 3 | DPIA cho việc dùng dữ liệu CDP vào mục đích thu hồi | DPO | Tháng 2 |
| 4 | Bổ sung `IF-CDP-01/02/03` vào interface catalog và tài liệu Kiến trúc tích hợp | SA | Tuần 3 |
| 5 | Thiết kế cơ chế đối soát log gateway ↔ audit Guardrail (chống đi vòng) | SA + Compliance | Tháng 3 |
| 6 | Đo tỷ lệ ER vùng xám của CDP trên tập khách hàng có nợ quá hạn | Data Engineer | Tuần 4 |

---

*ADR phiên bản đề xuất. Cần xác nhận đặc điểm thực tế của CDP tại Ngân hàng (Mục 7) trước khi chuyển sang trạng thái "Đã chấp thuận".*
