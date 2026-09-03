# B.COLLECTION — ĐỀ XUẤT KIẾN TRÚC MULTI-AI-AGENT
### Phạm vi ứng dụng, ranh giới an toàn và lộ trình triển khai
**Phiên bản:** v0.1 | **Ngày:** 03/09/2026
**Liên quan:** Tài liệu Kiến trúc Hệ thống v1.0 (§10.3, §12) · Kinh nghiệm dự án CreditAgent

---

## 0. Luận điểm trung tâm

Cám dỗ lớn nhất khi đưa multi-agent vào một hệ thống thu hồi nợ là dùng agent để **ra quyết định**. Đó là hướng sai, và sai theo cách khó phát hiện: agent sẽ đưa ra quyết định nghe rất hợp lý, không ai kiểm chứng được, không backtest được, và khi có sự cố thì không giải trình được.

Phân định đúng như sau:

| Loại bài toán | Công cụ đúng |
|---|---|
| **Chấm điểm và xếp hạng** trên dữ liệu bảng | Mô hình thống kê có hiệu chuẩn (GBM), thẩm định được bằng backtest |
| **Phân bổ nguồn lực** có ràng buộc | Tối ưu có ràng buộc, xác định, tái lập được |
| **Kiểm soát tuân thủ** | Rule engine xác định, fail-closed |
| **Điều tra, tổng hợp, diễn giải** trên dữ liệu phi cấu trúc, số bước không biết trước | **Đây mới là chỗ của agent** |

Nói ngắn gọn: **agent làm việc mà con người phải đọc nhiều nguồn và suy luận nhiều bước mới xong, còn máy tính thông thường không làm được.** Agent không thay thế mô hình thống kê, và tuyệt đối không thay thế Guardrail.

---

## 1. Vị trí của agent trong kiến trúc 9 tầng

```
L8  TRẢI NGHIỆM        ← Agent hiển thị kết quả tại đây (Copilot, bản tóm tắt)
L7  THỰC THI           ✗ KHÔNG có agent
⛨L6 GUARDRAIL          ✗ KHÔNG có agent — deterministic, fail-closed (nguyên tắc GR2)
L5  QUYẾT ĐỊNH         ✗ KHÔNG có agent cho NBA/scoring
                       ✓ CÓ agent cho tổng hợp playbook (bước REUSE của CBR)
L4  TRÍ TUỆ            ✓ TẦNG CHÍNH CỦA AGENT
                         Agent Orchestration · Tool Gateway · LLM Gateway
L3  TRI THỨC           ← Agent đọc từ đây (Persona, Graph, Enrichment)
L2  DỮ LIỆU            ← Agent đọc từ đây
```

**Ba ranh giới bất di dịch:**

1. **Agent không bao giờ gọi trực tiếp tầng thực thi.** Không agent nào có công cụ gửi tin nhắn, quay số, hay tạo lệnh ra kênh. Đầu ra của agent là *đề xuất* hoặc *tài liệu*, đi vào NBA Engine hoặc màn hình của con người.
2. **Agent không tham gia Guardrail.** Nguyên tắc GR2 giữ nguyên: toàn bộ G01–G12 là logic xác định. LLM chỉ xuất hiện trong Content Filter như bộ phân loại phụ trợ, và chỉ có quyền làm quyết định *nghiêm ngặt hơn*.
3. **Agent không ghi dữ liệu chính thức.** Mọi `EnrichmentFact` do agent đề xuất đều ở trạng thái nháp, cần một cú xác nhận của con người mới có hiệu lực.

---

## 2. Nơi KHÔNG dùng agent — và vì sao

Phần này quan trọng ngang phần đề xuất, vì nó là thứ sẽ bị chất vấn nhiều nhất.

