# B.COLLECTION — PHƯƠNG PHÁP CHỨNG MINH ROI
### Thiết kế đo lường nhân quả cho Ban Lãnh đạo
**Phiên bản:** v0.1 | **Ngày:** 01/09/2026
**Liên quan:** Kiến trúc tổng thể v0.2 (Mục 9.4) · Persona Model v0.2 (A4.2) · Tech Stack MVP (R6)

---

## 0. Luận điểm trung tâm

Hầu hết dự án chuyển đổi thu hồi nợ báo cáo thành công bằng câu: *"Tỷ lệ thu hồi tăng từ 62% lên 71% sau khi triển khai."*

**Câu đó không chứng minh được điều gì.** Trong cùng kỳ, danh mục thay đổi, kinh tế vĩ mô thay đổi, đội ngũ được đào tạo lại, lãnh đạo quan tâm hơn, và chính việc có dự án đã làm mọi người làm việc chăm chỉ hơn. Không có cách nào tách phần đóng góp của hệ thống ra khỏi những yếu tố đó bằng cách so sánh trước–sau.

Chỉ có **một** cách tạo ra bằng chứng nhân quả đáng tin cậy: **so sánh hai nhóm khách hàng tương đương, trong cùng một khoảng thời gian, khác nhau duy nhất ở việc có được hệ thống mới xử lý hay không.**

Đây không phải sự cầu toàn học thuật. Đây là điều kiện để trả lời được câu hỏi mà Ban Lãnh đạo chắc chắn sẽ hỏi ở năm thứ hai: *"Chúng ta đã chi bao nhiêu, và thu về được gì mà nếu không có hệ thống thì đã không có?"*

---

## 1. Vì sao so sánh trước–sau luôn sai

Sáu nguồn nhiễu, tất cả đều hiện diện trong bối cảnh Ngân hàng:

| # | Nguồn nhiễu | Biểu hiện |
|---|---|---|
| 1 | **Chu kỳ kinh tế** | Khả năng trả nợ của khách hàng thay đổi theo vĩ mô, không liên quan hệ thống |
| 2 | **Thay đổi thành phần danh mục** | Chuẩn cấp tín dụng siết/nới → cohort quá hạn năm nay khác bản chất năm ngoái |
| 3 | **Mùa vụ** | Thu hồi quý IV và quanh Tết khác hẳn quý II |
| 4 | **Hồi quy về trung bình** | Dự án thường khởi động khi chỉ số đang xấu bất thường; nó sẽ tự cải thiện |
| 5 | **Hiệu ứng Hawthorne** | Đội ngũ làm tốt hơn vì biết đang được đo, không phải vì công cụ |
| 6 | **Thay đổi đồng thời** | Đào tạo lại, đổi cơ chế lương thưởng, tuyển thêm người — thường diễn ra cùng lúc với dự án |

Nguồn nhiễu 5 và 6 đặc biệt khó chịu vì chúng **tương quan thuận với dự án** — nghĩa là chúng làm kết quả đẹp lên và khiến người ta tin dự án hiệu quả hơn thực tế.

---

## 2. Thiết kế thí nghiệm chính

### 2.1 Cấu trúc

```
Toàn bộ khách hàng đủ điều kiện vào phạm vi thí nghiệm
                    │
      Phân bổ NGẪU NHIÊN, phân tầng, ở mức KHÁCH HÀNG
                    │
        ┌───────────┴────────────┐
        ▼                        ▼
   NHÓM CAN THIỆP (90%)     NHÓM ĐỐI CHỨNG (10%)
   B.Collection xử lý       Quy trình hiện hành xử lý
   (Persona + NBA +         (phân công và treatment
    Guardrail + kênh số)     như trước khi có dự án)
        │                        │
        └───────────┬────────────┘
                    ▼
    Đo cùng chỉ số, cùng thời điểm, cùng cách tính
```

### 2.2 Bảy quyết định thiết kế và lý do

**(a) Đơn vị ngẫu nhiên hoá: khách hàng, không phải khoản nợ.**
Một khách hàng có thể có nhiều khoản nợ. Nếu randomize theo khoản nợ, cùng một người vừa nhận treatment mới vừa nhận treatment cũ — hai nhóm nhiễm chéo nhau và kết quả không diễn giải được. Randomize ở mức khách hàng, phân tích ở mức khách hàng.

