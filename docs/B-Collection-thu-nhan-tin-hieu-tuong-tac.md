# B.COLLECTION — THIẾT KẾ THU NHẬN TÍN HIỆU TƯƠNG TÁC
### Tối đa hóa dữ liệu tự động, tối thiểu hóa nhập tay
**Phiên bản:** v0.1 | **Ngày:** 01/09/2026
**Liên quan:** Persona Model v0.2 (Phần B) · Guardrail Service v1.0 · Tech Stack MVP · Kiến trúc tích hợp

---

## 0. Nguyên tắc trung tâm

> **Ghi nhận dữ liệu phải là sản phẩm phụ của công việc, không phải công việc thêm.**

Mọi hệ thống bắt cán bộ "nhập liệu sau khi làm việc" đều thất bại theo cùng một cách: tháng đầu nhập đầy đủ, tháng thứ ba nhập qua loa, tháng thứ sáu chọn bừa giá trị đầu tiên trong dropdown. Không có cơ chế khuyến khích nào sửa được điều này, vì vấn đề nằm ở thiết kế chứ không ở kỷ luật.

Cách duy nhất hiệu quả là **giảm số thao tác cần thiết xuống gần 0** bằng cách lấy tín hiệu từ nơi nó phát sinh tự nhiên.

**Mục tiêu định lượng:** thời gian ghi nhận sau mỗi cuộc gọi ≤ **15 giây**, trong đó ≥ 80% nội dung là xác nhận gợi ý sẵn (một chạm), ≤ 20% là chọn từ danh mục, và **0% là gõ văn bản tự do bắt buộc**.

---

## 1. Thang bậc tự động hóa

Mọi tín hiệu được phân vào một trong bốn bậc. Nguyên tắc thiết kế: **đẩy càng nhiều tín hiệu lên bậc cao càng tốt**, và mỗi khi phải thêm một trường ở bậc 4, đó là dấu hiệu thiết kế có vấn đề.

| Bậc | Cơ chế | Chi phí cho cán bộ | Tỷ trọng mục tiêu |
|---|---|---|---|
| **1** | Hoàn toàn tự động — hệ thống tự biết | 0 giây | **60%** |
| **2** | Tự động suy ra, cán bộ xác nhận một chạm | 2–3 giây | **25%** |
| **3** | Chọn từ danh mục có gợi ý sẵn | 5–8 giây | **15%** |
| **4** | Nhập văn bản tự do | 30+ giây | **< 2%, luôn tùy chọn** |

---

## 2. Bản đồ tín hiệu theo kênh

### 2.1 Bậc 1 — hoàn toàn tự động (không cần cán bộ làm gì)

Đây là nhóm bị đánh giá thấp nhất và có tỷ lệ giá trị trên chi phí cao nhất. Phần lớn có thể triển khai **ngay trong MVP, không cần AI**.

| Tín hiệu | Nguồn | Ý nghĩa cho Persona |
|---|---|---|
| Cuộc gọi: có kết nối, thời lượng, ai gác máy trước | CTI/Dialer metadata | `avoidance_pattern`, `contactability_score` |
| Số lần đổ chuông trước khi nghe | CTI | Chỉ báo né tránh |
| SMS/ZNS: đã gửi, đã nhận, đã đọc | Gateway callback | Kênh nào thực sự tiếp cận được |
| Bấm vào link trong tin nhắn | URL có token theo case | **Tín hiệu quan tâm rất mạnh** |
| Đăng nhập app sau khi nhận tin nhắn | Kênh số | Đã đọc và có phản ứng |
| Mở màn hình khoản vay trong app | Kênh số | Đang xem xét |
| **Bắt đầu mô phỏng cơ cấu rồi bỏ dở** | Portal tự phục vụ | **Tín hiệu giá trị nhất** — muốn trả nhưng vướng gì đó |
| Thanh toán: thời điểm, số tiền, một phần hay đủ | Core (`IF-CORE-04`) | Thiện chí, khả năng |
| Thời điểm trả so với ngày lương | Core + enrichment | Xác nhận `cash_availability_window` |
| Bấm phím IVR | IVR | Ý định đã khai báo |
| Gọi vào tổng đài chủ động | CTI | `proactive_contact_count` |