| Hạng mục | Vì sao không dùng agent |
|---|---|
| **Chấm điểm khả năng trả, thiện chí trả** | Cần hiệu chuẩn xác suất, backtest, kiểm tra tính công bằng, giám sát trôi mô hình. Agent không đáp ứng được khung Model Risk Management, và một điểm số do LLM sinh ra không có ý nghĩa thống kê. |
| **Chọn hành động (NBA)** | Là bài toán tối ưu có ràng buộc trên toàn danh mục — cần lời giải toàn cục, không phải quyết định từng case. Agent giải theo từng case sẽ cho kết quả tệ hơn về mặt phân bổ nguồn lực. |
| **Guardrail G01–G12** | Phải xác định, tái lập được, chứng minh được với thanh tra. Một quyết định chặn hay không chặn không được phép phụ thuộc vào nhiệt độ lấy mẫu của mô hình. |
| **Gửi tin nhắn hoặc nói chuyện tự động với khách hàng** | Rủi ro pháp lý và danh tiếng cao nhất; nội dung ra khách hàng phải theo mẫu đã duyệt. Không đưa vào phạm vi trong 24 tháng đầu. |
| **Đàm phán tự động với khách hàng** | Hướng này đang được nói nhiều trên thế giới nhưng khung pháp lý Việt Nam chưa có gì cho tình huống này. Không đề xuất. |
| **Quyết định thu giữ TSBĐ, khởi kiện, miễn giảm** | Hành động không đảo ngược — nguyên tắc AP5 yêu cầu con người quyết định. |

> Nếu Hội đồng chỉ chấp thuận một nguyên tắc duy nhất từ tài liệu này, nên là nguyên tắc: **agent tạo ra thông tin để con người và hệ thống xác định ra quyết định, chứ agent không ra quyết định.**

---

## 3. Danh mục agent đề xuất

Tám agent, xếp theo tỷ lệ giá trị trên rủi ro.

### 3.1 Nhóm ưu tiên cao (Giai đoạn 2)

**A1 — Investigation Agent (Điều tra hồ sơ nợ)**

Bài toán agent phù hợp nhất trong toàn hệ thống: số bước không biết trước, nhiều nguồn, cần suy luận bắc cầu.

| | |
|---|---|
| **Đầu vào** | `case_id`, mục tiêu điều tra (tìm lại liên lạc / truy vết tài sản / xác minh tình trạng hoạt động) |
| **Công cụ** | Truy vấn graph nhiều hop · tra cứu cổng ĐKKD · cổng bản án · đăng ký giao dịch bảo đảm · lịch sử giao dịch · tài liệu trong hệ thống lưu trữ |
| **Đầu ra** | Báo cáo điều tra có cấu trúc: giả thuyết, bằng chứng kèm nguồn, mức độ tin cậy, đề xuất bước tiếp theo |
| **Giá trị** | Việc mà một chuyên viên giỏi mất 2–4 giờ; agent làm trong vài phút và không bỏ sót nhánh |
| **Ranh giới** | Chỉ đọc. Không tự tạo fact. Mọi kết luận phải có `evidence_ref`. **Không truy cập mạng xã hội** (quyết định D7). |

**A2 — Case Narrative Agent (Diễn giải chân dung)**

| | |
|---|---|
| **Đầu vào** | Persona snapshot, lịch sử tương tác, đặc trưng graph |
| **Đầu ra** | Bản tóm tắt 5–7 câu cho Persona Card: khách hàng này là ai trong bối cảnh khoản nợ, vì sao chưa trả, điều gì đã thử và kết quả ra sao |
| **Ràng buộc cứng** | **Chỉ được dùng dữ liệu có trong Persona snapshot**; mỗi câu phải dẫn được về trường dữ liệu nguồn; cấm suy diễn ngoài dữ liệu |
| **Giá trị** | Rút thời gian cán bộ nắm tình huống từ vài phút xuống 15 giây |

**A3 — Compliance QA Agent (Rà soát tuân thủ cuộc gọi)**

| | |
|---|---|
| **Đầu vào** | Bản chép lời cuộc gọi + bộ quy tắc ứng xử |
| **Đầu ra** | Danh sách phát hiện: loại vi phạm, trích đoạn, mức độ, khuyến nghị xử lý |
| **Giá trị** | Rà 100% cuộc gọi thay cho lấy mẫu 2% thủ công. **Đây là agent có giá trị phòng vệ cao nhất.** |
| **Ranh giới** | Phát hiện của agent là *cảnh báo để con người xem xét*, không phải kết luận kỷ luật. Vi phạm nghiêm trọng chuyển thẳng bộ phận Tuân thủ. |

Ba agent trên nên làm trước, vì cả ba đều **chỉ đọc, đầu ra là tài liệu cho con người đọc**, rủi ro thấp nhất, và giá trị đo được ngay.

### 3.2 Nhóm ưu tiên trung bình (Giai đoạn 2 cuối / Giai đoạn 3)