**(b) Nhóm đối chứng nhận quy trình hiện hành, KHÔNG bị bỏ mặc.**
Đây là điểm phải nói rõ với Ban Lãnh đạo ngay từ đầu, vì phản đối lớn nhất sẽ là *"sao lại bỏ mặc 10% khách hàng?"*. Nhóm đối chứng được thu hồi đúng như cách Ngân hàng đang làm hôm nay — không tệ hơn hiện trạng một chút nào. Câu hỏi thí nghiệm là *"hệ thống mới có tốt hơn cách làm hiện tại không"*, không phải *"làm gì đó có tốt hơn không làm gì không"*.

**(c) Phân bổ phân tầng (stratified), không ngẫu nhiên thuần.**
Phân tầng theo: bucket DPD × phân khúc sản phẩm × dải dư nợ × chi nhánh. Với cỡ mẫu vừa phải, ngẫu nhiên thuần có thể tạo ra hai nhóm lệch nhau đáng kể. Phân tầng loại bỏ rủi ro đó và tăng độ nhạy của phép đo.

**(d) Tỷ lệ 10% cho đối chứng.**
Đủ để phát hiện hiệu ứng có ý nghĩa kinh tế trong 3–6 tháng (xem Mục 4), đủ nhỏ để chi phí cơ hội chấp nhận được. Không nên xuống dưới 5% — dưới mức đó, khoảng tin cậy rộng đến mức kết luận nào cũng không chắc chắn.

**(e) Phân bổ cố định và bền vững.**
Khách hàng đã vào nhóm nào thì ở nguyên nhóm đó trong suốt thí nghiệm, kể cả khi phát sinh khoản nợ mới. Hash của `golden_customer_id` + seed cố định → nhóm. Cách này cho kết quả tái lập được và không cần lưu bảng phân bổ.

**(f) Đo theo cohort (vintage), không đo theo tháng lịch.**
"Tỷ lệ thu hồi tháng 9" trộn lẫn các khoản nợ ở giai đoạn khác nhau. Đúng ra phải là: *"trong nhóm khách hàng quá hạn lần đầu trong tháng 6, tỷ lệ thu hồi sau 90 ngày của nhóm can thiệp so với nhóm đối chứng."* Mỗi cohort là một quan sát độc lập.

**(g) Phân tích theo nguyên tắc "ý định điều trị" (intention-to-treat).**
Khách hàng đã phân vào nhóm can thiệp thì tính vào nhóm can thiệp, kể cả khi hệ thống chọn `NO_ACTION`, kể cả khi Guardrail chặn, kể cả khi cán bộ không dùng khuyến nghị. Nếu chỉ tính những case "được xử lý đúng quy trình", ta vô tình loại bỏ đúng những case khó — và tạo ra kết quả đẹp giả tạo. Đây là sai lầm phổ biến nhất trong đo lường dự án nội bộ.

### 2.3 Đăng ký trước phân tích (pre-registration)

Đây là yếu tố khiến phương pháp này *khoa học* chứ không chỉ *có đối chứng*.

**Trước khi thí nghiệm bắt đầu**, lập một văn bản có chữ ký của PO + đại diện Khối Tài chính, ghi rõ:
- Chỉ số chính (**đúng một**), công thức tính chính xác
- Các chỉ số phụ và chỉ số bảo vệ
- Cỡ mẫu và thời gian chạy tối thiểu
- Phương pháp phân tích, cách xử lý dữ liệu thiếu
- Ngưỡng để kết luận thành công

Văn bản này commit vào `bcollection-data/experiments/pre-registration/` và **không được sửa sau khi có dữ liệu**.

Lý do: nếu không đăng ký trước, khi kết quả chỉ số chính không đẹp, sẽ luôn có người tìm được một chỉ số phụ nào đó đẹp và báo cáo cái đó. Với đủ số chỉ số, luôn tìm được một cái có vẻ có ý nghĩa. Đăng ký trước là cách duy nhất ngăn điều này một cách đáng tin.

---

## 3. Hệ thống chỉ số

### 3.1 Chỉ số chính — chọn đúng một