> **Tín hiệu "bắt đầu mô phỏng cơ cấu rồi bỏ dở"** đáng nói riêng. Nó cho biết khách hàng *muốn* giải quyết nhưng gặp trở ngại — có thể là điều kiện không phù hợp, có thể là không hiểu, có thể là số tiền vẫn quá cao. Đây là tín hiệu mà không cuộc gọi nào thu được, và nó nên kích hoạt một treatment riêng: gọi lại trong 24h với đúng nội dung khách hàng đang xem. Chi phí triển khai gần bằng 0 nếu portal có event tracking.

### 2.2 Bậc 2 — xác nhận một chạm

Nguồn chính là phân tích cuộc gọi (Mục 3). Ngoài ra:

| Tín hiệu | Cách suy ra |
|---|---|
| Cam kết trả nợ (PTP): số tiền, ngày | Trích từ cuộc gọi → chip xác nhận |
| Nguyên nhân chậm trả | Phân loại từ cuộc gọi → gợi ý enum `root_cause` |
| Kênh và khung giờ ưa thích | Suy từ lịch sử RPC → cán bộ xác nhận khi khách hàng nói khác |
| Số điện thoại mới | Nhận diện trong cuộc gọi → chip xác nhận |
| Chu kỳ lương | Suy từ phân bố dòng tiền vào → xác nhận |

### 2.3 Bậc 3 — chọn từ danh mục
Kết quả cuộc gọi (`RPC`, `WRONG_PARTY`, `NO_ANSWER`, `REFUSED`, `DISPUTED`), loại phản đối, bước tiếp theo. Tất cả là enum, tối đa 6 lựa chọn mỗi trường, **có gợi ý mặc định** dựa trên nội dung cuộc gọi.

### 2.4 Bậc 4 — văn bản tự do
Chỉ một trường: `INTERACTION_NOTE`, tối đa 500 ký tự, **luôn tùy chọn**, và đi qua Content Filter. Không có trường tự do nào khác trong toàn hệ thống.

---

## 3. Pipeline phân tích cuộc gọi

### 3.1 Kiến trúc

```
[1] CTI/Dialer ──► ghi âm (2 kênh riêng: cán bộ / khách hàng)
                   │
[2] Lưu trữ  ─────►│ Object store, mã hóa at-rest, TTL theo chính sách
                   │
[3] ASR tiếng Việt ┤ Speech-to-text + timestamp từng từ
                   │
[4] Diarization ───┤ Tách người nói (nếu ghi âm không tách kênh)
                   │
[5] Trích xuất ────┤ LLM có schema đầu ra (Pydantic) → fact có cấu trúc
    có cấu trúc    │   · PTP: số tiền, ngày
                   │   · root_cause
                   │   · số điện thoại / địa chỉ mới
                   │   · loại phản đối
                   │   · tín hiệu dễ tổn thương
                   │   · tín hiệu tranh chấp
                   │
[6] Phân loại ─────┤ Nhóm tín hiệu (Mục 4) — KHÔNG phải "sentiment" đơn thuần
                   │
[7] QA tuân thủ ───┤ Rà 100% cuộc gọi tìm vi phạm quy tắc ứng xử
                   │
[8] Hàng đợi ──────► Chip xác nhận trên màn hình call wrap-up
    xác nhận         Cán bộ bấm [Đúng] / [Sửa] / [Bỏ qua]
                   │
[9] EnrichmentFact ► Chỉ tạo SAU khi con người xác nhận
```

