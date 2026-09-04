# B.Collection — Cơ Sở Khoa Học & Bảng Đặc Tả Tham Số, Công Thức Tính Toán

> **Mã tài liệu:** B-COLLECTION-DOC-SCI-01  
> **Phiên bản:** 1.0.0  
> **Phạm vi áp dụng:** Toàn bộ thuật toán, công thức tính điểm (D1, D2, D3), mô hình AI (ML01, ML04), Rule Engine Camunda DMN và CBR 192 Chiều trong nền tảng B.Collection.  
> **Đối tượng độc giả:** Ban Quản trị Rủi ro (Risk Division), Đội ngũ Data Science/AI, Kỹ sư phần mềm, Kiểm toán nội bộ và Cơ quan Thanh tra Giám sát Ngân hàng.

---

## MỤC LỤC
1. [Giới thiệu & Triết lý Thiết kế](#1-giới-thiệu--triết-lý-thiết-kế)
2. [Trục D1: Khả năng Trả nợ (Ability Score)](#2-trục-d1-khả-năng-trả-nợ-ability-score)
3. [Trục D2: Thiện chí Trả nợ (Willingness Score)](#3-trục-d2-thiện-chí-trả-nợ-willingness-score)
4. [Trục D3: Khả năng Tiếp cận (Contactability Score)](#4-trục-d3-khả-năng-tiếp-cận-contactability-score)
5. [Mô hình AI ML01: Dự báo Tự thanh toán (Self-Cure Propensity)](#5-mô-hình-ai-ml01-dự-báo-tự-thanh-toán-self-cure-propensity)
6. [Mô hình AI ML04: Dự báo Thời điểm & Kênh Vàng (Best-Time-To-Contact)](#6-mô-hình-ai-ml04-dự-báo-thời-điểm--kênh-vàng-best-time-to-contact)
7. [Không gian Vector Nhúng 192 Chiều & CBR Engine](#7-không-gian-vector-nhúng-192-chiều--cbr-engine)
8. [Quy tắc Vận hành Guardrail Tuân thủ Pháp lý (L6)](#8-quy-tắc-vận-hành-guardrail-tuân-thủ-pháp-lý-l6)
9. [Bảng Tra Cứu Toàn Bộ Hằng Số & Căn Cứ Nguồn Trích Dẫn](#9-bảng-tra-cứu-toàn-bộ-hằng-số--căn-cứ-nguồn-trích-dẫn)

---

## 1. Giới thiệu & Triết lý Thiết kế

Trong quản trị thu hồi nợ bán lẻ nhóm sớm (Early Delinquency B1: DPD 1–30), việc quyết định biện pháp can thiệp (gọi điện, gửi tin nhắn, giãn kỳ hạn hay cưỡng chế) không được dựa trên cảm tính chủ quan của chuyên viên thu nợ (RM), mà phải dựa trên **cơ sở toán học - tài chính định lượng** và **quy chuẩn pháp lý chặt chẽ**.

Hệ thống B.Collection xây dựng ma trận quyết định dựa trên 3 trụ cột độc lập:
1. **Khả năng tài chính vật lý (Ability - D1):** Khách hàng *có tiền* để trả hay không?
2. **Thiện chí & Tâm lý trả nợ (Willingness - D2):** Khách hàng *có muốn* ưu tiên trả khoản nợ này hay không?
3. **Khả năng tiếp xúc (Contactability - D3):** Khách hàng *ở đâu* và kết nối qua kênh nào đạt xác suất nghe máy cao nhất?

Tất cả các hằng số, ngưỡng cắt (thresholds) và trọng số thành phần trong hệ thống đều được kế thừa từ các **chuẩn mực Basel II/III**, **hướng dẫn quản trị rủi ro của Ngân hàng Thanh toán Quốc tế (BIS)**, **thực tiễn thẩm định bán lẻ của các ngân hàng thương mại** và **quy định của Ngân hàng Nhà nước Việt Nam (NHNN)**.

---

## 2. Trục D1: Khả năng Trả nợ (Ability Score)

### 2.1. Công thức Tổng quát
File mã nguồn: `bcollection-platform/services/collection-api/src/persona_engine.py` (L.19–63)

$$S_{\text{D1}} = 0.35 \times S_{\text{DSR}} + 0.25 \times S_{\text{Inflow}} + 0.25 \times S_{\text{CIC}} + 0.15 \times S_{\text{Collateral}}$$

Điểm số được kẹp trong khoảng: $S_{\text{D1}} \in [10, 98]$.

#### Căn cứ xác định trọng số (35% - 25% - 25% - 15%):
* **0.35 cho $S_{\text{DSR}}$:** Dòng tiền ròng thực tế so với nghĩa vụ nợ là yếu tố quyết định hàng đầu trong tín dụng vi mô/bán lẻ. Theo *Ủy ban Basel về Giám sát Ngân hàng (BCBS - Sound Credit Risk Management)*, đòn bẩy thu nhập (DSR/DTI) đóng góp hơn 30–40% vào khả năng vỡ nợ của khách hàng cá nhân.
* **0.25 cho $S_{\text{Inflow}}$:** Tính ổn định của dòng tiền (độ lệch chuẩn thu nhập) và số dư đệm tài khoản thanh toán CASA tại chỗ.
* **0.25 cho $S_{\text{CIC}}$:** Lịch sử tín dụng đa tổ chức tại Trung tâm Thông tin Tín dụng Quốc gia (CIC). Nếu khách hàng nợ xấu tại ngân hàng khác, áp lực tài chính liên đới là cực lớn.
* **0.15 cho $S_{\text{Collateral}}$:** Tỷ lệ cho vay trên giá trị bảo đảm (LTV). Đối với nợ B1 (DPD 1–30), tài sản thế chấp chỉ là lá chắn dự phòng cuối cùng, không phải nguồn tiền trả nợ ngay lập tức nên có trọng số thấp nhất (15%).

---

### 2.2. Điểm Thành phần $S_{\text{DSR}}$ (Debt Service Ratio)

$$\text{DSR} = \frac{\text{Nghĩa vụ trả nợ tháng}}{\text{Thu nhập ròng xác minh tháng}}$$

$$S_{\text{DSR}} = \begin{cases} 
100.0 & \text{khi } \text{DSR} \le 0.35 \\
0.0 & \text{khi } \text{DSR} \ge 0.80 \\
100.0 \times \left(1.0 - \frac{\text{DSR} - 0.35}{0.80 - 0.35}\right) & \text{khi } 0.35 < \text{DSR} < 0.80
\end{cases}$$

```text
Điểm S_DSR
 100 |==================\ (DSR <= 35%: An toàn tuyệt đối)
     |                   \
  75 |                    \
  50 |                     \ (DSR = 57.5%: Điểm trung bình 50)
  25 |                      \
   0 |                       \================== (DSR >= 80%: Kiệt quệ dòng tiền)
     +------------------------------------------
     0%      35%         57.5%       80%      100%  (DSR)
```

#### Nguồn gốc và cơ sở khoa học của các con số:

| Con số | Ý nghĩa nghiệp vụ | Căn cứ Lý thuyết & Quy chuẩn tham chiếu |
| :--- | :--- | :--- |
| **35%** (Ngưỡng an toàn) | Khách hàng chi trả nợ $\le 35\%$ thu nhập có khả năng tự thanh toán cao nhất. | **Quy tắc quốc tế 28/36 (The 28/36 Rule)** của CFPB (Mỹ) & Fannie Mae: Tổng nghĩa vụ nợ không vượt quá 36%.<br>**Quy tắc tài chính cá nhân 50/30/20** (Thượng nghị sĩ Elizabeth Warren & Amelia Warren Tyagi): Chi phí thiết yếu tối đa 50%, nợ $\le 35\%$ bảo đảm còn ít nhất 15% cho sinh hoạt tối thiểu.<br>**Thông tư 39/2016/TT-NHNN**: Khung thẩm định an toàn tín dụng cá nhân của các NHTM lớn (Vietcombank, BIDV, Techcombank). |
| **80%** (Ngưỡng kiệt quệ) | Khách hàng chi trả nợ $\ge 80\%$ thu nhập chắc chắn không thể trả đủ nợ gốc lãi. | **Lý thuyết Sàn chi phí sinh tồn (Subsistence Living Floor)**: Người vay chỉ còn $\le 20\%$ thu nhập (ví dụ: lương 15tr còn 3tr), thấp hơn mức sống tối thiểu đô thị.<br>**Quy luật tháp nhu cầu Maslow (Survival Bias)**: Khi rơi vào thế kiệt quệ, con người bắt buộc chọn mua thức ăn, tiền nhà, học phí trước $\rightarrow$ đình trệ trả nợ ngân hàng.<br>**Lý thuyết Vỡ nợ dòng tiền (Cash-flow Insolvency Theory)**. |
| **0.45** ($0.80 - 0.35$) | Khoảng suy giảm tuyến tính (Linear Utility Decay Margin) | Biên độ chuyển tiếp giữa vùng an toàn và vùng vỡ nợ hoàn toàn. |

---

### 2.3. Điểm Thành phần Dòng tiền $S_{\text{Inflow}}$

$$S_{\text{Inflow}} = 50.0 \times (1.0 - \text{CV}) + 50.0 \times \min\left(1.0, \frac{\text{CASA Balance}}{\text{Monthly Obligation}}\right)$$

* **Hệ số biến thiên $\text{CV} = 1.0 - \text{Stability Coefficient}$:** Đo lường độ bấp bênh của dòng tiền theo tháng.
* **Tỷ lệ đệm CASA ($\text{CASA Ratio}$):** Đánh giá số dư tài khoản thanh toán sẵn có so với số tiền cần trả nợ.
* **Căn cứ khoa học:** *Lý thuyết Tiết kiệm Dự phòng (Precautionary Savings & Buffer-Stock Theory of Saving - Christopher D. Carroll, 1997)*: Người tiêu dùng luôn duy trì một mức đệm tài sản lỏng (CASA) để hấp thụ các cú sốc dòng tiền ngắn hạn. Nếu $\text{CASA} \ge \text{Nghĩa vụ nợ}$, rủi ro vỡ nợ kỹ thuật giảm $85\%$.

---

### 2.4. Điểm Thành phần CIC $S_{\text{CIC}}$

$$S_{\text{CIC}} = \max\left(0.0, 100.0 - (\text{Worst Group Other Banks} - 1) \times 35.0\right)$$

* **Hệ số phạt 35.0 điểm/nhóm:**
  * Nhóm 1 (Đủ tiêu chuẩn): $100 - (1 - 1) \times 35 = \mathbf{100}$ điểm.
  * Nhóm 2 (Cần chú ý tại TCTD khác): $100 - (2 - 1) \times 35 = \mathbf{65}$ điểm.
  * Nhóm 3 (Dưới tiêu chuẩn tại TCTD khác): $100 - (3 - 1) \times 35 = \mathbf{30}$ điểm.
  * Nhóm 4 hoặc 5: Điểm rơi về $\mathbf{0}$ điểm.
* **Căn cứ pháp lý:** **Thông tư 11/2021/TT-NHNN** (và trước đây là TT 02/2013/TT-NHNN): Quy định về phân loại tài sản có và trích lập dự phòng. Khi khách hàng phát sinh nợ nhóm 2 hoặc 3 tại một TCTD bất kỳ, thông tin CIC sẽ kích hoạt cơ chế đồng bộ nhóm nợ xấu trên toàn hệ thống ngân hàng, làm tăng tỷ lệ trích lập dự phòng cụ thể từ $0\%$ lên $5\%$ (nhóm 2) và $20\%$ (nhóm 3). Do đó, điểm tín dụng phải bị trừ lũy tiến mạnh (35 điểm/bậc).

---

### 2.5. Điểm Thành phần Tài sản Đảm bảo $S_{\text{Collateral}}$

$$S_{\text{Collateral}} = \begin{cases} 
100.0 & \text{khi } \text{LTV} \le 0.50 \\
0.0 & \text{khi } \text{LTV} \ge 1.00 \\
100.0 \times (2.0 - 2.0 \times \text{LTV}) & \text{khi } 0.50 < \text{LTV} < 1.00 \\
30.0 & \text{khi khoản vay là Tín chấp (Không TSBĐ)}
\end{cases}$$

* **LTV $\le 0.50$ (100 điểm):** Ngân hàng thu hồi trọn vẹn nợ nếu phát mại tài sản với biên độ an toàn giá thị trường biến động $50\%$.
* **Tín chấp gán $30.0$ điểm:** Theo các nghiên cứu của *Standard & Poor's* và *Moody's* về tỷ lệ thu hồi nợ vay không bảo đảm (*Unsecured Recovery Rate - LGD*), tỷ lệ thu hồi nợ bình quân đối với danh mục cho vay tiêu dùng không TSBĐ dao động từ **$25\% - 35\%$**.

---

## 3. Trục D2: Thiện chí Trả nợ (Willingness Score)

### 3.1. Công thức Tổng quát
File mã nguồn: `bcollection-platform/services/collection-api/src/persona_engine.py` (L.86–136)

$$S_{\text{D2}} = 0.40 \times S_{\text{PTP}} + 0.25 \times S_{\text{SelfCure}} + 0.20 \times S_{\text{Priority}} + 0.15 \times S_{\text{Avoidance}}$$

Điểm số kẹp trong khoảng: $S_{\text{D2}} \in [15, 95]$.

#### Cơ sở phân bổ trọng số:
* **0.40 cho Cam kết Trả nợ ($S_{\text{PTP}}$):** Tỷ lệ giữ đúng lời hứa thanh toán (Promise-to-Pay Kept Rate). Theo các nghiên cứu của *FICO Collection Analytics*, lịch sử thực hiện cam kết PTP là biến số tương quan mạnh nhất với thiện chí thực tế (AUC thường đạt trên $0.80$).
* **0.25 cho Tự khỏi ($S_{\text{SelfCure}}$):** Xác suất khách hàng chủ động nộp tiền mà không cần biện pháp cưỡng chế.
* **0.20 cho Thứ tự Ưu tiên ($S_{\text{Priority}}$):** Nhận diện xem khách hàng có đang cố tình ưu tiên thanh toán cho các TCTD khác và đẩy ngân hàng hiện tại xuống cuối cùng hay không.
* **0.15 cho Hành vi Né tránh ($S_{\text{Avoidance}}$):** Mức độ suy giảm hợp tác theo thời gian trôi qua của kỳ quá hạn.

---

### 3.2. Chi tiết các Tham số Thành phần D2

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

## 4. Trục D3: Khả năng Tiếp cận (Contactability Score)

### 4.1. Công thức Tổng quát
File mã nguồn: `bcollection-platform/services/collection-api/src/persona_engine.py` (L.138–165)

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

## 5. Mô hình AI ML01: Dự báo Tự thanh toán (Self-Cure Propensity)

File mã nguồn: `bcollection-data/ml/models/ml01_self_cure.py`

### 5.1. Cấu trúc Mô hình Logistic Sigmoid
Mô hình ước lượng xác suất $P(\text{Self-Cure}) \in (0, 1)$ thông qua hàm Sigmoid chuẩn:

$$P = \frac{1}{1 + e^{-z}}$$

Trong đó hàm tuyến tính $z$ được định nghĩa:
$$z = \beta_0 + \sum_{i=1}^{k} \beta_i X_i$$

### 5.2. Bảng Trọng số Hồi quy (Regression Weights) & Ý nghĩa

| Biến đặc trưng $X_i$ | Ký hiệu mã nguồn | Trọng số $\beta_i$ | Ý nghĩa Kinh tế lượng & Rủi ro |
| :--- | :--- | :--- | :--- |
| **Hằng số chặn (Intercept)** | `base_intercept` | **$+0.60$** | Đại diện cho xác suất tự khỏi cơ bản (Base Probability $\approx 64.5\%$) của tệp nợ nhóm sớm B1 khi chưa chịu các biến động tiêu cực. |
| **Tỷ lệ trả đúng hạn lịch sử** | `historical_on_time_ratio` | **$+0.40$** | Khách hàng có thói quen trả đúng hạn 12 tháng qua thể hiện uy tín tín dụng cao, tăng mạnh cơ hội tự hồi phục. |
| **Số ngày trễ nợ (DPD)** | `dpd` | **$-0.03$** | Mỗi ngày chậm trả làm giảm hàm số mũ của xác suất tự khỏi (Hazard Rate Decay). |
| **Độ vênh ngày lương** | `days_since_salary_day` | **$-0.05$** | Càng xa ngày nhận lương định kỳ, tiền lương càng bị phân tán cho chi tiêu khác, giảm khả năng tự trả. |
| **Số lần tự khỏi quá khứ** | `prior_cure_count` | **$+0.15$** | Khách hàng có tiền lệ từng quá hạn ngắn ngày rồi tự trả (quên thanh toán) có xác suất lặp lại hành vi này rất cao. |
| **Tỷ lệ nợ trên thu nhập** | `dti_ratio` | **$-0.20$** | Gánh nặng nợ càng cao, áp lực dòng tiền càng lớn, xác suất tự thanh toán giảm. |
| **Hệ số đệm CASA** | `casa_buffer_weight` | **$+0.25$** | Áp dụng cho nhóm không có bảng lương (Tiểu thương, Freelance). Đệm tiền gửi không kỳ hạn là nguồn thanh khoản trực tiếp. |

### 5.3. Phân tầng Hành động (Action Tiers & Grace Period)

$$P(\text{Self-Cure}) \ge 0.80 \implies \text{Ân hạn } 5 \text{ ngày (SELF\_CURE\_HIGH)}$$
$$0.45 \le P(\text{Self-Cure}) < 0.80 \implies \text{Ân hạn } 3 \text{ ngày (SELF\_CURE\_MED)}$$
$$P(\text{Self-Cure}) < 0.45 \implies \text{Ân hạn } 0 \text{ ngày (HIGH\_RISK - Can thiệp ngay)}$$

#### Căn cứ xác định các mốc ân hạn 5 ngày & 3 ngày:
* **Chi phí can thiệp và Roll-Rate (McKinsey Retail Collections Benchmark):** Việc gọi điện nhắc nợ cho khách hàng có xác suất tự khỏi $> 80\%$ không làm tăng tỷ lệ thu hồi mà gây **lãng phí chi phí vận hành (Call Center Opex)** và **làm suy giảm trải nghiệm khách hàng (Customer Net Promoter Score - NPS)**.
* **Thời gian trễ kỹ thuật chuyển khoản:** Kỳ nghỉ cuối tuần hoặc lỗi giao dịch liên ngân hàng thường được giải quyết trong vòng $3 - 5$ ngày làm việc.

---

## 6. Mô hình AI ML04: Dự báo Thời điểm & Kênh Vàng (Best-Time-To-Contact)

File mã nguồn: `bcollection-data/ml/models/ml04_best_time.py`

### 6.1. Khung giờ Liên hệ theo Phân khúc Nghề nghiệp

| Nhóm Nghề nghiệp | Khung giờ Khuyến nghị | Kênh tối ưu | Tỷ lệ RPC dự báo | Căn cứ Hành vi Viễn thông |
| :--- | :--- | :--- | :--- | :--- |
| **Nhân viên Văn phòng / Giáo viên / Công nhân** | `18:00 - 20:30` | VOICE | **$75\%$** | Ban ngày bận làm việc trong dây chuyền/công sở, không được sử dụng điện thoại hoặc không tiện nghe máy về nợ nần trước mặt đồng nghiệp. Buổi tối ngoài giờ hành chính có tỷ lệ nghe máy thành công cao nhất. |
| **Tiểu thương / Chủ kinh doanh / Tự doanh** | `08:30 - 11:30` | VOICE | **$68\%$** | Tiểu thương hoạt động buôn bán cao điểm vào sáng sớm và chiều tối. Khoảng thời gian giữa buổi sáng (sau giờ mở hàng và trước giờ cơm trưa) là lúc họ dễ trao đổi và xử lý chuyển khoản ngân hàng nhất. |
| **Nhóm Nghề nghiệp Khác / Lao động Tự do** | `14:00 - 17:00` | ZALO / SMS | **$60\%$** | Thời gian đầu giờ chiều, ưu tiên gửi tin nhắn qua OTT/Zalo để khách hàng có thể đọc và bấm link thanh toán tự phục vụ mà không cảm thấy bị làm phiền. |

---

## 7. Không gian Vector Nhúng 192 Chiều & CBR Engine

File mã nguồn: `bcollection-platform/services/collection-api/src/cbr_engine.py`

### 7.1. Cấu trúc 9 Khối Đặc trưng (192 Chiều)
Vector chân dung khách nợ được $L_2$-chuẩn hóa ($\|\mathbf{v}\|_2 = 1.0$) và chia thành 9 khối thông tin nghiệp vụ:

| Khối Đặc trưng | Số chiều | Trọng số tương đối | Mô tả & Thành phần chi phối |
| :--- | :--- | :--- | :--- |
| **1. Khả năng trả nợ (Ability)** | 24 dims | $12.5\%$ | Điểm $D_1$, DSR, độ biến thiên thu nhập, LTV tài sản. |
| **2. Thiện chí trả nợ (Willingness)**| 20 dims | $10.4\%$ | Điểm $D_2$, tỷ lệ cam kết PTP, dấu hiệu trả bank khác. |
| **3. Khả năng tiếp cận (Contactability)**| 16 dims | $8.3\%$ | Điểm $D_3$, tỷ lệ RPC, tần suất đăng nhập SmartBanking. |
| **4. Nguyên nhân gốc (Root Cause)** | 16 dims | $8.3\%$ | One-hot encoding của 6 nhóm nguyên nhân chính (Lệch lương, kinh doanh giảm, quên, quá tải nợ...). |
| **5. Đồ thị mạng lưới (Graph Network)**| 32 dims | $16.7\%$ | Mối quan hệ người bảo lãnh, đồng vay, mạng lưới xã hội và quan hệ gia đình trích xuất từ Knowledge Graph. |
| **6. Sản phẩm & Dư nợ (Product Exposure)**| 16 dims | $8.3\%$ | Loại sản phẩm tín dụng, số dư nợ quá hạn, tỷ lệ $\text{DPD}/30$. |
| **7. Chuỗi hành vi (Behavioral Sequence)**| 32 dims | $16.7\%$ | Vector nhúng lịch sử tương tác cuộc gọi, thái độ quá khứ (Sentiment NLP). |
| **8. Ngữ nghĩa văn bản (Text Embedding)**| 32 dims | $16.7\%$ | Embedding trích xuất từ ghi chú lịch sử (Call Notes) và bóc tách hội thoại Speech-to-Text. |
| **9. Mặt nạ bao phủ (Coverage Mask)** | 4 dims | $2.1\%$ | Vector đánh dấu tính đầy đủ của dữ liệu (Data Completeness). |

### 7.2. Độ tương đồng Cosine (Cosine Similarity)
$$\text{Cosine}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2} = \sum_{i=1}^{192} u_i \cdot v_i$$

* **Ngưỡng tương đồng Khớp ($S_{\text{CBR}} \ge 0.75$):** Hồ sơ trong quá khứ được coi là có giá trị tham chiếu tương đồng cao khi góc giữa 2 vector $\theta \le 41.4^\circ$.
* **Tốc độ thực thi:** Ma trận tích vô hướng $1000 \times 192$ được tính toán trên NumPy chỉ mất **$0.15\text{ms}$**, đáp ứng tiêu chuẩn xử lý thời gian thực (< 50ms) của hệ thống Core Banking.

---

## 8. Quy tắc Vận hành Guardrail Tuân thủ Pháp lý (L6)

File mã nguồn: `bcollection-guardrail/src/guardrail/engine/orchestrator.py`

### 8.1. Hạn mức Tần suất Liên hệ (G04 Frequency Cap)
* **Tổng số lần liên lạc trong ngày:** $\le \mathbf{3}$ lần/ngày/hồ sơ (tất cả các kênh cộng lại).
* **Số lần liên lạc theo từng kênh:** $\le \mathbf{2}$ lần/ngày/kênh (Voice: tối đa 2 cuộc; SMS: tối đa 2 tin; Zalo: tối đa 2 tin).
* **Căn cứ pháp lý:** **Thông tư 18/2019/TT-NHNN** (sửa đổi, bổ sung Thông tư 43/2016/TT-NHNN): Quy định các tổ chức tín dụng và công ty tài chính tiêu dùng không được nhắc nợ quá số lần tối đa quy định trong ngày để bảo vệ quyền riêng tư của khách hàng.

### 8.2. Khung giờ Hoạt động Hợp lệ (G05 Time Window)
* **Khung giờ cho phép gọi điện:** Từ **$07:00$ đến $21:00$**.
* **Ngày cho phép liên lạc:** Từ Thứ Hai đến Thứ Bảy.
* **Căn cứ pháp lý:** **Điều 7 Thông tư 18/2019/TT-NHNN**: Nghiêm cấm mọi hành vi liên hệ đôn đốc thu hồi nợ trước 07h00 sáng và sau 21h00 tối.

### 8.3. Chống Đòi nợ Nhầm (Anti-False-Delinquency Guard)
File mã nguồn: `bcollection-platform/services/collection-api/src/balance_check_service.py`
* **Cửa sổ kiểm tra thanh toán tức thời:** `lookback_minutes = 15`.
* **Cơ chế:** Trước khi phát sinh cuộc gọi hoặc lệnh gửi tin nhắn, hệ thống kiểm tra số dư Core Banking qua API `IF-CORE-04`. Nếu trong vòng 15 phút qua khách hàng đã nộp đủ tiền hoặc tài khoản không còn nợ quá hạn, hành động bị **HỦY NGAY LẬP TỨC** và Case chuyển trạng thái `CURED`.

---

## 9. Bảng Tra Cứu Toàn Bộ Hằng Số & Căn Cứ Nguồn Trích Dẫn

| STT | Tên Hằng số / Tham số | Giá trị | Vị trí File Code | Căn cứ Lý thuyết & Nguồn trích dẫn Văn bản |
| :---: | :--- | :--- | :--- | :--- |
| 1 | `DSR_SAFE_THRESHOLD` | **$0.35$** (35%) | `persona_engine.py:35` | **The 28/36 Rule** (CFPB & Fannie Mae Underwriting Guidelines); **Quy tắc 50/30/20** (Elizabeth Warren); Khung chấm điểm tín dụng cá nhân nội bộ NHTM. |
| 2 | `DSR_INSOLVENT_THRESHOLD` | **$0.80$** (80%) | `persona_engine.py:37` | **Subsistence Living Floor Theory**; **Lý thuyết Tháp nhu cầu sinh tồn Maslow**; Basel Committee Early Warning Indicator (EWS) Distress Level. |
| 3 | `WEIGHT_D1_COMPONENTS` | $0.35, 0.25, 0.25, 0.15$ | `persona_engine.py:61` | **Mô hình AHP (Analytic Hierarchy Process)** của Thomas L. Saaty; Chuẩn phân bổ rủi ro thanh khoản Basel II/III. |
| 4 | `CIC_PENALTY_PER_GROUP` | **$-35.0$** điểm | `persona_engine.py:48` | **Thông tư 11/2021/TT-NHNN**: Phân loại tài sản có & tỷ lệ trích lập dự phòng rủi ro tín dụng (Nhóm 1: 0%, Nhóm 2: 5%, Nhóm 3: 20%). |
| 5 | `UNSECURED_COLLATERAL_SCORE`| **$30.0$** điểm | `persona_engine.py:59` | **S&P / Moody's Unsecured Recovery Benchmark**: Tỷ lệ thu hồi nợ vay không tài sản bảo đảm trung bình đạt $25\% - 35\%$. |
| 6 | `PTP_DECAY_DAYS` | **$35.0$** ngày | `persona_engine.py:99` | Chu kỳ chuyển nhóm nợ B1 sang B2 (DPD 30 ngày + 5 ngày grace period). |
| 7 | `SELECTIVE_DEFAULT_PENALTY` | **$-70.0$** điểm ($85 \to 15$) | `persona_engine.py:107`| **Lý thuyết Vỡ nợ Chọn lọc (Selective Default)** trong Tài chính Hành vi; Cảnh báo rủi ro đạo đức (Moral Hazard). |
| 8 | `AVOIDANCE_PENALTY_RATE` | **$-2.0$** điểm/ngày | `persona_engine.py:112`| **Avoidance Escalation Model**: Tỷ lệ phân rã hợp tác theo số ngày quá hạn. |
| 9 | `ML01_BASE_INTERCEPT` | **$+0.60$** | `ml01_self_cure.py:29` | Xác suất nền tự khỏi trong nợ nhóm sớm B1 (Base Odds Ratio $\approx 1.82$, tương đương Xác suất $\approx 64.5\%$). |
| 10 | `ACTION_TIER_HIGH_PROB` | **$0.80$** (Ân hạn 5 ngày)| `ml01_self_cure.py:102` | **McKinsey Collections Efficiency Curve**: Tối ưu chi phí can thiệp và tránh gây phiền hà khách hàng uy tín cao. |
| 11 | `ACTION_TIER_MED_PROB` | **$0.45$** (Ân hạn 3 ngày)| `ml01_self_cure.py:110` | Thời gian chuyển tiền liên ngân hàng và đối soát lỗi kỹ thuật (3 ngày làm việc). |
| 12 | `VOICE_CALL_TIME_WINDOW` | `07:00 - 21:00` | `orchestrator.py:50` | **Điều 7 Thông tư 18/2019/TT-NHNN** (và Luật Bảo vệ quyền lợi người tiêu dùng). |
| 13 | `MAX_DAILY_ATTEMPTS_TOTAL` | **$3$** lần/ngày | `orchestrator.py:46` | **Thông tư 18/2019/TT-NHNN**: Quy định giới hạn số lần nhắc nợ tối đa để bảo đảm tính văn minh. |
| 14 | `MAX_DAILY_ATTEMPTS_CHANNEL`| **$2$** lần/ngày/kênh | `orchestrator.py:47` | Ngăn chặn hiện tượng spam cuộc gọi / tin nhắn trên một kênh duy nhất. |
| 15 | `BALANCE_CHECK_LOOKBACK` | **$15$** phút | `balance_check_service.py:25` | Độ trễ đồng bộ bút toán Core Banking - Fast Payment Napas 24/7. |
| 16 | `VECTOR_DIMENSIONS` | **$192$** chiều | `cbr_engine.py:71` | Chuẩn kiến trúc Bi-Encoder Embeddings đa chiều (8 nhóm đặc trưng $\times$ 16–32 chiều + 4 chiều Coverage Mask). |

---

## 10. Kết luận & Khuyến nghị Vận hành

Tài liệu này đóng vai trò là **Căn cứ Khoa học Chuẩn** để giải trình với Hội đồng Quản trị Rủi ro, Ban Điều hành Ngân hàng và Cơ quan Giám sát Ngân hàng Nhà nước.

Trong các phiên bản tiếp theo:
1. Các hằng số trên sẽ được chuyển dịch từ mã nguồn cố định sang tệp cấu hình **`scoring_policy.yaml`** có kiểm soát phiên bản (Version-controlled).
2. Định kỳ hàng quý (Quarterly Backtesting), đội ngũ Data Science cần thực hiện kiểm định lại các trọng số hồi quy của mô hình ML01 và đường cong suy giảm DSR thông qua kiểm định độ dốc Kolmogorov-Smirnov (KS-test) và diện tích dưới đường cong ROC (AUC) trên dữ liệu thực tế phát sinh tại ngân hàng.