**Đề xuất: Giá trị thu hồi ròng trên mỗi khách hàng vào ngày thứ 90 kể từ khi vào cohort.**

```
NCV₉₀ = (Tổng tiền thu được trong 90 ngày)
      − (Chi phí thu hồi trực tiếp: nhân công, kênh, field visit, pháp lý)
      − (Giá trị miễn giảm đã cấp)
```

Vì sao chỉ số này chứ không phải tỷ lệ thu hồi:
- Tỷ lệ thu hồi có thể tăng bằng cách **chi nhiều hơn** — gọi gấp đôi, thăm hiện trường nhiều hơn. Đó không phải cải thiện.
- Tỷ lệ thu hồi có thể tăng bằng cách **miễn giảm hào phóng hơn**. Đó cũng không phải cải thiện.
- NCV nắm bắt được cả hai mặt, và là ngôn ngữ mà Ban Lãnh đạo và Khối Tài chính hiểu trực tiếp.

**Ước lượng cần báo cáo:**
```
Uplift tuyệt đối = E[NCV₉₀ | can thiệp] − E[NCV₉₀ | đối chứng]
```
kèm **khoảng tin cậy 95%**, không chỉ giá trị điểm.

### 3.2 Chỉ số phụ (báo cáo nhưng không dùng để kết luận)
Cure rate B1, roll rate B1→B2, PTP kept rate, RPC rate, chi phí trên mỗi đồng thu được (CTC), tỷ lệ liên hệ số hoá.

### 3.3 Chỉ số bảo vệ — không được xấu đi

Đây là nhóm quan trọng nhất về mặt quản trị rủi ro. Một hệ thống làm tăng NCV nhưng làm hỏng các chỉ số này là hệ thống thất bại, bất kể con số tài chính.

| Chỉ số | Ngưỡng |
|---|---|
| Tỷ lệ khiếu nại / 1.000 tương tác | Không cao hơn nhóm đối chứng có ý nghĩa |
| **Tỷ lệ tái quá hạn sau cơ cấu (re-default 180 ngày)** | Không cao hơn nhóm đối chứng |
| Kết quả của nhóm khách hàng dễ tổn thương | Không kém hơn nhóm đối chứng |
| Số lần Guardrail chặn do vi phạm | Giảm dần theo thời gian |
| Chênh lệch kết quả giữa các nhóm phân tách (vùng miền, giới tính, độ tuổi) | Không mở rộng |

Re-default rate đáng chú ý nhất: nó phát hiện trường hợp hệ thống "thu hồi" thành công bằng cách ép khách hàng vào phương án không khả thi. Trên chỉ số 90 ngày trông rất đẹp; trên chỉ số 180 ngày lộ ra là thu hồi ảo.

---

## 4. Cỡ mẫu và thời gian

### 4.1 Công thức
Với so sánh hai trung bình, cỡ mẫu tối thiểu mỗi nhóm:
```
n = 2 × (z_{α/2} + z_β)² × σ² / δ²
```
Với α = 0,05 và power 80%: `(z_{α/2} + z_β)² ≈ 7,85`

### 4.2 Ví dụ minh hoạ

Giả định (cần thay bằng số thực của Ngân hàng):
- Số case quá hạn mới mỗi tháng ở phân khúc bán lẻ B1: **20.000**
- NCV₉₀ trung bình: **3,0 triệu đồng**, độ lệch chuẩn **6,0 triệu**
- Hiệu ứng tối thiểu đáng quan tâm (MDE): **+5%**, tức δ = 0,15 triệu

```
n = 2 × 7,85 × 6,0² / 0,15² = 25.120 khách hàng mỗi nhóm
```

Với nhóm đối chứng 10%, cần tổng cộng ~251.000 khách hàng vào cohort → **khoảng 12,5 tháng** ở nhịp 20.000/tháng.

Con số này khó chịu nhưng phải nói thẳng: **phát hiện hiệu ứng 5% cần khoảng một năm.** Ba cách rút ngắn hợp lệ:

| Cách | Hiệu quả | Ghi chú |
|---|---|---|
| Chấp nhận MDE lớn hơn (10%) | Cỡ mẫu giảm 4 lần → ~3 tháng | Hợp lý cho giai đoạn đầu, khi hiệu ứng kỳ vọng lớn |
| **CUPED** (dùng biến trước can thiệp để giảm phương sai) | Giảm 20–40% cỡ mẫu | Nên làm; biến hiệp phương sai: NCV lịch sử, dư nợ, DPD |
| Phân tầng chặt + phân tích trong tầng | Giảm 10–20% | Đã có trong thiết kế |

**Không hợp lệ:** nhìn dữ liệu liên tục rồi dừng khi thấy có ý nghĩa thống kê. Đây là cách chắc chắn tạo ra kết quả giả. Nếu cần theo dõi liên tục, phải dùng phương pháp có hiệu chỉnh (sequential testing với alpha spending), khai báo trước.

---

## 5. Từ hiệu quả sang tiền — mô hình ROI

Uplift đo được trên mẫu, quy ra toàn danh mục:

```
Lợi ích năm  = uplift_NCV_per_case × số case đủ điều kiện/năm × tỷ lệ phủ

Chi phí năm  = khấu hao đầu tư (phần mềm, hạ tầng, triển khai)
             + vận hành (nhân sự CNTT, hạ tầng, license)
             + chi phí thay đổi tổ chức (đào tạo, quản trị)
             + CHI PHÍ CƠ HỘI CỦA HOLDOUT
```

**Chi phí cơ hội của holdout** = uplift × số case trong nhóm đối chứng. Phải đưa vào mô hình ROI một cách minh bạch, không giấu. Nó chính là **giá của việc biết sự thật** — và nên trình bày đúng như vậy: một khoản chi để mua thông tin đáng tin cậy, tương tự chi phí kiểm toán.

Báo cáo lên Ban Lãnh đạo cần có: NPV 3 năm (chiết khấu theo chi phí vốn của Ngân hàng), thời gian hoàn vốn, IRR, và **phân tích độ nhạy** với ba kịch bản uplift (biên dưới khoảng tin cậy / điểm ước lượng / biên trên). Trình bày biên dưới trước là cách xây dựng niềm tin tốt nhất.

---

## 6. Những gì KHÔNG chứng minh được bằng thí nghiệm

Phần này quan trọng về mặt trung thực. Ba hạng mục lớn của dự án không randomize được, và không nên giả vờ ngược lại.

### 6.1 Guardrail Service — không đo bằng ROI được

Không thể randomize việc tuân thủ pháp luật. Không thể có nhóm đối chứng "không kiểm soát tần suất liên hệ" để so sánh.

**Cách trình bày đúng:** Guardrail không phải hạng mục sinh lợi, mà là **hạng mục giảm rủi ro**, và nên được đánh giá như bảo hiểm hoặc kiểm soát nội bộ — không ai hỏi ROI của bộ phận kiểm toán nội bộ.

Định lượng gián tiếp có thể trình bày:
- Số lần chặn hành động vi phạm (bằng chứng kiểm soát đang hoạt động)
- Chi phí kỳ vọng tránh được: xác suất sự cố × chi phí sự cố (xử phạt, bồi thường, chi phí khắc phục, tổn thất danh tiếng)
- Thời gian xuất gói bằng chứng khi thanh tra: từ vài ngày xuống vài phút

Nhưng phải nói rõ đây là **ước lượng, không phải đo lường**.

### 6.2 Làm sạch dữ liệu liên hệ — dùng stepped-wedge

Không randomize được ở mức khách hàng (dữ liệu sạch thì sạch cho tất cả). Thiết kế thay thế: **triển khai theo bậc thang** — mỗi tháng bật cho một nhóm chi nhánh, thứ tự ngẫu nhiên. Mỗi chi nhánh vừa là nhóm can thiệp (sau khi bật) vừa là nhóm đối chứng (trước khi bật). Đây là thiết kế được chấp nhận rộng rãi khi không thể randomize cá thể, và mạnh hơn nhiều so với so sánh trước–sau đơn thuần.

### 6.3 Hành động pháp lý và thu giữ TSBĐ

Không được randomize vì lý do đạo đức và pháp lý. Dùng phương pháp bán thực nghiệm: ghép cặp theo điểm xu hướng (propensity score matching) trên các đặc trưng quan sát được, và **trình bày với cảnh báo rõ ràng** rằng phương pháp này không loại trừ được yếu tố gây nhiễu chưa quan sát được.