**Độ trễ mục tiêu:** bước 3–6 hoàn tất trong **≤ 30 giây** sau khi cuộc gọi kết thúc, để chip xuất hiện ngay trên màn hình wrap-up. Nếu chậm hơn, cán bộ đã đóng màn hình và cơ chế mất tác dụng — đây là yêu cầu phi chức năng quan trọng nhất của toàn pipeline.

### 3.2 Ba nguyên tắc bất di dịch

1. **LLM không bao giờ tự tạo fact.** Nó chỉ đề xuất; `EnrichmentFact` chỉ tồn tại sau khi có một cú bấm của con người. Bản ghi lưu `source_type = DEBTOR_DECLARED`, `collection_channel = CALL_ASR_CONFIRMED`.
2. **Bản ghi âm gốc là bằng chứng, bản chép lời không phải.** Mọi tranh chấp quay về bản ghi âm. ASR có sai số và không được dùng làm chứng cứ pháp lý.
3. **Toàn bộ chạy on-premise.** Dữ liệu cuộc gọi thu hồi nợ chứa thông tin khách hàng và dữ liệu sinh trắc học (Mục 5). Không gửi ra API bên ngoài.

### 3.3 Lựa chọn công nghệ ASR tiếng Việt

Bối cảnh ngân hàng Việt Nam đòi hỏi on-premise, nên lựa chọn thu hẹp đáng kể.

| Nhóm | Ứng viên cần đánh giá | Ghi chú |
|---|---|---|
| Mô hình mở, tự host | Whisper large-v3 (tinh chỉnh tiếng Việt), PhoWhisper (VinAI, mã nguồn mở) | Kiểm soát hoàn toàn, không phí theo phút; cần GPU và đội vận hành |
| Nhà cung cấp trong nước | Viettel AI, VNPT AI, FPT.AI, Zalo AI, VBee | Có phương án triển khai tại chỗ; chất lượng tiếng Việt thường tốt hơn mô hình đa ngôn ngữ chung |
| Diarization | pyannote.audio | Chỉ cần nếu ghi âm không tách được 2 kênh |

> **Bối cảnh công nghệ ASR thay đổi nhanh; danh sách trên là điểm khởi đầu để đánh giá tại thời điểm hiện tại, không phải khuyến nghị chọn sẵn.**

**Bắt buộc: tự benchmark, không tin WER của nhà cung cấp.** Chỉ số WER công bố thường đo trên giọng đọc chuẩn, môi trường sạch. Điều kiện thực tế của B.Collection khác hẳn:

| Yếu tố | Vì sao quan trọng |
|---|---|
| **Giọng vùng miền** | Khách hàng thu hồi nợ phân bố toàn quốc; WER giọng miền Trung thường cao hơn đáng kể |
| **Chất lượng đường truyền** | Điện thoại 8kHz, nhiễu nền, khách hàng đang ở ngoài đường |
| **Từ vựng chuyên ngành** | "dư nợ gốc", "lãi phạt quá hạn", "tài sản bảo đảm", "cơ cấu lại thời hạn trả nợ" |
| **Số và ngày** | Sai một chữ số trong "trả 5 triệu ngày 15" là sai toàn bộ fact |
| **Nói chồng lấn** | Rất phổ biến trong cuộc gọi thu hồi |

**Quy trình đánh giá đề xuất:** lấy 200 cuộc gọi thật đại diện theo vùng miền và bucket, chép lời thủ công làm chuẩn vàng, đo WER tổng thể **và WER riêng trên số/ngày/tên riêng**. Chỉ số quyết định không phải WER trung bình mà là **độ chính xác trích xuất fact** — vì đó mới là thứ hệ thống dùng.

### 3.4 Trích xuất có cấu trúc

Dùng LLM tiếng Việt tự host với đầu ra ràng buộc schema:

