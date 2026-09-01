# B.COLLECTION — ĐẶC TẢ THIẾT KẾ PHƯƠNG PHÁP XÁC ĐỊNH NGUYÊN NHÂN GỐC CỦA NỢ (ROOT CAUSE IDENTIFICATION BLUEPRINT)
### Cơ chế 3 Tầng Tích hợp (3-Tier Engine): Suy luận Số liệu (Pre-call), Xử lý Hội thoại (Speech AI), & Xác thực Thủ công (Manual Enrichment)
**Dự án:** Hệ thống Quản lý & Tối ưu Thu hồi nợ B.Collection — BIDV  
**Tác giả:** Lead Enterprise Architect & Chief Data Scientist  
**Phiên bản:** v1.0 | **Ngày ban hành:** 01/09/2026

---

## 📑 MỤC LỤC
1. [Bối cảnh & Tầm quan trọng của Nguyên nhân Gốc trong Thu hồi Nợ Hiện đại](#1-bối-cảnh--tầm-quan-trọng-của-nguyên-nhân-gốc-trong-thu-hồi-nợ-hiện-đại)
2. [Danh mục Đóng 13 Nhóm Nguyên nhân Gốc Chuẩn hóa (13 Canonical Enums)](#2-danh-mục-đóng-13-nhóm-nguyên-nhân-gốc-chuẩn-hóa-13-canonical-enums)
3. [Kiến trúc Tổng thể Cơ chế 3 Tầng Xác định Nguyên nhân](#3-kiến-trúc-tổng-thể-cơ-chế-3-tầng-xác-định-nguyên-nhân)
4. [TẦNG 1: Suy luận Tự động từ Số liệu Định lượng (Pre-Call Data Inference)](#4-tầng-1-suy-luận-tự-động-từ-số-liệu-định-lượng-pre-call-data-inference)
5. [TẦNG 2: Phân tích Hội thoại & Nhận diện Ý định qua Speech AI (Post-Call NLP Analytics)](#5-tầng-2-phân-tích-hội-thoại--nhận-diện-ý-định-qua-speech-ai-post-call-nlp-analytics)
6. [TẦNG 3: Xác thực & Làm giàu Dữ liệu Nhập tay bởi Chuyên viên (Manual Enrichment)](#6-tầng-3-xác-thực--làm-giàu-dữ-liệu-nhập-tay-bởi-chuyên-viên-manual-enrichment)
7. [Kiểm soát Pháp lý, Bộ lọc Cấm & Cơ chế Bán rã Độ tin cậy (Half-Life Decay)](#7-kiểm-soát-pháp-lý-bộ-lọc-cấm--cơ-chế-bán-rã-độ-tin-cậy-half-life-decay)
8. [Ánh xạ Ma trận: Nguyên nhân Gốc $\rightarrow$ Đòn bẩy & Kịch bản Hành động Tối ưu](#8-ánh-xạ-ma-trận-nguyên-nhân-gốc--đòn-bẩy--kịch-bản-hành-động-tối-ưu)

---

## 1. BỐI CẢNH & TẦM QUAN TRỌNG CỦA NGUYÊN NHÂN GỐC TRONG THU HỒI NỢ HIỆN ĐẠI

Trong cách tiếp cận thu nợ truyền thống, mọi khách hàng quá hạn đều bị đối xử như nhau bằng các cuộc gọi nhắc nợ dồn dập. Điều này dẫn tới:
* Khách hàng tốt bị ức chế, dẫn tới khiếu nại hoặc mất lòng tin vào thương hiệu ngân hàng.
* Khách hàng thực sự khó khăn bị đẩy vào ngõ cụt thay vì được tư vấn phương án giãn nợ/miễn giảm lãi phù hợp.
* Chi phí vận hành cuộc gọi tăng cao nhưng tỷ lệ thu hồi (*Cure Rate*) không cải thiện.

**Triết lý của B.Collection:**  
*"Chữa bệnh phải chữa từ gốc. Tìm đúng nguyên nhân khách hàng chưa trả nợ là chìa khóa để lựa chọn đúng kênh liên lạc, đúng khung giờ và đúng đòn bẩy đàm phán hợp pháp."*

---

## 2. DANH MỤC ĐÓNG 13 NHÓM NGUYÊN NHÂN GỐC CHUẨN HÓA (13 CANONICAL ENUMS)

Hệ thống quản lý nguyên nhân nợ theo danh mục đóng 13 loại, loại bỏ hoàn toàn các ghi chú tự do không có cấu trúc:

```
┌────┬──────────────────────────┬──────────────────────────────────────────────────────────────────┬─────────────────────────────┐
│ STT│ Mã Nguyên nhân Gốc       │ Bản chất Tình huống Nợ                                           │ Dấu hiệu Nhận biết Cốt lõi  │
├────┼──────────────────────────┼──────────────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 1  │ `FORGOT_OR_ADMIN`        │ Quên hạn thanh toán, lỗi app chuyển tiền, sai số tài khoản.      │ DPD 1–5, CASA cao, lịch sử  │
│    │                          │                                                                  │ 12 tháng trả rất đúng hạn.  │
├────┼──────────────────────────┼──────────────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 2  │ `CASHFLOW_TIMING`        │ Có tiền nhưng lệch chu kỳ: Ngày nhận lương/công nợ sau ngày đến  │ Core Inflow về ngày 10–14,  │
│    │                          │ hạn thanh toán của ngân hàng.                                    │ kỳ trả nợ là ngày 05.       │
├────┼──────────────────────────┼──────────────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 3  │ `INCOME_LOSS`            │ Mất việc làm, giảm biên chế, lương bị cắt giảm tạm thời.         │ Inflow Core giảm >50%,      │
│    │                          │                                                                  │ không còn giao dịch trả lương│
├────┼──────────────────────────┼──────────────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 4  │ `BUSINESS_DOWNTURN`      │ Hộ kinh doanh/Doanh nghiệp chậm thu hồi công nợ, đọng hàng tồn.  │ Doanh số POS/QR giảm,       │
│    │                          │                                                                  │ chu kỳ quay vòng vốn kéo dài│
├────┼──────────────────────────┼──────────────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 5  │ `OVER_INDEBTED`          │ Vay nhiều nơi, mất cân đối gánh nặng nợ (DSR > 70%).             │ CIC báo có nợ tại ≥3 TCTD,  │
│    │                          │                                                                  │ dư nợ tín chấp tăng vọt.    │
├────┼──────────────────────────┼──────────────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 6  │ `DISPUTE`                │ Tranh chấp về số dư nợ, lãi suất, phí phạt hoặc phí bảo hiểm.    │ Khách khiếu nại lên Hotline,│
│    │                          │                                                                  │ từ chối thanh toán để tra soát│
├────┼──────────────────────────┼──────────────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 7  │ `FRAUD_VICTIM`           │ Khách hàng bị lừa đảo công nghệ cao, bị thao túng chiếm đoạt tiền│ Có biên bản trình báo công  │
│    │                          │                                                                  │ an, tài khoản bị rút sạch.  │
├────┼──────────────────────────┼──────────────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 8  │ `HEALTH_OR_FAMILY_EVENT` │ Biến cố sức khỏe/gia đình đột xuất (Chỉ lưu nhãn, không lưu bệnh)│ Chi tiêu y tế đột biến,     │
│    │                          │                                                                  │ cần luồng hỗ trợ an sinh.   │
├────┼──────────────────────────┼──────────────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 9  │ `FORCE_MAJEURE`          │ Thiên tai, bão lũ, hỏa hoạn, dịch bệnh bất khả kháng.            │ Địa bàn nằm trong vùng công │
│    │                          │                                                                  │ bố thiên tai của Chính phủ. │
├────┼──────────────────────────┼──────────────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 10 │ `COLLATERAL_ISSUE`       │ Vướng mắc tranh chấp pháp lý tài sản thế chấp (nhà đất, xe ô tô) │ Tranh chấp quyền sở hữu,    │
│    │                          │                                                                  │ tài sản bị cơ quan khác phong tỏa│
├────┼──────────────────────────┼──────────────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 11 │ `WILFUL_DEFAULT`         │ Có khả năng trả nhưng cố tình chây ỳ, né tránh trả nợ BIDV.      │ Đang trả đều các bank khác  │
│    │                          │ *(Bắt buộc bằng chứng định lượng & duyệt 4 mắt)*                 │ nhưng chặn số né tránh BIDV.│
├────┼──────────────────────────┼──────────────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 12 │ `UNREACHABLE`            │ Mất liên lạc hoàn toàn, tất cả các số điện thoại đều thuê bao.   │ 0 RPC trong 60 ngày dù gọi  │
│    │                          │                                                                  │ ≥ 8 lần qua tất cả các kênh.│
├────┼──────────────────────────┼──────────────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 13 │ `UNKNOWN`                │ Chưa đủ dữ liệu để kết luận nguyên nhân.                         │ Hồ sơ mới phát sinh quá hạn.│
└────┴──────────────────────────┴──────────────────────────────────────────────────────────────────┴─────────────────────────────┘
```

---

## 3. KIẾN TRÚC TỔNG THỂ CƠ CHẾ 3 TẦNG XÁC ĐỊNH NGUYÊN NHÂN

```
                                  ┌────────────────────────────────────────────────────────┐
                                  │      CƠ CHẾ 3 TẦNG XÁC ĐỊNH NGUYÊN NHÂN GỐC CỦA NỢ     │
                                  └────────────────────────────────────────────────────────┘
                                                              │
          ┌───────────────────────────────────────────────────┼───────────────────────────────────────────────────┐
          ▼                                                   ▼                                                   ▼
┌───────────────────────────────────┐       ┌───────────────────────────────────┐       ┌───────────────────────────────────┐
│ TẦNG 1: SUY LUẬN TỰ ĐỘNG TỪ SỐ LIỆU│      │ TẦNG 2: PHÂN TÍCH HỘI THOẠI NLP   │       │ TẦNG 3: CHUYÊN VIÊN XÁC NHẬN      │
│ (PRE-CALL DATA INFERENCE)         │       │ (POST-CALL SPEECH ANALYTICS)      │       │ (STRUCTURED MANUAL ENRICHMENT)    │
├───────────────────────────────────┤       ├───────────────────────────────────┤       ├───────────────────────────────────┤
│ • Dòng tiền Core Banking (Lương)  │       │ • Speech-to-Text cuộc gọi         │       │ • Collector chọn Fact danh mục đóng│
│ • Báo cáo CIC toàn ngành          │       │ • Nhận diện ý định & từ khóa      │       │ • Đánh giá độ tin cậy (1–5)       │
│ • Lịch sử trả nợ & số dư CASA     │       │ • Phát hiện khiếu nại / biến cố   │       │ • Bắt buộc duyệt 4 mắt với nhãn   │
│ • Độ trễ DPD & Loại sản phẩm      │       │ • Tự động gợi ý Root Cause        │       │   nặng (WILFUL_DEFAULT)           │
└───────────────────────────────────┘       └───────────────────────────────────┘       └───────────────────────────────────┘
```

---

## 4. TẦNG 1: SUY LUẬN TỰ ĐỘNG TỪ SỐ LIỆU ĐỊNH LƯỢNG (PRE-CALL DATA INFERENCE)

Hàng đêm, luồng xử lý dữ liệu tự động (*dbt & Rule Engine*) quét qua các nguồn dữ liệu lớn để gán nhãn sơ bộ:

```
                  ┌─────────────────────────────────────────────────────────┐
                  │          LUỒNG SUY LUẬN DỮ LIỆU ĐỊNH LƯỢNG TẦNG 1       │
                  └─────────────────────────────────────────────────────────┘
                                               │
       ┌───────────────────────────────┬───────┴───────────────────────┬───────────────────────────────┐
       ▼                               ▼                               ▼                               ▼
┌───────────────────────────────┐┌───────────────────────────────┐┌───────────────────────────────┐┌───────────────────────────────┐
│ 1. DÒNG TIỀN CORE BANKING     ││ 2. TÍN HIỆU CIC TOÀN NGÀNH    ││ 3. DƯ ĐỊA SỐ DƯ TIẾT KIỆM/CASA││ 4. LỊCH SỬ DPD & SẢN PHẨM     │
│ • Ngày lương > Ngày hạn nợ    ││ • Trả bank khác, nợ BIDV      ││ • Số dư CASA > 2x Nghĩa vụ   ││ • DPD 1–5 + Thẻ tín dụng      │
│ $\implies$ `CASHFLOW_TIMING`  ││   $\implies$ `WILFUL_DEFAULT` ││   $\implies$ `FORGOT_OR_ADMIN`││   $\implies$ `FORGOT_OR_ADMIN`│
│ • Inflow giảm >50%            ││ • Mở mới ≥3 thẻ, DTI > 70%   ││ • Số dư = 0 liên tục 3 tháng ││ • DPD 11–18 + Vay thế chấp   │
│   $\implies$ `INCOME_LOSS`    ││   $\implies$ `OVER_INDEBTED`  ││   $\implies$ `INCOME_LOSS`    ││   $\implies$ `BUSINESS_DOWNTURN│
└───────────────────────────────┘└───────────────────────────────┘└───────────────────────────────┘└───────────────────────────────┘
```

### Chi tiết Quy tắc Suy luận:
1. **Phân tích Dòng tiền Lương (Core Banking Flow):**
   * *Thuật toán:* Trích xuất các giao dịch ghi có tài khoản có nội dung `LUONG`, `SALARY`, `PAYROLL` hoặc nguồn tiền từ tài khoản tổ chức.
   * *Quy tắc:* Nếu $Day(\text{Lương}) > Day(\text{Hạn nợ})$ $\implies$ Tự động gán `CASHFLOW_TIMING` với độ tin cậy $Confidence = 4$.
2. **Phân tích Tín hiệu CIC Chéo (Cross-Bank CIC Signals):**
   * *Quy tắc 1 (Cố tình chây ỳ):* Khách hàng có lịch sử trả nợ đầy đủ, không quá hạn tại Ngân hàng A, Ngân hàng B trong 3 tháng qua, nhưng lại để quá hạn nhóm B1 tại BIDV $\implies$ Gợi ý cờ nghi vấn `WILFUL_DEFAULT` (Tín hiệu chọn lọc ưu tiên).
   * *Quy tắc 2 (Quá tải nợ):* Khách hàng mở thêm 3 thẻ tín dụng mới trong 6 tháng và tổng DTI $> 70\%$ $\implies$ Tự động gán `OVER_INDEBTED`.
3. **Phân tích Dư địa Tài chính & Số dư CASA:**
   * Khách hàng có số dư tiền gửi tiết kiệm hoặc tài khoản thanh toán $> 2 \times \text{Số tiền nợ gốc lãi}$ nhưng vẫn quá hạn DPD 1–3 ngày $\implies$ Tự động gán `FORGOT_OR_ADMIN`.

---

## 5. TẦNG 2: PHÂN TÍCH HỘI THOẠI & NHẬN DIỆN Ý ĐỊNH QUA SPEECH AI (POST-CALL NLP ANALYTICS)

Khi chuyên viên thực hiện cuộc gọi qua WebRTC Softphone, file ghi âm được chuyển thành văn bản (*Speech-to-Text bằng mô hình tiếng Việt chuyên biệt*) và chạy qua bộ trích xuất ngữ nghĩa:

```
                                  ┌────────────────────────────────────────────────────────┐
                                  │            LUỒNG XỬ LÝ SPEECH AI BẮT NGUYÊN NHÂN       │
                                  └────────────────────────────────────────────────────────┘
                                                              │
               ┌───────────────────────────────┼───────────────────────────────┐
               ▼                               ▼                               ▼
┌───────────────────────────────┐┌───────────────────────────────┐┌───────────────────────────────┐
│ 1. NHÓM TỪ KHÓA DÒNG TIỀN     ││ 2. NHÓM TỪ KHÓA MẤT VIỆC/KINH ││ 3. NHÓM TỪ KHÓA TRANH CHẤP/  │
│                               ││    DOANH SUY GIẢM             ││    LỪA ĐẢO                   │
├───────────────────────────────┤├───────────────────────────────┤├───────────────────────────────┤
│ • "Chờ lương về...",          ││ • "Công ty cắt giảm...",      ││ • "Phí này ở đâu ra?",        │
│ • "Công nợ khách chưa trả...",││ • "Đang thất nghiệp...",      ││ • "Tôi bị lừa đảo qua mạng",  │
│ • "Cuối tuần gom được tiền..."││ • "Hàng tồn không bán được..."││ • "Tôi yêu cầu tra soát..."   │
│ $\implies$ `CASHFLOW_TIMING`  ││ $\implies$ `INCOME_LOSS` /    ││ $\implies$ `DISPUTE` /        │
│                               ││            `BUSINESS_DOWNTURN`││            `FRAUD_VICTIM`     │
└───────────────────────────────┘└───────────────────────────────┘└───────────────────────────────┘
```

* **Cơ chế gợi ý tức thì:** Ngay khi cuộc gọi kết thúc, AI hiển thị nhãn đề xuất trên cửa sổ **Call Wrap-up**: *"Hệ thống nhận diện 85% nguyên nhân là LỆCH CHU KỲ LƯƠNG. Bạn có muốn lưu nhãn này?"*

---

## 6. TẦNG 3: XÁC THỰC & LÀM GIÀU DỮ LIỆU NHẬP TAY BỞI CHUYÊN VIÊN (MANUAL ENRICHMENT)

Chuyên viên thu hồi nợ trực tiếp xác nhận hoặc điều chỉnh nguyên nhân gốc sau cuộc trao đổi:

```python
# Cấu trúc dữ liệu Fact làm giàu thông tin nguyên nhân gốc
class RootCauseEnrichmentPayload(BaseModel):
    case_id: str
    debtor_cif: str
    primary_root_cause: RootCausePrimaryEnum
    confidence_score: int = Field(ge=1, le=5) # 1: Nghi vấn, 5: Đã xác thực giấy tờ
    evidence_type: str # "CALL_RECORDING", "INCOME_STATEMENT", "POLICE_REPORT"
    evidence_reference: str # Mã bản ghi âm / Số công văn
    collector_id: str
```

---

## 7. KIỂM SOÁT PHÁP LÝ, BỘ LỌC CẤM & CƠ CHẾ BÁN RÃ ĐỘ TIN CẬY (HALF-LIFE DECAY)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🔒 CÁC NGUYÊN TẮC BẢO VỆ PHÁP LÝ & ĐẠO ĐỨC (COMPLIANCE ENFORCEMENT)                                   │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. **Bộ Lọc Cấm (Content Filter Regex):** Tuyệt đối CHẶN các ghi chú chứa thông tin bệnh án cụ thể    │
│    (ung thư, tai nạn, HIV...), chỉ cho phép chọn nhãn bao quát `HEALTH_OR_FAMILY_EVENT`.              │
│ 2. **Kiểm Soát 4 Mắt Cho `WILFUL_DEFAULT`:** Nhãn "Cố tình chây ỳ" ảnh hưởng đến hồ sơ pháp lý của   │
│    khách hàng nên bắt buộc phải đính kèm bằng chứng (Evidence Link) và được Trưởng nhóm phê duyệt.     │
│ 3. **Cơ Chế Bán Rã (Half-Life Decay):** Nguyên nhân nợ không có giá trị vĩnh viễn. Sau 120–270 ngày,  │
│    độ tin cậy của nhãn sẽ tự động giảm 50% nếu không có sự kiện mới xác thực lại:                      │
│    $$\text{Effective\_Confidence}(t) = \text{Initial\_Confidence} \cdot (0.5)^{\frac{\Delta t}{T_{1/2}}}$$│
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 8. ÁNH XẠ MA TRẬN: NGUYÊN NHÂN GỐC $\rightarrow$ ĐÒN BẨY & KỊCH BẢN HÀNH ĐỘNG TỐI ƯU

| Nguyên nhân gốc xác định | Kênh ưu tiên | Kịch bản & Đòn bẩy đàm phán tối ưu |
|:---|:---|:---|
| **`FORGOT_OR_ADMIN`** | Zalo / SMS | Gửi link thanh toán nhanh **VietQR**, không cần gọi điện làm phiền. |
| **`CASHFLOW_TIMING`** | Softphone | Chốt cam kết **PTP vào đúng ngày nhận lương**; đề xuất đổi ngày trả nợ. |
| **`INCOME_LOSS` / `BUSINESS_DOWNTURN`** | Softphone | Tư vấn chính sách **miễn giảm 30%–50% lãi phạt** hoặc cơ cấu giãn kỳ hạn. |
| **`OVER_INDEBTED`** | Softphone | Cảnh báo **nguy cơ nhảy nhóm nợ CIC toàn quốc** làm tắc mọi khoản vay khác. |
| **`WILFUL_DEFAULT`** | Voice + Văn bản | Cảnh báo **khởi kiện pháp lý và xử lý tài sản bảo đảm** (Nhà đất/Ô tô). |
| **`DISPUTE`** | Hotline / Chi nhánh | **Tạm dừng đòi nợ**, chuyển hồ sơ sang Phòng Chăm sóc khách hàng tra soát. |

Tài liệu này hoàn thiện toàn bộ cơ sở lý luận, kiến trúc kỹ thuật và quy trình vận hành cho phân hệ **Xác định Nguyên nhân Gốc của Nợ** trong nền tảng B.Collection!