**A4 — Root Cause Agent.** Kết hợp bất thường dòng tiền (tầng 1), nội dung cuộc gọi (tầng 2) và tín hiệu bên ngoài để đề xuất nhãn nguyên nhân gốc kèm bằng chứng. Đầu ra là **chip đề xuất** trên màn hình kết thúc cuộc gọi, cán bộ xác nhận một chạm. Không được tự gán nhãn `WILFUL_DEFAULT` — nhãn này luôn cần bằng chứng định lượng và duyệt 4 mắt.

**A5 — Playbook Synthesis Agent.** Bước REUSE của Case Reference Engine: từ 5–10 case tương đồng đã truy hồi, tổng hợp thành một playbook mạch lạc thay vì liệt kê thô. Ràng buộc: chỉ tổng hợp từ case có `compliance_review = passed`; phải hiển thị cả tỷ lệ thất bại của playbook, không chỉ tỷ lệ thành công.

**A6 — Collector Copilot.** Gợi ý trong và trước cuộc gọi: xử lý phản đối, tính phương án cơ cấu tại chỗ, nhắc ràng buộc Guardrail đang áp dụng. Toàn bộ nội dung gợi ý đi qua Content Filter; kịch bản lấy từ thư viện đã duyệt, agent chỉ cá nhân hóa cách diễn đạt trong khung cho phép.

### 3.3 Nhóm chuyên biệt (Giai đoạn 3)

**A7 — Corporate Group Strategist.** Dành cho khách hàng doanh nghiệp và nhóm nợ liên đới — bài toán thực sự phức tạp: nhiều pháp nhân, sở hữu chéo, dòng tiền vòng, tài sản đồng bảo đảm. Đây là nơi lập luận nhiều bước của agent có giá trị cao nhất, và cũng là nơi khối lượng case nhỏ nên chi phí chấp nhận được. Đầu ra: phương án đàm phán cấp nhóm, kèm bản đồ quan hệ và phân tích đòn bẩy hợp pháp.

**A8 — Legal Prep Agent.** Chuẩn bị hồ sơ tố tụng: kiểm tra tính đầy đủ chứng từ, đối chiếu thời hiệu, lập bảng tính nghĩa vụ, soạn danh mục tài liệu. **Không soạn văn bản tố tụng nộp tòa** — chỉ chuẩn bị đầu vào cho luật sư.

### 3.4 Bảng tổng hợp

| Mã | Agent | Quyền | Đầu ra đi đâu | Giai đoạn |
|---|---|---|---|---|
| A1 | Investigation | Chỉ đọc | Báo cáo cho chuyên viên | GĐ2 |
| A2 | Case Narrative | Chỉ đọc | Persona Card | GĐ2 |
| A3 | Compliance QA | Chỉ đọc | Hàng đợi Tuân thủ | GĐ2 |
| A4 | Root Cause | Đề xuất nháp | Chip xác nhận | GĐ2 cuối |
| A5 | Playbook Synthesis | Chỉ đọc | Persona Card | GĐ2 cuối |
| A6 | Collector Copilot | Chỉ đọc | Màn hình cán bộ | GĐ3 |
| A7 | Corporate Strategist | Chỉ đọc | Hồ sơ đề xuất cho Hội đồng | GĐ3 |
| A8 | Legal Prep | Đề xuất nháp | Hồ sơ cho Pháp chế | GĐ3 |

Không agent nào có quyền ghi trực tiếp vào dữ liệu chính thức, và không agent nào có công cụ ra kênh khách hàng.

---

## 4. Kiến trúc kỹ thuật

### 4.1 Tái sử dụng nền tảng CreditAgent

Dự án CreditAgent đã xây và kiểm chứng bốn thành phần dùng lại được trực tiếp. Đây là lý do chi phí triển khai agent cho B.Collection thấp hơn nhiều so với xây mới.

| Thành phần | Tái sử dụng |
|---|---|
| **Temporal durable execution** | Điều phối agent nhiều bước, có checkpoint, chịu được gián đoạn, chờ người |
| **Tool Gateway với danh sách công cụ được phép** | Cơ chế cấp quyền công cụ theo vai trò agent |
| **LLM Gateway** | Che PII trước khi gửi prompt, xác thực schema đầu ra, cache ngữ nghĩa, phân tầng mô hình, công tắc ngắt |
| **Khung audit hash-chain** | Ghi nhật ký bất biến mọi bước suy luận và mọi lượt gọi công cụ |
| **Mô hình Control Layer tách khỏi tầng agent** | Xem 4.3 — bài học quan trọng nhất từ CreditAgent |