```python
class CallExtraction(BaseModel):
    ptp: PTPCandidate | None          # amount, date, confidence
    root_cause: RootCauseEnum | None
    root_cause_evidence_span: str | None   # trích đoạn để cán bộ đối chiếu
    new_contact_points: list[ContactCandidate]
    objection_type: ObjectionEnum | None
    signals: list[SignalEnum]          # xem Mục 4
    compliance_flags: list[str]        # xem Mục 6
    extraction_confidence: float
```

**`root_cause_evidence_span` là trường quan trọng nhất về mặt UX.** Chip xác nhận hiển thị kèm trích đoạn nguyên văn: *"Nguyên nhân: lệch kỳ dòng tiền — «lương em về ngày mùng 10 mà kỳ trả nợ mùng 5»"*. Cán bộ đối chiếu trong 1 giây thay vì phải nhớ lại cuộc gọi. Không có trường này, tỷ lệ xác nhận sai sẽ cao và cán bộ sẽ mất tin tưởng vào gợi ý.

---

## 4. Về "sentiment analysis" — nên thiết kế khác đi

Đây là chỗ tôi khuyên điều chỉnh cách đặt vấn đề.

### 4.1 Vì sao sentiment thuần túy gần như vô dụng ở đây

Phân loại tích cực/tiêu cực/trung tính không mang thông tin hành động trong bối cảnh thu hồi nợ:

- Gần như **mọi** cuộc gọi thu hồi đều "tiêu cực" — không ai vui khi bị đòi nợ. Chỉ số này bão hòa và không phân biệt được gì.
- Khách hàng **tức giận** có thể là người sắp trả (đang bức xúc vì vướng thủ tục) hoặc người sắp khiếu nại. Cùng một nhãn, hai hành động ngược nhau.
- Khách hàng **lịch sự, dễ chịu** thường là người khất nợ chuyên nghiệp. Sentiment tích cực ở đây là tín hiệu xấu.

### 4.2 Thay bằng phân loại tín hiệu theo ý định

Đề xuất thay `sentiment_score` bằng một tập nhãn có ý nghĩa hành động:

| Nhóm | Nhãn | Hành động hệ thống |
|---|---|---|
| **Cam kết** | `PTP_EXPLICIT`, `PTP_VAGUE`, `PTP_REFUSED` | Tạo PTP hoặc leo thang |
| **Khó khăn** | `HARDSHIP_DISCLOSED`, `INCOME_LOSS_MENTIONED` | Kích hoạt luồng khoan dung |
| **Phản đối** | `AMOUNT_DISPUTED`, `FEE_DISPUTED`, `NOT_MY_DEBT`, `ALREADY_PAID` | `DISPUTE_HOLD` — Guardrail G08 |
| **Dễ tổn thương** | `VULNERABILITY_SIGNAL` | Chuyển bộ phận chuyên trách, khóa treatment cứng |
| **Pháp lý** | `LEGAL_COUNSEL_MENTIONED`, `THREAT_TO_COMPLAIN`, `MEDIA_THREAT` | Leo thang ngay |
| **Né tránh** | `AVOIDANCE_PATTERN`, `WRONG_PARTY_CLAIM` | Cập nhật `contactability` |
| **Kênh** | `PREFERRED_CHANNEL_STATED`, `DO_NOT_CALL_REQUESTED` | **`DNC_REQUEST` — Guardrail G03** |

`DO_NOT_CALL_REQUESTED` là nhãn có giá trị pháp lý cao nhất trong danh sách: nếu khách hàng yêu cầu ngừng liên hệ trong cuộc gọi mà cán bộ quên ghi nhận, hệ thống tiếp tục gọi và tạo ra vi phạm. Tự động phát hiện nhãn này rồi buộc cán bộ xác nhận là biện pháp phòng vệ rất rẻ.

**Nếu vẫn muốn giữ một chỉ số cảm xúc**, dùng nó như *một feature yếu trong nhiều feature*, không phải chỉ số hiển thị cho cán bộ, và tuyệt đối **không đưa vào Persona như thuộc tính của khách hàng** — điều đó vi phạm nguyên tắc P4 (Persona mô tả tình huống nợ, không mô tả con người).