---

## 7. Phản biện dự kiến từ Ban Lãnh đạo

| Phản biện | Cách trả lời |
|---|---|
| *"Sao lại bỏ mặc 10% khách hàng?"* | Không bỏ mặc. Họ nhận đúng quy trình hiện hành — không tệ hơn hôm nay một chút nào. Câu hỏi là hệ thống mới có tốt hơn cách làm hiện tại không |
| *"Chúng ta mất tiền vì holdout"* | Đúng, và con số đó đã nằm trong mô hình ROI ở Mục 5. Đó là giá của việc biết sự thật. Không có nó, sang năm thứ hai ta không trả lời được câu hỏi về giá trị dự án |
| *"Sao không so với cùng kỳ năm ngoái cho nhanh?"* | Sáu nguồn nhiễu ở Mục 1. Cách đó cho ra một con số, nhưng con số đó không diễn giải được — và nếu có ai chất vấn, ta không bảo vệ được |
| *"Sao lâu thế mới có kết quả?"* | Chỉ số phụ báo cáo được từ tháng thứ 2. Kết luận chắc chắn về chỉ số chính cần thời gian tương ứng với độ lớn hiệu ứng — xem lịch ở Mục 8 |
| *"Đội dự án tự đo kết quả của mình à?"* | Không. Xem Mục 9 — phép đo do bên độc lập sở hữu |
| *"Nếu kết quả không tốt thì sao?"* | Thì ta biết sớm và điều chỉnh, thay vì biết sau ba năm. Đây chính là giá trị của phương pháp |

Phản biện cuối là phép thử thực sự. **Cần thống nhất trước với Ban Lãnh đạo rằng "kết quả không có uplift" là một kết quả hợp lệ và không phải thất bại của đội dự án** — nếu không, khi số liệu xấu, áp lực sẽ dồn vào việc tìm cách trình bày khác thay vì tìm cách cải thiện.

---

## 8. Lịch báo cáo

| Mốc | Báo cáo được gì | Chưa báo cáo được gì |
|---|---|---|
| **T+30 ngày** | Tính toàn vẹn thí nghiệm: hai nhóm có cân bằng không (balance check), tỷ lệ nhiễm chéo | Bất kỳ kết quả nào |
| **T+60** | Chỉ số vận hành: RPC, tỷ lệ số hoá, chi phí liên hệ. Chỉ số bảo vệ | Chỉ số chính |
| **T+90** | Cohort đầu tiên đủ 90 ngày: uplift NCV₉₀ sơ bộ kèm khoảng tin cậy (nhiều khả năng chưa có ý nghĩa thống kê — **phải nói rõ điều này**) | Kết luận |
| **T+180** | Nhiều cohort, khoảng tin cậy hẹp lại. Re-default rate cohort đầu | Kết luận chắc chắn nếu hiệu ứng nhỏ |
| **T+270 → 360** | **Kết luận chính thức** + mô hình ROI đầy đủ + khuyến nghị mở rộng | — |

Nguyên tắc trình bày: ở mọi mốc, báo cáo **khoảng tin cậy chứ không chỉ giá trị điểm**, và nói rõ khi kết quả chưa đủ chắc chắn. Báo cáo "uplift +7%" ở tháng thứ 3 mà không kèm khoảng tin cậy (có thể là −3% đến +17%) là gây hiểu nhầm, và sẽ phản tác dụng khi con số biến động ở kỳ sau.

---

## 9. Quản trị phép đo — điểm dễ bị bỏ qua nhất

**Đội dự án không được sở hữu phép đo kết quả của chính mình.** Không phải vì nghi ngờ động cơ, mà vì thiên lệch vô thức là có thật và không thể tự khắc phục.

| Vai trò | Trách nhiệm |
|---|---|
| **Chủ sở hữu phép đo** | Khối Tài chính hoặc Khối Quản lý rủi ro — **không thuộc dự án** |
| Đội dự án | Cung cấp dữ liệu, không tính toán kết quả cuối |
| Model Risk / Kiểm toán nội bộ | Thẩm định phương pháp trước khi bắt đầu; xác nhận không có sửa đổi sau |
| Kỹ thuật | Bảo đảm phân bổ ngẫu nhiên hoạt động đúng và không bị can thiệp |