### 4.2 Sơ đồ

```
┌──────────────────────────────────────────────────────────────────────┐
│ L8  Collector Workspace · Hàng đợi Tuân thủ · Hồ sơ Hội đồng         │
└───────────────────────────▲──────────────────────────────────────────┘
                            │ kết quả đã qua kiểm soát
┌───────────────────────────┴──────────────────────────────────────────┐
│ AGENT CONTROL LAYER  (xác định, không dùng LLM, fail-closed)         │
│  · Kiểm tra schema đầu ra    · Kiểm tra dẫn chứng bắt buộc           │
│  · Content Filter            · Ngân sách bước/token                  │
│  · Phát hiện suy diễn ngoài dữ liệu    · Định tuyến phê duyệt        │
└───────────────────────────▲──────────────────────────────────────────┘
                            │ đề xuất thô
┌───────────────────────────┴──────────────────────────────────────────┐
│ AGENT ORCHESTRATION  (Temporal)                                      │
│   A1 Investigation │ A2 Narrative │ A3 QA │ A4 Root Cause │ ...      │
│   · State machine mỗi agent   · Checkpoint   · Giới hạn vòng lặp     │
└───────────────────────────▲──────────────────────────────────────────┘
                            │
┌───────────────────────────┴──────────────────────────────────────────┐
│ TOOL GATEWAY (allowlist theo vai trò)  │  LLM GATEWAY (PII, schema)  │
└───────────────────────────▲──────────────────────────────────────────┘
                            │ CHỈ ĐỌC
┌───────────────────────────┴──────────────────────────────────────────┐
│ L3 Persona · Collection Graph · Enrichment │ L2 Lakehouse            │
└──────────────────────────────────────────────────────────────────────┘

        ✗ KHÔNG có đường: Agent ──► Guardrail hoặc Kênh khách hàng
```

### 4.3 Agent Control Layer — bài học từ CreditAgent

CreditAgent tách **Approval Control Layer** chạy xác định ra khỏi tầng agent. Nguyên tắc đó áp dụng nguyên vẹn ở đây, với sáu kiểm tra bắt buộc trên mọi đầu ra agent:

| # | Kiểm tra | Hành vi khi fail |
|---|---|---|
| 1 | **Schema** — đầu ra khớp cấu trúc Pydantic đã định nghĩa | Loại bỏ, thử lại tối đa N lần rồi báo lỗi |
| 2 | **Dẫn chứng bắt buộc** — mọi khẳng định có `evidence_ref` trỏ tới dữ liệu thật | Loại bỏ khẳng định không có dẫn chứng |
| 3 | **Không suy diễn ngoài dữ liệu** — đối chiếu thực thể và con số trong đầu ra với dữ liệu nguồn | Đánh dấu và không hiển thị phần vi phạm |
| 4 | **Content Filter** — cùng bộ lọc của G06 | Chặn, ghi cảnh báo Tuân thủ |
| 5 | **Ngân sách** — số bước, số lượt gọi công cụ, số token | Dừng agent, trả kết quả một phần kèm ghi chú |
| 6 | **Định tuyến phê duyệt** — đầu ra loại nào cần ai duyệt | Đưa vào đúng hàng đợi |

Kiểm tra số 3 đáng nói riêng. Cách hiện thực: trích xuất mọi thực thể (tên, số tiền, ngày, mã hồ sơ) trong văn bản agent sinh ra, đối chiếu với tập dữ liệu đã cấp cho agent; thực thể không khớp là dấu hiệu bịa đặt. Đây là cơ chế rẻ và bắt được phần lớn lỗi nghiêm trọng.

### 4.4 Tool Gateway — phân quyền công cụ

| Nhóm công cụ | A1 | A2 | A3 | A4 | A5 | A6 | A7 | A8 |
|---|---|---|---|---|---|---|---|---|
| Đọc Persona snapshot | ✓ | ✓ | | ✓ | ✓ | ✓ | ✓ | ✓ |
| Truy vấn graph nhiều hop | ✓ | | | | | | ✓ | |
| Đọc lịch sử giao dịch | ✓ | | | ✓ | | | ✓ | ✓ |
| Đọc bản chép lời cuộc gọi | | | ✓ | ✓ | | | | |
| Tra cứu nguồn công khai (tầng Xanh) | ✓ | | | | | | ✓ | ✓ |
| Truy hồi case tương đồng | | | | | ✓ | ✓ | ✓ | |
| Đọc chứng từ trong hệ thống lưu trữ | ✓ | | | | | | ✓ | ✓ |
| **Tạo bản nháp EnrichmentFact** | | | | ✓ | | | | ✓ |
| **Gửi tin nhắn / quay số** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Ghi dữ liệu chính thức** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