### 4.3 Cảnh báo về phân tích cảm xúc từ giọng nói

Phân tích cảm xúc dựa trên đặc trưng âm học (cao độ, tốc độ, năng lượng) — khác với phân tích từ nội dung — có ba vấn đề:

1. **Độ tin cậy thấp và thiên lệch theo văn hóa.** Các mô hình này thường huấn luyện trên dữ liệu phương Tây và hoạt động kém với cách biểu đạt cảm xúc trong tiếng Việt.
2. **Rủi ro pháp lý.** Suy luận trạng thái cảm xúc của một người là tạo ra dữ liệu mới về họ mà họ không cung cấp — cần cơ sở pháp lý riêng và nằm trong phạm vi DPIA.
3. **Rủi ro sử dụng sai.** Một điểm số "khách hàng đang lo lắng" rất dễ bị dùng như một đòn bẩy gây áp lực, mà đó chính là điều danh mục `negotiation_lever` đã cấm.

**Khuyến nghị: không triển khai phân tích cảm xúc từ âm học.** Phân tích từ nội dung lời nói (Mục 4.2) cho thông tin hữu ích hơn, giải thích được, và không tạo ra ba rủi ro trên.

---

## 5. Ghi âm và pháp lý — giọng nói là dữ liệu sinh trắc học

Điểm này phải xử lý ngay từ thiết kế, không phải bổ sung sau.

Theo Luật BVDLCN 91/2025 và NĐ 356/2025, dữ liệu sinh trắc học thuộc nhóm được bảo vệ nghiêm ngặt hơn, và **bản ghi âm giọng nói có thể thuộc nhóm này**. Nghị định 356 quy định với dữ liệu vị trí và sinh trắc học, ngoài thông báo cho cơ quan chức năng khi có vi phạm, còn phải thông báo cho chủ thể dữ liệu trong 72 giờ kể từ khi phát hiện, và hồ sơ vi phạm lưu tối thiểu 5 năm.

**Yêu cầu thiết kế:**

| Hạng mục | Yêu cầu |
|---|---|
| Thông báo ghi âm | Câu thông báo ở đầu mỗi cuộc gọi; ghi nhận thời điểm thông báo vào metadata |
| Cơ sở pháp lý | Xác định rõ trong DPIA — ghi âm phục vụ mục đích gì (chất lượng dịch vụ, giải quyết tranh chấp, tuân thủ) |
| Giới hạn mục đích | Bản ghi âm dùng cho thu hồi nợ **không** tự động dùng được cho marketing hay huấn luyện mô hình khác |
| Thời hạn lưu | Đặt TTL rõ ràng; xóa tự động khi hết hạn 🔶 (Pháp chế xác định số tháng) |
| Kiểm soát truy cập | RBAC chặt; mọi lượt nghe lại đều ghi audit kèm `case_id` và lý do |
| Quy trình vi phạm | Cơ chế thông báo 72 giờ phải sẵn sàng và được diễn tập |
| Huấn luyện mô hình | Nếu dùng bản ghi để tinh chỉnh ASR, cần cơ sở pháp lý riêng — 🔶 xác nhận với DPO |

Hạng mục cuối hay bị bỏ qua: tinh chỉnh mô hình ASR trên dữ liệu cuộc gọi khách hàng là một mục đích xử lý mới, không nằm trong mục đích "thu hồi nợ".

---

## 6. QA tuân thủ tự động — giá trị lớn nhất, thường bị xếp cuối

Khi đã có pipeline ASR, việc rà **100%** cuộc gọi để tìm vi phạm quy tắc ứng xử gần như miễn phí. So với cách lấy mẫu 2% thủ công, đây là bước nhảy về năng lực kiểm soát.

