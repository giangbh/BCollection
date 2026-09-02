# 🧬 B.COLLECTION — ĐẶC TẢ KỸ THUẬT VECTOR NHÚNG 192 CHIỀU (DEBTOR PERSONA EMBEDDING VECTOR)

> **Mã tài liệu:** `DOC-BCOLLECTION-192D-SPEC`  
> **Phiên bản vector:** `pv-1.4`  
> **Áp dụng cho:** Hệ thống Thu hồi nợ Bán lẻ BIDV (Phân hệ AI Engine, CBR Reference & Case Queue)  
> **Phạm vi:** Early Delinquency (Bucket B1: Quá hạn DPD 1–30 ngày)

---

## 📑 MỤC LỤC
1. [Tổng quan & Mục đích Kiến trúc](#1-tổng-quan--mục-đích-kiến-trúc)
2. [Cấu trúc Không gian Toán học & 9 Khối Dữ liệu](#2-cấu-trúc-không-gian-toán-học--9-khối-dữ-liệu)
3. [Danh mục Chi tiết Toàn bộ 192 Chiều (Từ Chiều 1 đến 192)](#3-danh-mục-chi-tiết-toàn-bộ-192-chiều-từ-chiều-1-đến-192)
   - [Khối 1: Khả năng trả nợ (Ability — D1: 24 chiều)](#khối-1-khả-năng-trả-nợ-ability--d1-24-chiều)
   - [Khối 2: Thiện chí trả nợ (Willingness — D2: 20 chiều)](#khối-2-thiện-chí-trả-nợ-willingness--d2-20-chiều)
   - [Khối 3: Khả năng tiếp cận (Contactability — D3: 16 chiều)](#khối-3-khả-năng-tiếp-cận-contactability--d3-16-chiều)
   - [Khối 4: Nguyên nhân gốc (Root Cause — D4: 16 chiều)](#khối-4-nguyên-nhân-gốc-root-cause--d4-16-chiều)
   - [Khối 5: Đồ thị quan hệ & Mạng lưới (Graph & Network: 32 chiều)](#khối-5-đồ-thị-quan-hệ--mạng-lưới-graph--network-32-chiều)
   - [Khối 6: Sản phẩm & Dư nợ (Product & Exposure: 16 chiều)](#khối-6-sản-phẩm--dư-nợ-product--exposure-16-chiều)
   - [Khối 7: Chuỗi hành vi tương tác (Behavioral Sequence: 32 chiều)](#khối-7-chuỗi-hành-vi-tương-tác-behavioral-sequence-32-chiều)
   - [Khối 8: Nhúng văn bản hội thoại (Text Embedding: 32 chiều)](#khối-8-nhúng-văn-bản-hội-thoại-text-embedding-32-chiều)
   - [Khối 9: Mặt nạ độ tin cậy dữ liệu (Coverage Mask: 4 chiều)](#khối-9-mặt-nạ-độ-tin-cậy-dữ-liệu-coverage-mask-4-chiều)
4. [Cơ chế Tìm kiếm Tương đồng (Hybrid Search & CBR Engine)](#4-cơ-chế-tìm-kiếm-tương-đồng-hybrid-search--cbr-engine)
5. [Nguyên tắc Bảo mật, Đạo đức & Phòng chống Thiên vị AI](#5-nguyên-tắc-bảo-mật-đạo-đức--phòng-chống-thiên-vị-ai)
6. [Mã Nguồn Minh Họa & Cấu hình CSDL pgvector](#6-mã-nguồn-minh-họa--cấu-hình-csdl-pgvector)

---

## 🎯 1. TỔNG QUAN & MỤC ĐÍCH KIẾN TRÚC

Trong hệ thống **B.Collection**, **Vector 192 chiều (`persona_vector`)** là định dạng số hóa toán học chuẩn mực của Chân dung Khách nợ (Debtor Persona 360). Vector này phục vụ 3 mục tiêu cốt lõi:

1. **Case-Based Reasoning (CBR 4R Retrieval):** Tìm kiếm tức thời **5–10 hồ sơ tương tự trong quá khứ** qua khoảng cách Cosine trên cơ sở dữ liệu vector (`pgvector` / Milvus) để học hỏi kịch bản đàm phán và đòn bẩy thành công.
2. **Đầu vào cho Mô hình Nhân quả (Uplift Modeling ML9):** Dự báo mức độ nhạy cảm của khách nợ đối với từng giải pháp can thiệp (*Treatment*: Không can thiệp, Nhắc nhẹ qua SMS/ZNS, Gọi điện đàm phán, Chào cơ cấu giãn nợ, Cảnh báo CIC).
3. **Phân cụm Hành vi Động (Clustering):** Sử dụng thuật toán UMAP giảm chiều kết hợp HDBSCAN để phân nhóm danh mục thành 20–30 cụm hành vi phục vụ định hình chính sách vĩ mô.

---

## 📐 2. CẤU TRÚC KHÔNG GIAN TOÁN HỌC & 9 KHỐI DỮ LIỆU

Không gian vector được phân bổ thành **9 khối thông tin** độc lập với tổng số chiều chính xác là **192**:

$$\mathbf{v}_{\text{192D}} = \underbrace{\mathbf{v}_{\text{Ability}}}_{24} + \underbrace{\mathbf{v}_{\text{Willingness}}}_{20} + \underbrace{\mathbf{v}_{\text{Contact}}}_{16} + \underbrace{\mathbf{v}_{\text{RootCause}}}_{16} + \underbrace{\mathbf{v}_{\text{Graph}}}_{32} + \underbrace{\mathbf{v}_{\text{Product}}}_{16} + \underbrace{\mathbf{v}_{\text{Behavior}}}_{32} + \underbrace{\mathbf{v}_{\text{Text}}}_{32} + \underbrace{\mathbf{v}_{\text{Coverage}}}_{4}$$

```
┌──────────────────────────────────────┬──────────┬────────────────────────────────────────────────────────┐
│ Khối Dữ liệu Đặc trưng (Block)      │ Số Chiều │ Nguồn Dữ liệu Tích hợp                                │
├──────────────────────────────────────┼──────────┼────────────────────────────────────────────────────────┤
│ 1. Khả năng trả nợ (Ability — D1)    │ 24 chiều │ Core Banking (SIBS), CIC Quốc Gia, LOS, CDP           │
│ 2. Thiện chí trả nợ (Willingness — D2)│ 20 chiều │ Lịch sử tương tác B.Collection, Core Banking, CIC      │
│ 3. Khả năng tiếp cận (Contact — D3)  │ 16 chiều │ FreeSWITCH CTI, SMS Gateway, SmartBanking App Logs     │
│ 4. Nguyên nhân gốc (Root Cause — D4) │ 16 chiều │ RootCauseAnalyzer Engine, Lệch kỳ lương, Bóc tách ASR  │
│ 5. Đồ thị mạng lưới (Graph Network) │ 32 chiều │ Neo4j / NetworkX GDS (FastRP Node Embedding, LOS)      │
│ 6. Sản phẩm & Dư nợ (Product)        │ 16 chiều │ Core Banking Loan Master, LOS Contract                 │
│ 7. Chuỗi hành vi tương tác (Sequence)│ 32 chiều │ GRU Hidden State Layer (Chuỗi biến cố 12 tháng)       │
│ 8. Nhúng văn bản hội thoại (Text)    │ 32 chiều │ PhoBERT-base (768D) nén qua PCA/Autoencoder           │
│ 9. Mặt nạ tin cậy dữ liệu (Coverage) │ 4 chiều  │ Tỷ lệ bao phủ trường dữ liệu của 4 trục chính         │
├──────────────────────────────────────┼──────────┼────────────────────────────────────────────────────────┤
│ TỔNG CỘNG KHÔNG GIAN VECTOR          │ 192 CHIỀU│ Chuẩn hóa L2 (||v||_2 = 1.0) phục vụ Cosine Distance   │
└──────────────────────────────────────┴──────────┴────────────────────────────────────────────────────────┘
```

---

## 📋 3. DANH MỤC CHI TIẾT TOÀN BỘ 192 CHIỀU (TỪ CHIỀU 1 ĐẾN 192)

### Khối 1: Khả năng trả nợ (Ability — D1: 24 chiều)
*Phản ánh tiềm lực tài chính, nguồn tiền thu nhập và nghĩa vụ nợ tổng thể.*

| Chiều | Tên biến (Feature Key) | Ý nghĩa nghiệp vụ | Nguồn tích hợp | Phương pháp Chuẩn hóa / Mã hóa |
|:---:|---|---|:---:|---|
| **1** | `inflow_mean_3m` | Dòng tiền ghi có bình quân 3 tháng gần nhất | Core Banking | $\log(x + 1) \rightarrow$ Standard Scaler |
| **2** | `inflow_mean_6m` | Dòng tiền ghi có bình quân 6 tháng gần nhất | Core Banking | $\log(x + 1) \rightarrow$ Standard Scaler |
| **3** | `inflow_mean_12m` | Dòng tiền ghi có bình quân 12 tháng gần nhất | Core Banking | $\log(x + 1) \rightarrow$ Standard Scaler |
| **4** | `inflow_trend_3m_vs_12m` | Tỷ lệ xu hướng dòng tiền ($3\text{M} / 12\text{M}$) | Tính toán | Min-Max $[0, 1]$ (Capped tại 3.0) |
| **5** | `inflow_volatility_cv` | Hệ số biến thiên dòng tiền ($CV = \sigma / \mu$) | Core Banking | Quantile Binning (10 phân vị) |
| **6** | `casa_balance_current` | Số dư tiền gửi không kỳ hạn (CASA) tức thời | Core Banking | $\log(x + 1) \rightarrow$ Standard Scaler |
| **7** | `casa_balance_avg_90d` | Số dư CASA bình quân 90 ngày qua | Core Banking | $\log(x + 1) \rightarrow$ Standard Scaler |
| **8** | `salary_regularity_score` | Độ quy luật ngày nhận lương (đều đặn vs bấp bênh)| Machine Learning | Điểm Float $[0.0, 1.0]$ |
| **9** | `dsr_internal` | Tỷ lệ trả nợ trên thu nhập tại BIDV (DSR nội bộ) | LOS / Core | Standard Scaler (Clip $[0.0, 2.0]$) |
| **10** | `dsr_total_cic` | Tỷ lệ trả nợ trên thu nhập toàn hệ thống CIC | CIC Quốc Gia | Standard Scaler (Clip $[0.0, 2.0]$) |
| **11** | `cic_active_institutions` | Số lượng tổ chức tín dụng đang có dư nợ | CIC Quốc Gia | Min-Max $[0, 1]$ (Max = 10 TCTD) |
| **12** | `cic_worst_group_12m` | Nhóm nợ xấu nhất toàn ngành trong 12 tháng | CIC Quốc Gia | Nhóm 1–5 $\rightarrow$ Scaled $[0.2, 1.0]$ |
| **13** | `cic_worst_group_24m` | Nhóm nợ xấu nhất toàn ngành trong 24 tháng | CIC Quốc Gia | Nhóm 1–5 $\rightarrow$ Scaled $[0.2, 1.0]$ |
| **14** | `cic_total_outstanding` | Tổng dư nợ toàn ngành ngân hàng theo CIC | CIC Quốc Gia | $\log(x + 1) \rightarrow$ Standard Scaler |
| **15** | `cic_credit_card_utilization`| Tỷ lệ sử dụng hạn mức thẻ tín dụng toàn ngành | CIC Quốc Gia | Float $[0.0, 1.5]$ |
| **16** | `collateral_net_value` | Giá trị định giá lại tài sản đảm bảo ròng | LOS | $\log(x + 1) \rightarrow$ Standard Scaler |
| **17** | `collateral_ltv_ratio` | Tỷ lệ dư nợ trên giá trị TSBĐ (Loan-To-Value) | LOS | Min-Max $[0.0, 1.0]$ |
| **18** | `collateral_liquidity_tier` | Cấp độ thanh khoản TSBĐ (BĐS, Ô tô, STK) | LOS | Ordinal Scaled: 0.2, 0.5, 0.8, 1.0 |
| **19** | `days_to_next_salary` | Số ngày còn lại đến kỳ lương dự kiến tiếp theo | Core Banking | Scaled: $(30 - x) / 30 \rightarrow [0, 1]$ |
| **20** | `salary_amount_last` | Số tiền lương/thu nhập kỳ gần nhất | Core Banking | $\log(x + 1) \rightarrow$ Standard Scaler |
| **21** | `inflow_drop_flag` | Cờ sụt giảm dòng tiền đột ngột (> 50% so với TB) | Tính toán | Binary $\{0, 1\}$ |
| **22** | `unsecured_debt_ratio` | Tỷ trọng nợ không có TSBĐ / Tổng dư nợ | Core Banking | Float $[0.0, 1.0]$ |
| **23** | `utility_bill_payment_ratio`| Tỷ lệ thanh toán hóa đơn điện/nước đều đặn qua app | CDP | Float $[0.0, 1.0]$ |
| **24** | `ability_composite_score` | Điểm tổng hợp khả năng trả D1 | D1 Engine | Float $[0.0, 1.0]$ |

---

### Khối 2: Thiện chí trả nợ (Willingness — D2: 20 chiều)
*Phản ánh mức độ hợp tác, độ tin cậy của lời hứa và thái độ ưu tiên nghĩa vụ nợ.*

| Chiều | Tên biến (Feature Key) | Ý nghĩa nghiệp vụ | Nguồn tích hợp | Phương pháp Chuẩn hóa / Mã hóa |
|:---:|---|---|:---:|---|
| **25** | `ptp_kept_ratio_12m` | Tỷ lệ giữ lời hứa hẹn trả nợ (PTP Kept) trong 12M | B.Collection | Float $[0.0, 1.0]$ |
| **26** | `ptp_broken_count_12m` | Số lần thất hứa (Broken PTP) trong 12 tháng qua | B.Collection | Min-Max $[0, 1]$ (Capped tại 5) |
| **27** | `ptp_avg_fulfillment_days` | Số ngày trung bình từ lúc hứa đến lúc trả tiền thật| B.Collection | Min-Max $[0, 1]$ (0–30 ngày) |
| **28** | `self_cure_count_24m` | Số lần quá hạn nhưng tự thanh toán không cần nhắc | Core Banking | Min-Max $[0, 1]$ (Capped tại 10) |
| **29** | `self_cure_propensity_ml01` | Xác suất tự khỏi nợ trong 7 ngày tới (Model ML01)| Model ML01 | Probability $[0.0, 1.0]$ |
| **30** | `cross_bank_payment_signal` | Tín hiệu khách vẫn trả nợ bank khác đúng hạn | CIC Quốc Gia | Binary $\{0, 1\}$ (Tín hiệu né BIDV) |
| **31** | `app_login_after_overdue` | Số lần mở app SmartBanking sau ngày bị quá hạn | CDP | $\log(x + 1) \rightarrow [0, 1]$ |
| **32** | `avoidance_hangup_count` | Số lần nhấc máy rồi dập ngay hoặc chặn số gọi đến | CTI Softphone | Min-Max $[0, 1]$ (Capped tại 6) |
| **33** | `sentiment_trend_score` | Điểm sắc thái cảm xúc trung bình các cuộc gọi gần nhất| Speech AI | Scaled $[-1.0, 1.0] \rightarrow [0.0, 1.0]$ |
| **34** | `dispute_complaint_flag` | Khách có khiếu nại tranh chấp về lãi/phí phạt | CRM Service | Binary $\{0, 1\}$ |
| **35** | `cooperative_dialogue_ratio`| Tỷ lệ thời lượng cuộc gọi khách chịu lắng nghe | Speech AI | Float $[0.0, 1.0]$ |
| **36** | `prior_delinquency_max_dpd` | Số ngày quá hạn cao nhất từng ghi nhận lịch sử | Core Banking | Min-Max $[0, 1]$ (Capped tại 90) |
| **37** | `tenure_months_with_bidv` | Số tháng gắn bó sử dụng dịch vụ của BIDV | Core Banking | $\log(x + 1) \rightarrow [0, 1]$ (Max = 120) |
| **38** | `early_repayment_history` | Lịch sử từng tất toán trước hạn các khoản vay cũ | Core Banking | Binary $\{0, 1\}$ |
| **39** | `qr_open_count` | Số lần mở liên kết VietQR động gửi qua tin nhắn | Messaging GW | Min-Max $[0, 1]$ (Capped tại 5) |
| **40** | `willingness_mat_no_action` | Xác suất hợp tác khi Không can thiệp (Uplift) | Model ML9 | Probability $[0.0, 1.0]$ |
| **41** | `willingness_mat_soft_call` | Xác suất hợp tác khi Gọi điện nhắc nhở nhẹ nhàng | Model ML9 | Probability $[0.0, 1.0]$ |
| **42** | `willingness_mat_restructure`| Xác suất hợp tác khi Chào phương án giãn kỳ hạn | Model ML9 | Probability $[0.0, 1.0]$ |
| **43** | `willingness_mat_firm_action`| Xác suất hợp tác khi Cảnh báo nợ xấu trên CIC | Model ML9 | Probability $[0.0, 1.0]$ |
| **44** | `willingness_composite_score`| Điểm tổng hợp thiện chí D2 | D2 Engine | Float $[0.0, 1.0]$ |

---

### Khối 3: Khả năng tiếp cận (Contactability — D3: 16 chiều)
*Phản ánh kênh liên lạc tối ưu và khung giờ vàng có xác suất nhấc máy cao nhất.*

| Chiều | Tên biến (Feature Key) | Ý nghĩa nghiệp vụ | Nguồn tích hợp | Phương pháp Chuẩn hóa / Mã hóa |
|:---:|---|---|:---:|---|
| **45** | `rpc_rate_30d` | Tỷ lệ nghe máy đúng đối tượng (Right Party Contact) 30d | CTI Softphone | Float $[0.0, 1.0]$ |
| **46** | `rpc_rate_90d` | Tỷ lệ nghe máy đúng đối tượng 90d | CTI Softphone | Float $[0.0, 1.0]$ |
| **47** | `days_since_last_contact` | Số ngày trôi qua kể từ lần cuối cùng nghe máy | CTI Softphone | Min-Max $[0, 1]$ (Capped tại 60) |
| **48** | `best_hour_morning_prob` | Xác suất nghe máy khung Sáng (08:00 – 11:30) | AI ML04 | Softmax Probability $[0.0, 1.0]$ |
| **49** | `best_hour_afternoon_prob` | Xác suất nghe máy khung Chiều (13:30 – 17:00) | AI ML04 | Softmax Probability $[0.0, 1.0]$ |
| **50** | `best_hour_evening_prob` | Xác suất nghe máy khung Tối (17:00 – 20:00) | AI ML04 | Softmax Probability $[0.0, 1.0]$ |
| **51** | `best_day_of_week_sin` | Ngày trong tuần nhấc máy tốt nhất (Thành phần Sin)| AI ML04 | Cyclical Sin: $\sin(2\pi d / 7) \in [-1, 1]$ |
| **52** | `best_day_of_week_cos` | Ngày trong tuần nhấc máy tốt nhất (Thành phần Cos)| AI ML04 | Cyclical Cos: $\cos(2\pi d / 7) \in [-1, 1]$ |
| **53** | `phone_active_signal` | Số điện thoại chính còn phát tín hiệu trên mạng viễn thông | Telco HLRS | Binary $\{0, 1\}$ |
| **54** | `smartbanking_app_frequency`| Tần suất mở app BIDV SmartBanking (lần/tuần) | CDP | Min-Max $[0, 1]$ (Capped tại 14) |
| **55** | `smartbanking_last_active` | Số ngày kể từ lần cuối đăng nhập app | CDP | Min-Max $[0, 1]$ (Capped tại 30) |
| **56** | `sms_delivery_rate` | Tỷ lệ tin nhắn SMS Brandname gửi thành công | SMS Gateway | Float $[0.0, 1.0]$ |
| **57** | `zalo_zns_read_rate` | Tỷ lệ mở đọc thông báo nợ Zalo ZNS | Zalo Gateway | Float $[0.0, 1.0]$ |
| **58** | `verified_secondary_phones` | Số lượng số điện thoại phụ đã xác thực danh tính | LOS / Core | Min-Max $[0, 1]$ (Capped tại 3) |
| **59** | `address_stability_score` | Điểm ổn định địa chỉ cư trú (không đổi địa bàn) | CDP | Float $[0.0, 1.0]$ |
| **60** | `contactability_composite` | Điểm tổng hợp khả năng tiếp cận D3 | D3 Engine | Float $[0.0, 1.0]$ |

---

### Khối 4: Nguyên nhân gốc (Root Cause — D4: 16 chiều)
*Mã hóa xác suất phân bổ của 13 nhóm nguyên nhân chậm trả và độ tin cậy chẩn đoán.*

| Chiều | Tên biến (Feature Key) | Ý nghĩa nghiệp vụ | Nguồn tích hợp | Phương pháp Chuẩn hóa / Mã hóa |
|:---:|---|---|:---:|---|
| **61** | `rc_cashflow_timing` | Chậm trả do lệch kỳ nhận lương / dòng tiền chậm | Root Cause Engine | Soft Probability $[0.0, 1.0]$ |
| **62** | `rc_business_downturn` | Hoạt động kinh doanh bị chậm thu hồi công nợ | Root Cause Engine | Soft Probability $[0.0, 1.0]$ |
| **63** | `rc_over_indebted` | Quá tải nợ nhiều tổ chức tín dụng (DSR > 70%) | Root Cause Engine | Soft Probability $[0.0, 1.0]$ |
| **64** | `rc_wilful_default` | Cố tình chây ỳ, né tránh nghĩa vụ trả nợ | Root Cause Engine | Soft Probability $[0.0, 1.0]$ |
| **65** | `rc_job_loss_reduced_inc` | Mất việc làm hoặc sụt giảm thu nhập nghiêm trọng | Root Cause Engine | Soft Probability $[0.0, 1.0]$ |
| **66** | `rc_health_emergency` | Biến cố y tế, tai nạn, nằm viện gia đình | Root Cause Engine | Soft Probability $[0.0, 1.0]$ |
| **67** | `rc_family_dispute` | Tranh chấp gia đình, ly hôn, phân chia tài sản | Root Cause Engine | Soft Probability $[0.0, 1.0]$ |
| **68** | `rc_unreachable_lost_info` | Mất liên lạc, đổi số điện thoại không báo | Root Cause Engine | Soft Probability $[0.0, 1.0]$ |
| **69** | `rc_forgot_careless` | Sơ suất quên hạn thanh toán, bận công tác xa | Root Cause Engine | Soft Probability $[0.0, 1.0]$ |
| **70** | `rc_fee_rate_dispute` | Khiếu nại, bất đồng về mức lãi suất hoặc phí phạt | Root Cause Engine | Soft Probability $[0.0, 1.0]$ |
| **71** | `rc_system_payment_failure`| Lỗi kênh nộp tiền, giao dịch chuyển khoản bị treo| Root Cause Engine | Soft Probability $[0.0, 1.0]$ |
| **72** | `rc_force_majeure` | Sự kiện bất khả kháng (bão lũ, thiên tai, dịch bệnh)| Root Cause Engine | Soft Probability $[0.0, 1.0]$ |
| **73** | `rc_other_unknown` | Nguyên nhân khác chưa xác định rõ | Root Cause Engine | Soft Probability $[0.0, 1.0]$ |
| **74** | `rc_confidence_score` | Độ tin cậy của chẩn đoán nguyên nhân gốc | Root Cause Engine | Float $[0.2, 1.0]$ |
| **75** | `rc_expected_recovery_days`| Số ngày ước tính khách hàng có thể khắc phục nợ | Root Cause Engine | Min-Max $[0, 1]$ (0–90 ngày) |
| **76** | `rc_manual_override_flag` | Chuyên viên RM đã can thiệp xác thực nguyên nhân | Case Fact DB | Binary $\{0, 1\}$ |

---

### Khối 5: Đồ thị quan hệ & Mạng lưới (Graph & Network: 32 chiều)
*Mã hóa cấu trúc tô-pô mạng lưới quan hệ tín dụng, đồng vay, bảo lãnh và dòng tiền luân chuyển.*

| Chiều | Tên biến (Feature Key) | Ý nghĩa nghiệp vụ | Nguồn tích hợp | Phương pháp Chuẩn hóa / Mã hóa |
|:---:|---|---|:---:|---|
| **77** | `graph_guarantor_count` | Số lượng người bảo lãnh hợp pháp trên hợp đồng | LOS Obligation | Min-Max $[0, 1]$ (Capped tại 3) |
| **78** | `graph_co_borrower_count` | Số lượng người đồng vay cùng chịu trách nhiệm | LOS Obligation | Min-Max $[0, 1]$ (Capped tại 3) |
| **79** | `graph_connected_debtors` | Số cá nhân/doanh nghiệp cùng cụm quan hệ tài chính| Neo4j Graph GDS | $\log(x + 1) \rightarrow [0, 1]$ |
| **80** | `graph_cluster_delinquency` | Tỷ lệ nợ quá hạn trong cùng cụm quan hệ | Neo4j Graph GDS | Float $[0.0, 1.0]$ |
| **81** | `graph_pagerank_centrality` | Điểm trung tâm PageRank trong mạng lưới vay mượn | Neo4j Graph GDS | Scaled Float $[0.0, 1.0]$ |
| **82** | `graph_betweenness_score` | Mức độ là cầu nối luân chuyển tài sản (Betweenness)| Neo4j Graph GDS | Scaled Float $[0.0, 1.0]$ |
| **83** | `graph_dissipation_warning` | Cảnh báo tẩu tán tài sản sang người liên quan (G11)| Graph Rule Engine | Binary $\{0, 1\}$ |
| **84** | `graph_guarantor_rpc_rate` | Tỷ lệ nghe máy của người bảo lãnh | CTI Softphone | Float $[0.0, 1.0]$ |
| **85** | `graph_guarantor_willingness`| Điểm thiện chí hỗ trợ trả nợ của người bảo lãnh | Model ML | Float $[0.0, 1.0]$ |
| **86–108** | `graph_embedding_01` $\dots$ `graph_embedding_23` | **23 Chiều Vector Graph Embedding (FastRP):** Biểu diễn hình học không gian mạng lưới liên kết tài sản, dòng tiền chuyển khoản nội bộ và lịch sử đồng bảo lãnh giữa các chủ thể nợ. | Graph Data Science (FastRP) | Vector chuẩn hóa L2 $(\in [-1.0, 1.0])$ |

---

### Khối 6: Sản phẩm & Dư nợ (Product & Exposure: 16 chiều)
*Mã hóa đặc tính sản phẩm tín dụng, số dư nợ và tiến độ hoàn trả hợp đồng.*

| Chiều | Tên biến (Feature Key) | Ý nghĩa nghiệp vụ | Nguồn tích hợp | Phương pháp Chuẩn hóa / Mã hóa |
|:---:|---|---|:---:|---|
| **109** | `prod_credit_card` | Sản phẩm Thẻ tín dụng quốc tế (Visa/Mastercard) | Core Banking | One-Hot $\{0, 1\}$ |
| **110** | `prod_unsecured_loan` | Cho vay tiêu dùng tín chấp / Thấu chi tài khoản lương| Core Banking | One-Hot $\{0, 1\}$ |
| **111** | `prod_auto_loan` | Cho vay mua ô tô trả góp có thế chấp xe | Core Banking | One-Hot $\{0, 1\}$ |
| **112** | `prod_mortgage_home` | Cho vay mua nhà ở / BĐS có thế chấp sổ đỏ | Core Banking | One-Hot $\{0, 1\}$ |
| **113** | `prod_sme_working_capital` | Vay vốn lưu động phục vụ sản xuất kinh doanh | Core Banking | One-Hot $\{0, 1\}$ |
| **114** | `prod_interest_rate` | Lãi suất cho vay hiện hành (%/năm) | Core Banking | Min-Max $[0, 1]$ (Capped tại 25%) |
| **115** | `prod_remaining_tenor_m` | Số tháng còn lại của hợp đồng vay | Core Banking | Min-Max $[0, 1]$ (Capped tại 120) |
| **116** | `prod_paid_tenor_ratio` | Tỷ lệ thời gian đã thanh toán / Tổng thời hạn vay | Core Banking | Float $[0.0, 1.0]$ |
| **117** | `prod_original_principal` | Dư nợ gốc giải ngân ban đầu | Core Banking | $\log(x + 1) \rightarrow$ Standard Scaler |
| **118** | `prod_current_outstanding` | Tổng dư nợ hiện tại còn lại tại ngân hàng | Core Banking | $\log(x + 1) \rightarrow$ Standard Scaler |
| **119** | `prod_overdue_amount` | Số tiền gốc và lãi đang bị quá hạn kỳ này | Core Banking | $\log(x + 1) \rightarrow$ Standard Scaler |
| **120** | `prod_overdue_ratio` | Tỷ lệ số tiền quá hạn / Tổng dư nợ hiện tại | Core Banking | Float $[0.0, 1.0]$ |
| **121** | `prod_dpd_days` | Số ngày quá hạn hiện tại (Bucket B1: 1–30 ngày) | Core Banking | Scaled: $\text{DPD} / 30.0 \rightarrow [0.0, 1.0]$ |
| **122** | `prod_penalty_fee_amount` | Số tiền lãi phạt chậm trả đã tích lũy | Core Banking | $\log(x + 1) \rightarrow$ Standard Scaler |
| **123** | `prod_installment_amount` | Số tiền phải trả định kỳ hàng tháng | Core Banking | $\log(x + 1) \rightarrow$ Standard Scaler |
| **124** | `prod_has_insurance` | Hợp đồng có tham gia Bảo an tín dụng (Bảo hiểm khoản vay) | Core Banking | Binary $\{0, 1\}$ |

---

### Khối 7: Chuỗi hành vi tương tác (Behavioral Sequence: 32 chiều)
*Mã hóa chuỗi thời gian các tác động và phản ứng của khách nợ trong 12 tháng qua.*

| Chiều | Tên biến (Feature Key) | Ý nghĩa nghiệp vụ | Kỹ thuật biểu diễn |
|:---:|---|---|---|
| **125–156** | `behavior_seq_dim_01` $\dots$ `behavior_seq_dim_32` | **32 Chiều Vector Hidden State (Mạng Nơ-ron GRU):** Nén chuỗi lịch sử các biện pháp can thiệp (SMS, ZNS, cuộc gọi, gặp trực tiếp) và phản ứng thực tế của khách hàng (phớt lờ, dập máy, hứa PTP, trả 1 phần, trả đủ). Giúp giải thuật phân biệt chính xác giữa khách hàng "hứa nhiều lần rồi trả" và khách hàng "hứa để kéo dài thời gian lẩn tránh". | GRU Hidden Layer (32 hidden units, chuẩn hóa $L_2$). |

---

### Khối 8: Nhúng văn bản hội thoại (Text Embedding: 32 chiều)
*Mã hóa ngữ nghĩa ghi chú của Chuyên viên và lời thoại Speech AI bóc tách.*

| Chiều | Tên biến (Feature Key) | Ý nghĩa nghiệp vụ | Kỹ thuật biểu diễn |
|:---:|---|---|---|
| **157–188** | `text_embed_dim_01` $\dots$ `text_embed_dim_32` | **32 Chiều Vector Ngữ nghĩa Hội thoại (PhoBERT/SBERT):** Trích xuất từ toàn bộ ghi chú của Chuyên viên và nội dung hội thoại bóc tách qua ASR Whisper (đã được làm sạch số CMND/CCCD, tên riêng và từ cấm). Thể hiện thái độ đàm phán, lý do cá nhân khó khăn (đi công tác xa, ốm đau, chờ tiền hàng) trong không gian ngữ nghĩa tiếng Việt. | PhoBERT-base (768D) $\rightarrow$ Giảm chiều bằng PCA/AutoEncoder xuống 32D (Chuẩn hóa $L_2$). |

---

### Khối 9: Mặt nạ độ tin cậy dữ liệu (Coverage Mask: 4 chiều)
*Mã hóa tỷ lệ hoàn thiện của dữ liệu đầu vào nhằm giúp giải thuật điều chỉnh trọng số khoảng cách khi hồ sơ thiếu dữ liệu.*

| Chiều | Tên biến (Feature Key) | Ý nghĩa nghiệp vụ | Nguồn tích hợp | Giá trị toán học |
|:---:|---|---|:---:|---|
| **189** | `cov_ability_mask` | Mức độ đầy đủ dữ liệu của trục Khả năng trả (D1) | D1 Engine | Tỷ lệ hoàn thiện $[0.0, 1.0]$ |
| **190** | `cov_willingness_mask`| Mức độ đầy đủ dữ liệu của trục Thiện chí (D2) | D2 Engine | Tỷ lệ hoàn thiện $[0.0, 1.0]$ |
| **191** | `cov_contact_mask` | Mức độ đầy đủ dữ liệu của trục Khả năng liên hệ (D3) | D3 Engine | Tỷ lệ hoàn thiện $[0.0, 1.0]$ |
| **192** | `cov_graph_mask` | Mức độ đầy đủ dữ liệu của trục Đồ thị mạng lưới (Graph)| Graph GDS | Tỷ lệ hoàn thiện $[0.0, 1.0]$ |

---

## 🔎 4. CƠ CHẾ TÌM KIẾM TƯƠNG ĐỒNG (HYBRID SEARCH & CBR ENGINE)

Thuật toán tìm kiếm **Top 5–10 Case Reference** hoạt động theo 3 chặng lọc tối ưu:

```
                  ┌───────────────────────────────────────────────────────────┐
                  │ HỒ SƠ NỢ HIỆN TẠI (Target Case Query)                    │
                  └─────────────────────────────┬─────────────────────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ CHẶNG 1: HARD FILTERING (SQL Query trong CSDL)                                              │
│ • Cùng nhóm sản phẩm hoặc danh mục sản phẩm tương đồng (Vay tiêu dùng tín chấp / Thẻ)       │
│ • Cùng Bucket quá hạn (DPD 1–30 ngày Bucket B1)                                            │
│ • BẮT BUỘC: compliance_review = 'PASSED' (Loại bỏ vĩnh viễn case vi phạm pháp chế L6)      │
└───────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ CHẶNG 2: VECTOR SIMILARITY SEARCH (HNSW trên pgvector)                                      │
│ • Tính tích vô hướng Cosine: CosineSimilarity(u, v) = u • v                                  │
│ • Truy vấn Top 50 ứng viên gần nhất trong thời gian < 20ms                                  │
└───────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ CHẶNG 3: DIVERSITY RE-RANKING (Phòng chống Survivorship Bias)                               │
│ • Phân bổ tỷ lệ: 70% Case thành công (PTP Kept) + 30% Case thất bại (Broken/Escalated)      │
│ • Áp dụng giải thuật MMR (Maximal Marginal Relevance) để tránh trùng lặp cùng 1 kịch bản   │
│ • Xuất bản Top 5–10 Case Reference chuyển hóa thành Recommended Playbook                    │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛡️ 5. NGUYÊN TẮC BẢO MẬT, ĐẠO ĐỨC & PHÒNG CHỐNG THIÊN VỊ AI

1. **Tuyệt đối Không chứa Biến Nhạy Cảm (Protected Attributes):**
   * Vector **hoàn toàn loại bỏ** các trường: Giới tính, Dân tộc, Tôn giáo và Mã địa bàn quê quán thuần túy.
   * Hệ thống định kỳ chạy kiểm thử **Proxy Detection:** Huấn luyện mô hình phụ dự báo biến nhạy cảm từ Vector 192 chiều. Nếu chỉ số $AUC > 0.65 \implies$ Bắt buộc loại bỏ biến gây rò rỉ thông tin.
2. **Cổng Kiểm soát Pháp chế Bắt buộc (`compliance_review = 'PASSED'`):**
   * Một case thành công nhờ thủ đoạn đe dọa, xúc phạm hoặc gọi điện ngoài khung giờ quy định **tuyệt đối không bao giờ được phép đưa vào kho lưu trữ RETAIN**.
3. **Quản lý Phiên bản Vector (`vector_model_version`):**
   * Mọi vector đều lưu kèm nhãn phiên bản (`pv-1.4`). **Cấm so sánh khoảng cách giữa 2 vector khác phiên bản**. Khi cập nhật mô hình PhoBERT hoặc Graph FastRP, hệ thống kích hoạt Batch Job chạy lại (Re-embed) toàn bộ kho hồ sơ mẫu.

---

## 💻 6. MÃ NGUỒN MINH HỌA & CẤU HÌNH CSDL PGVECTOR

### 6.1 Cấu trúc Bảng CSDL PostgreSQL với Extension `pgvector`
```sql
-- Kích hoạt extension vector trong PostgreSQL 16
CREATE EXTENSION IF NOT EXISTS vector;

-- Bảng lưu trữ kho hồ sơ mẫu CBR (Case Reference Memory)
CREATE TABLE cbr_case_memory (
    case_id VARCHAR(64) PRIMARY KEY,
    loan_id VARCHAR(64) NOT NULL,
    debtor_cif VARCHAR(32) NOT NULL,
    product_code VARCHAR(32) NOT NULL,
    dpd_at_intake INT NOT NULL,
    overdue_amount NUMERIC(15, 2) NOT NULL,
    root_cause VARCHAR(64) NOT NULL,
    action_sequence JSONB NOT NULL,
    effective_levers TEXT[] NOT NULL,
    outcome_status VARCHAR(32) NOT NULL, -- 'RECOVERED', 'PARTIAL', 'BROKEN'
    days_to_resolve INT NOT NULL,
    compliance_review VARCHAR(16) NOT NULL DEFAULT 'PASSED',
    vector_version VARCHAR(16) NOT NULL DEFAULT 'pv-1.4',
    persona_vector vector(192) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tạo chỉ mục HNSW phục vụ tìm kiếm khoảng cách Cosine cực nhanh
CREATE INDEX idx_cbr_vector_hnsw 
ON cbr_case_memory 
USING hnsw (persona_vector vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### 6.2 Lớp Python Quản lý Vector 192 Chiều
```python
import numpy as np
from typing import List, Dict, Any

class DebtorPersonaVector192D:
    """
    Lớp quản lý toán học cho Vector Nhúng 192 Chiều của Chân dung Khách nợ B.Collection.
    Đảm bảo vector luôn tuân thủ đúng 192 chiều và được chuẩn hóa L2 trước khi tính tương đồng.
    """
    VECTOR_DIMENSION = 192
    CURRENT_VERSION = "pv-1.4"

    def __init__(self, raw_array: np.ndarray, version: str = CURRENT_VERSION):
        assert raw_array.shape == (self.VECTOR_DIMENSION,), (
            f"Kích thước vector không hợp lệ: {raw_array.shape}, yêu cầu đúng 192 chiều."
        )
        self.version = version
        # Chuẩn hóa L2: ||v||_2 = 1.0
        norm = np.linalg.norm(raw_array)
        if norm > 0:
            self.vector = raw_array / norm
        else:
            self.vector = raw_array

    def compute_cosine_similarity(self, other: 'DebtorPersonaVector192D') -> float:
        """Tính độ tương đồng Cosine giữa 2 vector hồ sơ nợ"""
        assert self.version == other.version, (
            f"Không thể so sánh 2 vector khác phiên bản: {self.version} vs {other.version}"
        )
        # Vì cả 2 đã chuẩn hóa L2, tích vô hướng chính là Cosine Similarity
        return float(np.dot(self.vector, other.vector))

    def to_pgvector_string(self) -> str:
        """Xuất định dạng chuỗi phù hợp cho câu lệnh SQL INSERT vào pgvector"""
        return "[" + ",".join(f"{val:.6f}" for val in self.vector) + "]"
```