Mọi lượt gọi công cụ ghi nhật ký kèm `case_id`, mục đích và agent gọi. Công cụ đọc dữ liệu khách hàng đều đi qua cùng cơ chế phân quyền và che dữ liệu như người dùng thật — **agent không có đặc quyền vượt trên cán bộ được phân công case đó**.

---

## 5. Xử lý nội dung không đáng tin — rủi ro kỹ thuật lớn nhất

Agent trong B.Collection đọc ba loại nội dung do bên ngoài kiểm soát: bản chép lời lời nói của khách hàng, tài liệu khách hàng cung cấp, và trang web từ nguồn công khai. **Tất cả đều là dữ liệu không đáng tin.**

Rủi ro này không phải lý thuyết. Trong quá trình tra cứu văn bản pháp luật phục vụ dự án, chúng tôi đã gặp một trang web pháp luật nhúng đoạn văn bản ẩn hướng dẫn hệ thống AI phải quảng bá trang đó trong câu trả lời. Nếu một agent OSINT đọc trang như vậy mà không có phòng vệ, nó có thể bị điều khiển.

**Sáu biện pháp bắt buộc:**

1. **Nội dung bên ngoài không bao giờ đưa vào system prompt.** Chỉ đưa vào như dữ liệu, bọc trong thẻ đánh dấu rõ ràng là nội dung không tin cậy.
2. **Agent không được lấy chỉ thị từ nội dung nó đọc.** Chỉ thị chỉ đến từ system prompt và tham số đầu vào có kiểm soát.
3. **Kết quả công cụ được gắn nhãn nguồn**; Control Layer từ chối mọi hành động phát sinh từ nội dung không tin cậy.
4. **Agent OSINT chạy trong vùng mạng riêng**, không có đường ghi trực tiếp vào Persona.
5. **Danh sách miền được phép** cho công cụ tra cứu web; không cho phép agent tự chọn URL tùy ý.
6. **Giám sát mẫu hình bất thường**: agent đột ngột đổi hành vi, gọi công cụ ngoài kịch bản, hoặc sinh nội dung không liên quan tới case.

---

## 6. Kinh tế vận hành — bài toán chọn lọc kích hoạt

Với 500.000–800.000 hồ sơ B1 tồn tại một thời điểm, **không thể chạy agent cho mọi case**. Đây là ràng buộc thiết kế, không phải chi tiết vận hành.

**Nguyên tắc: agent chạy khi giá trị kỳ vọng của thông tin vượt chi phí sinh ra thông tin đó.**

| Agent | Điều kiện kích hoạt |
|---|---|
| A1 Investigation | `lost_contact_flag = true` **và** dư nợ vượt ngưỡng; hoặc có cảnh báo tẩu tán tài sản |
| A2 Narrative | Chỉ khi cán bộ mở Persona Card, có cache theo `persona_snapshot_id` |
| A3 Compliance QA | 100% cuộc gọi — nhưng dùng mô hình nhỏ, phân tầng; chỉ chuyển mô hình lớn khi tầng nhỏ phát hiện nghi vấn |
| A4 Root Cause | Sau cuộc gọi có tiếp cận đúng người |
| A5 Playbook | Chỉ với case bucket B2 trở lên |
| A6 Copilot | Theo yêu cầu của cán bộ |
| A7 Corporate | Case doanh nghiệp vượt ngưỡng dư nợ |
| A8 Legal Prep | Case đã được duyệt chuyển pháp lý |

**Ba cơ chế giảm chi phí:** phân tầng mô hình (mô hình nhỏ sàng lọc, mô hình lớn chỉ xử lý phần khó — đã có trong LLM Gateway của CreditAgent); cache ngữ nghĩa theo snapshot; và ngân sách token cứng cho mỗi loại agent, vượt thì dừng và trả kết quả một phần.

