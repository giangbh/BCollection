# B.COLLECTION — SỔ TAY HƯỚNG DẪN SỬ DỤNG CHO NGƯỜI DÙNG CUỐI (END-USER USER GUIDE)
### Cẩm nang Thao tác Chi tiết theo 5 Vai trò Người dùng (Role-Based Operating Manual)
**Dự án:** Hệ thống Quản lý & Tối ưu Thu hồi nợ B.Collection — Ngân hàng  
**Tác giả:** Lead Enterprise Architect & Tổ Công tác Triển khai  
**Phiên bản:** v1.0 | **Ngày ban hành:** 01/09/2026

---

## 📑 MỤC LỤC
1. [Ma trận Phân quyền 5 Vai trò Người dùng (User Roles Matrix)](#1-ma-trận-phân-quyền-5-vai-trò-người-dùng-user-roles-matrix)
2. [HƯỚNG DẪN CHO ROLE 1: Chuyên viên Thu hồi Nợ (Collector)](#2-hướng-dẫn-cho-role-1-chuyên-viên-thu-hồi-nợ-collector)
3. [HƯỚNG DẪN CHO ROLE 2: Trưởng phòng / Trưởng nhóm Xử lý Nợ (Supervisor)](#3-hướng-dẫn-cho-role-2-trưởng-phòng--trưởng-nhóm-xử-lý-nợ-supervisor)
4. [HƯỚNG DẪN CHO ROLE 3: Cán bộ Pháp chế & Kiểm soát Tuân thủ (Compliance Officer)](#4-hướng-dẫn-cho-role-3-cán-bộ-pháp-chế--kiểm-soát-tuân-thủ-compliance-officer)
5. [HƯỚNG DẪN CHO ROLE 4: Chuyên viên Phân tích Chiến lược & Dữ liệu (Strategy Analyst)](#5-hướng-dẫn-cho-role-4-chuyên-viên-phân-tích-chiến-lược--dữ-liệu-strategy-analyst)
6. [HƯỚNG DẪN CHO ROLE 5: Quản trị viên Hệ thống (System Administrator)](#6-hướng-dẫn-cho-role-5-quản-trị-viên-hệ-thống-system-administrator)
7. [Các Câu hỏi Thường gặp & Xử lý Lỗi Phổ biến (FAQ & Troubleshooting)](#7-các-câu-hỏi-thường-gặp--xử-lý-lỗi-phổ-biến-faq--troubleshooting)

---

## 1. MA TRẬN PHÂN QUYỀN 5 VAI TRÒ NGƯỜI DÙNG (USER ROLES MATRIX)

Hệ thống **B.Collection** phân định quyền hạn chặt chẽ dựa trên vai trò nghiệp vụ (RBAC - Role-Based Access Control) thông qua cổng đăng nhập tập trung (SSO/Keycloak):

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              MA TRẬN PHÂN QUYỀN CHỨC NĂNG THEO 5 ROLES                                 │
├────────────────────────────┬──────────┬──────────┬──────────┬──────────┬───────────────────────────────┤
│ Chức năng Hệ thống         │ Role 1   │ Role 2   │ Role 3   │ Role 4   │ Role 5                        │
│                            │Collector │Supervisor│Compliance│ Analyst  │ SysAdmin                      │
├────────────────────────────┼──────────┼──────────┼──────────┼──────────┼───────────────────────────────┤
│ **Xem Queue & Persona Card**   │    ✅    │    ✅    │    👁️    │    👁️    │      ❌                       │
│ **Gọi Softphone & Chốt PTP**   │    ✅    │    ✅    │    ❌    │    ❌    │      ❌                       │
│ **Nhập Fact Làm giàu (Enrich)**│    ✅    │    ✅    │    ❌    │    ❌    │      ❌                       │
│ **Duyệt Cơ cấu / Miễn giảm lãi**│    ❌    │    ✅    │    ❌    │    ❌    │      ❌ (Checker)             │
│ **Cấu hình Policy / Khung giờ** │    ❌    │    ❌    │    ✅    │    ❌    │      ❌                       │
│ **Tra soát Audit Hash-Chain**  │    ❌    │    👁️    │    ✅    │    ❌    │      👁️                       │
│ **Kích hoạt Emergency Kill-SW**│    ❌    │    ❌    │    ✅    │    ❌    │      ✅ (PO / C-Level)        │
│ **Xem Dashboard ROI & Uplift** │    ❌    │    ✅    │    👁️    │    ✅    │      ❌                       │
│ **Quản trị User / Cấu hình ESB**│   ❌    │    ❌    │    ❌    │    ❌    │      ✅                       │
└────────────────────────────┴──────────┴──────────┴──────────┴──────────┴───────────────────────────────┘
Ghi chú: ✅: Có toàn quyền thao tác | 👁️: Chỉ xem (Read-only) | ❌: Bị chặn quyền truy cập
```

---

## 2. HƯỚNG DẪN CHO ROLE 1: CHUYÊN VIÊN THU HỒI NỢ (COLLECTOR)

### 🎯 Mục tiêu công việc
Tiếp nhận danh sách hồ sơ nợ B1 được phân công trong ngày, đọc nhanh chân dung khách hàng, thực hiện cuộc gọi đúng chuẩn mực pháp lý và chốt cam kết thanh toán (PTP).

> 💡 **Cẩm nang Minh họa Ảnh chụp Màn hình Thực tế:** Xem tài liệu hướng dẫn chuyên sâu về cơ chế Softphone, SMS VietQR, Email, thuật toán bóc tách AI và Case History tại [`B-Collection-Huong-Dan-Lien-He-Va-Boc-Tach-AI.md`](file:///Users/giangbh/BLending/BCollection/docs/B-Collection-Huong-Dan-Lien-He-Va-Boc-Tach-AI.md).

```
                  ┌─────────────────────────────────────────────────────────┐
                  │          QUY TRÌNH 4 BƯỚC THAO TÁC CỦA CHUYÊN VIÊN      │
                  └─────────────────────────────────────────────────────────┘
                                               │
       ┌───────────────────────────────┬───────┴───────────────────────┬───────────────────────────────┐
       ▼                               ▼                               ▼                               ▼
┌───────────────────────────────┐┌───────────────────────────────┐┌───────────────────────────────┐┌───────────────────────────────┐
│ BƯỚC 1: CHỌN HỒ SƠ            ││ BƯỚC 2: ĐỌC PERSONA TRONG 15S ││ BƯỚC 3: GỌI ĐIỆN SOFTPHONE   ││ BƯỚC 4: GHI NHẬN KẾT QUẢ      │
│ • Xem bảng Case Queue         ││ • Xem 3 điểm số D1, D2, D3    ││ • Bấm [GỌI ĐIỆN]             ││ • Bấm [KẾT THÚC]              │
│ • Lọc theo DPD (1–30)         ││ • Đọc LƯU Ý GUARDRAIL BẮT BUỘC││ • Áp dụng kịch bản AI đề xuất ││ • Chọn PTP (Số tiền, Ngày hẹn)│
│ • Nhận diện cờ Treatment      ││ • Nắm nguyên nhân chậm trả    ││ • Dùng đòn bẩy đàm phán hợp lệ││ • Bổ sung Fact làm giàu       │
└───────────────────────────────┘└───────────────────────────────┘└───────────────────────────────┘└───────────────────────────────┘
```

### 📋 Hướng dẫn thao tác chi tiết:

#### Bước 1: Xem Danh sách Hồ sơ (Case Queue)
1. Đăng nhập hệ thống tại địa chỉ: `https://bcollection.bank.vn`.
2. Trên màn hình chính, bảng bên trái hiển thị danh sách hồ sơ được phân bổ trong ngày:
   * **Cột Khách hàng/CIF:** Họ tên, số CIF và số điện thoại liên hệ.
   * **Cột DPD:** Số ngày quá hạn (Hiển thị nhãn xanh lá: DPD 1–10; nhãn vàng: DPD 11–20; nhãn đỏ: DPD 21–30).
   * **Cột Nhóm:** Phân loại rõ `Treatment 90%` (Xử lý theo nền tảng B.Collection) hoặc `Holdout 10%` (Nhóm đối chứng).
3. Bấm chuột vào dòng hồ sơ cần xử lý $\rightarrow$ Thông tin Persona Card bên phải sẽ tự động hiển thị tức thì ($< 300\text{ms}$).

#### Bước 2: Đọc Thẻ Chân Dung (Persona Card) trong 15 Giây
Trước khi gọi điện, Chuyên viên phải quét nhanh qua 4 khối thông tin:
1. **Khối 3 Điểm số:**
   * *Khả năng trả (D1):* Điểm cao $\rightarrow$ Khách có tiền nhưng quên/chưa kịp trả; Điểm thấp $\rightarrow$ Khách đang khó khăn dòng tiền.
   * *Thiện chí (D2):* Điểm cao $\rightarrow$ Khách hợp tác; Điểm thấp $\rightarrow$ Khách có dấu hiệu né tránh.
   * *Khả năng liên hệ (D3):* Điểm cao $\rightarrow$ Số điện thoại chính xác, dễ nghe máy.
2. **Khối Cảnh báo Đỏ (LƯU Ý BẮT BUỘC TỪ L6 GUARDRAIL):**
   * Đọc kỹ ai được phép liên hệ (Chính chủ hoặc Bên bảo lãnh hợp pháp).
   * **CẤM:** Không được gọi người thân hay cơ quan công tác nếu không có cam kết bảo lãnh.
3. **Khối Nguyên nhân Chậm trả (Root Cause):** Nắm rõ lý do (Ví dụ: Chờ lương ngày 10, Sự cố kinh doanh, Quên hạn thanh toán).
4. **Khối Khuyến nghị Hành động AI (Next Best Action):** Đọc gợi ý câu thoại và các đòn bẩy cho phép (Ví dụ: Đề xuất miễn 30% lãi phạt nếu trả trong tuần).

#### Bước 3: Thực hiện Cuộc gọi qua Softphone
1. Bấm nút **[GỌI ĐIỆN]** màu xanh trên thanh Header.
2. Hệ thống sẽ tự động gọi L6 Guardrail Service để thẩm tra tính hợp lệ:
   * Nếu hợp lệ $\rightarrow$ Trình duyệt tự động nối máy qua WebRTC, bộ đếm thời gian bắt đầu chạy.
   * Nếu vi phạm (ngoài giờ 07:00–21:00 hoặc đã gọi quá 3 lần hôm nay) $\rightarrow$ Hệ thống tự động chặn và hiển thị thông báo lỗi màu đỏ.
3. Trong cuộc gọi, Chuyên viên trao đổi lịch sự, giải thích rõ nghĩa vụ nợ và đưa ra phương án thanh toán qua VietQR.

#### Bước 4: Ghi nhận Kết quả Cuộc gọi (Call Wrap-up) & Làm giàu Dữ liệu
1. Khi khách đồng ý trả nợ hoặc dập máy, bấm nút **[KẾT THÚC]** màu đỏ.
2. Cửa sổ **Ghi nhận Kết quả Cuộc gọi** sẽ tự động bật lên:
   * Nếu khách đồng ý trả nợ: Chọn **✅ Hẹn ngày thanh toán (PTP Agreed)** $\rightarrow$ Nhập số tiền cam kết và chọn ngày hẹn $\rightarrow$ Bấm **[Lưu & Commit Guardrail]**.
   * Nếu khách từ chối: Chọn **❌ Khách hàng từ chối / Bất hợp tác**.
   * Nếu không nghe máy: Chọn **📵 Không nghe máy / Máy bận**.
3. **Bổ sung dữ liệu mới (Manual Enrichment):** Nếu trong cuộc gọi khai thác được thông tin mới (Ví dụ: Ngày nhận lương là ngày 10 hàng tháng, hoặc khách chỉ nghe máy sau 18:00):
   * Bấm nút **[LÀM GIÀU THÔNG TIN]**.
   * Chọn loại thông tin tương ứng và chọn giá trị $\rightarrow$ Bấm **[Ghi nhận Fact]**.

---

## 3. HƯỚNG DẪN CHO ROLE 2: TRƯỞNG PHÒNG / SUPERVISOR (GIÁM SÁT & DUYỆT 4 MẮT)

### 🎯 Mục tiêu công việc
Điều phối phân bổ hồ sơ, giám sát tiến độ thực hiện cam kết PTP của các chi nhánh, nghe lại ghi âm cuộc gọi để đảm bảo chất lượng, và phê duyệt các đề xuất miễn giảm lãi/cơ cấu nợ (Maker-Checker).

```
                                  ┌─────────────────────────────────────────────────────────┐
                                  │           QUY TRÌNH PHÊ DUYỆT CỦA TRƯỞNG PHÒNG          │
                                  └─────────────────────────────────────────────────────────┘
                                                               │
               ┌───────────────────────────────┼───────────────────────────────┐
               ▼                               ▼                               ▼
┌───────────────────────────────┐┌───────────────────────────────┐┌───────────────────────────────┐
│ 1. GIÁM SÁT TIẾN ĐỘ HÀNG NGÀY ││ 2. KIỂM TRA CHẤT LƯỢNG (QA)  ││ 3. DUYỆT CƠ CẤU / GIẢM LÃI    │
│ • Theo dõi tỷ lệ PTP Kept     ││ • Nghe lại ngẫu nhiên 5% ghi âm││ • Nhận yêu cầu từ Collector   │
│ • Theo dõi tỷ lệ Cure Rate    ││ • Đánh giá thái độ giao tiếp ││ • Thẩm tra theo thẩm quyền    │
│ • Tái phân bổ hồ sơ tắc nghẽn ││ • Phát hiện nguy cơ khiếu nại││ • Duyệt hoặc Từ chối trong 4h │
└───────────────────────────────┘└───────────────────────────────┘└───────────────────────────────┘
```

### 📋 Hướng dẫn thao tác chi tiết:

#### 1. Theo dõi Bảng điều khiển Giám sát Đội ngũ
* Truy cập mục **Quản trị Đội ngũ (Team Dashboard)**:
  * Xem số lượng cuộc gọi đã thực hiện của từng Chuyên viên trong ngày.
  * Xem tỷ lệ cam kết PTP giữ đúng hạn (*PTP Kept Rate*) — Mục tiêu tối thiểu $\ge 75\%$.
  * Xem danh sách các hồ sơ bị khách hàng khiếu nại hoặc quá hạn chưa được liên hệ.

#### 2. Phê duyệt Đề xuất Cơ cấu nợ / Miễn giảm lãi phạt (Maker-Checker)
* Khi Chuyên viên gửi đề xuất giảm lãi phạt hoặc giãn nợ cho khách hàng khó khăn (Segment S3):
  1. Vào menu **Phê duyệt Hồ sơ (Approval Inbox)**.
  2. Bấm vào hồ sơ để xem chi tiết: Tỷ lệ đề xuất giảm (ví dụ: Miễn 30% lãi phạt nếu trả gốc trước ngày 15), lịch sử trả nợ cũ và báo cáo xác minh thu nhập.
  3. Bấm **[PHÊ DUYỆT]** (Ký duyệt điện tử) $\rightarrow$ Hệ thống tự động cập nhật số tiền phải trả mới lên cổng VietQR và gửi thông báo SMS/Zalo cho khách hàng.
  4. Nếu từ chối: Bấm **[TỪ CHỐI]** và ghi rõ lý do.

---

## 4. HƯỚNG DẪN CHO ROLE 3: PHÁP CHẾ & KIỂM SOÁT TUÂN THỦ (COMPLIANCE OFFICER)

### 🎯 Mục tiêu công việc
Quản lý chính sách tuân thủ dạng dữ liệu (Policy-as-Code), kiểm toán tính toàn vẹn của sổ cái Hash-Chain, và kích hoạt Nút Dừng Khẩn Cấp khi có sự cố.

```
                                  ┌─────────────────────────────────────────────────────────┐
                                  │          QUY TRÌNH KIỂM SOÁT CỦA CÁN BỘ PHÁP CHẾ        │
                                  └─────────────────────────────────────────────────────────┘
                                                               │
               ┌───────────────────────────────┼───────────────────────────────┐
               ▼                               ▼                               ▼
┌───────────────────────────────┐┌───────────────────────────────┐┌───────────────────────────────┐
│ 1. CẬP NHẬT CHÍNH SÁCH TUÂN THỦ││ 2. KIỂM TOÁN SỔ CÁI HASH-CHAIN││ 3. NÚT DỪNG KHẨN CẤP (P0)     │
│ • Thay đổi khung giờ gọi điện ││ • Vào trang Kiểm toán Audit   ││ • Phát hiện sự cố dữ liệu     │
│ • Thay đổi hạn mức số lần gọi ││ • Bấm [XÁC MINH TOÀN VẸN]     ││ • Bấm [EMERGENCY HALT]        │
│ • Ký số PKI phê duyệt policy  ││ • Xuất bằng chứng nộp Thanh tra││ • Toàn bộ hệ thống dừng 1s   │
└───────────────────────────────┘└───────────────────────────────┘└───────────────────────────────┘
```

### 📋 Hướng dẫn thao tác chi tiết:

#### 1. Điều chỉnh Chính sách Tuân thủ (Policy-as-Code)
* Khi Ngân hàng Nhà nước hoặc Ban Điều hành ban hành quy định mới (Ví dụ: Giảm giờ gọi nhắc nợ từ 21:00 xuống 20:00 vào các ngày lễ):
  1. Truy cập trang **Quản trị Chính sách Tuân thủ (Compliance Policy Manager)**.
  2. Thay đổi tham số trực tiếp trên giao diện:
     * *Khung giờ bắt đầu:* `07:00` $\rightarrow$ *Khung giờ kết thúc:* `20:00`.
     * *Hạn mức gọi tối đa:* `3 lần/ngày`.
  3. Cắm Token Chữ ký số PKI / SmartOTP nội bộ Ngân hàng $\rightarrow$ Bấm **[KÝ SỐ VÀ PHÁT HÀNH POLICY]**.
  4. Hệ thống sẽ tự động cập nhật file chính sách `current.yaml` $\rightarrow$ **Toàn bộ hệ thống áp dụng ngay lập tức mà không cần khởi động lại máy chủ**.

#### 2. Kiểm toán Độc lập Sổ cái Hash-Chain
* Phục vụ các đợt thanh tra của Ngân hàng Nhà nước hoặc Cục An ninh Mạng:
  1. Vào menu **Kiểm toán Sổ cái (Audit Ledger Verification)**.
  2. Bấm nút **[XÁC MINH TÍNH TOÀN VẸN]**.
  3. Hệ thống sẽ quét qua toàn bộ các Hash-Chain:
     * Nếu chuỗi hợp lệ: Hiển thị trạng thái **✅ 100% TOÀN VẸN (Không bị can thiệp/sửa xóa)**.
     * Hiển thị Genesis Hash và Latest Hash.
  4. Bấm nút **[XUẤT GÓI BẰNG CHỨNG (EVIDENCE PACK)]** $\rightarrow$ Tải file nén `.zip` chứa toàn bộ log đã được đóng dấu thời gian để nộp cho cơ quan chức năng.

#### 3. Kích hoạt Nút Dừng Khẩn Cấp (Emergency Kill-Switch)
* Trong trường hợp phát hiện sự cố nghiêm trọng (Ví dụ: Sai lệch số dư hàng loạt từ Core Banking):
  1. Bấm nút đỏ **[EMERGENCY HALT]** ở góc trên bên phải màn hình.
  2. Nhập mã xác thực 2 lớp $\rightarrow$ Bấm **[XÁC NHẬN DỪNG HỆ THỐNG]**.
  3. **Hệ quả:** Toàn bộ lệnh gửi SMS, Zalo và cuộc gọi Softphone sẽ bị khóa cứng trong vòng **1 giây**.

---

## 5. HƯỚNG DẪN CHO ROLE 4: CHUYÊN VIÊN PHÂN TÍCH CHIẾN LƯỢC (STRATEGY ANALYST)

### 🎯 Mục tiêu công việc
Theo dõi kết quả thử nghiệm A/B giữa nhóm Holdout 10% và nhóm Treatment 90%, đánh giá hiệu quả của các mô hình AI (ML1/ML4), và đề xuất tinh chỉnh chiến dịch.

### 📋 Hướng dẫn thao tác chi tiết:

#### 1. Theo dõi Dashboard Hiệu quả ROI & Uplift
* Truy cập màn hình **Báo cáo Chiến lược (Strategy & Uplift Analytics)**:
  * **Biểu đồ So sánh Cure Rate:** Đường cong tỷ lệ thu hồi nợ của nhóm Treatment (B.Collection) so với nhóm Control (Holdout).
  * **Chỉ số Tăng trưởng Thực tế ($\Delta \text{Cure Rate}$):** Đảm bảo duy trì mức tăng $\ge +8\%$.
  * **Kiểm định Thống kê ($Z\text{-test}$):** Theo dõi giá trị $p\text{-value}$ (Yêu cầu $p < 0.05$ để đảm bảo kết quả không phải do ngẫu nhiên).
  * **Chi phí Thu hồi trên 1 Hồ sơ (Cost-to-Collect):** Theo dõi mức tiết kiệm chi phí nhờ chuyển dịch sang kênh số Zalo/VietQR.

#### 2. Giám sát Hiệu năng Mô hình AI (Model Risk Management)
* Kiểm tra tỷ lệ hội tụ và độ chính xác của **ML1 (Self-cure Propensity)**:
  * Khách hàng được dự báo tự khỏi ($p \ge 80\%$) có thực sự tự thanh toán đúng hạn không.
  * Nếu phát hiện độ lệch (Drift) $\rightarrow$ Xuất dữ liệu để Data Science Team huấn luyện lại mô hình (*Model Retraining*).

---

## 6. HƯỚNG DẪN CHO ROLE 5: QUẢN TRỊ VIÊN HỆ THỐNG (SYSTEM ADMINISTRATOR)

### 🎯 Mục tiêu công việc
Quản trị tài khoản, cấp phát quyền RBAC, giám sát tình trạng hoạt động (Health Check), độ trễ kết nối Core Banking/LOS và bảo mật hạ tầng.

### 📋 Hướng dẫn thao tác chi tiết:

#### 1. Quản lý Tài khoản & Phân quyền Người dùng (RBAC)
* Vào cổng Quản trị **Keycloak Admin Console**:
  * Tạo tài khoản Chuyên viên mới: Điền Mã Cán bộ (CB-xxxx), Họ tên, Email, Chi nhánh.
  * Gán đúng Role: `COLLECTOR`, `SUPERVISOR`, `COMPLIANCE_OFFICER`, hoặc `STRATEGY_ANALYST`.
  * Thiết lập xác thực 2 lớp (MFA/OTP) bắt buộc.

#### 2. Giám sát Sức khỏe Hệ thống (System Health Monitoring)
* Kiểm tra trạng thái các dịch vụ qua endpoint `/health`:
  * `bcollection-guardrail`: Yêu cầu Throughput $\ge 1.000\text{ TPS}$, $P_{99} < 15\text{ms}$.
  * `Redis 7 Cluster`: Bộ nhớ sử dụng $< 60\%$, độ trễ $< 1\text{ms}$.
  * `PostgreSQL 16`: Connection Pool (PgBouncer) hoạt động ổn định.
  * `Core Banking Adapter`: Độ trễ kiểm tra số dư Real-time $< 300\text{ms}$.

---

## 7. CÁC CÂU HỎI THƯỜNG GẶP & XỬ LÝ LỖI PHỔ BIẾN (FAQ)

```
┌───────────────────────────────────────────────────┬────────────────────────────────────────────────────┐
│ Tình huống / Câu hỏi                              │ Hướng dẫn Xử lý Chi tiết                           │
├───────────────────────────────────────────────────┼────────────────────────────────────────────────────┤
│ **Q1: Tại sao nút [GỌI ĐIỆN] bị mờ không bấm được?│ Do chưa chọn hồ sơ từ danh sách bên trái, hoặc     │
│                                                   │ hồ sơ đó đã được giải quyết xong (CURED/CLOSED).   │
├───────────────────────────────────────────────────┼────────────────────────────────────────────────────┤
│ **Q2: Màn hình báo "Chặn do vượt quá 3 lần/ngày"? │ Theo quy định tuân thủ TT 18/NHNN, 1 khách hàng    │
│                                                   │ chỉ được nhắc tối đa 3 lần/24h. Hãy chuyển sang    │
│                                                   │ hồ sơ khác và liên hệ lại vào ngày hôm sau.        │
├───────────────────────────────────────────────────┼────────────────────────────────────────────────────┤
│ **Q3: Khách hàng bảo đã chuyển khoản rồi thì sao? │ Bấm nút [KIỂM TRA SỐ DƯ REALTIME]. Hệ thống sẽ     │
│                                                   │ gọi Core Banking. Nếu tiền đã vào, Case sẽ tự động │
│                                                   │ đổi sang CURED và hủy mọi lịch gọi nhắc nợ.        │
├───────────────────────────────────────────────────┼────────────────────────────────────────────────────┤
│ **Q4: Tôi có thể nhập số điện thoại người thân    │ TUYỆT ĐỐI KHÔNG, trừ khi người đó có hợp đồng      │
│     vào phần Làm giàu thông tin không?**          │ bảo lãnh hợp pháp trong hệ thống LOS. Mọi vi phạm  │
│                                                   │ sẽ bị lưu vết vào Sổ cái Audit và báo cáo DPO.     │
└───────────────────────────────────────────────────┴────────────────────────────────────────────────────┘
```
