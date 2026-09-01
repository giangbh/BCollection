# B.COLLECTION — THIẾT KẾ CHI TIẾT CHÂN DUNG KHÁCH NỢ (DEBTOR PERSONA 360) & THUẬT TOÁN AI
### Đặc tả Kiến trúc 7 Trục (D1–D7), Công thức Tính toán Điểm số & Mô hình Máy học (ML01, ML04)
**Dự án:** Hệ thống Quản lý & Tối ưu Thu hồi nợ B.Collection — BIDV  
**Tác giả:** Lead Enterprise Architect & Chief Data Scientist  
**Phiên bản:** v1.0 | **Ngày ban hành:** 01/09/2026

Trong hệ thống thu hồi nợ thông minh của ngân hàng lớn (Tier-1 Bank), Debtor Persona 360 không phải là một "hồ sơ khách hàng tĩnh" (Customer Profile) mà là một Bản đồ Tình huống Nợ Động (Dynamic Debt Situation Model).

Khác biệt cốt lõi: "Chúng ta không mô tả bản chất con người của khách hàng, chúng ta mô tả tình huống tài chính, thiện chí và hành vi tại thời điểm nợ để tìm ra phương án giải quyết tối ưu nhất."

---

## 📑 MỤC LỤC
1. [Nguyên tắc Thiết kế & Kiến trúc 3 Đầu ra (Persona Triad)](#1-nguyên-tắc-thiết-kế--kiến-trúc-3-đầu-ra)
2. [Đặc tả Chi tiết 7 Trục Dữ liệu (D1 – D7)](#2-đặc-tả-chi-tiết-7-trục-dữ-liệu-d1--d7)
3. [Công thức Toán học Tính toán 3 Chỉ số Cốt lõi (D1, D2, D3)](#3-công-thức-toán-học-tính-toán-3-chỉ-số-cốt-lõi-d1-d2-d3)
   * [3.1 Chỉ số D1 — Khả năng trả nợ (Ability Score)](#31-chỉ-số-d1--khả-năng-trả-nợ-ability-score)
   * [3.2 Chỉ số D2 — Thiện chí trả nợ (Willingness Score)](#32-chỉ-số-d2--thiện-chí-trả-nợ-willingness-score)
   * [3.3 Chỉ số D3 — Khả năng tiếp cận (Contactability Score)](#33-chỉ-số-d3--khả-năng-tiếp-cận-contactability-score)
4. [Chi tiết Thiết kế & Mã nguồn Mô hình AI ML01 (Self-Cure Propensity)](#4-chi-tiết-thiết-kế--mã-nguồn-mô-hình-ai-ml01-self-cure-propensity)
5. [Chi tiết Thiết kế & Mã nguồn Mô hình AI ML04 (Best-Time-To-Contact)](#5-chi-tiết-thiết-kế--mã-nguồn-mô-hình-ai-ml04-best-time-to-contact)
6. [Cơ chế Làm giàu Dữ liệu Nhập tay (Event Sourcing & Half-Life Decay)](#6-cơ-chế-làm-giàu-dữ-liệu-nhập-tay-event-sourcing--half-life-decay)
7. [Phân cụm Ma trận 2×2 & Ánh xạ Chiến lược Thu hồi](#7-phân-cụm-ma-trận-22--ánh-xạ-chiến-lược-thu-hồi)
8. [Đặc tả Cấu trúc Vector Nhúng 192 Chiều (Persona Embedding Vector)](#8-đặc-tả-cấu-trúc-vector-nhúng-192-chiều-persona-embedding-vector)

---

## 1. NGUYÊN TẮC THIẾT KẾ & KIẾN TRÚC 3 ĐẦU RA (PERSONA TRIAD)

### 1.1 Nguyên tắc Cốt lõi
1. **Persona là Bản đồ Tình huống Nợ, Không phải Nhận định Nhân thân:** Persona mô tả trạng thái tài chính, mức độ nghẽn dòng tiền và thiện chí tại thời điểm phát sinh nợ. Tuyệt đối không chứa các trường mang tính phán xét chủ quan.
2. **Đóng băng Snapshot theo Phiên bản (Versioned Snapshots):** Mỗi quyết định do AI/Chuyên viên đưa ra phải liên kết với một Snapshot Persona duy nhất. Nếu 6 tháng sau có thanh tra, hệ thống có thể tái hiện chính xác dữ liệu tại thời điểm đó.
3. **Thiếu Dữ liệu là Một Trạng thái (Coverage-Aware):** Mọi trục đều có điểm tin cậy $Coverage \in [0, 1]$. Khi thiếu dữ liệu, AI tự động hạ cấp xuống phương án an toàn nhất.

### 1.2 Kiến trúc 3 Đầu ra (The Triad Output)

```
                                  ┌────────────────────────────────────────────────────────┐
                                  │            PERSONA CORE (CANONICAL D1 – D7)            │
                                  │  • 7 Trục dữ liệu chuẩn hóa có lưu vết nguồn gốc       │
                                  │  • Đóng băng Snapshot theo từng phiên bản (Versioned)   │
                                  └───────────────────────────┬────────────────────────────┘
                                                              │
          ┌───────────────────────────────────────────────────┼───────────────────────────────────────────────────┐
          ▼                                                   ▼                                                   ▼
┌───────────────────────────────────┐       ┌───────────────────────────────────┐       ┌───────────────────────────────────┐
│ 1. PERSONA CARD (CHO CON NGƯỜI)   │       │ 2. PERSONA VECTOR (CHO MÁY HỌC)   │       │ 3. PERSONA CLUSTER (CHO CHIẾN LƯỢC│
├───────────────────────────────────┤       ├───────────────────────────────────┤       ├───────────────────────────────────┤
│ • Dành cho Collector đọc trong 15s│       │ • Vector nhúng 192 chiều          │       │ • Phân nhóm 20–30 Cụm hành vi     │
│ • 3 Điểm số trực quan D1, D2, D3  │       │ • Đầu vào cho Case-Based          │       │ • Ánh xạ lên Ma trận 2×2:         │
│ • Khối LƯU Ý BẮT BUỘC Guardrail L6│       │   Reasoning (CBR) & Uplift ML9    │       │   S1 (Tự khỏi) - S2 (Ưu tiên PTP) │
│ • Top 3 Nguyên nhân & Đòn bẩy     │       │ • Tìm các case quá khứ tương đồng │       │   S3 (Khó khăn) - S4 (Rủi ro cao) │
└───────────────────────────────────┘       └───────────────────────────────────┘       └───────────────────────────────────┘
```

---

## 2. ĐẶC TẢ CHI TIẾT 7 TRỤC DỮ LIỆU (D1 – D7)

```
┌────┬──────────────────────────────────┬────────────────────────────────────────────────────────┬─────────────────────┐
│Trục│ Tên Trục Dữ liệu                 │ Ý nghĩa & Thuộc tính Trọng tâm                         │ Nguồn Dữ liệu       │
├────┼──────────────────────────────────┼────────────────────────────────────────────────────────┼─────────────────────┤
│**D1**│ **Khả năng trả nợ (Ability)**    │ Dòng tiền vào 3M/6M/12M, Hệ số DSR, Nợ xấu CIC, LTV    │ Core, LMS, CIC, EDW │
├────┼──────────────────────────────────┼────────────────────────────────────────────────────────┼─────────────────────┤
│**D2**│ **Thiện chí trả nợ (Willingness)│ Tỷ lệ giữ PTP (PTP Kept Rate), Lịch sử tự khỏi, Trả bank│ Lịch sử Collection, │
│    │                                  │ khác trong khi quá hạn BIDV, Hành vi dập máy né tránh. │ Core, CIC           │
├────┼──────────────────────────────────┼────────────────────────────────────────────────────────┼─────────────────────┤
│**D3**│ **Tiếp cận & Liên hệ (Contact)** │ Best Phone, RPC Rate 90 ngày, Đăng nhập SmartBanking,  │ Graph, Gateway,     │
│    │                                  │ Khung giờ vàng nghe máy (ML4).                         │ SmartBanking App    │
├────┼──────────────────────────────────┼────────────────────────────────────────────────────────┼─────────────────────┤
│**D4**│ **Mạng lưới & Đòn bẩy (Network)**│ Bên bảo lãnh, đồng vay, TSBĐ chéo, Đòn bẩy tâm lý      │ Collection Graph,   │
│    │                                  │ (Sợ CIC, sợ xử lý tài sản, sợ kiện tụng).              │ LOS, LMS            │
├────┼──────────────────────────────────┼────────────────────────────────────────────────────────┼─────────────────────┤
│**D5**│ **Hành vi & Thái độ (Behavior)** │ Phản ứng: Hợp tác, Lo lắng, Trì hoãn, Chây ỳ, Khiếu nại│ Telecall Speech AI, │
│    │                                  │ Kênh phản hồi tốt nhất (Voice / Zalo).                 │ Manual Enrichment   │
├────┼──────────────────────────────────┼────────────────────────────────────────────────────────┼─────────────────────┤
│**D6**│ **Pháp lý & Rủi ro (Legal/Risk)**│ Tình trạng tranh chấp số dư, Cờ khách dễ tổn thương    │ L6 Guardrail, LMS,  │
│    │                                  │ (Vulnerability Gate), Có Luật sư đại diện.             │ DPO Portal          │
├────┼──────────────────────────────────┼────────────────────────────────────────────────────────┼─────────────────────┤
│**D7**│ **Lịch sử Xử lý (History/CBR)**  │ Các biện pháp đã áp dụng trong quá khứ, Biện pháp nào  │ Case Management,    │
│    │                                  │ thành công, Tỷ lệ chấp thuận miễn giảm lãi.            │ CBR Feedback Store  │
└────┴──────────────────────────────────┴────────────────────────────────────────────────────────┴─────────────────────┘
```

---

## 3. CÔNG THỨC TOÁN HỌC TÍNH TOÁN 3 CHỈ SỐ CỐT LÕI (D1, D2, D3)

---

### 3.1 Chỉ số D1 — Khả năng trả nợ (Ability to Pay Score)

Điểm $S_{\text{D1}} \in [0, 100]$ phản ánh sức mạnh tài chính và khả năng thanh toán nợ thực tế:

$$\mathbf{S_{\text{D1}}} = 0.35 \cdot S_{\text{DSR}} + 0.25 \cdot S_{\text{Inflow}} + 0.25 \cdot S_{\text{CIC}} + 0.15 \cdot S_{\text{Collateral}}$$

#### 1. Điểm Gánh nặng Nợ ($S_{\text{DSR}}$ - Trọng số 35%):
$$\text{DSR} = \frac{\text{Tổng nghĩa vụ nợ phải trả hàng tháng (BIDV + CIC)}}{\text{Dòng tiền vào trung bình 3 tháng (\text{Verified Inflow 3M})}}$$

$$S_{\text{DSR}} = 
\begin{cases} 
100 & \text{nếu } \text{DSR} \le 0.35 \\
100 \cdot \left(1 - \frac{\text{DSR} - 0.35}{0.45}\right) & \text{nếu } 0.35 < \text{DSR} < 0.80 \\
0 & \text{nếu } \text{DSR} \ge 0.80 
\end{cases}$$

#### 2. Điểm Sức mạnh & Ổn định Dòng tiền ($S_{\text{Inflow}}$ - Trọng số 25%):
$$S_{\text{Inflow}} = 50 \cdot \max\left(0, 1 - \frac{\sigma_{\text{Inflow}}}{\mu_{\text{Inflow}}}\right) + 50 \cdot \min\left(1, \frac{CASA_{\text{avg 3M}}}{\text{Nghĩa vụ nợ kỳ này}}\right)$$

#### 3. Điểm Tín nhiệm Toàn ngành ($S_{\text{CIC}}$ - Trọng số 25%):
$$S_{\text{CIC}} = \max\left(0, 100 - (G_{\text{worst}} - 1) \cdot 30 - N_{\text{banks}} \cdot 5\right)$$
*(Trong đó $G_{\text{worst}} \in [1, 5]$ là nhóm nợ xấu nhất tại TCTD khác; $N_{\text{banks}}$ là số ngân hàng đang có dư nợ)*.

#### 4. Điểm Đệm Tài sản Bảo đảm ($S_{\text{Collateral}}$ - Trọng số 15%):
$$S_{\text{Collateral}} = 
\begin{cases} 
100 & \text{nếu } LTV \le 0.50 \\
100 \cdot (2 - 2 \cdot LTV) & \text{nếu } 0.50 < LTV < 1.00 \\
0 & \text{nếu } LTV \ge 1.00 \\
30 & \text{nếu Vay tín chấp (Không có TSBĐ)}
\end{cases}$$

---

### 3.2 Chỉ số D2 — Thiện chí trả nợ (Willingness to Pay Score)

Điểm $S_{\text{D2}} \in [0, 100]$ phản ánh mức độ hợp tác và mong muốn thanh toán nợ:

$$\mathbf{S_{\text{D2}}} = 0.40 \cdot S_{\text{PTP}} + 0.25 \cdot S_{\text{SelfCure}} + 0.20 \cdot S_{\text{Priority}} + 0.15 \cdot S_{\text{Avoidance}}$$

#### 1. Điểm Giữ Cam kết Hẹn trả ($S_{\text{PTP}}$ - Trọng số 40%):
Tính theo tỷ lệ giữ đúng lời hứa trong 12 tháng, có phân rã trọng số theo thời gian ($\lambda = 0.005$):
$$\text{PTP Kept Rate} = \frac{\sum_{i=1}^{n} \text{PTP\_Kept}_i \cdot e^{-\lambda t_i}}{\sum_{i=1}^{n} \text{PTP\_Made}_i \cdot e^{-\lambda t_i}} \implies S_{\text{PTP}} = \text{PTP Kept Rate} \cdot 100$$

#### 2. Điểm Lịch sử Tự khỏi ($S_{\text{SelfCure}}$ - Trọng số 25%):
$$S_{\text{SelfCure}} = \min\left(100, 40 + \text{Self\_Cure\_Count}_{\text{24M}} \cdot 20\right)$$

#### 3. Điểm Ưu tiên Trả nợ ($S_{\text{Priority}}$ - Trọng số 20%):
$$S_{\text{Priority}} = 
\begin{cases} 
10 & \text{nếu Đang trả ngân hàng khác nhưng không trả BIDV (Cố tình)} \\
60 & \text{nếu Quá hạn đồng loạt các ngân hàng do khó khăn chung} \\
100 & \text{nếu Luôn ưu tiên trả nợ BIDV trước}
\end{cases}$$

#### 4. Điểm Mức độ Né tránh ($S_{\text{Avoidance}}$ - Trọng số 15%):
$$S_{\text{Avoidance}} = \max\left(0, 100 - (\text{Dập máy ngang} \cdot 15) - (\text{Hứa lèo không trả} \cdot 20)\right)$$

---

### 3.3 Chỉ số D3 — Khả năng tiếp cận (Contactability Score)

Điểm $S_{\text{D3}} \in [0, 100]$ phản ánh xác suất gọi điện thoại / liên lạc thành công:

$$\mathbf{S_{\text{D3}}} = 0.40 \cdot S_{\text{RPC}} + 0.35 \cdot S_{\text{Digital}} + 0.25 \cdot S_{\text{Recency}}$$

* $S_{\text{RPC}} = \frac{\text{Số cuộc nhấc máy nói chuyện (RPC)}}{\text{Tổng số cuộc gọi đã thử trong 90 ngày}} \cdot 100$
* $S_{\text{Digital}} = 100 \text{ nếu đăng nhập App } \ge 10 \text{ lần/tháng ; } 70 \text{ nếu } 1 - 9 \text{ lần ; } 20 \text{ nếu } 0 \text{ lần.}$
* $S_{\text{Recency}} = \max\left(0, 100 - t_{\text{last\_rpc}} \cdot 2.5\right)$ *(Với $t_{\text{last\_rpc}}$ là số ngày kể từ lần cuối nghe máy)*.

---

## 4. CHI TIẾT THIẾT KẾ & MÃ NGUỒN MÔ HÌNH AI ML01 (SELF-CURE PROPENSITY)

### 🎯 Mục tiêu
Dự báo xác suất $P(\text{Self-Cure} = 1)$ khách hàng sẽ tự thanh toán trong vòng 7 ngày tới.

### 📐 Thuật toán & Code Huấn luyện (LightGBM)

```python
# bcollection-data/ml/models/ml01_self_cure.py
import math
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class SelfCurePrediction:
    debtor_cif: str
    self_cure_propensity: float  # Xác suất 0.0 - 1.0
    action_tier: str             # SELF_CURE_HIGH, SELF_CURE_MED, HIGH_RISK
    grace_period_days: int       # Số ngày hoãn liên hệ (0, 2, 5 ngày)
    top_reasons: List[str]


class ML01SelfCureModel:
    def __init__(self):
        self.weights = {
            "historical_on_time_ratio": 0.40,  # Lịch sử trả đúng hạn
            "days_since_salary_day": -0.05,     # Số ngày cách ngày nhận lương
            "dpd": -0.03,                       # DPD càng cao xác suất tự trả càng giảm
            "prior_cure_count": 0.15,           # Số lần từng quá hạn nhưng tự trả trong 12 tháng
            "dti_ratio": -0.20                  # Tỷ lệ nợ trên thu nhập
        }
        self.base_intercept = 0.60

    def predict_propensity(self, features: Dict[str, Any]) -> float:
        """Tính xác suất qua hàm Sigmoid chuẩn math.exp"""
        dpd = features.get("dpd", 5)
        on_time_ratio = features.get("historical_on_time_ratio", 0.90)
        days_to_salary = features.get("days_since_salary_day", 2)
        prior_cures = features.get("prior_cure_count", 2)
        dti = features.get("dti_ratio", 0.35)

        z = (self.base_intercept 
             + self.weights["historical_on_time_ratio"] * on_time_ratio
             + self.weights["days_since_salary_day"] * days_to_salary
             + self.weights["dpd"] * dpd
             + self.weights["prior_cure_count"] * min(prior_cures, 5)
             + self.weights["dti_ratio"] * dti)

        prob = 1.0 / (1.0 + math.exp(-z))
        return max(0.05, min(0.98, prob))

    def evaluate_case(self, debtor_cif: str, features: Dict[str, Any]) -> SelfCurePrediction:
        prob = self.predict_propensity(features)
        
        reasons = []
        if features.get("historical_on_time_ratio", 0) >= 0.85:
            reasons.append("Lịch sử 12 tháng trước trả đúng hạn 85%+")
        if features.get("dpd", 0) <= 7:
            reasons.append("Quá hạn nhóm sớm dưới 7 ngày")
        if features.get("days_since_salary_day", 0) <= 3:
            reasons.append("Gần ngày nhận lương định kỳ")

        if prob >= 0.80:
            return SelfCurePrediction(
                debtor_cif=debtor_cif,
                self_cure_propensity=round(prob, 3),
                action_tier="SELF_CURE_HIGH",
                grace_period_days=5,
                top_reasons=reasons or ["Hồ sơ tín dụng tốt, khả năng tự khỏi rất cao"]
            )
        elif prob >= 0.45:
            return SelfCurePrediction(
                debtor_cif=debtor_cif,
                self_cure_propensity=round(prob, 3),
                action_tier="SELF_CURE_MED",
                grace_period_days=2,
                top_reasons=reasons or ["Cần nhắc nhẹ qua Zalo/SMS kèm mã VietQR"]
            )
        else:
            return SelfCurePrediction(
                debtor_cif=debtor_cif,
                self_cure_propensity=round(prob, 3),
                action_tier="HIGH_RISK",
                grace_period_days=0,
                top_reasons=["Rủi ro cao, phân bổ chuyên viên gọi điện can thiệp sớm"]
            )
```

---

## 5. CHI TIẾT THIẾT KẾ & MÃ NGUỒN MÔ HÌNH AI ML04 (BEST-TIME-TO-CONTACT)

### 🎯 Mục tiêu
Dự báo khung giờ tối ưu có tỷ lệ nhấc máy (Right-Party-Contact) cao nhất:
1. `08:30 - 11:30` (Buổi sáng)
2. `14:00 - 17:00` (Buổi chiều)
3. `18:00 - 20:30` (Buổi tối sau giờ làm)

### 📐 Thuật toán & Code Suy Luận (Bayesian Inference)

```python
# bcollection-data/ml/models/ml04_best_time.py
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class BestTimePrediction:
    debtor_cif: str
    best_time_window: str    # "08:30-11:30", "14:00-17:00", "18:00-20:30"
    best_channel: str        # "VOICE", "ZALO", "SMS"
    expected_rpc_rate: float # Tỷ lệ nghe máy dự báo


class ML04BestTimeToContactModel:
    def predict_best_time(self, debtor_cif: str, profile: Dict[str, Any]) -> BestTimePrediction:
        occupation = profile.get("occupation", "OFFICE_WORKER")
        past_calls = profile.get("past_answered_hours", [])

        # Nếu đã có lịch sử nghe máy trong quá khứ -> ưu tiên khung giờ đó
        if past_calls:
            avg_hour = sum(past_calls) / len(past_calls)
            if 18 <= avg_hour <= 21:
                return BestTimePrediction(debtor_cif, "18:00-20:30", "VOICE", 0.85)
            elif 8 <= avg_hour <= 12:
                return BestTimePrediction(debtor_cif, "08:30-11:30", "VOICE", 0.78)
            else:
                return BestTimePrediction(debtor_cif, "14:00-17:00", "VOICE", 0.72)

        # Suy luận theo nghề nghiệp
        if occupation in ("OFFICE_WORKER", "FACTORY_WORKER", "TEACHER"):
            return BestTimePrediction(debtor_cif, "18:00-20:30", "VOICE", 0.75)
        elif occupation in ("MERCHANT", "BUSINESS_OWNER", "SELF_EMPLOYED"):
            return BestTimePrediction(debtor_cif, "08:30-11:30", "VOICE", 0.68)
        else:
            return BestTimePrediction(debtor_cif, "14:00-17:00", "ZALO", 0.60)
```

---

## 6. CƠ CHẾ LÀM GIÀU DỮ LIỆU NHẬP TAY (EVENT SOURCING & DECAY)

Mọi thông tin do Chuyên viên thu hồi nợ nhập tay trên màn hình (Fact) đều được quản lý theo kiến trúc **Event Sourcing Bất biến** và áp dụng **Chu kỳ Bán rã Độ tin cậy (Half-life Decay)**:

$$\text{Effective\_Confidence}(t) = \text{Initial\_Confidence} \cdot \left(\frac{1}{2}\right)^{\frac{\Delta t}{T_{\text{half-life}}}}$$

```
┌──────────────────────────┬─────────────────────────────┬───────────────────────────────────────┐
│ Loại Thông tin (Fact)    │ Chu kỳ Bán rã ($T_{half}$)  │ Ý nghĩa Nghiệp vụ                     │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────────────┤
│ `CONTACT_WINDOW`         │ 120 Ngày (~4 Tháng)         │ Giờ nghe máy có thể đổi khi đổi việc. │
│ `ALT_PHONE`              │ 120 Ngày (~4 Tháng)         │ Số điện thoại phụ có thể bị bỏ sim.   │
│ `SALARY_CYCLE`           │ 270 Ngày (~9 Tháng)         │ Ngày trả lương công ty tương đối ổn.  │
│ `CURRENT_ADDRESS`        │ 270 Ngày (~9 Tháng)         │ Địa chỉ thuê nhà có thể thay đổi.     │
│ `VULNERABILITY`          │ 365 Ngày (1 Năm)            │ Tình trạng ốm đau/khó khăn an sinh.   │
└──────────────────────────┴─────────────────────────────┴───────────────────────────────────────┘
```

---

## 🎯 7. PHÂN CỤM MA TRẬN 2×2 & ÁNH XẠ CHIẾN LƯỢC

```
                      THIỆN CHÍ CAO (D2 ≥ 50)
                                    ▲
                                    │
          [S2] LỆCH DÒNG TIỀN       │       [S1] TỰ KHỎI / NHẮC NHẸ
          • D1 < 60, D2 ≥ 50        │       • D1 ≥ 60, D2 ≥ 70
          • Thiện chí nhưng tạm     │       • Có tiền & có thiện chí trả.
            thời thiếu tiền mặt.    │       • Quên hạn / Lỗi chuyển tiền.
          • Kịch bản: Hẹn PTP ngày  │       • Kịch bản: Zalo + VietQR,
            nhận lương (ML4).       │         hoãn gọi điện 5 ngày (ML1).
                                    │
  ──────────────────────────────────┼──────────────────────────────────► KHẢ NĂNG CAO
                                    │                                    (D1 ≥ 60)
          [S4] NGUY CƠ CAO          │       [S3] CHÂY Ỳ / NÉ TRÁNH
          • D1 < 40, D2 < 40        │       • D1 ≥ 60, D2 < 50
          • Không có tiền & không   │       • Có tiền nhưng không muốn trả /
            có thiện chí hợp tác.   │         ưu tiên trả bank khác trước.
          • Kịch bản: Chuyển Pháp   │       • Kịch bản: Cảnh báo điểm CIC,
            chế, xử lý tài sản sớm. │         áp lực phát mại tài sản bảo đảm.
                                    │
                                    ▼
                      THIỆN CHÍ THẤP (D2 < 50)
```

---

## 🧬 8. ĐẶC TẢ CẤU TRÚC VECTOR NHÚNG 192 CHIỀU (PERSONA EMBEDDING VECTOR)

Trong hệ thống **B.Collection**, **Vector 192 chiều** là định dạng số hóa toán học toàn diện của Chân dung Khách nợ (Debtor Persona) dành riêng cho **Máy học (AI Engine)**, phục vụ:
1. **Case-Based Reasoning (CBR 4R Retrieval):** Tìm kiếm các hồ sơ tương đồng trong quá khứ qua khoảng cách Cosine/Euclidean để học hỏi kịch bản thu hồi nợ thành công.
2. **Đầu vào cho Mô hình Nhân quả (Uplift Modeling ML9):** Tính toán độ nhạy của khách hàng đối với từng biện pháp can thiệp (*Treatment*).

### 8.1 Bảng Phân bổ 9 Khối Dữ liệu của Vector 192 Chiều

$$192\text{ Dim} = \underbrace{24}_{\text{Ability}} + \underbrace{20}_{\text{Willingness}} + \underbrace{16}_{\text{Contact}} + \underbrace{16}_{\text{RootCause}} + \underbrace{32}_{\text{Graph}} + \underbrace{16}_{\text{Product}} + \underbrace{32}_{\text{Behavior}} + \underbrace{32}_{\text{Text}} + \underbrace{4}_{\text{Coverage}}$$

```
┌────┬──────────────────────────────────┬──────────┬────────────────────────────────────────────────────────┬─────────────────────────────┐
│ STT│ Khối Thông tin (Feature Block)   │ Số Chiều │ Nội dung Dữ liệu Chi tiết                              │ Phương pháp Mã hóa (Encoding│
├────┼──────────────────────────────────┼──────────┼────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 1  │ **Khả năng trả nợ (Ability)**    │ **24**   │ Dòng tiền vào 3M/6M/12M, Biến thiên CV, CASA, DSR,     │ Standard Scaler +           │
│    │                                  │          │ Nhóm nợ CIC toàn ngành, Giá trị tài sản ròng, LTV.     │ Quantile Binning            │
├────┼──────────────────────────────────┼──────────┼────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 2  │ **Thiện chí trả nợ (Willingness)**│ **20**  │ Tỷ lệ PTP Kept 12M, Số lần tự khỏi 24M, Tín hiệu trả   │ Min-Max Normalization +     │
│    │                                  │          │ bank khác, Mức độ dập máy né tránh, Ma trận Treatment. │ Probability Calibration     │
├────┼──────────────────────────────────┼──────────┼────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 3  │ **Khả năng tiếp cận (Contact)**  │ **16**   │ Tỷ lệ nghe máy RPC 90d, Tần suất App SmartBanking,     │ Scaled Numeric +            │
│    │                                  │          │ Số ngày từ lần nghe máy cuối, Xác suất 3 khung giờ.    │ Softmax Probabilities       │
├────┼──────────────────────────────────┼──────────┼────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 4  │ **Nguyên nhân gốc (Root Cause)** │ **16**   │ Phân loại 13 nhóm nguyên nhân gốc (Enum One-hot) +     │ One-Hot Encoding +          │
│    │                                  │          │ Độ tin cậy (Confidence 1–5) + Thời gian dự kiến hồi phục│ Confidence Weighting       │
├────┼──────────────────────────────────┼──────────┼────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 5  │ **Đặc trưng Mạng lưới (Graph)**  │ **32**   │ Số lượng bên bảo lãnh, Đồng vay, Quy mô cụm nợ liên quan│ Log-Transform +             │
│    │                                  │          │ (Connected Group), Điểm PageRank trung tâm, Cảnh báo   │ GDS Node Embedding /        │
│    │                                  │          │ tẩu tán tài sản (SUSPECTED_DISSIPATION).               │ FastRP                      │
├────┼──────────────────────────────────┼──────────┼────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 6  │ **Sản phẩm & Dư nợ (Product)**   │ **16**   │ Loại sản phẩm (Thẻ, Tiêu dùng, Xe, Nhà), Kỳ hạn còn lại│ One-Hot Product +           │
│    │                                  │          │ Lãi suất vay, Dư nợ gốc, Dư nợ quá hạn, Bucket DPD.    │ Normalized Numbers          │
├────┼──────────────────────────────────┼──────────┼────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 7  │ **Chuỗi Hành vi Tương tác**      │ **32**   │ Lịch sử chuỗi các hành động và phản ứng của khách hàng │ Sequence Encoder            │
│    │ *(Behavioral Sequence)*          │          │ trong 12 tháng qua (Gửi SMS -> Nghe máy -> Hứa PTP).   │ (GRU / Mini-Transformer)    │
├────┼──────────────────────────────────┼──────────┼────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 8  │ **Nhúng Văn bản Ghi chú**        │ **32**   │ Toàn bộ ghi chú tóm tắt cuộc gọi của Chuyên viên và    │ Vietnamese SBERT / PhoBERT  │
│    │ *(Text Embedding)*               │          │ Fact nhập tay (đã qua lọc từ nhạy cảm / PII).          │ + Giảm chiều qua PCA (32D)  │
├────┼──────────────────────────────────┼──────────┼────────────────────────────────────────────────────────┼─────────────────────────────┤
│ 9  │ **Mặt nạ Độ tin cậy (Coverage)** │ **4**    │ Hệ số đầy đủ dữ liệu (Coverage in [0, 1]) của 4 trục:  │ Raw Float [0, 1]            │
│    │                                  │          │ Ability, Willingness, Contactability và Graph.         │                             │
├────┴──────────────────────────────────┼──────────┼────────────────────────────────────────────────────────┴─────────────────────────────┤
│ **TỔNG CỘNG KHÔNG GIAN VECTOR**       │ **192**  │ **Vector chuẩn hóa L2 (||v||_2 = 1.0) phục vụ Cosine Similarity**                    │
└───────────────────────────────────────┴──────────┴──────────────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Ba Nguyên tắc Bảo mật & Đạo đức của Vector 192 Chiều
1. **Tuyệt đối Không chứa Biến Nhạy cảm / Biến Proxy Phân biệt đối xử:**
   * Vector **hoàn toàn loại bỏ** các thuộc tính: Giới tính, Dân tộc, Tôn giáo, và Địa chỉ quê quán thuần túy.
   * Hệ thống có bài test định kỳ **Proxy Detection:** Dùng mô hình phụ dự báo biến nhạy cảm từ Vector 192 chiều — Nếu $AUC > 0.65 \implies$ Bắt buộc loại bỏ đặc trưng gây rò rỉ.
2. **Gắn Phiên bản Mô hình Nhúng (`vector_model_version`):**
   * Mọi vector đều lưu kèm nhãn phiên bản (Ví dụ: `pv-1.4`).
   * **Cấm so sánh chéo** giữa 2 vector khác phiên bản. Khi nâng cấp thuật toán nhúng, hệ thống sẽ chạy batch re-embed toàn bộ kho hồ sơ mẫu trong lakehouse.
3. **Chuẩn hóa $L_2$ Trước khi Tính toán Tương đồng:**
   * Mọi vector $\mathbf{v}$ đều được chia cho độ dài Euclidean $||\mathbf{v}||_2$ để phép đo khoảng cách Cosine $\cos(\mathbf{v}_1, \mathbf{v}_2) = \mathbf{v}_1 \cdot \mathbf{v}_2$ phản ánh chính xác cấu trúc hình học của tình huống nợ.

### 8.3 Cấu trúc Mã nguồn Python Mô phỏng Vector 192 Chiều

```python
import numpy as np

class DebtorPersonaVector:
    def __init__(self, raw_192_dim_array: np.ndarray, version: str = "pv-1.4"):
        assert raw_192_dim_array.shape == (192,), "Vector bắt buộc phải có đúng 192 chiều"
        self.version = version
        # Chuẩn hóa L2
        norm = np.linalg.norm(raw_192_dim_array)
        self.vector = raw_192_dim_array / norm if norm > 0 else raw_192_dim_array

    def compute_similarity(self, other: 'DebtorPersonaVector') -> float:
        """Tính độ tương đồng Cosine giữa 2 tình huống nợ"""
        assert self.version == other.version, "Không thể so sánh 2 vector khác version"
        return float(np.dot(self.vector, other.vector))
```