**Ba biện pháp kỹ thuật chống can thiệp:**
1. Hàm phân bổ nhóm nằm trong `bcollection-data/experiments/`, có test khẳng định tính xác định và tỷ lệ; thay đổi cần Model Risk duyệt.
2. `experiment_arm` là trường **chỉ đọc** sau khi gán; mọi nỗ lực ghi đè bị từ chối và ghi audit.
3. Guardrail ghi `experiment_arm` vào audit log của mọi quyết định — giúp phát hiện nếu nhóm đối chứng vô tình nhận treatment mới.

Biện pháp 3 đồng thời giải quyết rủi ro nhiễm chéo: nếu một cán bộ dùng Persona Card cho khách hàng thuộc nhóm đối chứng, audit log sẽ lộ ra.

---

## 10. Rủi ro của chính phương pháp

| # | Rủi ro | Biện pháp |
|---|---|---|
| M1 | Nhiễm chéo — cán bộ áp dụng cách làm mới cho cả nhóm đối chứng | Không thể ngăn hoàn toàn (đội ngũ chung). Đo mức nhiễm bằng audit log; nhiễm chéo làm uplift bị **ước lượng thấp**, tức kết quả thiên về thận trọng |
| M2 | Áp lực dừng holdout giữa chừng khi thấy kết quả tốt | Cam kết thời gian tối thiểu trong văn bản đăng ký trước, có chữ ký Ban Lãnh đạo |
| M3 | Hiệu ứng thay đổi theo thời gian (mới đầu tốt, sau nhạt dần) | Duy trì holdout thường trực ở tỷ lệ nhỏ hơn (3–5%) sau khi kết luận |
| M4 | Khối lượng case không đủ cho power mong muốn | Đánh giá lại MDE; mở rộng phạm vi phân khúc; chấp nhận kết luận yếu hơn nhưng nói rõ |
| M5 | Chỉ số chính bị thao túng (ví dụ hoãn ghi nhận chi phí) | Công thức tính do Khối Tài chính chốt và tính, không do dự án tính |
| M6 | Nhóm đối chứng bị phản đối vì lý do đạo đức | Nhóm đối chứng nhận quy trình hiện hành — chuẩn mực đạo đức tương đương "chăm sóc thông thường" trong thử nghiệm y khoa |

---

## 11. Việc cần làm ngay

| # | Hạng mục | Chủ trì | Hạn |
|---|---|---|---|
| 1 | **Trình Ban Lãnh đạo phê duyệt nguyên tắc holdout 10%** | PO + EA | **Tuần 2 của dự án** |
| 2 | Thay số giả định ở Mục 4.2 bằng số thực (khối lượng case, NCV, độ lệch chuẩn) | Khối Tài chính + Data | Tuần 4 |
| 3 | Chốt công thức NCV₉₀ chính xác với Khối Tài chính | Tài chính | Tuần 6 |
| 4 | Lập văn bản đăng ký trước, ký, commit vào repo | PO + Tài chính | Trước go-live |
| 5 | Chỉ định chủ sở hữu phép đo độc lập | Ban Điều hành | Tuần 4 |
| 6 | Hiện thực `holdout_assignment.py` + test | Data Eng | Tháng 2 |
| 7 | Thẩm định phương pháp bởi Model Risk / Kiểm toán nội bộ | MRM | Trước go-live |
| 8 | Thiết kế stepped-wedge cho hạng mục làm sạch dữ liệu | Data | Tháng 2 |

Hạng mục 1 là hạng mục có tính chặn cao nhất trong toàn dự án về mặt đo lường. **Holdout không thể thiết lập hồi tố.** Nếu go-live mà chưa có, cơ hội chứng minh ROI một cách đáng tin cậy mất vĩnh viễn cho toàn bộ cohort đã triển khai — và không có cách nào khắc phục sau đó.

---

*Tài liệu phương pháp, phiên bản đề xuất. Các giả định định lượng ở Mục 4.2 là số minh hoạ, cần thay bằng dữ liệu thực tế của Ngân hàng trước khi tính cỡ mẫu chính thức.*
