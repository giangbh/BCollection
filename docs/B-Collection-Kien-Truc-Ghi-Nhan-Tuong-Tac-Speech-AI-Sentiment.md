# B.COLLECTION — KIẾN TRÚC TỰ ĐỘNG HÓA GHI NHẬN TƯƠNG TÁC (SPEECH AI & SENTIMENT INTELLIGENCE)
### Giải pháp Giảm 90% Thao tác Nhập tay của Chuyên viên, Phân tích Ghi âm, Bóc tách PTP & Đo lường Cảm xúc
**Dự án:** Hệ thống Quản lý & Tối ưu Thu hồi nợ B.Collection — BIDV  
**Tác giả:** Lead Enterprise Architect & Chief AI Scientist  
**Phiên bản:** v1.0 | **Ngày ban hành:** 02/09/2026

---

## 📑 MỤC LỤC
1. [Vấn đề của Việc Nhập tay Truyền thống (The Manual Input Pain-Points)](#1-vấn-đề-của-việc-nhập-tay-truyền-thống-the-manual-input-pain-points)
2. [Chiến lược 2 Trụ cột Tự động hóa: Kênh Thoại & Kênh Số](#2-chiến-lược-2-trụ-cột-tự-động-hóa-kênh-thoại--kênh-số)
3. [Kiến trúc Kỹ thuật Phân hệ Voice & Speech AI (Audio Processing Pipeline)](#3-kiến-trúc-kỹ-thuật-phân-hệ-voice--speech-ai-audio-processing-pipeline)
4. [Mô hình Bóc tách Thực thể (NER) & Trích xuất Cam kết PTP Tự động](#4-mô-hình-bóc-tách-thực-thể-ner--trích-xuất-cam-kết-ptp-tự-động)
5. [Thiết kế Phân tích Cảm xúc (Sentiment & Behavioral Drift)](#5-thiết-kế-phân-tích-cảm-xúc-sentiment--behavioral-drift)
6. [Trải nghiệm Collector Workspace: Rút ngắn Wrap-up Time từ 180s xuống 10s](#6-trải-nghiệm-collector-workspace-rút-ngắn-wrap-up-time-từ-180s-xuống-10s)
7. [Đề xuất Lựa chọn Giải pháp Công nghệ (Tech Stack Recommendation)](#7-đề-xuất-lựa-chọn-giải-pháp-công-nghệ-tech-stack-recommendation)

---

## 1. VẤN ĐỀ CỦA VIỆC NHẬP TAY TRUYỀN THỐNG (THE MANUAL INPUT PAIN-POINTS)

```
┌───────────────────────────────────────┬────────────────────────────────────────────────────────────────┐
│ Thực trạng Nhập tay Truyền thống      │ Hậu quả Nghiêm trọng đối với Ngân hàng                         │
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ **Thời gian Wrap-up quá dài (ACW)**   │ Chuyên viên mất 2–3 phút sau mỗi cuộc gọi để gõ text tóm tắt.  │
│                                       │ Với 80 cuộc gọi/ngày $\rightarrow$ mất 3–4 tiếng chỉ để gõ bàn phím!│
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ **Dữ liệu mang tính đối phó, sơ sài** │ Ghi chú thường rất ngắn: "KH hứa trả", "KH bận", hoặc copy-    │
│                                       │ paste hàng loạt, làm mất hoàn toàn ngữ cảnh sâu sắc của nợ.    │
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ **Bỏ sót các Rủi ro Pháp lý Đỏ**      │ Bỏ lọt các tín hiệu nguy hiểm: Khách dọa khiếu nại NHNN, dọa   │
│                                       │ tự tử, biến cố sức khỏe nặng, hoặc dấu hiệu lừa đảo công nghệ. │
├───────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ **Sai lệch Cam kết PTP**              │ Gõ nhầm số tiền hoặc ngày hẹn trả nợ $\rightarrow$ gửi tin nhắc sai,│
│                                       │ gây phản ứng gay gắt từ phía khách hàng.                       │
└───────────────────────────────────────┴────────────────────────────────────────────────────────────────┘
```

**MỤC TIÊU CỐT LÕI CỦA THIẾT KẾ MỚI:**  
Chuyển đổi từ cơ chế **"Chuyên viên tự nhớ và gõ lại"** sang cơ chế **"Hệ thống AI tự động nghe, tự bóc tách, tự điền 95% biểu mẫu; Chuyên viên chỉ kiểm tra 3 giây và bấm Xác nhận"**.

---

## 2. CHIẾN LƯỢC 2 TRỤ CỘT TỰ ĐỘNG HÓA: KÊNH THOẠI & KÊNH SỐ

Tương tác của khách hàng không chỉ có cuộc gọi thoại. Toàn bộ hành vi trên kênh số cũng phải được thu thập tự động mà không cần sự can thiệp của con người:

```
                                  ┌────────────────────────────────────────────────────────┐
                                  │       HỆ THỐNG THU THẬP TƯƠNG TÁC TỰ ĐỘNG ĐA KÊNH       │
                                  └────────────────────────────────────────────────────────┘
                                                              │
          ┌───────────────────────────────────────────────────┼───────────────────────────────────────────────────┐
          ▼                                                   ▼                                                   ▼
┌───────────────────────────────────┐       ┌───────────────────────────────────┐       ┌───────────────────────────────────┐
│ TRỤ CỘT 1: KÊNH THOẠI (SPEECH AI) │       │ TRỤ CỘT 2: KÊNH SỐ (DIGITAL EVENTS│       │ TRỤ CỘT 3: HỆ THỐNG CORE & TÀI SẢN│
├───────────────────────────────────┤       ├───────────────────────────────────┤       ├───────────────────────────────────┤
│ • Ghi âm 2 kênh độc lập (Stereo)  │       │ • Khách bấm link VietQR trên Zalo │       │ • Biến động số dư tài khoản Core  │
│ • Speech-to-Text tiếng Việt       │       │ • Khách mở tin nhắn SMS thông báo │       │ • Tần suất mở App SmartBanking    │
│ • Tự bóc tách PTP (Tiền & Ngày)   │       │ • Khách quét mã QR thanh toán     │       │ • Cập nhật tình trạng trả nợ CIC  │
│ • Tự phát hiện Nguyên nhân gốc    │       │ $\implies$ Tự động ghi nhận       │       │ $\implies$ Tự động đổi trạng thái │
│ • Phân tích Cảm xúc & Từ cấm      │       │    Engagement không cần gõ        │       │    CURED ngay khi tiền vào        │
└───────────────────────────────────┘       └───────────────────────────────────┘       └───────────────────────────────────┘
```

---

## 3. KIẾN TRÚC KỸ THUẬT PHÂN HỆ VOICE & SPEECH AI (AUDIO PROCESSING PIPELINE)

Để đảm bảo hiệu năng và bảo mật ngân hàng, quy trình xử lý cuộc gọi được thiết kế hoàn toàn bất đồng bộ (Asynchronous Event-Driven):

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                        KIẾN TRÚC LUỒNG XỬ LÝ SPEECH AI SAU CUỘC GỌI (POST-CALL PIPELINE)               │
└───────────────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                                    │
    1. CUỘC GỌI KẾT THÚC (Gác máy trên WebRTC Softphone)
    │
    ▼
┌───────────────────────────────────┐
│ SIP Telephony / FreeSWITCH Server │ ── Ghi âm 2 kênh riêng biệt: Kênh 0 (Collector) | Kênh 1 (Khách nợ)
└─────────────────┬─────────────────┘
                  │ Đẩy file `.wav` 16kHz vào hàng đợi Kafka: topic `call.recorded.raw`
                  ▼
┌───────────────────────────────────┐
│ Audio Pre-processing & Storage    │ ── Lưu an toàn vào On-Premise MinIO/Ceph (Mã hóa AES-256)
└─────────────────┬─────────────────┘
                  │
                  ▼
┌───────────────────────────────────┐
│ ASR Engine (Speech-to-Text)       │ ── Chuyển Audio thành Văn bản có gán nhãn người nói (Diarization)
│ (Fine-tuned Whisper / FPT.AI)     │    Độ trễ: 2–3 giây cho cuộc gọi 3 phút
└─────────────────┬─────────────────┘
                  │ Transcript JSON: `{"speaker": "DEBTOR", "text": "thứ 6 này em mới có lương trả 5 triệu"}`
                  ▼
┌───────────────────────────────────┐
│ NLP / Local LLM Intelligence Unit │ ── Chạy song song 4 mô hình:
│ (Qwen-2.5-7B / PhoBERT Fine-tuned)│    1. NER: Bóc tách Cam kết PTP (Số tiền, Ngày hẹn)
└─────────────────┬─────────────────┘    2. Root Cause Classifier: Gán 1 trong 13 nhóm nguyên nhân
                  │                      3. Sentiment Analyzer: Điểm cảm xúc & mức độ hợp tác
                  │                      4. Compliance Scanner: Cảnh báo vi phạm quy chế thu nợ
                  ▼
┌───────────────────────────────────┐
│ Auto-Fill Webhook to Workspace    │ ── Đẩy kết quả lên UI Collector Workspace (Trước khi màn hình bật lên!)
└───────────────────────────────────┘
```

---

## 4. MÔ HÌNH BÓC TÁCH THỰC THỂ (NER) & TRÍCH XUẤT CAM KẾT PTP TỰ ĐỘNG

Thay vì để Chuyên viên tự gõ số tiền và ngày hẹn, một mô hình **Named Entity Recognition (NER) & Contextual Parser** chuyên sâu cho tiếng Việt tài chính sẽ tự động bóc tách:

```
Ví dụ đoạn thoại của Khách hàng:
"Hiện tại em kẹt quá, phải chờ công ty chuyển lương. Thứ Sáu tuần này em sẽ chuyển khoản trước năm triệu nhé."
```

```json
{
  "ptp_detected": true,
  "ptp_entities": {
    "raw_amount_text": "năm triệu",
    "normalized_amount": 5000000,
    "raw_date_text": "Thứ Sáu tuần này",
    "normalized_date": "2026-09-04",
    "payment_channel": "BANK_TRANSFER"
  },
  "root_cause_detected": {
    "primary": "CASHFLOW_TIMING",
    "confidence": 4,
    "keyword_triggers": ["chờ công ty chuyển lương", "kẹt quá"]
  },
  "extraction_confidence": 0.94
}
```

---

## 5. THIẾT KẾ PHÂN TÍCH CẢM XÚC (SENTIMENT & BEHAVIORAL DRIFT)

### 5.1 Đo lường Sự Dịch chuyển Cảm xúc (Emotional Drift)
Trong nghiệp vụ thu nợ, cảm xúc quan trọng nhất không phải là "Vui/Buồn", mà là **"Mức độ Cởi mở & Hợp tác (Cooperative Index)"** và **"Sự thay đổi tâm lý từ đầu đến cuối cuộc gọi"**:

$$\Delta \text{Sentiment} = \text{Sentiment}_{\text{Cuối cuộc gọi}} - \text{Sentiment}_{\text{Đầu cuộc gọi}}$$

```
                      CẢM XÚC CUỐI CUỘC GỌI
                                ▲
                                │   [CHUYỂN HÓA THÀNH CÔNG]
                                │   • Đầu cuộc gọi: Bực bội, phòng thủ.
                                │   • Cuối cuộc gọi: Thấu hiểu, đồng ý trả.
                                │   $\implies \Delta \text{Sentiment} > 0$
                                │   (Khen thưởng kỹ năng Chuyên viên)
                                │
  ──────────────────────────────┼──────────────────────────────► CẢM XÚC ĐẦU CUỘC GỌI
                                │
    [LEO THANG XUNG ĐỘT]        │
    • Đầu cuộc gọi: Bình thường │
    • Cuối cuộc gọi: Đe dọa kiện│
    $\implies \Delta \text{Sentiment} < 0$
    (Tự động cảnh báo QA/Trưởng phòng)
                                │
                                ▼
```

### 5.2 Phát hiện Rủi ro Pháp lý & Vi phạm Tuân thủ (Compliance & Red Flags)
Hệ thống tự động quét transcript để phát hiện các tín hiệu nguy hiểm:
* **Từ khóa Dọa khiếu nại:** *"Tôi sẽ kiện ra tòa"*, *"Tôi sẽ gửi đơn lên Ngân hàng Nhà nước"*, *"Báo công an"*, *"Đăng mạng xã hội"*.
* **Từ khóa Y tế / Khủng hoảng:** *"Tôi đang xạ trị ung thư"*, *"Gia đình vừa có tang"*, *"Không muốn sống nữa"*.
  $\implies$ **Hệ thống tự động bật cờ đỏ (Red Flag) và khóa tạm thời các chiến dịch gọi tự động**.
* **Kiểm tra Chuyên viên:** Chuyên viên có xưng danh BIDV không? Có giải thích rõ khoản nợ không? Có dùng từ ngữ đe dọa không?

---

## 6. TRẢI NGHIỆM COLLECTOR WORKSPACE: RÚT NGẮN TỪ 180S XUỐNG 10S

Khi Chuyên viên bấm nút **[KẾT THÚC CUỘC GỌI]**, cửa sổ **Ghi nhận Kết quả (Call Wrap-up)** sẽ hiển thị với **TOÀN BỘ CÁC TRƯỜNG ĐÃ ĐƯỢC ĐIỀN TỰ ĐỘNG**:

```
┌────────────────────────────────────────────────────────────────────────┐
│ 📞 GHI NHẬN KẾT QUẢ CUỘC GỌI — [AI TỰ ĐỘNG ĐIỀN 95%]                   │
├────────────────────────────────────────────────────────────────────────┤
│ Trạng thái Cuộc gọi: [ ✅ HẸN THANH TOÁN (PTP AGREED)                ▼]│
│                                                                        │
│ 💰 Số tiền cam kết (VNĐ): [ 5,000,000      ] (AI trích xuất: "năm triệu")│
│ 📅 Ngày hẹn thanh toán:   [ 04/09/2026     ] (AI quy đổi: "thứ 6 tuần này")│
│                                                                        │
│ 🔍 Nguyên nhân chính:     [ CASHFLOW_TIMING: Chờ công ty chuyển lương ▼]│
│ 🎭 Cảm xúc cuộc gọi:      [ 🟢 HỢP TÁC (Tích cực hóa +0.45)           ]│
│                                                                        │
│ 📝 Tóm tắt AI tự sinh:                                                 │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ "Khách hàng xác nhận nợ thẻ tín dụng. Hiện đang chờ lương công ty  │ │
│ │  vào ngày 04/09, cam kết sẽ thanh toán trước 5.000.000đ qua VietQR"│ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│         [ SỬA THỦ CÔNG ]               [ ✅ XÁC NHẬN & LƯU (3s) ]      │
└────────────────────────────────────────────────────────────────────────┘
```

> ⏱️ **KẾT QUẢ:** Chuyên viên chỉ mất **3 đến 5 giây để kiểm tra bằng mắt và bấm [Xác nhận]**. Năng suất cuộc gọi tăng vọt từ 60 cuộc/ngày lên **120–150 cuộc/ngày**!

---

## 7. ĐỀ XUẤT LỰA CHỌN GIẢI PHÁP CÔNG NGHỆ (TECH STACK)

Đối với một ngân hàng lớn như BIDV, **bảo mật dữ liệu âm thanh và bí mật ngân hàng là tối thượng** (Không được gửi file ghi âm cuộc gọi lên Cloud nước ngoài như OpenAI/Google Cloud).

```
┌──────────────────────────┬───────────────────────────────────────────┬─────────────────────────────────┐
│ Thành phần Hệ thống      │ Giải pháp Khuyến nghị (On-Premise)        │ Ưu điểm Nổi bật                 │
├──────────────────────────┼───────────────────────────────────────────┼─────────────────────────────────┤
│ **1. Tổng đài & Ghi âm** │ **FreeSWITCH / Kamailio + WebRTC**        │ Mã nguồn mở, cân 5.000 cuộc gọi │
│                          │                                           │ đồng thời, tách 2 kênh Stereo.  │
├──────────────────────────┼───────────────────────────────────────────┼─────────────────────────────────┤
│ **2. Speech-to-Text**    │ **Whisper Large-v3 (Fine-tuned Tiếng Việt)**│ Triển khai trên cụm GPU nội bộ  │
│    *(ASR Engine)*        │ hoặc **FPT.AI / Viettel AI On-Premise**   │ Nhận diện tốt giọng Bắc-Trung-Nam│
├──────────────────────────┼───────────────────────────────────────────┼─────────────────────────────────┤
│ **3. NLP / LLM Trích xuất**│ **Qwen-2.5-7B-Instruct / Llama-3.1-8B**  │ Chạy qua vLLM / TensorRT-LLM,   │
│    *(NLU Unit)*          │ (Fine-tuned tập dữ liệu tài chính Việt)   │ Tốc độ sinh 80 tokens/giây.     │
├──────────────────────────┼───────────────────────────────────────────┼─────────────────────────────────┤
│ **4. Lưu trữ File Âm thanh**│ **MinIO S3 Compatible Object Storage**   │ Lưu trữ phân tán On-premise,    │
│                          │ (Mã hóa tại chỗ AES-256)                  │ Chi phí thấp, lưu trữ 5 năm.    │
├──────────────────────────┼───────────────────────────────────────────┼─────────────────────────────────┤
│ **5. Hàng đợi Xử lý**    │ **Apache Kafka + Redis Streams**          │ Đảm bảo không nghẽn/mất gói ghi │
│                          │                                           │ âm khi có đợt gọi cao điểm.     │
└──────────────────────────┴───────────────────────────────────────────┴─────────────────────────────────┘
```

---

## 🚀 8. KẾ HOẠCH TRIỂN KHAI 2 PHA CHO BIDV

1. **Pha 1 (Pilot MVP - 2 Tháng):**
   * Triển khai mô hình **Whisper Fine-tuned** chuyển audio thành text sau cuộc gọi.
   * Dùng Rule-based Regex + NLP cơ bản để tự trích xuất số tiền và ngày hẹn PTP.
   * Đo lường: Rút ngắn thời gian Wrap-up từ 180s xuống **30s**.
2. **Pha 2 (Toàn hàng - Scale Production):**
   * Triển khai cụm **Local LLM 7B/8B On-premise** để tóm tắt hội thoại tự động, chấm điểm cảm xúc (Sentiment) và phát hiện từ cấm tuân thủ thời gian thực.
   * Tích hợp Webhook kênh số (Zalo/VietQR/SmartBanking) đồng bộ tức thì vào Persona 360.
   * Thời gian Wrap-up giảm tối đa còn **10s**!
