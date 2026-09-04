# B.COLLECTION — TÀI LIỆU GIAI ĐOẠN 4: UAT, ĐÀO TẠO SOP, PILOT ROLLOUT & ĐO LƯỜNG UPLIFT
### Cẩm nang Triển khai Nghiệm thu Nghiệp vụ, Vận hành Thực địa và Chứng minh Hiệu quả Kinh tế
**Dự án:** Hệ thống Quản lý & Tối ưu Thu hồi nợ B.Collection — Ngân hàng  
**Giai đoạn:** Giai đoạn 4 (Tháng 4 / Sprint 7 & 8) | **Quy mô:** Pilot Bán lẻ B1 (DPD 1–30)  
**Tác giả:** Lead Enterprise Architect, Khối Xử lý Nợ & Taskforce Dự án  
**Phiên bản:** v1.0 (Bản chuẩn phát hành phục vụ UAT & Go-Live Pilot)

---

## 📑 MỤC LỤC
1. [Tổng quan Giai đoạn 4 & Điều kiện Tiên quyết (Pre-requisites)](#1-tổng-quan-giai-đoạn-4--điều-kiện-tiên-quyết)
2. [Kế hoạch & 10 Kịch bản Kiểm thử Chấp nhận Người dùng (UAT Scenarios)](#2-kế-hoạch--10-kịch-bản-kiểm-thử-uAt-nghiệp-vụ)
3. [Quy trình Vận hành Chuẩn (SOP) cho Chuyên viên Thu hồi Nợ](#3-quy-trình-vận-hành-chuẩn-sop-cho-chuyên-viên)
   * [3.1 Quy tắc "Đọc Persona Card trong 15 Giây"](#31-quy-tắc-đọc-persona-card-trong-15-giây)
   * [3.2 Quy trình Gọi điện Softphone & Chốt Cam kết PTP](#32-quy-trình-gọi-điện-softphone--chốt-cam-kết-ptp)
   * [3.3 Hướng dẫn Nhập Manual Enrichment Chuẩn hóa](#33-hướng-dẫn-nhập-manual-enrichment-chuẩn-hóa)
   * [3.4 Xử lý Khi Gặp Cảnh báo Chặn của L6 Guardrail](#34-xử-lý-khi-gặp-cảnh-báo-chặn-của-l6-guardrail)
4. [Kế hoạch Triển khai Thực địa (Pilot Rollout tại 1–2 Chi nhánh)](#4-kế-hoạch-triển-khai-thực-địa-pilot-rollout)
5. [Khung Giám sát & Dashboard Đo lường ROI Thời gian Thực](#5-khung-giám-sát--dashboard-đo-lường-roi-thời-gian-thực)
6. [Sổ tay Xử lý Ngoại lệ & Kịch bản Khủng hoảng (Incident Runbook)](#6-sổ-tay-xử-lý-ngoại-lệ--kịch-bản-khủng-hoảng)

---

## 1. TỔNG QUAN GIAI ĐOẠN 4 & ĐIỀU KIỆN TIÊN QUYẾT

Giai đoạn 4 là bước chuyển dịch mang tính quyết định từ **Sản phẩm Kỹ thuật** sang **Vận hành Thực địa**:
* **Thời gian:** 4 Tuần (Sprint 7: UAT & Đào tạo; Sprint 8: Go-Live Pilot & Đo lường Uplift).
* **Phạm vi Pilot:** Toàn bộ danh mục nợ B1 ($DPD \text{ 1 – 30}$) tại **2 Chi nhánh thí điểm** (ước tính 30.000 – 50.000 hợp đồng nợ).
* **Lực lượng tham gia:** 20 Chuyên viên Thu hồi nợ (Collectors) và 2 Trưởng bộ phận Xử lý nợ.

```
                  ┌─────────────────────────────────────────────────────────┐
                  │          4 ĐIỀU KIỆN TIÊN QUYẾT TRƯỚC KHI PILOT         │
                  └─────────────────────────────────────────────────────────┘
                                               │
               ┌───────────────────────────────┼───────────────────────────────┐
               ▼                               ▼                               ▼
┌───────────────────────────────┐┌───────────────────────────────┐┌───────────────────────────────┐
│ 1. KỸ THUẬT & TUÂN THỦ (100%) ││ 2. PHÊ DUYỆT PHÁP LÝ & AN NINH││ 3. ĐÀO TẠO CÁN BỘ (100% PASS) │
│ • 24/24 Test cases pass       ││ • DPO/Pháp chế ký phê duyệt   ││ • 20 Collectors hoàn thành   │
│ • Guardrail Fail-Closed OK    ││ • An toàn thông tin quét 0 lỗi││   khóa học & bài test SOP    │
│ • Realtime check < 300ms      ││ • Kích hoạt Holdout Group 10% ││ • Thao tác Softphone thành thạo│
└───────────────────────────────┘└───────────────────────────────┘└───────────────────────────────┘
```

---

## 2. KẾ HOẠCH & 10 KỊCH BẢN KIỂM THỬ UAT NGHIỆP VỤ

Thời gian kiểm thử UAT: **5 Ngày làm việc liên tục** trên môi trường UAT (Dữ liệu đã qua Masking/Tokenization an toàn).

```
┌────┬──────────────────────────────────┬────────────────────────────────────────────┬───────────────────────────┐
│ STT│ Kịch bản Nghiệp vụ (Scenario)    │ Thao tác của Tester / Collector            │ Kết quả Kỳ vọng (Pass DoD)│
├────┼──────────────────────────────────┼────────────────────────────────────────────┼───────────────────────────┤
│ 01 │ **Đăng nhập & Tải Case Queue**   │ Mở Workspace, lọc hồ sơ theo DPD và Nhóm.  │ Tải danh sách < 1s; hiển  │
│    │                                  │                                            │ thị cờ Holdout 10% rõ ràng│
├────┼──────────────────────────────────┼────────────────────────────────────────────┼───────────────────────────┤
│ 02 │ **Đọc Persona Card trong 15s**   │ Chọn một hồ sơ bất kỳ.                     │ Hiển thị tức thì 3 điểm số│
│    │                                  │                                            │ (D1, D2, D3), Root Cause. │
├────┼──────────────────────────────────┼────────────────────────────────────────────┼───────────────────────────┤
│ 03 │ **Gọi điện Hợp lệ (Click-to-Call)│ Bấm nút [GỌI ĐIỆN] trong giờ làm việc      │ Guardrail duyệt ALLOW     │
│    │                                  │ (08:30 - 20:30) cho khách hàng nợ B1.      │ $\rightarrow$ Nối máy, bật timer│
├────┼──────────────────────────────────┼────────────────────────────────────────────┼───────────────────────────┤
│ 04 │ **Chốt Cam kết PTP**             │ Bấm [KẾT THÚC], chọn PTP, nhập số tiền     │ Lưu trạng thái Case thành │
│    │                                  │ 5.000.000đ và ngày hẹn (3 ngày sau).       │ PTP_SCHEDULED; commit lần │
├────┼──────────────────────────────────┼────────────────────────────────────────────┼───────────────────────────┤
│ 05 │ **Chặn Gọi Ngoài Giờ (G05)**     │ Thử bấm gọi lúc 21:05 tối hoặc 06:30 sáng. │ Guardrail CHẶN tức thì;   │
│    │                                  │                                            │ báo lỗi rõ khung giờ cấm. │
├────┼──────────────────────────────────┼────────────────────────────────────────────┼───────────────────────────┤
│ 06 │ **Chặn Gọi Quá 3 Lần/Ngày (G04)**│ Thực hiện 3 cuộc gọi liên tiếp trong ngày, │ Cuộc gọi thứ 4 bị CHẶN;   │
│    │                                  │ thử bấm gọi lần thứ 4.                     │ báo vượt hạn mức ngày.    │
├────┼──────────────────────────────────┼────────────────────────────────────────────┼───────────────────────────┤
│ 07 │ **Chặn Người Thân Không BL (G02)│ Chọn liên hệ số người thân `FAMILY_OF`.    │ Guardrail CHẶN tuyệt đối; │
│    │                                  │                                            │ không cấp token liên hệ.  │
├────┼──────────────────────────────────┼────────────────────────────────────────────┼───────────────────────────┤
│ 08 │ **Chống Đòi nợ Nhầm (Realtime)** │ Giả lập khách trả tiền qua Core Banking,   │ Hệ thống báo "Khách vừa   │
│    │                                  │ sau đó bấm lệnh gửi SMS/Zalo.              │ trả nợ", tự hủy lệnh gửi. │
├────┼──────────────────────────────────┼────────────────────────────────────────────┼───────────────────────────┤
│ 09 │ **Gửi Tin Nhắn Zalo + VietQR**   │ Chọn gửi nhắc nợ tự động cho nhóm ML1      │ Gửi tin ZNS có gắn link   │
│    │                                  │ tự khỏi trung bình (45% - 79%).            │ rút gọn `bank.vn/c/...`   │
├────┼──────────────────────────────────┼────────────────────────────────────────────┼───────────────────────────┤
│ 10 │ **Làm giàu Dữ liệu (Enrichment)**│ Bổ sung Fact: "Ngày nhận lương là ngày 10",│ Lưu Fact thành công; tự   │
│    │                                  │ thử nhập từ ngữ cấm (đe dọa, bôi nhọ).     │ động CHẶN từ ngữ nhạy cảm.│
└────┴──────────────────────────────────┴────────────────────────────────────────────┴───────────────────────────┘
```

---

## 3. QUY TRÌNH VẬN HÀNH CHUẨN (SOP) CHO CHUYÊN VIÊN THU HỒI NỢ

### 3.1 Quy tắc "Đọc Persona Card trong 15 Giây"
Trước khi bấm nút gọi, Chuyên viên **bắt buộc** quét nhanh qua 4 vùng thông tin trên màn hình trong 15 giây:

```
[VÙNG 1: 3 GIÂY]      [VÙNG 2: 3 GIÂY]      [VÙNG 3: 4 GIÂY]      [VÙNG 4: 5 GIÂY]
3 ĐIỂM SỐ CỐT LÕI  →  LƯU Ý BẮT BUỘC    →   NGUYÊN NHÂN GỐC   →   ĐÒN BẨY ĐỀ XUẤT
• D1: Khả năng trả    • Ai được gọi?        • Lệch chu kỳ lương?  • Giảm 30% lãi phạt?
• D2: Thiện chí       • Khung giờ hợp lệ?   • Quên lịch trả?      • Đổi ngày thanh toán?
• D3: Khả năng nghe   • Khách tổn thương?   • Mất thu nhập?       • Cảnh báo lịch sử CIC?
```

### 3.2 Quy trình Gọi điện Softphone & Chốt Cam kết PTP
1. **Bấm gọi:** Bấm nút **[GỌI ĐIỆN]** trên Softphone Bar $\rightarrow$ Hệ thống tự động kiểm tra Guardrail L6 trong $< 15\text{ms}$.
2. **Trong cuộc gọi:**
   * Áp dụng đúng kịch bản đề xuất từ vùng *Khuyến nghị Hành động (Next Best Action)*.
   * Sử dụng các đòn bẩy đàm phán hợp pháp (`CIC_CREDIT_RECORD`, `EARLY_SETTLEMENT_DISCOUNT`).
   * **CẤM TUYỆT ĐỐI:** Sử dụng lời lẽ đe dọa, xúc phạm, nhắc đến người thân hoặc cơ quan làm việc.
3. **Kết thúc cuộc gọi:** Bấm **[KẾT THÚC]** $\rightarrow$ Form *Ghi nhận kết quả cuộc gọi (Call Wrap-up)* tự động bật lên:
   * Nếu khách đồng ý trả: Chọn **PTP Agreed**, nhập chính xác Số tiền và Ngày hẹn.
   * Nếu khách từ chối: Chọn **Refused**, chọn lý do từ dropdown list (không gõ tự do).

### 3.3 Hướng dẫn Nhập Manual Enrichment Chuẩn hóa
* Khi khai thác được thông tin mới trong cuộc gọi (ví dụ khách đổi giờ nghe máy hoặc đổi ngày nhận lương), bấm nút **[LÀM GIÀU THÔNG TIN]**.
* **Chỉ chọn các trường có cấu trúc:**
  * Khung giờ liên hệ thuận tiện: Sáng (08:30–11:30), Chiều (14:00–17:00), Tối (18:00–20:30).
  * Ngày nhận lương: Ngày từ 1 đến 31.
  * Số điện thoại phụ: Chỉ nhập số chính chủ khách hàng cung cấp.
* Mọi Fact sẽ tự động được hệ thống gắn nhãn nguồn gốc (*Provenance*) và giảm dần độ tin cậy theo thời gian (*Half-life Decay*).

### 3.4 Xử lý Khi Gặp Cảnh báo Chặn của L6 Guardrail
* Khi màn hình hiển thị hộp thoại màu đỏ **"GUARDRAIL CHẶN HÀNH ĐỘNG"**:
  * **Hành động đúng:** Đọc lý do chặn hiển thị trên màn hình (Ví dụ: `G05_OUTSIDE_PERMITTED_HOURS` hoặc `G04_DAILY_TOTAL_LIMIT_EXCEEDED`).
  * **Xử lý:** Chuyển sang hồ sơ khác. Tuyệt đối không cố gắng dùng điện thoại cá nhân để gọi ngoài luồng.

---

## 4. KẾ HOẠCH TRIỂN KHAI THỰC ĐỊA (PILOT ROLLOUT)

### 4.1 Lịch trình 14 Ngày Đầu Tiên của Pilot (Day 1 – Day 14)

```
TUẦN 1: KÍCH HOẠT & THEO DÕI SÁT                TUẦN 2: TỐI ƯU HÓA & ĐO LƯỜNG UPLIFT
┌────────────┬────────────┬────────────┐        ┌────────────┬────────────┬────────────┐
│ Day 1 - 2  │ Day 3 - 4  │ Day 5      │        │ Day 6 - 8  │ Day 9 - 11 │ Day 12 - 14│
├────────────┼────────────┼────────────┤        ├────────────┼────────────┼────────────┤
│ • Kích hoạt│ • Chạy luồng│ • Họp rà  │        │ • Đẩy mạnh │ • Giám sát │ • Đo lường │
│   20 user  │   Zalo ZNS │   soát tuần│        │   luồng PTP│   độ lệch  │   Uplift sơ│
│ • Bật cờ   │   + VietQR │   đầu với  │        │   và thu   │   Holdout  │   bộ 14 ngày│
│   Holdout  │ • Theo dõi │   Lãnh đạo │        │   hồi nợ   │   (Z-test) │ • Báo cáo  │
│   10%      │   tỷ lệ RPC│   Chi nhánh│        │   qua App  │ • Tinh chỉnh│   Ban QLDA │
└────────────┴────────────┴────────────┘        └────────────┴────────────┴────────────┘
```

### 4.2 Kế hoạch Phân bổ Danh mục (Holdout 10% vs Treatment 90%)
* Tổng số hồ sơ nợ B1 đưa vào Pilot: **40.000 hồ sơ**.
* **Nhóm 1 (Holdout Control - 4.000 hồ sơ):** Xử lý theo quy trình cũ thông thường của chi nhánh (gọi nhắc nợ thủ công, không có AI Scoring, không có Persona Card 15s).
* **Nhóm 2 (Treatment - 36.000 hồ sơ):** Xử lý 100% qua nền tảng **B.Collection** (AI phân luồng tự khỏi ML1, Zalo ZNS + VietQR, Persona Card, WebRTC Softphone).

---

## 5. KHUNG GIÁM SÁT & DASHBOARD ĐO LƯỜNG ROI THỜI GIAN THỰC

Hằng ngày vào lúc 08:00 sáng, hệ thống tự động cập nhật Dashboard giám sát hiệu quả so sánh giữa Nhóm Treatment và Nhóm Holdout Control:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               B.COLLECTION PILOT MONITORING DASHBOARD (GRAFANA METRICS)                │
├──────────────────────────┬───────────────────┬───────────────────┬─────────────────────┤
│ Chỉ số Đo lường (KPI)     │ Nhóm Control (10%)│ Nhóm Treatment (90│ Mức Tăng trưởng (Δ) │
├──────────────────────────┼───────────────────┼───────────────────┼─────────────────────┤
│ **Tỷ lệ Tự khỏi / Thu hồi**  │ 62.4%             │ **71.8%**         │ **+ 9.4%** (Vượt KPI│
│ *(Cure Rate B1)*         │                   │                   │  mục tiêu ≥ +8%)    │
├──────────────────────────┼───────────────────┼───────────────────┼─────────────────────┤
│ **Tỷ lệ Nghe máy (RPC)**     │ 38.5%             │ **56.2%**         │ **+ 17.7%**         │
│ *(Right-Party-Contact)*  │                   │                   │ (Nhờ ML4 Best-time) │
├──────────────────────────┼───────────────────┼───────────────────┼─────────────────────┤
│ **Chi phí trên 1 Hồ sơ** │ 42.000 VNĐ        │ **28.500 VNĐ**    │ **- 32.1%**         │
│ *(Cost-to-Collect)*      │                   │                   │ (Tiết kiệm chi phí) │
├──────────────────────────┼───────────────────┼───────────────────┼─────────────────────┤
│ **Thu hồi Tiền mặt Tăng thêm**│ Baseline          │ **+ 14.8 Tỷ VNĐ** │ **ROI: 8.2x**       │
│ *(Incremental Recovery)* │                   │                   │                     │
├──────────────────────────┼───────────────────┼───────────────────┼─────────────────────┤
│ **Kiểm định Thống kê**   │ N/A               │ **p-value = 0.0082│ **Có ý nghĩa thống  │
│ *(Z-test on Cure Rate)*  │                   │ (p < 0.05)**      │  kê tuyệt đối**     │
├──────────────────────────┼───────────────────┼───────────────────┼─────────────────────┤
│ **Số vụ Vi phạm Tuân thủ**│ 0                 │ **0**             │ **100% An toàn**    │
└──────────────────────────┴───────────────────┴───────────────────┴─────────────────────┘
```

---

## 6. SỔ TAY XỬ LÝ NGOẠI LỆ & KỊCH BẢN KHỦNG HOẢNG (INCIDENT RUNBOOK)

| Tình huống Ngoại lệ | Mức độ | Quy trình Xử lý & Khắc phục Ngay |
|:---|:---:|:---|
| **Khách hàng phản ánh bị đòi nợ nhầm** (do đã thanh toán trước đó) | 🔴 P1 | 1. Tra soát ngay log `IF-CORE-04` và số dư Core Banking.<br>2. Nếu đúng khách đã trả: Hệ thống gửi tin nhắn xin lỗi tự động trong 5 phút.<br>3. Kiểm tra độ trễ đồng bộ của Core Banking adapter (yêu cầu $< 5$ phút). |
| **Mất kết nối với L6 Guardrail Service** | 🔴 P0 | Toàn bộ hệ thống tự động kích hoạt chế độ **Fail-Closed**: Khóa toàn bộ các nút [GỌI ĐIỆN] và kênh gửi tin nhắn tự động. Chuyển alert P0 tới đội On-Call DevOps. |
| **Khách hàng khiếu nại về thái độ của Chuyên viên** | 🟡 P2 | Trích xuất ngay bản ghi âm cuộc gọi từ Softphone và bảng log Audit Hash-Chain (`/v1/guardrail/audit/verify`) gửi Trưởng phòng XLN thẩm tra trong 2 giờ. |
| **Nút Khẩn cấp (Emergency Kill-Switch)** | 🔴 P0 | Khi phát hiện sự cố dữ liệu diện rộng: PO hoặc Compliance Officer kích hoạt lệnh `SET SYSTEM_EMERGENCY_HALT=TRUE` $\rightarrow$ Toàn bộ chiến dịch đòi nợ dừng trong 1 giây. |

---

## 🎯 7. KẾT LUẬN & BÀN GIAO VẬN HÀNH

Tài liệu này là cẩm nang vận hành toàn diện cho Giai đoạn 4. Khi kết thúc 4 tuần của Giai đoạn 4:
1. Dự án sẽ có **Báo cáo Chứng minh Hiệu quả Kinh tế Thực tế (Business Case Proof)** có đầy đủ bằng chứng thống kê $Z\text{-test}$ để trình Hội đồng Quản trị Ngân hàng.
2. Nền tảng B.Collection sẽ sẵn sàng để mở rộng quy mô (Rollout) ra toàn bộ 190 Chi nhánh và các phân khúc nợ phức tạp hơn (B2, B3, SME & Doanh nghiệp lớn).
