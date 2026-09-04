# B.COLLECTION — KẾ HOẠCH TRIỂN KHAI GIAI ĐOẠN MVP (16 TUẦN / 8 SPRINTS)
### Bản Kế hoạch Thực thi Chi tiết: Tối ưu Tốc độ, Quản trị Rủi ro & Chứng minh Hiệu quả Kinh tế (ROI)
**Dự án:** Hệ thống Quản lý & Tối ưu Thu hồi nợ B.Collection — Ngân hàng  
**Giai đoạn:** MVP (Tháng 1 – 4) | **Quy mô:** Khối Bán lẻ (Nhóm nợ B1: DPD 1–30)  
**Tác giả:** Lead Enterprise Architect & Project Taskforce  
**Phiên bản:** v1.0 (Bản chuẩn phê duyệt triển khai)

---

## 📑 MỤC LỤC
1. [Mục tiêu Cốt lõi & Tiêu chí Nghiệm thu MVP (Definition of Done)](#1-mục-tiêu-cốt-lõi--tiêu-chí-nghiệm-thu-mvp-definition-of-done)
2. [Cơ cấu Tổ chức Đội ngũ & Ma trận Phân quyền (Team & RACI)](#2-cơ-cấu-tổ-chức-đội-ngũ--ma-trận-phân-quyền-team--raci)
3. [Lộ trình Triển khai 16 Tuần (8 Sprints $\times$ 2 Tuần)](#3-lộ-trình-triển-khai-16-tuần-8-sprints-times-2-tuần)
   * [Giai đoạn 1: Nền tảng, Làm sạch Dữ liệu & Guardrail Core (Sprint 1 – 2)](#giai-đoạn-1-nền-tảng-làm-sạch-dữ-liệu--guardrail-core-sprint-1--2)
   * [Giai đoạn 2: Workflow, Persona Engine & Collector Workspace (Sprint 3 – 4)](#giai-đoạn-2-workflow-persona-engine--collector-workspace-sprint-3--4)
   * [Giai đoạn 3: AI Scoring, VietQR Link & Tích hợp Toàn diện (Sprint 5 – 6)](#giai-đoạn-3-ai-scoring-vietqr-link--tích-hợp-toàn-diện-sprint-5--6)
   * [Giai đoạn 4: UAT, Đào tạo, Pilot Thực địa & Đo lường Uplift (Sprint 7 – 8)](#giai-đoạn-4-uat-đào-tạo-pilot-thực-địa--đo-lường-uplift-sprint-7--8)
4. [4 Cổng Kiểm soát Chất lượng Bắt buộc (Quality Gates)](#4-4-cổng-kiểm-soát-chất-lượng-bắt-buộc-quality-gates)
5. [Kế hoạch Quản trị Rủi ro & Phương án Dự phòng](#5-kế-hoạch-quản-trị-rủi-ro--phương-án-dự-phòng)
6. [Dự toán Hạ tầng & Ngân sách Triển khai MVP](#6-dự-toán-hạ-tầng--ngân-sách-triển-khai-mvp)

---

## 1. MỤC TIÊU CỐT LÕI & TIÊU CHÍ NGHIỆM THU MVP

### 1.1 Phạm vi Mục tiêu (MVP Scope)
* **Đối tượng:** Khách hàng cá nhân vay vốn/thẻ tín dụng quá hạn nhóm sớm **Bucket B1 ($DPD \text{ 1 – 30}$)**.
* **Địa bàn thí điểm:** 1–2 Chi nhánh lớn hoặc 1 Trung tâm Xử lý Nợ Bán lẻ tập trung.
* **Cơ chế thí điểm:** Thử nghiệm ngẫu nhiên có kiểm soát với **10% Holdout Group (Nhóm đối chứng)**.

```
                  ┌─────────────────────────────────────────────────────────┐
                  │            3 CHỈ SỐ NGHIỆM THU CỐT LÕI CỦA MVP          │
                  └─────────────────────────────────────────────────────────┘
                                               │
               ┌───────────────────────────────┼───────────────────────────────┐
               ▼                               ▼                               ▼
┌───────────────────────────────┐┌───────────────────────────────┐┌───────────────────────────────┐
│ 1. HIỆU QUẢ THU HỒI (UPLIFT)  ││ 2. TỐI ƯU CHI PHÍ VẬN HÀNH   ││ 3. AN TOÀN TUÂN THỦ (100%)    │
│ • Cure Rate tăng: ≥ +8%       ││ • Cost-to-Collect: giảm ≥ 20% ││ • 0 cuộc gọi/tin nhắn vi phạm │
│ • Recovery tăng thêm: ≥ 10 Tỷ ││ • Tự động hóa kênh số: ≥ 60%  ││ • 100% lệnh qua L6 Guardrail  │
└───────────────────────────────┘└───────────────────────────────┘└───────────────────────────────┘
```

### 1.2 Tiêu chí Hoàn thành (Definition of Done - DoD)
1. **L6 Compliance Guardrail:** Chặn 100% các trường hợp vi phạm khung giờ (07:00–21:00), vượt quá 3–5 lần liên hệ/ngày, hoặc liên hệ người không có nghĩa vụ bảo lãnh.
2. **Data Cleansing:** Tỷ lệ số điện thoại liên hệ hợp lệ đạt $\ge 75\%$ sau khi chuẩn hóa.
3. **Real-time Balance Check:** Không có bất kỳ tin nhắn/cuộc gọi đòi nợ nào gửi tới khách hàng đã thanh toán trước đó $> 5$ phút.
4. **Holdout Uplift Proof:** Báo cáo kiểm định $Z\text{-test}$ đạt độ tin cậy thống kê $p\text{-value} < 0.05$.

---

## 2. CƠ CẤU TỔ CHỨC ĐỘI NGŨ & MA TRẬN PHÂN QUYỀN (RACI)

Đội ngũ nòng cốt (Taskforce) gồm **15 thành viên chuyên trách**, làm việc theo mô hình Agile/Scrum (Sprint 2 tuần):

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          CƠ CẤU TỔ CHỨC DỰ ÁN MVP (15 THÀNH VIÊN)                      │
├──────────────────────┬─────┬───────────────────────────────────────────────────────────┤
│ Vai trò              │ SL  │ Trách nhiệm chính trong Sprint                            │
├──────────────────────┼─────┼───────────────────────────────────────────────────────────┤
│ **Product Owner (PO)**   │ 1   │ Lãnh đạo Khối XLN — Chốt nghiệp vụ, KPI và duyệt Pilot     │
│ **Lead SA / Tech Lead**  │ 1   │ Chịu trách nhiệm kiến trúc, code review, ranh giới 4 repos│
│ **Backend Engineers**    │ 3   │ Python FastAPI, Temporal Workflow, 1 người chuyên Guardrail│
│ **Data Engineers**       │ 2   │ dbt-core, SQL pipeline, làm sạch SĐT, đồng bộ EDW         │
│ **Data Scientists**      │ 2   │ Huấn luyện ML1 (Self-cure), ML4 (Best-time), Đo lường ROI │
│ **Frontend Engineers**   │ 2   │ React Workspace, UI Persona Card, nhúng WebRTC Softphone  │
│ **Lead Business Analyst**│ 2   │ Đặc tả luồng B1, quy tắc Maker-Checker, nghiệm thu chức năng│
│ **QA / Test Engineers**  │ 2   │ 1 QA chức năng, 1 QA chuyên trách bộ test Tuân thủ 150 case│
│ **DevOps / Security**    │ 1   │ Hạ tầng VM, CI/CD, Vault, Keycloak, quét mã bảo mật        │
└──────────────────────┴─────┴───────────────────────────────────────────────────────────┘
```

---

## 3. LỘ TRÌNH TRIỂN KHAI 16 TUẦN (8 SPRINTS $\times$ 2 TUẦN)

```
THÁNG 1: NỀN TẢNG & DỮ LIỆU      THÁNG 2: WORKFLOW & WORKSPACE   THÁNG 3: AI & TÍCH HỢP          THÁNG 4: UAT & PILOT
┌──────────────┬──────────────┐ ┌──────────────┬──────────────┐ ┌──────────────┬──────────────┐ ┌──────────────┬──────────────┐
│  Sprint 1    │  Sprint 2    │ │  Sprint 3    │  Sprint 4    │ │  Sprint 5    │  Sprint 6    │ │  Sprint 7    │  Sprint 8    │
│ Tuần 1 - 2   │ Tuần 3 - 4   │ │ Tuần 5 - 6   │ Tuần 7 - 8   │ │ Tuần 9 - 10  │ Tuần 11 - 12 │ │ Tuần 13 - 14 │ Tuần 15 - 16 │
└──────────────┴──────────────┘ └──────────────┴──────────────┘ └──────────────┴──────────────┘ └──────────────┴──────────────┘
 [Gate 1: Guardrail & Data]      [Gate 2: Core Flow & Token]     [Gate 3: E2E Integration]       [Gate 4: Go-Live Pilot]
```

---

### GIAI ĐOẠN 1: NỀN TẢNG, LÀM SẠCH DỮ LIỆU & GUARDRAIL CORE (TUẦN 1 – 4)

#### 🎯 Sprint 1 (Tuần 1 – 2): Thiết lập Hạ tầng, 4 Repos & Data Profiling
* **DevOps/Hạ tầng:**
  * Khởi tạo 3 máy chủ ảo (App, DB, AI Worker) trên hạ tầng On-Premise.
  * Cài đặt PostgreSQL 16, Redis 7, Keycloak IAM, Temporal Server và GitLab Runner.
  * Khởi tạo **4 Repositories** độc lập (`platform`, `guardrail`, `policy`, `data`) kèm cấu hình `CODEOWNERS` và pre-commit `gitleaks`.
* **Data Engineering & BA:**
  * Thiết lập kết nối đọc dữ liệu từ EDW / DWH hiện có qua `dbt-core`.
  * **Chạy Data Profiling trên 500.000 hồ sơ quá hạn lịch sử:** Đo tỷ lệ SĐT rác, tỷ lệ khuyết thông tin người bảo lãnh (`IF-LOS-02`).
  * Xây dựng script sinh dữ liệu tổng hợp (*Synthetic Data Generator*) cho môi trường DEV.
* **Backend:**
  * Dựng khung thư viện `bc-domain` và `bc-guardrail-client`.
  * Khởi tạo bảng dữ liệu `party_obligation` trên PostgreSQL.

#### 🎯 Sprint 2 (Tuần 3 – 4): L6 Guardrail Service v1 & Làm sạch Số điện thoại
* **Guardrail Team:**
  * Hiện thực hóa 5 controls cốt lõi: `G01` (Debt Validity), `G02` (Party Eligibility), `G03` (Consent/DNC), `G05` (Time Window), `G12` (Audit Hash-chain).
  * Xây dựng engine cấp phát `guardrail_token` (ký số ES256, TTL 5 phút).
  * **Hoàn thành Bộ Test Tuân thủ ($\ge 150$ Test Cases):** Bao gồm $\ge 15$ test case cố tình tấn công/bypass Guardrail.
* **Data Team:**
  * Xây dựng Pipeline `int_phone_normalized.sql`: Chuẩn hóa E.164, lọc số tổng đài (`shared_degree > 3`), tính `contactability_score` ban đầu.
  * Cài đặt hàm Băm xác định `holdout_assignment.py` (Cố định 10% Control / 90% Treated).
* 🛑 **QUALITY GATE 1 (Cuối Tuần 4):** Bộ test Guardrail pass 100%; tỷ lệ dữ liệu liên hệ hợp lệ đạt baseline $\ge 65\%$.

---

### GIAI ĐOẠN 2: WORKFLOW, PERSONA ENGINE & COLLECTOR WORKSPACE (TUẦN 5 – 8)

#### 🎯 Sprint 3 (Tuần 5 – 6): Case Workflow & Manual Enrichment API
* **Backend & Workflow:**
  * Xây dựng quy trình vòng đời Case trên **Temporal Workflow** (`Created → Assigned → In-Treatment → PTP → Closed`).
  * Xây dựng API `Collection Core`: Phân công hồ sơ, ghi nhận kết quả liên hệ, lịch hẹn PTP.
  * Phát triển `Enrichment API`: Xử lý 8 fact types đầu tiên (SĐT phụ, địa chỉ thực tế, giờ liên hệ, chu kỳ lương...) theo kiến trúc Event Sourcing.
* **Frontend:**
  * Khởi tạo ứng dụng `collector-workspace` (React 18 + TypeScript + Ant Design).
  * Dựng khung giao diện: Bảng danh sách hồ sơ cần xử lý trong ngày (Case Queue) có phân màu theo mức độ ưu tiên.

#### 🎯 Sprint 4 (Tuần 7 – 8): Persona Card v0, WebRTC Softphone & Channel Adapter
* **Frontend:**
  * Hoàn thiện màn hình **Persona Card v0** (tải dưới $< 500\text{ms}$): Hiển thị 3 điểm số (Ability, Willingness, Contactability), lý do chậm trả, và khối *Lưu ý Bắt buộc*.
  * Tích hợp thư viện `SIP.js`: Nút **Click-to-Call** trực tiếp trên giao diện trình duyệt.
* **Backend & Integration:**
  * Xây dựng `Channel Adapters` cho **SMS Brandname** và **Zalo ZNS**: Cài đặt lớp kiểm tra cứng `base.py` — **Từ chối 100% lệnh gửi nếu thiếu `guardrail_token`**.
  * Xây dựng cơ chế Maker-Checker cho luồng đề xuất giảm lãi/cơ cấu nợ.
* 🛑 **QUALITY GATE 2 (Cuối Tuần 8):** Giao diện Workspace gọi thử nghiệm thành công qua Softphone; tin nhắn SMS/Zalo gửi qua Gateway có kiểm tra token thành công.

---

### GIAI ĐOẠN 3: AI SCORING, VIETQR LINK & TÍCH HỢP TOÀN DIỆN (TUẦN 9 – 12)

#### 🎯 Sprint 5 (Tuần 9 – 10): 2 Mô hình AI (ML1/ML4) & Sinh Link VietQR Động
* **Data Science / AI:**
  * Huấn luyện và đóng gói **ML1 (Self-cure Propensity)** và **ML4 (Best-time-to-contact)** bằng LightGBM.
  * Chạy thử nghiệm giải thích mô hình bằng SHAP values; đăng ký mô hình lên MLflow Registry.
  * Triển khai Job Batch Scoring ban đêm: Tính toán điểm số nạp sẵn vào bảng `dm_persona_features`.
* **Backend & Portal:**
  * Xây dựng Module sinh **Tokenized URL & Mã VietQR Động**: Khách bấm vào tin nhắn là hiển thị ngay số tiền nợ chính xác và thông tin thanh toán.
  * Xây dựng cơ chế **Real-time Balance Check** trước khi gửi tin (gọi API Core để tránh đòi nợ người vừa thanh toán).

#### 🎯 Sprint 6 (Tuần 11 – 12): Tích hợp Toàn diện (E2E Integration) & Diễn tập Sự cố
* **Toàn đội:**
  * Kết nối thông suốt luồng E2E: `EDW nạp dữ liệu → AI Scoring → Guardrail Token → Gửi Zalo/SMS + VietQR → Khách trả tiền → Core xác nhận → Đóng Case`.
  * Chạy **Contract Tests hằng ngày trên môi trường UAT** cho 19 interfaces.
  * **Diễn tập Kịch bản Sự cố (Chaos Engineering):**
    * Tắt đột ngột Redis $\rightarrow$ Guardrail phải tự động chuyển sang trạng thái `BLOCK` (Fail-closed an toàn).
    * Giả lập gửi tin ngoài khung giờ (21:05) $\rightarrow$ Hệ thống tự động hoãn (Queue) đến 08:30 sáng hôm sau.
* 🛑 **QUALITY GATE 3 (Cuối Tuần 12):** Toàn bộ luồng E2E chạy tự động trên môi trường UAT; độ trễ kiểm tra Guardrail $< 15\text{ms}$; 0 lỗi bảo mật nghiêm trọng.

---

### GIAI ĐOẠN 4: UAT, ĐÀO TẠO, PILOT THỰC ĐỊA & ĐO LƯỜNG UPLIFT (TUẦN 13 – 16)

#### 🎯 Sprint 7 (Tuần 13 – 14): Nghiệm thu UAT & Đào tạo Cán bộ Thu hồi Nợ
* **Nghiệm thu Nghiệp vụ (UAT):**
  * 20 Chuyên viên thu hồi nợ (Collectors) và Lãnh đạo phòng tham gia thao tác trực tiếp trên môi trường UAT trong 5 ngày liên tục.
  * Ký biên bản nghiệm thu kỹ thuật và an toàn thông tin với Khối CNTT và Khối Pháp chế/DPO.
* **Đào tạo & Quản trị Thay đổi (Change Management):**
  * Tổ chức 3 buổi đào tạo thực hành cho toàn bộ Cán bộ tham gia Pilot: Cách đọc Persona Card trong 15s, cách nhập Manual Enrichment chuẩn hóa.
  * Ban hành Quy trình Vận hành Tạm thời (SOP) cho giai đoạn Pilot.

#### 🎯 Sprint 8 (Tuần 15 – 16): Go-Live Pilot & Vận hành Đo lường ROI Hằng ngày
* **Triển khai Thực địa (Go-Live):**
  * Kích hoạt hệ thống trên môi trường Production tại **1–2 Chi nhánh thí điểm** (danh mục ~30.000 – 50.000 hồ sơ B1).
  * 90% Khách hàng được phân bổ vào luồng *B.Collection Treatment*; 10% Khách hàng nằm trong *Holdout Control*.
* **Vận hành & Giám sát:**
  * Bật Dashboard theo dõi Uplift thời gian thực trên Grafana: Đo lường *Cure Rate*, *RPC Rate*, *Cost-to-Collect* và $p\text{-value}$.
  * Họp rà soát hằng ngày (Daily Standup 15 phút) giữa Đội Dự án và Lãnh đạo Khối XLN để xử lý nhanh các vướng mắc thực tế.
* 🛑 **QUALITY GATE 4 (Cuối Tuần 16):** Nghiệm thu Báo cáo Kết quả Pilot MVP 120 Ngày; trình Ban Điều hành phê duyệt Kế hoạch Mở rộng Toàn hàng (Giai đoạn 2).

---

## 4. 4 CỔNG KIỂM SOÁT CHẤT LƯỢNG BẮT BUỘC (QUALITY GATES)

Để dự án không bao giờ bị "trôi tiến độ" hoặc "đưa lỗi lên Production", Taskforce thiết lập **4 Cổng Chặn Tuyệt Đối (Kill-Switches)**:

```
┌───────────────┬────────────────────────────────────────────────────────┬───────────────────────┐
│ Cổng Kiểm Soát│ Điều kiện Tiên quyết để Vượt qua Cổng                  │ Hệ quả nếu KHÔNG đạt  │
├───────────────┼────────────────────────────────────────────────────────┼───────────────────────┤
│ **GATE 1**        │ • Bộ test Guardrail 150/150 pass 100% (gồm 15 bypass).  │ **DỪNG TOÀN BỘ**      │
│ (Hết Tuần 4)  │ • Tỷ lệ số điện thoại hợp lệ sau làm sạch $\ge 65\%$.  │ Không viết tiếp code  │
│               │ • 4 Repositories phân quyền đúng CODEOWNERS.           │ cho đến khi pass test.│
├───────────────┼────────────────────────────────────────────────────────┼───────────────────────┤
│ **GATE 2**        │ • Kênh Zalo/SMS từ chối 100% lệnh thiếu token.         │ **HOÃN TÍCH HỢP KÊNH**│
│ (Hết Tuần 8)  │ • Softphone WebRTC gọi thông suốt trên Chrome.         │ Chỉ test nội bộ.      │
│               │ • Temporal Workflow xử lý trơn tru các bước chờ PTP.   │                       │
├───────────────┼────────────────────────────────────────────────────────┼───────────────────────┤
│ **GATE 3**        │ • Realtime Balance Check phản hồi $< 500\text{ms}$.     │ **CHƯA CHO PHÉP UAT** │
│ (Hết Tuần 12) │ • Contract Tests của 19 interfaces pass trên UAT.      │ Phải fix lỗi đồng bộ. │
│               │ • Fail-closed diễn tập thành công khi tắt Redis/DB.    │                       │
├───────────────┼────────────────────────────────────────────────────────┼───────────────────────┤
│ **GATE 4**        │ • Biên bản phê duyệt An toàn Thông tin & Pháp chế/DPO. │ **KHÔNG ĐƯỢC GO-LIVE**│
│ (Hết Tuần 14) │ • 100% Cán bộ tham gia Pilot hoàn thành bài test ĐT.   │ Lùi ngày Pilot.       │
│               │ • Cơ chế Holdout 10% được kích hoạt bất biến.          │                       │
└───────────────┴────────────────────────────────────────────────────────┴───────────────────────┘
```

---

## 5. KẾ HOẠCH QUẢN TRỊ RỦI RO & PHƯƠNG ÁN DỰ PHÒNG

| Mã | Rủi ro Tiềm ẩn | Mức độ | Kế hoạch Ứng phó & Phương án Dự phòng |
|:---:|:---|:---:|:---|
| **R1** | **Dữ liệu EDW cấp quyền chậm** do thủ tục nội bộ kéo dài. | 🔴 Cao | PO ký văn bản chỉ đạo khẩn cấp ngay Tuần 1; chuẩn bị phương án nạp dữ liệu qua file CSV/Parquet bảo mật trong 2 tuần đầu. |
| **R2** | **Dữ liệu người bảo lãnh trong LOS bị thiếu** $\rightarrow$ G02 chặn nhiều. | 🔴 Cao | Khảo sát ngay Tuần 3. Bổ sung giao diện cho phép Cán bộ chi nhánh cập nhật hợp đồng bảo lãnh bổ sung (có kiểm duyệt 4 mắt). |
| **R3** | **Tích hợp Zalo ZNS / SMS Gateway bị vướng** đàm phán thủ tục. | 🟡 TB | Khởi động từ Ngày 1; nếu chưa kịp ký phụ lục hợp đồng, tuần đầu Pilot dùng luồng SMS nội bộ sẵn có của ngân hàng. |
| **R4** | **Cán bộ chi nhánh phản đối dùng hệ thống mới** (sợ bị giám sát). | 🟡 TB | Thiết kế UX 15 giây, tự động điền form gọi điện; gắn điểm thưởng *Enrichment Contribution Score (ECS)* vào thi đua mềm. |
| **R5** | **Khách hàng khiếu nại vì bị đòi nợ nhầm** (do trễ dữ liệu). | 🔴 Cao | Áp dụng bắt buộc bước **Real-time Balance Check** trước khi gửi; nếu hệ thống nghi ngờ $\rightarrow$ Chuyển cờ an toàn, không gửi tin. |

---

## 6. DỰ TOÁN HẠ TẦNG & NGÂN SÁCH TRIỂN KHAI MVP

### 6.1 Tài nguyên Phần cứng MVP (Cấp phát nội bộ)
* **3 Máy chủ Ảo (VMs On-Premise) cấu hình chuẩn:**
  * `VM-APP-01` (Application & Temporal): 16 vCPU, 32GB RAM, 200GB SSD.
  * `VM-DATA-01` (PostgreSQL 16 & Redis): 16 vCPU, 64GB RAM, 1TB NVMe SSD.
  * `VM-AI-01` (AI Scoring & Analytics): 8 vCPU, 32GB RAM, 500GB SSD.
* **Tài nguyên Mạng & Bảo mật:**
  * 1 Domain nội bộ + 1 SSL Certificate chuẩn ngân hàng.
  * Cấu hình mở Port nội bộ giữa các VM và kết nối tới Core Banking/EDW.

### 6.2 Dự toán Ngân sách Vận hành Kênh Tin nhắn Pilot (3 Tháng)
* Quy mô Pilot: ~50.000 hồ sơ nợ B1.
* Ước tính số tin nhắn phát sinh:
  * 70% gửi qua Zalo ZNS: $35.000\text{ tin} \times 300\text{ đ} \approx 10.500.000\text{ VNĐ}$.
  * 30% gửi qua SMS Brandname: $15.000\text{ tin} \times 500\text{ đ} \approx 7.500.000\text{ VNĐ}$.
* **Tổng chi phí kênh ra ngoài trong 3 tháng Pilot:** $\approx \mathbf{18.000.000\text{ VNĐ}}$ *(Chi phí cực thấp so với lợi ích thu hồi hàng chục tỷ đồng)*.

---

## 🎯 7. KẾT LUẬN & ĐỀ XUẤT PHÊ DUYỆT

Bản Kế hoạch Triển khai MVP 16 Tuần này được xây dựng trên nguyên tắc: **Kỷ luật Kỹ thuật Tuyệt đối, Tinh gọn Nguồn lực và Tập trung 100% vào Tạo ra Giá trị Kinh tế Thực tế**.

### Đề xuất 3 Hành động Ngay trong Tuần này:
1. **Trình Ban Giám đốc Khối Xử lý Nợ và Khối CNTT ký phê duyệt Kế hoạch Triển khai MVP v1.0.**
2. **Ký Quyết định thành lập Tổ Công tác Dự án (Taskforce 15 thành viên)** để bàn giao nhân sự toàn thời gian từ Sprint 1.
3. **Khởi tạo 4 Repositories trên hệ thống GitLab của Ngân hàng** và bàn giao tài liệu kiến trúc cho đội ngũ kỹ sư.
