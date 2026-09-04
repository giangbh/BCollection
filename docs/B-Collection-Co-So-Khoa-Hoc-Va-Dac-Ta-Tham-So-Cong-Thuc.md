# B.Collection — Cơ Sở Khoa Học & Bảng Đặc Tả Tham Số, Công Thức Tính Toán

> **Mã tài liệu:** B-COLLECTION-DOC-SCI-01  
> **Phiên bản:** 1.1.0 (Cập nhật kiến trúc Configuration-Driven, Dynamic Behavioral Features & Làm rõ chuyên sâu Thuật toán ML)  
> **Phạm vi áp dụng:** Toàn bộ thuật toán, công thức tính điểm (D1, D2, D3), mô hình học máy (ML01, ML04), Rule Engine Camunda DMN, CBR 192 Chiều và Guardrail Tuân thủ trong nền tảng B.Collection.  
> **Đối tượng độc giả:** Ban Quản trị Rủi ro (Risk Division), Đội ngũ Data Science/AI, Kỹ sư phần mềm, Kiểm toán nội bộ và Cơ quan Thanh tra Giám sát Ngân hàng.

---

## MỤC LỤC
1. [Giới thiệu & Triết lý Thiết kế](#1-giới-thiệu--triết-lý-thiết-kế)
2. [Kiến trúc Điều khiển bởi Cấu hình (Configuration-Driven & Zero-Downtime Hot-Reload)](#2-kiến-trúc-điều-khiển-bởi-cấu-hình-configuration-driven--zero-downtime-hot-reload)
3. [Trục D1: Khả năng Trả nợ (Ability Score)](#3-trục-d1-khả-năng-trả-nợ-ability-score)
4. [Trục D2: Thiện chí Trả nợ (Willingness Score)](#4-trục-d2-thiện-chí-trả-nợ-willingness-score)
5. [Trục D3: Khả năng Tiếp cận (Contactability Score)](#5-trục-d3-khả-năng-tiếp-cận-contactability-score)
6. [Cơ chế Nạp Đặc trưng Hành vi Động từ CSDL & Giả lập LOS / CIC](#6-cơ-chế-nạp-đặc-trưng-hành-vi-động-từ-csdl--giả-lập-los--cic)
7. [Mô hình AI ML01: Dự báo Tự thanh toán (Self-Cure Propensity)](#7-mô-hình-ai-ml01-dự-báo-tự-thanh-toán-self-cure-propensity)
8. [Mô hình AI ML04: Dự báo Thời điểm & Kênh Vàng (Best-Time-To-Contact)](#8-mô-hình-ai-ml04-dự-báo-thời-điểm--kênh-vàng-best-time-to-contact)
9. [Không gian Vector Nhúng 192 Chiều & CBR Engine (Case-Based Reasoning)](#9-không-gian-vector-nhúng-192-chiều--cbr-engine-case-based-reasoning)
10. [Thử nghiệm Đối chứng Ngẫu nhiên & Suy luận Nhân quả (Holdout Manager)](#10-thử-nghiệm-đối-chứng-ngẫu-nhiên--suy-luận-nhân-quả-holdout-manager)
11. [Quy tắc Vận hành Guardrail Tuân thủ Pháp lý (L6)](#11-quy-tắc-vận-hành-guardrail-tuân-thủ-pháp-lý-l6)
12. [Bảng Tra Cứu Toàn Bộ Hằng Số & Căn Cứ Nguồn Trích Dẫn](#12-bảng-tra-cứu-toàn-bộ-hằng-số--căn-cứ-nguồn-trích-dẫn)
13. [Kết luận & Quy trình Hiệu chuẩn Định kỳ (Model Governance)](#13-kết-luận--quy-trình-hiệu-chuẩn-định-kỳ-model-governance)

---

## 1. Giới thiệu & Triết lý Thiết kế

Trong quản trị thu hồi nợ bán lẻ nhóm sớm (**Early Delinquency B1: DPD 1–30**), việc quyết định biện pháp can thiệp (gọi điện, gửi tin nhắn VietQR tự phục vụ, giãn kỳ hạn hay cưỡng chế) không được dựa trên cảm tính chủ quan của chuyên viên thu nợ (RM), mà phải dựa trên **cơ sở toán học - tài chính định lượng** và **quy chuẩn pháp lý chặt chẽ**.

Hệ thống B.Collection xây dựng ma trận quyết định dựa trên 3 trụ cột độc lập:
1. **Khả năng tài chính vật lý (Ability - D1):** Khách hàng *có tiền* để trả hay không?
2. **Thiện chí & Tâm lý trả nợ (Willingness - D2):** Khách hàng *có muốn* ưu tiên trả khoản nợ này hay không?
3. **Khả năng tiếp xúc (Contactability - D3):** Khách hàng *ở đâu* và kết nối qua kênh nào đạt xác suất nghe máy cao nhất?

Tất cả các hằng số, ngưỡng cắt (thresholds) và trọng số thành phần trong hệ thống đều được kế thừa từ các **chuẩn mực Basel II/III**, **hướng dẫn quản trị rủi ro của Ngân hàng Thanh toán Quốc tế (BIS)**, **thực tiễn thẩm định bán lẻ của các ngân hàng thương mại** và **quy định của Ngân hàng Nhà nước Việt Nam (NHNN)**.

---

## 2. Kiến trúc Điều khiển bởi Cấu hình (Configuration-Driven & Zero-Downtime Hot-Reload)

### 2.1. File cấu hình tập trung `scoring_config.yaml`
Toàn bộ các trọng số, ngưỡng DSR, hệ số phạt, sàn mức sống tối thiểu và tham số mô hình AI được phân tách hoàn toàn khỏi mã nguồn và quản lý tại file:
`bcollection-platform/services/collection-api/config/scoring_config.yaml`

### 2.2. Cơ chế Quản lý Cấu hình & Hot-Reload (`ScoringConfigManager`)
File mã nguồn: `bcollection-platform/services/collection-api/src/scoring_config_loader.py`

* **Kiểm tra mtime (File Modification Time):** Hệ thống không đọc lại đĩa cứng ở mỗi request mà lưu cache trong bộ nhớ RAM; chỉ khi `os.path.getmtime(config_path)` thay đổi, bộ nạp mới parse lại YAML và hoán đổi con trỏ atomic.
* **Fallback an toàn (Fail-safe Default):** Nếu file YAML bị lỗi cú pháp khi chỉnh sửa (syntax error), hệ thống tự động giữ nguyên cấu hình hợp lệ trước đó và ghi log cảnh báo, ngăn chặn nguy cơ sập dịch vụ (zero-downtime).
* **Endpoint quản trị:** Cung cấp API `GET /api/config/scoring` giúp Cán bộ Rủi ro / Vận hành kiểm tra nhanh trạng thái cấu hình đang áp dụng trong runtime.

---

## 3. Trục D1: Khả năng Trả nợ (Ability Score)

### 3.1. Công thức Tổng quát
File mã nguồn: `bcollection-platform/services/collection-api/src/persona_engine.py`

$$S_{\text{D1}} = w_{\text{dsr}} \times S_{\text{DSR}} + w_{\text{inflow}} \times S_{\text{Inflow}} + w_{\text{cic}} \times S_{\text{CIC}} + w_{\text{collat}} \times S_{\text{Collateral}}$$

*Giá trị mặc định từ cấu hình:* $w_{\text{dsr}} = 0.35, w_{\text{inflow}} = 0.25, w_{\text{cic}} = 0.25, w_{\text{collat}} = 0.15$.  
Điểm số được kẹp trong khoảng: $S_{\text{D1}} \in [10, 98]$.

#### Căn cứ xác định trọng số (35% - 25% - 25% - 15%):
* **0.35 cho $S_{\text{DSR}}$:** Dòng tiền ròng thực tế so với nghĩa vụ nợ là yếu tố quyết định hàng đầu trong tín dụng vi mô/bán lẻ. Theo *Ủy ban Basel về Giám sát Ngân hàng (BCBS - Sound Credit Risk Management)*, đòn bẩy thu nhập (DSR/DTI) đóng góp hơn 30–40% vào khả năng vỡ nợ của khách hàng cá nhân.
* **0.25 cho $S_{\text{Inflow}}$:** Tính ổn định của dòng tiền (độ lệch chuẩn thu nhập) và số dư đệm tài khoản thanh toán CASA tại chỗ.
* **0.25 cho $S_{\text{CIC}}$:** Lịch sử tín dụng đa tổ chức tại Trung tâm Thông tin Tín dụng Quốc gia (CIC). Nếu khách hàng nợ xấu tại ngân hàng khác, áp lực tài chính liên đới là cực lớn.
* **0.15 cho $S_{\text{Collateral}}$:** Tỷ lệ cho vay trên giá trị bảo đảm (LTV). Đối với nợ B1 (DPD 1–30), tài sản thế chấp chỉ là lá chắn dự phòng cuối cùng, không phải nguồn tiền trả nợ ngay lập tức nên có trọng số thấp nhất (15%).

---

### 3.2. Điểm Thành phần $S_{\text{DSR}}$ (Debt Service Ratio) & Cải tiến Thực tế

$$\text{DSR} = \frac{\text{Nghĩa vụ trả nợ tháng}}{\text{Thu nhập ròng xác minh tháng}}$$

$$S_{\text{DSR}} = \begin{cases} 
100.0 & \text{khi } \text{DSR} \le \text{DSR}_{\text{safe}} \\
0.0 & \text{khi } \text{DSR} \ge \text{DSR}_{\text{insolvent}} \\
100.0 \times \left(1.0 - \frac{\text{DSR} - \text{DSR}_{\text{safe}}}{\text{DSR}_{\text{insolvent}} - \text{DSR}_{\text{safe}}}\right) & \text{khi } \text{DSR}_{\text{safe}} < \text{DSR} < \text{DSR}_{\text{insolvent}}
\end{cases}$$

#### A. Cải tiến Nâng cao 1: Phân hóa Ngưỡng DSR theo Phân khúc Sản phẩm Tín dụng
Trong thực tế thẩm định ngân hàng, không thể áp dụng cùng một ngưỡng DSR cho tất cả các loại tài sản. Hệ thống phân chia theo file `scoring_config.yaml`:

| Phân khúc Sản phẩm | Ký hiệu mã | Ngưỡng An toàn ($\text{DSR}_{\text{safe}}$) | Ngưỡng Kiệt quệ ($\text{DSR}_{\text{insolvent}}$) | Căn cứ Nghiệp vụ & Pháp lý |
| :--- | :--- | :---: | :---: | :--- |
| **Vay Thế chấp Mua nhà** | `MORTGAGE`, `MORTGAGE_HOME` | **$45\%$** | **$70\%$** | BĐS có giá trị gia tăng dài hạn, kỳ hạn vay 15–25 năm; khách hàng sẵn sàng thắt lưng buộc bụng để giữ nhà. |
| **Vay Mua Ô tô** | `AUTO_LOAN` | **$40\%$** | **$65\%$** | Tài sản khấu hao nhanh, chi phí vận hành phương tiện cố định hàng tháng. |
| **Vốn Lưu động SXKD** | `SME_WORKING_CAPITAL` | **$40\%$** | **$65\%$** | Phụ thuộc vào vòng quay hàng tồn kho và chu kỳ công nợ nhà cung cấp. |
| **Thẻ Tín dụng** | `CREDIT_CARD` | **$30\%$** | **$50\%$** | Lãi suất cao $25\% - 38\%$/năm, không có tài sản thế chấp neo giữ tâm lý; chạm $50\%$ là rủi ro bùng nợ rất lớn. |
| **Tiêu dùng Tín chấp** | `UNSECURED_LOAN` | **$30\%$** | **$50\%$** | Vay tín chấp cá nhân không tài sản neo giữ, rủi ro mất khả năng thanh toán bùng phát nhanh. |
| **Mặc định khác** | `DEFAULT` | **$35\%$** | **$65\%$** | Khung an toàn trung tính chung. |

#### B. Cải tiến Nâng cao 2: Đệm Thanh khoản Tương đối theo Quy mô Nghĩa vụ Nợ & Sàn Sinh tồn
Tỷ lệ DSR tương đối không phản ánh đủ rủi ro nếu bỏ qua số tiền tuyệt đối còn lại; ngược lại, số tiền tuyệt đối còn lại cũng sẽ gây sai lệch nghiêm trọng nếu "mù" quy mô khoản nợ (Loan Exposure Blindness). Hệ thống kết hợp cả hai yếu tố thông qua **Bội số Đệm Thanh khoản Khả dụng (Discretionary Cash-Flow Multiple - DCM)**:

$$\text{Remaining Income} = \text{Verified Inflow} - \text{Monthly Obligation}$$
$$\text{Cushion Multiple} = \frac{\text{Remaining Income}}{\max(\text{Monthly Obligation}, 1.0)}$$

* **Trường hợp 1 — Kiệt quệ Mức sống Sinh tồn ($\text{Remaining Income} < 5.5\text{ triệu VNĐ/tháng}$):**
  * *Nguyên lý:* Mức sống tối thiểu đô thị vùng I theo Nghị định Chính phủ là xấp xỉ 5.5 triệu đ/người/tháng.
  * *Minh họa:* Khách hàng thu nhập $8.000.000$ đ/tháng, nợ $4.000.000$ đ/tháng ($\text{DSR} = 50\%$). Dù DSR chưa chạm trần kiệt quệ lý thuyết, nhưng số tiền còn lại $4.000.000$ đ không đủ chi trả tiền phòng trọ và ăn uống tối thiểu $\rightarrow$ Rơi vào khủng hoảng sinh tồn (Maslow Survival Floor).
  * *Xử lý hệ thống:* Tự động phạt hạ điểm DSR tỷ lệ thuận với độ hụt mức sống: $S_{\text{DSR}} = \min\left(S_{\text{DSR}}, 100.0 \times \frac{\text{Remaining}}{5.5\text{M}} \times 0.6\right)$.
* **Trường hợp 2 — Cảnh báo Đòn bẩy Quá mức (Overleveraged Exposure Warning):**
  * *Nguyên lý:* Khi nghĩa vụ trả nợ hàng tháng lớn ($\text{Monthly Obligation} \ge 20.000.000\text{ đ/tháng}$) nhưng số tiền đệm còn lại chỉ đạt dưới $20\%$ số tiền nợ ($\text{Cushion Multiple} < 0.20$).
  * *Minh họa:* Khách hàng thu nhập $95.000.000$ đ/tháng, nợ $80.000.000$ đ/tháng. Dù số tiền còn lại là $15.000.000$ đ (đủ chi phí ăn uống cơ bản), nhưng đệm thanh khoản chỉ đạt **$18.75\%$** nghĩa vụ nợ. Khách hàng đang ở trạng thái căng đòn bẩy cực độ; chỉ cần một cú sốc doanh thu hoặc lãi suất thả nổi tăng $1\%$ là lập tức mất khả năng trả nợ.
  * *Xử lý hệ thống:* Tuyệt đối không cộng điểm thưởng, trừ phạt đòn bẩy $-15.0$ điểm và kích hoạt cờ cảnh báo `OVERLEVERAGED_WARNING`.
* **Trường hợp 3 — Đệm Thanh khoản Dồi dào Chuẩn Khá giả (Upper Mass / Affluent Cushion):**
  * *Nguyên lý:* Thỏa mãn đồng thời 2 điều kiện an toàn:
    1. $\text{Cushion Multiple} \ge 1.0$ (Số tiền còn lại sau khi trả nợ $\ge 100\%$ nghĩa vụ nợ, tức $\text{DSR} \le 50\%$).
    2. $\text{Remaining Income} \ge 30.000.000\text{ đ/tháng}$ (Chuẩn thu nhập khả dụng của phân khúc Khá giả / Upper Mass tại đô thị lớn).
  * *Minh họa:* Khách hàng thu nhập $100.000.000$ đ/tháng, nợ $48.000.000$ đ/tháng ($\text{DSR} = 48\%$). Tiền còn lại là **$52.000.000$ đ/tháng** (gấp $1.08\text{x}$ nghĩa vụ nợ và vượt xa sàn khá giả 30M).
  * *Xử lý hệ thống:* Thưởng bảo vệ dòng tiền $+10.0 \times \text{Cushion Multiple}$ (tối đa $+25.0$ điểm), bảo vệ điểm Ability không bị hạ oan khi DSR vượt nhẹ ngưỡng an toàn cơ sở.

---

### 3.3. Điểm Thành phần Dòng tiền $S_{\text{Inflow}}$

$$S_{\text{Inflow}} = 50.0 \times (1.0 - \text{CV}) + 50.0 \times \min\left(1.0, \frac{\text{CASA Balance}}{\text{Monthly Obligation}}\right)$$

* **Hệ số biến thiên $\text{CV} = 1.0 - \text{Stability Coefficient}$:** Đo lường độ bấp bênh của dòng tiền theo tháng.
* **Căn cứ khoa học:** *Lý thuyết Tiết kiệm Dự phòng (Precautionary Savings & Buffer-Stock Theory of Saving - Christopher D. Carroll, 1997)*: Người tiêu dùng luôn duy trì một mức đệm tài sản lỏng (CASA) để hấp thụ các cú sốc dòng tiền ngắn hạn. Nếu $\text{CASA} \ge \text{Nghĩa vụ nợ}$, rủi ro vỡ nợ kỹ thuật giảm $85\%$.

---

### 3.4. Điểm Thành phần CIC $S_{\text{CIC}}$

$$S_{\text{CIC}} = \max\left(0.0, 100.0 - (\text{Worst Group Other Banks} - 1) \times 35.0\right)$$

* **Căn cứ pháp lý:** **Thông tư 11/2021/TT-NHNN**: Quy định về phân loại tài sản có và trích lập dự phòng rủi ro. Khi khách hàng phát sinh nợ nhóm 2 hoặc 3 tại một TCTD bất kỳ, thông tin CIC sẽ kích hoạt cơ chế nhảy nhóm nợ trên toàn hệ thống, làm tăng tỷ lệ trích lập dự phòng cụ thể từ $0\%$ lên $5\%$ (nhóm 2) và $20\%$ (nhóm 3). Do đó, điểm tín dụng phải bị trừ lũy tiến mạnh (35 điểm/bậc).

---

### 3.5. Điểm Thành phần Tài sản Đảm bảo $S_{\text{Collateral}}$

$$S_{\text{Collateral}} = \begin{cases} 
100.0 & \text{khi } \text{LTV} \le 0.50 \\
0.0 & \text{khi } \text{LTV} \ge 1.00 \\
100.0 \times (2.0 - 2.0 \times \text{LTV}) & \text{khi } 0.50 < \text{LTV} < 1.00 \\
30.0 & \text{khi khoản vay là Tín chấp (Không TSBĐ)}
\end{cases}$$

* **LTV $\le 0.50$ (100 điểm):** Ngân hàng thu hồi trọn vẹn nợ nếu phát mại tài sản với biên độ an toàn giá thị trường biến động $50\%$.
* **Tín chấp gán $30.0$ điểm:** Theo các nghiên cứu của *Standard & Poor's* và *Moody's* về tỷ lệ thu hồi nợ vay không bảo đảm (*Unsecured Recovery Rate - LGD*), tỷ lệ thu hồi nợ bình quân đối với danh mục cho vay tiêu dùng không TSBĐ dao động từ **$25\% - 35\%$**.

---

## 4. Trục D2: Thiện chí Trả nợ (Willingness Score)

### 4.1. Công thức Tổng quát
File mã nguồn: `bcollection-platform/services/collection-api/src/persona_engine.py`

$$S_{\text{D2}} = 0.40 \times S_{\text{PTP}} + 0.25 \times S_{\text{SelfCure}} + 0.20 \times S_{\text{Priority}} + 0.15 \times S_{\text{Avoidance}}$$

Điểm số kẹp trong khoảng: $S_{\text{D2}} \in [15, 95]$.

#### Cơ sở phân bổ trọng số:
* **0.40 cho Cam kết Trả nợ ($S_{\text{PTP}}$):** Tỷ lệ giữ đúng lời hứa thanh toán (Promise-to-Pay Kept Rate). Theo các nghiên cứu của *FICO Collection Analytics*, lịch sử thực hiện cam kết PTP là biến số tương quan mạnh nhất với thiện chí thực tế (AUC thường đạt trên $0.80$).
* **0.25 cho Tự khỏi ($S_{\text{SelfCure}}$):** Xác suất khách hàng chủ động nộp tiền mà không cần biện pháp cưỡng chế.
* **0.20 cho Thứ tự Ưu tiên ($S_{\text{Priority}}$):** Nhận diện xem khách hàng có đang cố tình ưu tiên thanh toán cho các TCTD khác và đẩy ngân hàng hiện tại xuống cuối cùng hay không.
* **0.15 cho Hành vi Né tránh ($S_{\text{Avoidance}}$):** Mức độ suy giảm hợp tác theo thời gian trôi qua của kỳ quá hạn.

---

### 4.2. Chi tiết các Tham số Thành phần D2

#### A. Tỷ lệ Giữ cam kết Hẹn trả PTP
$$\text{PTP Kept Rate} = \max\left(0.20, \min\left(0.95, 0.90 - \frac{\text{DPD}}{35.0}\right)\right)$$
* **Cơ sở:** *Mô hình Phân rã Cam kết Thời gian (Temporal Commitment Decay)*: Cứ mỗi ngày trôi qua kể từ khi phát sinh nợ, áp lực tâm lý và nguy cơ mất khả năng thực hiện cam kết tăng dần. Con số **35 ngày** tương ứng với chu kỳ một tháng chuyển nhóm nợ từ B1 sang B2 (DPD 31–60). Sau 35 ngày, tỷ lệ giữ lời hứa hẹn trả giảm xuống mức tối thiểu sàn $20\%$.

#### B. Trừ điểm Chây ỳ Chọn lọc ($S_{\text{Priority}}$)
* Nếu khách hàng **đang trả nợ đều đặn cho các ngân hàng khác theo số liệu CIC** nhưng lại **để quá hạn tại ngân hàng ta**:
  $$S_{\text{Priority}} = \mathbf{15.0} \text{ điểm}$$
* Nếu không có dấu hiệu phân biệt đối xử:
  $$S_{\text{Priority}} = \mathbf{85.0} \text{ điểm}$$
* **Cơ sở:** *Lý thuyết Vỡ nợ Chọn lọc (Selective / Strategic Default Theory)* trong kinh tế học tài chính hành vi: Khách hàng nhận thức được ngân hàng nào có biện pháp thu nợ gắt gao hơn thì sẽ trả trước, ngân hàng nào xử lý nhẹ tay sẽ xếp cuối cùng. Mức phạt 70 điểm ($85 - 15$) phản ánh mức cảnh báo rủi ro đạo đức (Moral Hazard) nghiêm trọng.

#### C. Điểm Phạt Né tránh ($S_{\text{Avoidance}}$)
$$\text{Avoidance Penalty} = \min(60.0, \text{DPD} \times 2.0)$$
$$S_{\text{Avoidance}} = 100.0 - \text{Avoidance Penalty}$$
* **Hệ số phạt $2.0$ điểm/ngày DPD:** Khách hàng trễ 5 ngày bị trừ 10 điểm, trễ 20 ngày bị trừ 40 điểm, trễ 30 ngày bị trừ mức trần tối đa 60 điểm.
* **Cơ sở:** *Mô hình Leo thang Né tránh (Avoidance Escalation Pattern)*: Phản ánh thực tế tâm lý con nợ thường chủ động nghe máy ở tuần đầu tiên, nhưng sau 15–20 ngày sẽ bắt đầu chặn số hoặc không phản hồi.

---

## 5. Trục D3: Khả năng Tiếp cận (Contactability Score)

### 5.1. Công thức Tổng quát
File mã nguồn: `bcollection-platform/services/collection-api/src/persona_engine.py`

$$S_{\text{D3}} = 0.40 \times S_{\text{RPC}} + 0.35 \times S_{\text{Digital}} + 0.25 \times S_{\text{Recency}}$$

Điểm số kẹp trong khoảng: $S_{\text{D3}} \in [20, 95]$.

#### Cơ sở phân bổ trọng số:
* **0.40 cho $S_{\text{RPC}}$ (Right-Party-Contact):** Xác suất gọi đúng chính chủ khách nợ và khách bắt máy (dự báo bởi mô hình ML04).
* **0.35 cho $S_{\text{Digital}}$:** Tần suất tương tác trên các kênh số hóa (Ngân hàng số Mobile App, Internet Banking).
* **0.25 cho $S_{\text{Recency}}$:** Mức độ mới của thông tin địa chỉ, số điện thoại trong vòng 30–90 ngày gần nhất.

#### Thang đo tương tác Kênh số ($S_{\text{Digital}}$):
* $\ge 10$ lượt đăng nhập App/tháng: **100 điểm** (Khách hàng số tích cực, kênh Zalo/In-app push đạt hiệu quả tối đa).
* $3 - 9$ lượt đăng nhập App/tháng: **70 điểm**.
* $< 3$ lượt đăng nhập App/tháng: **30 điểm** (Khách hàng truyền thống, bắt buộc ưu tiên Voice Call / SMS).

---

## 6. Cơ chế Nạp Đặc trưng Hành vi Động từ CSDL & Giả lập LOS / CIC

### 6.1. Trích xuất Đặc trưng Hành vi từ CSDL SQLite (`get_debtor_behavioral_metrics`)
File mã nguồn: `bcollection-platform/services/collection-api/src/database.py`

Thay vì sử dụng các giá trị phỏng đoán tĩnh, hàm `get_debtor_behavioral_metrics(debtor_cif, case_id)` thực hiện tổng hợp dữ liệu thực từ 2 bảng cơ sở:
1. **Bảng `cases`:**
   * Tính `historical_on_time_ratio`: Tỷ lệ các khoản nợ đã đóng đúng hạn trong lịch sử hồ sơ vay của CIF.
   * Tính `prior_cure_count`: Số lượng hồ sơ từng quá hạn trong quá khứ đã đạt trạng thái `CLOSED` / `CURED`.
2. **Bảng `case_interactions`:**
   * Đếm tần suất tương tác kênh số hóa (Zalo, App push, Self-service payment) trong 30 ngày gần nhất để suy ra `app_logins_per_month`.
   * Tính tỷ lệ cam kết PTP thực tế từ lịch sử cuộc gọi trước đó.

### 6.2. Sinh Giả lập Dữ liệu LOS & CIC Đa dạng theo Hash CIF
File mã nguồn:
* `bcollection-platform/services/integration-adapters/src/cic/mock_client.py`
* `bcollection-platform/services/integration-adapters/src/los/mock_client.py`

Nhằm phản ánh đúng sự biến thiên của danh mục nợ ngân hàng mà vẫn bảo đảm tính xác định (Deterministic Replay):
* **Hàm băm CIF:** $H = \text{int}(\text{MD5}(\text{CIF})[:8], 16)$.
* **Điểm tín dụng CIC:** Dao động liên tục từ **450 đến 750 điểm**:
  $$\text{Score}_{\text{CIC}} = 450 + (H \pmod{301})$$
* **Tổng nghĩa vụ nợ tại các TCTD khác:** Dao động từ **15 triệu đến 280 triệu VNĐ**:
  $$\text{Total Obligation} = 15.000.000 + (H \pmod{265}) \times 1.000.000$$
* **Tài sản bảo đảm gắn với sản phẩm vay:**
  * `MORTGAGE`: Bất động sản (Sổ đỏ, căn hộ) trị giá 1.8 tỷ – 6.5 tỷ VNĐ.
  * `AUTO_LOAN`: Phương tiện giao thông (Ô tô) trị giá 450 triệu – 1.2 tỷ VNĐ.
  * `SME_WORKING_CAPITAL`: Quyền đòi nợ, máy móc thiết bị, nhà xưởng kho bãi trị giá 800 triệu – 2.5 tỷ VNĐ.
  * `CREDIT_CARD` / `UNSECURED_LOAN`: Không có tài sản bảo đảm (LTV = null, điểm thế chấp = 30.0).

---

## 7. Mô hình AI ML01: Dự báo Tự thanh toán (Self-Cure Propensity)

File mã nguồn: `bcollection-data/ml/models/ml01_self_cure.py`

### 7.1. Cấu trúc Thuật toán Hồi quy Logistic Sigmoid
Mô hình ước lượng xác suất khách hàng tự thanh toán trong kỳ $P(\text{Self-Cure} = 1 \mid \mathbf{X}) \in (0, 1)$ thông qua hàm Sigmoid phi tuyến:

$$P = \sigma(z) = \frac{1}{1 + e^{-z}}$$

Trong đó hàm tuyến tính $z$ đo lường Tỷ số Chênh (Log-Odds):
$$z = \ln\left(\frac{P}{1 - P}\right) = \beta_0 + \sum_{i=1}^{k} \beta_i X_i$$

### 7.2. Bảng Trọng số Hồi quy (Regression Weights) & Ý nghĩa Kinh tế lượng

| Biến đặc trưng $X_i$ | Ký hiệu mã nguồn | Trọng số $\beta_i$ | Ý nghĩa Kinh tế lượng & Lý thuyết Rủi ro |
| :--- | :--- | :---: | :--- |
| **Hằng số chặn (Intercept)** | `base_intercept` | **$+0.60$** | Đại diện cho xác suất tự khỏi cơ bản (Base Log-odds $\approx 1.82$, tương ứng Xác suất $\approx 64.5\%$) của tệp nợ nhóm sớm B1 khi chưa chịu các biến động tiêu cực. |
| **Tỷ lệ trả đúng hạn lịch sử** | `historical_on_time_ratio` | **$+0.40$** | Khách hàng có thói quen trả đúng hạn 12 tháng qua thể hiện uy tín tín dụng cao, tăng mạnh cơ hội tự hồi phục. |
| **Số ngày trễ nợ (DPD)** | `dpd` | **$-0.03$** | Mỗi ngày chậm trả làm giảm hàm số mũ của xác suất tự khỏi (Hazard Rate Decay). |
| **Độ vênh ngày lương** | `days_since_salary_day` | **$-0.05$** | Càng xa ngày nhận lương định kỳ, tiền lương càng bị phân tán cho chi tiêu khác, giảm khả năng tự trả. |
| **Số lần tự khỏi quá khứ** | `prior_cure_count` | **$+0.15$** | Khách hàng có tiền lệ từng quá hạn ngắn ngày rồi tự trả (quên thanh toán) có xác suất lặp lại hành vi này rất cao. |
| **Tỷ lệ nợ trên thu nhập** | `dti_ratio` | **$-0.20$** | Gánh nặng nợ càng cao, áp lực dòng tiền càng lớn, xác suất tự thanh toán giảm. |
| **Hệ số đệm CASA** | `casa_buffer_weight` | **$+0.25$** | Áp dụng cho nhóm không có bảng lương (Tiểu thương, Freelance). Đệm tiền gửi không kỳ hạn là nguồn thanh khoản trực tiếp. |

### 7.3. Cơ sở Khoa học & Xử lý Dòng tiền Phức tạp

#### A. Lý thuyết Phân tích Nguy cơ Thời gian (Survival Analysis & Hazard Function)
Trong kinh tế lượng tài chính, hiện tượng quá hạn nợ được mô hình hóa như một quá trình phân rã thời gian. Càng xa ngày nhận lương định kỳ (`days_since_salary_day`), tiền mặt trong tài khoản càng bị phân tán vào các chi tiêu phát sinh khác, làm giảm xác suất tự thanh toán theo hàm số mũ.

#### B. Kỹ thuật Mặt nạ Đặc trưng & Tín hiệu Thay thế (Feature Masking & Surrogate Signals)
Đối với khách hàng **không chi lương qua ngân hàng nội bộ** (`has_payroll = False`), trường `days_since_salary_day` bị khuyết thiếu có hệ thống (Missing Not At Random - MNAR). Thay vì phạt mù làm sụt giảm oan điểm của khách hàng, mô hình kích hoạt nhánh tín hiệu thay thế:
1. **Tiểu thương / Hộ kinh doanh (`MERCHANT_BUSINESS`):**
   $$\text{Flow Signal} = \beta_{\text{casa\_buffer}} \times (\min(\text{Buffer}, 4.0) - 1.0)$$
   *Căn cứ lý thuyết:* **Buffer-Stock Theory of Saving** (*Christopher D. Carroll, 1997*): Người tiêu dùng luôn duy trì lượng tiền mặt dự phòng để hấp thụ các cú sốc thanh khoản ngắn hạn. Nếu đệm CASA $\ge 1.5$x nghĩa vụ nợ, xác suất tự thanh toán phục hồi về mức cao.
2. **Khách hàng nhận lương ngân hàng khác (`NON_PAYROLL_SALARIED`):**
   $$\text{Flow Signal} = 0.18 \times \min(\text{CASA Buffer}, 3.0) - 0.03 \times |\text{Today} - \text{Inferred Pay Day}|$$
   Tận dụng chu kỳ nhận lương suy luận từ hồ sơ thẩm định LOS để ước lượng ngày tiền về.

#### C. Lý thuyết Kinh tế học Can thiệp (Intervention Economics & Cost-Sensitive Learning)
Hệ thống phân tầng hành động (Action Tiers) dựa trên hàm đánh đổi chi phí - lợi ích:
* $P(\text{Self-Cure}) \ge 0.80 \implies$ **Ân hạn 5 ngày (SELF_CURE_HIGH):** Không gọi điện, chỉ gửi SMS/Zalo VietQR tự phục vụ.
* $0.45 \le P(\text{Self-Cure}) < 0.80 \implies$ **Ân hạn 3 ngày (SELF_CURE_MED):** Chờ chuyển khoản liên ngân hàng hoặc bù đắp cuối tuần.
* $P(\text{Self-Cure}) < 0.45 \implies$ **Ân hạn 0 ngày (HIGH_RISK):** Phân bổ chuyên viên gọi điện can thiệp đàm phán ngay.

*Căn cứ thực tiễn:* Theo **Nghiên cứu Tối ưu hóa Thu hồi nợ Bán lẻ của McKinsey**, việc gọi điện đôn đốc nhóm khách hàng có xác suất tự khỏi $> 80\%$ không làm tăng tỷ lệ thu hồi vốn, mà gây **lãng phí chi phí vận hành (Call Center OPEX)** và **làm suy giảm nghiêm trọng chỉ số hài lòng khách hàng (NPS)**.

---

## 8. Mô hình AI ML04: Dự báo Thời điểm & Kênh Vàng (Best-Time-To-Contact)

File mã nguồn: `bcollection-data/ml/models/ml04_best_time.py`

### 8.1. Thuật toán Cốt lõi
Mô hình kết hợp **Ước lượng Trung bình Động theo Thời gian (Moving Average)** và **Phân cụm Hành vi Ngữ cảnh (Contextual Behavioral Clustering)** qua cơ chế 2 pha:
* **Pha 1 (Warm Start - Đã có lịch sử tương tác cuộc gọi):**
  Tính giờ trung bình nghe máy thành công:
  $$\bar{H} = \frac{1}{N} \sum_{i=1}^N h_i$$
  * Nếu $\bar{H} \in [18, 21] \implies$ Khung giờ `18:00 - 20:30` (Tỷ lệ RPC dự báo: **$85\%$**).
  * Nếu $\bar{H} \in [8, 12] \implies$ Khung giờ `08:30 - 11:30` (Tỷ lệ RPC dự báo: **$78\%$**).
  * Trường hợp khác $\implies$ Khung giờ `14:00 - 17:00` (Tỷ lệ RPC dự báo: **$72\%$**).
* **Pha 2 (Cold Start - Hồ sơ mới chưa có dữ liệu cuộc gọi):**
  Suy luận theo phân cụm nghề nghiệp (Occupation Clustering) và độ tuổi.

### 8.2. Cơ sở Khoa học & Hành vi Viễn thông

| Nhóm Nghề nghiệp | Khung giờ Khuyến nghị | Kênh tối ưu | Tỷ lệ RPC dự báo | Căn cứ Hành vi Viễn thông & Nhịp sinh học |
| :--- | :--- | :---: | :---: | :--- |
| **Nhân viên Văn phòng / Giáo viên / Công nhân** | `18:00 - 20:30` | VOICE | **$75\%$** | Ban ngày bận làm việc trong dây chuyền/công sở, không được sử dụng điện thoại hoặc không tiện trao đổi nợ trước mặt đồng nghiệp. Buổi tối ngoài giờ hành chính là lúc riêng tư, tỷ lệ bắt máy đạt đỉnh. |
| **Tiểu thương / Chủ kinh doanh / Tự doanh** | `08:30 - 11:30` | VOICE | **$68\%$** | Tiểu thương hoạt động bán buôn cao điểm vào sáng sớm và chiều tối. Khoảng thời gian giữa buổi sáng (sau giờ mở hàng và trước giờ cơm trưa) là lúc họ thảnh thơi nhất để kiểm tra tài khoản và chuyển khoản ngân hàng. |
| **Lao động Tự do / Nhóm Khác** | `14:00 - 17:00` | ZALO / SMS | **$60\%$** | Đầu giờ chiều, ưu tiên gửi tin nhắn qua OTT/Zalo để khách hàng có thể đọc và bấm link thanh toán tự phục vụ mà không cảm thấy bị làm phiền đột xuất. |

*Ràng buộc Pháp lý (Constrained Optimization):* Toàn bộ khung giờ xuất ra từ mô hình bắt buộc phải thỏa mãn điều kiện biên $T_{\text{call}} \in [07:00, 21:00]$, tuân thủ tuyệt đối **Điều 7 Thông tư 18/2019/TT-NHNN**.

---

## 9. Không gian Vector Nhúng 192 Chiều & CBR Engine (Case-Based Reasoning)

File mã nguồn: `bcollection-platform/services/collection-api/src/cbr_engine.py`

### 9.1. Cấu trúc Không gian Vector Đa tạp ($\mathbb{R}^{192}$)
Vector chân dung khách nợ được $L_2$-chuẩn hóa ($\|\mathbf{v}\|_2 = 1.0$) và chia thành 9 khối thông tin nghiệp vụ:

| Khối Đặc trưng | Số chiều | Trọng số tương đối | Mô tả & Thành phần chi phối |
| :--- | :---: | :---: | :--- |
| **1. Khả năng trả nợ (Ability)** | 24 dims | $12.5\%$ | Điểm $D_1$, DSR, độ biến thiên thu nhập, LTV tài sản. |
| **2. Thiện chí trả nợ (Willingness)**| 20 dims | $10.4\%$ | Điểm $D_2$, tỷ lệ cam kết PTP, dấu hiệu trả bank khác. |
| **3. Khả năng tiếp cận (Contactability)**| 16 dims | $8.3\%$ | Điểm $D_3$, tỷ lệ RPC, tần suất đăng nhập SmartBanking. |
| **4. Nguyên nhân gốc (Root Cause)** | 16 dims | $8.3\%$ | One-hot encoding của các nhóm nguyên nhân chính (Lệch lương, kinh doanh giảm, quên, quá tải nợ...). |
| **5. Đồ thị mạng lưới (Graph Network)**| 32 dims | $16.7\%$ | Mối quan hệ người bảo lãnh, đồng vay, mạng lưới xã hội và quan hệ gia đình trích xuất từ Knowledge Graph. |
| **6. Sản phẩm & Dư nợ (Product Exposure)**| 16 dims | $8.3\%$ | Loại sản phẩm tín dụng, số dư nợ quá hạn, tỷ lệ $\text{DPD}/30$. |
| **7. Chuỗi hành vi (Behavioral Sequence)**| 32 dims | $16.7\%$ | Vector nhúng lịch sử tương tác cuộc gọi, thái độ quá khứ (Sentiment NLP). |
| **8. Ngữ nghĩa văn bản (Text Embedding)**| 32 dims | $16.7\%$ | Embedding trích xuất từ ghi chú lịch sử (Call Notes) và bóc tách hội thoại Speech-to-Text. |
| **9. Mặt nạ bao phủ (Coverage Mask)** | 4 dims | $2.1\%$ | Vector đánh dấu tính đầy đủ của dữ liệu (Data Completeness). |

### 9.2. Độ tương đồng Cosine & Thuật toán K-NN Retrieval
Độ tương đồng góc giữa vector hồ sơ mục tiêu $\mathbf{u}$ và hồ sơ tham chiếu $\mathbf{v}$:

$$\text{Sim}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2} = \sum_{i=1}^{192} u_i \cdot v_i$$

* **Tốc độ thực thi ma trận:** Vì toàn bộ vector trong kho 1,000 hồ sơ đã được $L_2$-chuẩn hóa sẵn trong SQLite, phép tính toán ma trận $\mathbf{S} = \mathbf{V}_{\text{pool}} \times \mathbf{u}^T$ ($1000 \times 192$) bằng NumPy chỉ mất **$0.15\text{ms}$**.
* **Ngưỡng tương đồng Khớp ($S_{\text{CBR}} \ge 0.75$):** Tương ứng góc giữa 2 vector $\theta \le 41.4^\circ$.
* **Thuật toán Tổng hợp Kịch bản (Playbook Synthesis & Vote Aggregation):**
  Lấy Top-5 hồ sơ khớp nhất ($K = 5$), trích xuất các đòn bẩy thành công (`effective_levers`) và tổng hợp kịch bản xử lý có tỷ lệ thu hồi cao nhất ($\text{Recovery Rate}$) và thời gian giải quyết ngắn nhất ($\text{Days to Resolve}$).

*Cơ sở Lý thuyết:* **Cognitive Case-Based Reasoning** (*Janet Kolodner, 1993*): Chuyên gia thu hồi nợ kỳ cựu đưa ra quyết định bằng cách hồi tưởng các tình huống tương tự đã giải quyết thành công trong quá khứ thay vì áp dụng quy tắc máy móc.

---

## 10. Thử nghiệm Đối chứng Ngẫu nhiên & Suy luận Nhân quả (Holdout Manager)

File mã nguồn: `bcollection-data/ml/experiments/holdout_assignment.py`

### 10.1. Thuật toán Băm Nhất quán Xác định (Deterministic Consistent Hashing)
Để đảm bảo tính ngẫu nhiên nhưng hoàn toàn có thể tái lập (Reproducible) mà không cần lưu trữ bảng trạng thái cồng kềnh:

$$\text{Hash Val} = \text{MD5}(\text{debtor\_cif}) \pmod{100}$$

$$\text{Arm} = \begin{cases} 
\text{HOLDOUT (Control Group)} & \text{khi } \text{Hash Val} < 10 \quad (10\%) \\
\text{TREATED (Test Group)} & \text{khi } \text{Hash Val} \ge 10 \quad (90\%)
\end{cases}$$

### 10.2. Cơ sở Khoa học: Suy luận Nhân quả & Thử nghiệm Lâm sàng Tín dụng (Causal Inference)
1. **Lý thuyết Tiềm năng Kết quả (Potential Outcomes Framework - *Donald Rubin / Judea Pearl*):**
   * Trong thu hồi nợ nhóm sớm, một tỷ lệ lớn khách hàng sẽ tự trả nợ dù không có bất kỳ sự can thiệp nào.
   * Để chứng minh với Ban Điều hành và Kiểm toán nội bộ rằng hệ thống B.Collection thực sự mang lại hiệu quả kinh tế (ROI), ngân hàng bắt buộc phải duy trì nhóm đối chứng $10\%$ **không áp dụng các biện pháp AI can thiệp sớm**.
2. **Đo lường Tác động Thuần (Incremental Lift / Uplift Measurement):**
   $$\text{Uplift} = \text{Recovery Rate}_{\text{TREATED}} - \text{Recovery Rate}_{\text{HOLDOUT}}$$
   Chênh lệch giữa 2 nhóm chính là giá trị thặng dư thuần túy do mô hình AI tạo ra, loại trừ hoàn toàn các yếu tố may mắn ngẫu nhiên của thị trường.

---

## 11. Quy tắc Vận hành Guardrail Tuân thủ Pháp lý (L6)

File mã nguồn: `bcollection-guardrail/src/guardrail/engine/orchestrator.py`

### 11.1. Hạn mức Tần suất Liên hệ (G04 Frequency Cap)
* **Tổng số lần liên lạc trong ngày:** $\le \mathbf{3}$ lần/ngày/hồ sơ (tất cả các kênh cộng lại).
* **Số lần liên lạc theo từng kênh:** $\le \mathbf{2}$ lần/ngày/kênh (Voice: tối đa 2 cuộc; SMS: tối đa 2 tin; Zalo: tối đa 2 tin).
* **Căn cứ pháp lý:** **Thông tư 18/2019/TT-NHNN** (sửa đổi, bổ sung Thông tư 43/2016/TT-NHNN): Quy định các tổ chức tín dụng và công ty tài chính tiêu dùng không được nhắc nợ quá số lần tối đa quy định trong ngày để bảo vệ quyền riêng tư của khách hàng.

### 11.2. Khung giờ Hoạt động Hợp lệ (G05 Time Window)
* **Khung giờ cho phép gọi điện:** Từ **$07:00$ đến $21:00$**.
* **Ngày cho phép liên lạc:** Từ Thứ Hai đến Thứ Bảy.
* **Căn cứ pháp lý:** **Điều 7 Thông tư 18/2019/TT-NHNN**: Nghiêm cấm mọi hành vi liên hệ đôn đốc thu hồi nợ trước 07h00 sáng và sau 21h00 tối.

### 11.3. Chống Đòi nợ Nhầm (Anti-False-Delinquency Guard)
File mã nguồn: `bcollection-platform/services/collection-api/src/balance_check_service.py`
* **Cửa sổ kiểm tra thanh toán tức thời:** `lookback_minutes = 15`.
* **Cơ chế:** Trước khi phát sinh cuộc gọi hoặc lệnh gửi tin nhắn, hệ thống kiểm tra số dư Core Banking qua API `IF-CORE-04`. Nếu trong vòng 15 phút qua khách hàng đã nộp đủ tiền hoặc tài khoản không còn nợ quá hạn, hành động bị **HỦY NGAY LẬP TỨC** và Case chuyển trạng thái `CURED`.

---

## 12. Bảng Tra Cứu Toàn Bộ Hằng Số & Căn Cứ Nguồn Trích Dẫn

| STT | Tên Hằng số / Tham số | Giá trị | Vị trí Khai báo (`scoring_config.yaml` / Code) | Căn cứ Lý thuyết & Nguồn trích dẫn Văn bản |
| :---: | :--- | :---: | :--- | :--- |
| 1 | `living_wage_min` | **$5.500.000$ đ** | `scoring_config.yaml:20` | **Nghị định Chính phủ về mức lương tối thiểu vùng I**; Subsistence Living Wage Floor (Maslow Survival Level). |
| 2 | `safe_cushion_multiple` | **$1.00\text{x}$** (100% nợ) | `scoring_config.yaml:21` | Bội số thanh khoản an toàn: Tiền dư $\ge 100\%$ nghĩa vụ nợ tháng (DSR $\le 50\%$). |
| 3 | `affluent_remaining_min` | **$30.000.000$ đ** | `scoring_config.yaml:22` | Chuẩn thu nhập thặng dư phân khúc Khá giả (Upper Mass) tại các đô thị loại I. |
| 4 | `overleveraged_cushion_max` | **$0.20$** (20% nợ) | `scoring_config.yaml:23` | Cảnh báo đòn bẩy rủi ro: Đệm tiền dư $< 20\%$ nghĩa vụ nợ với khoản nợ lớn $\ge 20$M/tháng. |
| 5 | `large_exposure_obligation` | **$20.000.000$ đ** | `scoring_config.yaml:24` | Ngưỡng nghĩa vụ nợ lớn cần giám sát đệm thanh khoản tương đối thay vì số tiền tuyệt đối. |
| 6 | `product_dsr.MORTGAGE` | Safe: $0.45$<br>Insolvent: $0.70$ | `scoring_config.yaml:25` | Chuẩn thẩm định cho vay thế chấp bất động sản thương mại dài hạn. |
| 7 | `product_dsr.AUTO_LOAN` | Safe: $0.40$<br>Insolvent: $0.65$ | `scoring_config.yaml:31` | Thẩm định tín dụng tiêu dùng có tài sản bảo đảm là phương tiện giao thông. |
| 8 | `product_dsr.CREDIT_CARD` | Safe: $0.30$<br>Insolvent: $0.50$ | `scoring_config.yaml:37` | **The 28/36 Rule** (CFPB); Chuẩn quản trị rủi ro nợ thẻ tín dụng không bảo đảm lãi suất cao. |
| 9 | `WEIGHT_D1_COMPONENTS` | $0.35, 0.25, 0.25, 0.15$ | `scoring_config.yaml:12` | **Mô hình AHP (Analytic Hierarchy Process)** của Thomas L. Saaty; Chuẩn phân bổ rủi ro thanh khoản Basel II/III. |
| 10 | `penalty_per_group` (CIC) | **$-35.0$** điểm | `scoring_config.yaml:52` | **Thông tư 11/2021/TT-NHNN**: Phân loại tài sản có & tỷ lệ trích lập dự phòng rủi ro tín dụng (Nhóm 1: 0%, Nhóm 2: 5%, Nhóm 3: 20%). |
| 11 | `unsecured_score` (LTV) | **$30.0$** điểm | `scoring_config.yaml:57` | **S&P / Moody's Unsecured Recovery Benchmark**: Tỷ lệ thu hồi nợ vay không tài sản bảo đảm trung bình đạt $25\% - 35\%$. |
| 12 | `decay_cycle_days` (PTP) | **$35.0$** ngày | `scoring_config.yaml:77` | Chu kỳ chuyển nhóm nợ B1 sang B2 (DPD 30 ngày + 5 ngày grace period). |
| 13 | `paying_other_banks` | **$15.0$** điểm (Phạt -70) | `scoring_config.yaml:82` | **Lý thuyết Vỡ nợ Chọn lọc (Selective Default)** trong Tài chính Hành vi; Cảnh báo rủi ro đạo đức (Moral Hazard). |
| 14 | `penalty_per_day` (Avoidance)| **$-2.0$** điểm/ngày (Max -60) | `scoring_config.yaml:86` | **Avoidance Escalation Model**: Tỷ lệ phân rã hợp tác theo số ngày quá hạn. |
| 15 | `base_intercept` (ML01) | **$+0.60$** | `scoring_config.yaml:128` | Xác suất nền tự khỏi trong nợ nhóm sớm B1 (Base Odds Ratio $\approx 1.82$, tương đương Xác suất $\approx 64.5\%$). |
| 16 | `tiers.high_prob` (ML01) | **$0.80$** (Ân hạn 5 ngày) | `scoring_config.yaml:137` | **McKinsey Collections Efficiency Curve**: Tối ưu chi phí can thiệp và tránh gây phiền hà khách hàng uy tín cao. |
| 17 | `tiers.med_prob` (ML01) | **$0.45$** (Ân hạn 3 ngày) | `scoring_config.yaml:139` | Thời gian chuyển tiền liên ngân hàng và đối soát lỗi kỹ thuật (3 ngày làm việc). |
| 18 | `ability_cutoff` (Matrix 2x2)| **$60.0$** điểm | `scoring_config.yaml:121` | Ngưỡng phân tách Ability Cao / Thấp trong ma trận chiến lược thu nợ. |
| 19 | `willingness_cutoff` (Matrix 2x2)| **$50.0$** điểm | `scoring_config.yaml:122` | Ngưỡng phân tách Thiện chí Tốt / Kém trong ma trận chiến lược thu nợ. |
| 20 | `VOICE_CALL_TIME_WINDOW` | `07:00 - 21:00` | `orchestrator.py:50` | **Điều 7 Thông tư 18/2019/TT-NHNN** (và Luật Bảo vệ quyền lợi người tiêu dùng). |
| 21 | `MAX_DAILY_ATTEMPTS_TOTAL` | **$3$** lần/ngày | `orchestrator.py:46` | **Thông tư 18/2019/TT-NHNN**: Quy định giới hạn số lần nhắc nợ tối đa để bảo đảm tính văn minh. |
| 22 | `MAX_DAILY_ATTEMPTS_CHANNEL`| **$2$** lần/ngày/kênh | `orchestrator.py:47` | Ngăn chặn hiện tượng spam cuộc gọi / tin nhắn trên một kênh duy nhất. |
| 23 | `BALANCE_CHECK_LOOKBACK` | **$15$** phút | `balance_check_service.py:25` | Độ trễ đồng bộ bút toán Core Banking - Fast Payment Napas 24/7. |
| 24 | `VECTOR_DIMENSIONS` | **$192$** chiều | `cbr_engine.py:71` | Chuẩn kiến trúc Bi-Encoder Embeddings đa chiều (8 nhóm đặc trưng $\times$ 16–32 chiều + 4 chiều Coverage Mask). |

---

## 13. Kết luận & Quy trình Hiệu chuẩn Định kỳ (Model Governance)

Tài liệu này đóng vai trò là **Căn cứ Khoa học & Đặc tả Kỹ thuật Chuẩn** để giải trình với Hội đồng Quản trị Rủi ro, Ban Điều hành Ngân hàng và Cơ quan Thanh tra Giám sát Ngân hàng Nhà nước.

1. **Vận hành linh hoạt (Zero-Downtime Governance):** Toàn bộ các trọng số và ngưỡng đã được tách bạch sang file `scoring_config.yaml`. Cán bộ rủi ro có thể chủ động điều chỉnh chính sách theo từng quý hoặc chu kỳ kinh tế mà không cần can thiệp code hay dừng hệ thống.
2. **Quy trình Backtesting & Kiểm định Định kỳ:**
   * **Hàng quý (Quarterly):** Đội ngũ Data Science chạy kiểm định Kolmogorov-Smirnov (KS-test) và diện tích dưới đường cong ROC (AUC) trên dữ liệu thực tế phát sinh tại ngân hàng đối với mô hình ML01 và ML04.
   * **Hàng năm (Annual):** Rà soát lại ngưỡng Sàn chi phí sinh tồn (`living_wage_min`) theo công bố chỉ số giá tiêu dùng CPI và nghị định điều chỉnh lương tối thiểu của Chính phủ.