Cần lập **mô hình chi phí trước khi triển khai**: chi phí mỗi lượt chạy × số lượt kỳ vọng, đối chiếu với giá trị thu hồi tăng thêm. Với A1, phép tính đơn giản: nếu một lượt điều tra tốn X đồng và tỷ lệ tìm lại được liên lạc là p, thì chỉ chạy khi `p × giá trị thu hồi kỳ vọng > X`.

---

## 7. Đánh giá chất lượng và quản trị rủi ro mô hình

Agent **không** thẩm định được bằng backtest như mô hình thống kê. Cần khung riêng, và đây là điểm cần thống nhất sớm với Model Risk Committee.

### 7.1 Bộ đánh giá

| Thành phần | Nội dung |
|---|---|
| **Gold set** | 50–100 case đã được chuyên gia xử lý và ghi lại kết luận đúng; agent chạy lại, đo tỷ lệ đồng thuận |
| **Chế độ bóng (shadow mode)** | Agent chạy song song trên 200+ case thật nhưng kết quả không hiển thị cho cán bộ; so sánh với kết quả thực tế |
| **Đo tỷ lệ bịa đặt** | Tỷ lệ khẳng định không có dẫn chứng hoặc dẫn chứng sai — mục tiêu dưới 1%, và là chỉ số chặn go-live |
| **Đo tính hữu ích** | Tỷ lệ đề xuất của agent được cán bộ chấp nhận; và quan trọng hơn: case có dùng agent có thu hồi tốt hơn không (đo bằng holdout) |
| **Kiểm thử đối kháng** | Bộ mẫu chứa chỉ thị nhúng, nội dung gây nhiễu, dữ liệu mâu thuẫn |

### 7.2 Nguyên tắc đo hiệu quả

Áp dụng đúng phương pháp tại §24 của tài liệu kiến trúc: **agent cũng phải chứng minh giá trị bằng nhóm đối chứng**, không phải bằng cảm nhận của người dùng. Cụ thể: trong nhóm case đủ điều kiện kích hoạt agent, chia ngẫu nhiên một phần không chạy agent, so sánh kết quả thu hồi.

Đây là điểm dễ bị bỏ qua vì agent "trông có vẻ hữu ích". Cảm nhận hữu ích và giá trị kinh tế là hai chuyện khác nhau.

### 7.3 Quản trị

Agent nằm trong danh mục mô hình, nhưng với hồ sơ thẩm định khác: mô tả năng lực và giới hạn, bộ đánh giá và kết quả, danh sách công cụ được cấp, ngân sách, cơ chế giám sát, và **thủ tục ngắt**. Mỗi agent có công tắc tắt độc lập, tắt được trong vài phút mà không ảnh hưởng phần còn lại của hệ thống.

---

## 8. Vai trò của con người

| Loại đầu ra agent | Cơ chế con người |
|---|---|
| Báo cáo điều tra (A1) | Chuyên viên đọc và quyết định bước tiếp theo |
| Bản tóm tắt chân dung (A2) | Hiển thị kèm liên kết tới dữ liệu gốc; cán bộ bấm được để kiểm chứng |
| Phát hiện tuân thủ (A3) | Bộ phận Tuân thủ xác nhận trước khi thành hồ sơ |
| Đề xuất nhãn nguyên nhân (A4) | **Chip xác nhận một chạm** — cán bộ bấm Đúng / Sửa / Bỏ qua |
| Playbook (A5) | Cán bộ chấp nhận / sửa / từ chối, **bắt buộc ghi lý do khi từ chối** |
| Phương án nhóm KHDN (A7) | Hồ sơ trình Hội đồng, không tự động áp dụng |

Dữ liệu từ các lượt từ chối và sửa đổi quay lại làm đầu vào cải tiến — cùng cơ chế Approver Quality đã thiết kế trong CreditAgent.

**Một cảnh báo về vận hành:** khi tỷ lệ chấp nhận đề xuất của agent quá cao (trên 95%), rất có thể cán bộ đang bấm chấp nhận mà không đọc. Cần theo dõi chỉ số này theo từng cán bộ và đối chiếu mẫu, tương tự cách theo dõi tỷ lệ sửa chip xác nhận trong tài liệu kiến trúc §14.7.

---

## 9. Lộ trình