| Nhóm phát hiện | Ví dụ |
|---|---|
| Ngôn ngữ đe dọa, xúc phạm | Từ điển + phân loại |
| Tuyên bố pháp lý sai | "sẽ bị bắt", "truy tố hình sự" với nợ dân sự |
| Tiết lộ khoản nợ cho bên thứ ba | Nói về khoản nợ khi người nghe không phải bên có nghĩa vụ |
| Bỏ qua yêu cầu DNC | Khách hàng yêu cầu ngừng, cán bộ tiếp tục |
| Không thông báo ghi âm | Thiếu câu thông báo đầu cuộc |
| Hứa hẹn ngoài thẩm quyền | Cam kết mức miễn giảm chưa được duyệt |

Tôi khuyến nghị **ưu tiên QA tuân thủ ngang với trích xuất fact** trong GĐ2. Lý do: trích xuất fact tạo ra hiệu quả kinh doanh, còn QA tuân thủ tạo ra bằng chứng phòng vệ — và bằng chứng phòng vệ là thứ mà một sự cố duy nhất có thể khiến giá trị của nó vượt xa toàn bộ lợi ích kinh doanh của dự án.

---

## 7. Thiết kế màn hình kết thúc cuộc gọi

```
┌────────────────────────────────────────────────────────────┐
│ Kết thúc cuộc gọi · Nguyễn Văn A · C-2026-88213 · 03:34    │
├────────────────────────────────────────────────────────────┤
│ Kết quả:  [●Gặp đúng người] [ Sai người] [ Từ chối] [ Khác]│
├────────────────────────────────────────────────────────────┤
│ HỆ THỐNG GHI NHẬN ĐƯỢC — xác nhận giúp:                    │
│                                                            │
│  ✓ Cam kết trả 5.000.000đ ngày 12/09          [Đúng][Sửa] │
│    «em hứa mùng 12 lương về em trả năm triệu»              │
│                                                            │
│  ✓ Nguyên nhân: lệch kỳ dòng tiền              [Đúng][Sửa] │
│    «lương em về ngày mùng 10 mà kỳ trả nợ mùng 5»          │
│                                                            │
│  ✓ Số điện thoại mới 09xx xxx 456              [Đúng][Bỏ]  │
│                                                            │
│  ⚠ Khách hàng nhắc tới khó khăn tài chính      [Đúng][Bỏ]  │
│    → nếu xác nhận, hệ thống sẽ chào phương án cơ cấu       │
├────────────────────────────────────────────────────────────┤
│ Ghi chú thêm (không bắt buộc)              [ ...        ]  │
├────────────────────────────────────────────────────────────┤
│                        [Lưu và sang case tiếp theo]        │
└────────────────────────────────────────────────────────────┘
```

**Bốn nguyên tắc UX:**
1. **Mặc định là đã chọn.** Nút [Đúng] được chọn sẵn; cán bộ chỉ can thiệp khi sai. Nếu bắt bấm [Đúng] cho từng mục, ta lại tạo ra công việc.
2. **Luôn kèm trích đoạn nguyên văn.** Đối chiếu 1 giây, không phải nhớ lại.
3. **Ghi chú tự do đặt cuối và ghi rõ không bắt buộc.**
4. **Một nút kết thúc.** Không có "Lưu nháp", không có nhiều bước.

---

## 8. Lộ trình — nhất quán với phạm vi MVP

Tài liệu Tech Stack đã loại LLM và ASR khỏi MVP. Giữ nguyên quyết định đó, nhưng làm rõ MVP vẫn thu được rất nhiều tín hiệu.

### MVP (không có ASR, không có LLM)
- **Toàn bộ tín hiệu Bậc 1** — đây là phần lớn giá trị và không cần AI
- Link có token trong SMS/ZNS để đo phản ứng
- Event tracking trên portal tự phục vụ (gồm tín hiệu "bỏ dở mô phỏng cơ cấu")
- Màn hình wrap-up với enum có gợi ý từ **quy tắc**, không phải từ LLM (ví dụ: nếu khách hàng vừa xem màn hình cơ cấu trên app, gợi ý sẵn `root_cause = CASHFLOW_TIMING`)
- Ghi âm cuộc gọi + lưu trữ có kiểm soát — **bắt đầu tích lũy dữ liệu cho GĐ2**