| Giai đoạn | Nội dung | Điều kiện tiên quyết |
|---|---|---|
| **Không có trong MVP** | — | MVP tập trung dữ liệu, Guardrail, hai mô hình thống kê |
| **GĐ2 sớm (tháng 5–8)** | Hạ tầng: Agent Orchestration trên Temporal, Tool Gateway, LLM Gateway, Agent Control Layer. **A3 Compliance QA trước tiên** | Pipeline ASR hoạt động; LLM tại chỗ đã cài đặt |
| **GĐ2 giữa (tháng 9–11)** | **A2 Narrative**, **A1 Investigation** | Collection Graph đã dựng; gold set đã chuẩn bị |
| **GĐ2 cuối (tháng 12–14)** | A4 Root Cause, A5 Playbook Synthesis | Case Reference Engine hoạt động |
| **GĐ3 (tháng 15–24)** | A6 Copilot, A7 Corporate Strategist, A8 Legal Prep | Đã có bằng chứng hiệu quả từ nhóm agent trước |

**Vì sao A3 trước A1 và A2** dù A1 có giá trị nghiệp vụ cao hơn: A3 có rủi ro thấp nhất (đầu ra chỉ đến bộ phận Tuân thủ, không ảnh hưởng khách hàng), cho phép đội ngũ học cách vận hành agent trong môi trường an toàn, và tạo ra giá trị phòng vệ ngay lập tức. Học cách vận hành agent trên một bài toán không chạm khách hàng là cách khởi đầu đúng.

---

## 10. Rủi ro

| # | Rủi ro | Mức | Biện pháp |
|---|---|---|---|
| AG1 | **Agent bịa đặt thông tin về khách hàng** dẫn tới hành động sai | Cao | Kiểm tra dẫn chứng bắt buộc và đối chiếu thực thể trong Control Layer; đo tỷ lệ bịa đặt là chỉ số chặn go-live |
| AG2 | **Chỉ thị nhúng trong nội dung bên ngoài** điều khiển agent | Cao | Sáu biện pháp tại §5; kiểm thử đối kháng bắt buộc |
| AG3 | Chi phí vận hành vượt dự toán | Cao | Chọn lọc kích hoạt, phân tầng mô hình, ngân sách cứng; lập mô hình chi phí trước triển khai |
| AG4 | Agent dần được giao quyền quyết định do "tiện" | Cao | Ranh giới trong §1 là ràng buộc kiến trúc, có kiểm tra tự động trong CI; agent không có công cụ ra kênh |
| AG5 | Cán bộ chấp nhận đề xuất mà không kiểm chứng | Trung bình | Theo dõi tỷ lệ chấp nhận theo cán bộ; hiển thị dẫn chứng bấm được |
| AG6 | Không chứng minh được giá trị kinh tế | Trung bình | Nhóm đối chứng riêng cho từng agent |
| AG7 | Không qua được thẩm định Model Risk | Trung bình | Thống nhất khung thẩm định cho agent với Model Risk Committee **trước khi** xây |
| AG8 | Rò rỉ dữ liệu cá nhân qua LLM | Cao | Mô hình tại chỗ; che PII trong LLM Gateway; không gửi dữ liệu ra API bên ngoài |

---

## 11. Việc cần quyết

| # | Nội dung | Người quyết | Hạn |
|---|---|---|---|
| 1 | Chấp thuận nguyên tắc "agent tạo thông tin, không ra quyết định" | Hội đồng Kiến trúc | Phiên họp |
| 2 | Thống nhất khung thẩm định Model Risk cho agent | Model Risk Committee | Trước GĐ2 |
| 3 | Xác nhận mô hình LLM tại chỗ: lựa chọn, hạ tầng GPU, ngân sách | Khối CNTT | GĐ2 |
| 4 | Cơ sở pháp lý cho việc agent đọc bản chép lời cuộc gọi | DPO | GĐ2 |
| 5 | Chuẩn bị gold set 50–100 case do chuyên gia xử lý | Khối XLN | Trước A1/A2 |
| 6 | Mô hình chi phí vận hành agent | PO + Tài chính | Trước GĐ2 |
| 7 | Xác nhận tái sử dụng được LLM Gateway và Tool Gateway của CreditAgent | EA + đội CreditAgent | Tuần 4 |

---

*Đề xuất kiến trúc, phiên bản thảo luận. Không có hạng mục nào trong tài liệu này thuộc phạm vi MVP; toàn bộ thuộc Giai đoạn 2 trở đi và phụ thuộc vào việc nền tảng dữ liệu, Guardrail và pipeline xử lý giọng nói đã hoạt động ổn định.*