> Việc bật ghi âm và lưu trữ đúng chuẩn ngay từ MVP là quan trọng, kể cả khi chưa phân tích. Dữ liệu không thu thập được hồi tố, và GĐ2 cần một kho ghi âm đủ lớn để tinh chỉnh và đánh giá ASR.

### GĐ2 — pipeline ASR
1. Benchmark 3–4 phương án ASR trên 200 cuộc gọi thật (Mục 3.3)
2. QA tuân thủ tự động **trước** trích xuất fact — dễ hơn về kỹ thuật, giá trị phòng vệ cao hơn
3. Trích xuất fact có cấu trúc + chip xác nhận
4. Phân loại tín hiệu theo ý định (Mục 4.2)

### GĐ3
Gợi ý thời gian thực trong cuộc gọi (Collector Copilot), phân tích ghép cặp cán bộ–khách hàng (ML12).

---

## 9. Chỉ số đo chính hệ thống thu nhận

| Chỉ số | Mục tiêu |
|---|---|
| Thời gian wrap-up trung bình | ≤ 15 giây |
| % tương tác có kết quả cấu trúc | > 95% |
| % fact đến từ Bậc 1–2 | > 85% |
| Tỷ lệ chip gợi ý bị sửa | **10–25%** — xem ghi chú |
| Độ trễ pipeline ASR | p95 ≤ 30 giây |
| WER trên số và ngày | < 5% |
| % cuộc gọi được QA tự động | 100% |
| Tỷ lệ dùng ghi chú tự do | < 20% (thấp là tốt) |

**Về "tỷ lệ chip bị sửa":** cả quá cao lẫn quá thấp đều là vấn đề. Trên 30% nghĩa là mô hình trích xuất kém, cán bộ sẽ mất niềm tin và bắt đầu bấm [Đúng] cho mọi thứ mà không đọc. Dưới 5% nhiều khả năng nghĩa là cán bộ **đang bấm [Đúng] không đọc** — nguy hiểm hơn, vì dữ liệu sai được đóng dấu xác nhận của con người. Cần theo dõi phân bố theo cán bộ và đối chiếu mẫu.

---

## 10. Việc cần quyết

| # | Câu hỏi | Chủ trì | Hạn |
|---|---|---|---|
| 1 | Hệ thống tổng đài hiện tại có ghi âm tách 2 kênh không? Có API lấy metadata cuộc gọi không? | CNTT | Tuần 3 |
| 2 | Portal tự phục vụ hiện có event tracking chưa? | CNTT | Tuần 3 |
| 3 | Cơ sở pháp lý và thời hạn lưu bản ghi âm | Pháp chế + DPO | Tháng 2 |
| 4 | Dùng bản ghi âm để tinh chỉnh ASR có được phép không? | DPO | Tháng 2 |
| 5 | Ngân sách GPU cho ASR on-premise (ước tính theo phút gọi/ngày) | CNTT | GĐ2 |
| 6 | Chuẩn bị bộ 200 cuộc gọi chép lời thủ công làm chuẩn vàng | PO + QA | GĐ2, trước benchmark |
| 7 | Xác nhận không triển khai phân tích cảm xúc từ âm học | PO + DPO | Tháng 2 |

Câu 1 quyết định độ phức tạp của toàn pipeline: nếu tổng đài ghi âm tách kênh sẵn, có thể bỏ bước diarization và tiết kiệm đáng kể chi phí cũng như sai số.

---

*Tài liệu thiết kế, phiên bản đề xuất. Danh sách công nghệ ASR là điểm khởi đầu để đánh giá, không phải khuyến nghị chọn sẵn; cần benchmark trên dữ liệu thực tế của BIDV.*
