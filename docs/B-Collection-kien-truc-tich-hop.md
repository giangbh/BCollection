# B.COLLECTION — KIẾN TRÚC TÍCH HỢP HỆ THỐNG
### Quan hệ với Core Banking, LOS/RLOS/CLOS, LMS, EWS, MIS/DWH và các hệ thống liên quan
**Phiên bản:** v0.1 | **Ngày:** 01/09/2026
**Tài liệu liên quan:** Kiến trúc tổng thể v0.2 · Collection Graph · Persona Model v0.2 · Guardrail Service v1.0 · Tech Stack MVP

---

## 1. Nguyên tắc tích hợp

| # | Nguyên tắc | Hệ quả |
|---|---|---|
| **I1** | **B.Collection là hệ thống quyết định, không phải hệ thống ghi sổ** | Không sở hữu dữ liệu khoản vay, khách hàng, hay tài sản. Chỉ sở hữu 4 loại dữ liệu: **case thu hồi, persona, enrichment fact, audit log**. |
| **I2** | **Không ghi trực tiếp vào Core Banking** | Mọi thay đổi tài chính (thu nợ, cơ cấu, miễn giảm) đi qua hệ thống nghiệp vụ tương ứng (LMS/Core). B.Collection *khởi tạo yêu cầu*, không *thực hiện bút toán*. |
| **I3** | **Một sự thật, một nguồn** | Mỗi trường dữ liệu có đúng một hệ thống chủ. B.Collection sao chép để phục vụ, không để trở thành nguồn thứ hai. |
| **I4** | **Không xây kho dữ liệu thứ hai** | Cám dỗ lớn nhất của mọi dự án collection: dần tích luỹ dữ liệu tới mức trở thành DWH bóng. Ràng buộc: chỉ giữ dữ liệu phục vụ quyết định thu hồi, có TTL. |
| **I5** | **Tách tín hiệu khỏi hành động** | Hệ thống khác *phát hiện và cung cấp tín hiệu* (EWS, Fraud, AML); B.Collection *quyết định và thực thi hành động thu hồi*. Không chồng lấn. |
| **I6** | **Vòng phản hồi là bắt buộc, không phải tuỳ chọn** | Kết quả thu hồi phải chảy ngược về LOS/RLOS/CLOS (mô hình chấm điểm), EWS (hiệu chỉnh tín hiệu) và DWH (báo cáo). Thiếu chiều này, ngân hàng học được ít hơn nhiều so với chi phí bỏ ra. |
| **I7** | **Mọi interface có hợp đồng, có version, có contract test** | Hệ thống Core và LOS thay đổi theo nhịp riêng; B.Collection phải phát hiện lệch schema trong CI chứ không phát hiện trong production. |

---

## 2. Bản đồ hệ sinh thái

```
                         ┌──────────────────────────────────────┐
                         │            B.COLLECTION              │
                         │  Case · Persona · Graph · Guardrail  │
                         │  NBA · Enrichment · Audit            │
                         └──┬────────┬──────────┬────────┬──────┘
         ĐỌC (nguồn sự thật)│        │          │        │GHI (yêu cầu / kết quả)
    ┌────────────────────────┘        │          │        └──────────────────────┐
    ▼                                 ▼          ▼                               ▼
┌─────────────┐  ┌──────────────┐ ┌────────┐ ┌──────────┐   ┌──────────────────────┐
│ CORE BANKING│  │ LMS / CLMS   │ │  EWS   │ │ MIS/DWH  │   │ LMS (yêu cầu cơ cấu) │
│ Dư nợ, DPD  │  │ Lịch trả nợ  │ │ Tín    │ │ Dữ liệu  │   │ CRM (tương tác)      │
│ Giao dịch   │  │ Cơ cấu, phí  │ │ hiệu   │ │ lịch sử  │   │ DWH (kết quả)        │
│ Nhóm nợ     │  │ Trạng thái   │ │ cảnh   │ │ Báo cáo  │   │ LOS (phản hồi mô hình│
└─────────────┘  └──────────────┘ │ báo    │ └──────────┘   │ EWS (hiệu chỉnh)     │
                                  └────────┘                └──────────────────────┘
    ▲            ▲            ▲          ▲          ▲            ▲
┌───┴───┐ ┌──────┴─────┐ ┌────┴────┐ ┌───┴────┐ ┌───┴────┐ ┌─────┴──────┐
│ CIF/  │ │ LOS/RLOS/  │ │Collateral│ │  CIC   │ │  CRM   │ │Contact Ctr │
│ eKYC  │ │ CLOS       │ │ Mgmt     │ │        │ │        │ │ Dialer/CTI │
└───────┘ └────────────┘ └──────────┘ └────────┘ └────────┘ └────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ HỆ THỐNG NỘI BỘ LIÊN QUAN: KHLQ (graph) · CreditAgent (LLM GW, audit)     │
│ AML/Fraud · GL/Kế toán · ECM (lưu trữ chứng từ) · HRM (dữ liệu cán bộ)    │
│ Kênh số (Ngân hàng số) · SMS/ZNS Gateway · Hệ thống bán nợ / AMC          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Ranh giới trách nhiệm — hệ thống nào quyết định điều gì

Đây là bảng quan trọng nhất của tài liệu. Phần lớn xung đột trong triển khai đến từ việc hai hệ thống cùng tưởng mình sở hữu một quyết định.

| Quyết định | Hệ thống chủ | B.Collection làm gì |
|---|---|---|
| Khoản vay có quá hạn không, bao nhiêu ngày | **Core Banking** | Đọc, không tính lại |
| Phân loại nhóm nợ (1–5), trích lập DPRR | **Core / Hệ thống phân loại nợ** | Đọc, không tính lại |
| Khách hàng có dấu hiệu suy giảm khả năng trả *trước khi* quá hạn | **EWS** | Nhận tín hiệu, xem Mục 5 |
| Khách hàng nào cần liên hệ, bằng kênh nào, lúc nào | **B.Collection** | Sở hữu hoàn toàn |
| Được phép liên hệ ai, bao nhiêu lần | **B.Collection (Guardrail)** | Sở hữu hoàn toàn |
| Phương án cơ cấu có được duyệt không | **LMS + thẩm quyền phê duyệt** | Đề xuất phương án, không phê duyệt |
| Hạch toán thu nợ, miễn giảm lãi | **Core / GL** | Không chạm |
| Có khởi kiện không | **Ban Pháp chế** (qua workflow) | Đề xuất + tính NPV, không quyết |
| Có được thu giữ TSBĐ không | **B.Collection (Guardrail G09) chặn**, **Hội sở duyệt** | Chặn hành động không hợp lệ; không tự cho phép |
| Giá bán nợ | **Hội đồng XLN** | Cung cấp dự báo thu hồi (ML3) |
| Điểm tín dụng khi khách hàng vay lại | **LOS/RLOS/CLOS** | Cung cấp dữ liệu hành vi thu hồi làm đầu vào |
| Cảnh báo giao dịch đáng ngờ | **AML/Fraud** | Không chạm; chỉ nhận cờ để tách luồng |

**Quy tắc chung:** nếu một quyết định có hệ quả tài chính hoặc pháp lý được ghi sổ, B.Collection *đề xuất*; hệ thống nghiệp vụ tương ứng *quyết định và ghi*.

---

## 4. Danh mục interface

Ký hiệu: `IF-<hệ thống>-<số>`. Cột "MVP" đánh dấu interface bắt buộc cho giai đoạn đầu.

### 4.1 Core Banking

| ID | Hướng | Nội dung | Cơ chế | Tần suất | MVP |
|---|---|---|---|---|---|
| `IF-CORE-01` | Đọc | Danh mục khoản vay: dư nợ gốc/lãi, DPD, nhóm nợ, kỳ hạn, lãi suất | Batch EOD + CDC cho bảng nóng | Ngày + near-RT | ✓ |
| `IF-CORE-02` | Đọc | Giao dịch tài khoản (tiền vào/ra) 12–24 tháng | Batch EOD; **stream cho tiền vào ≥ ngưỡng** | Ngày + < 5 phút | ✓ |
| `IF-CORE-03` | Đọc | Số dư và trạng thái tài khoản, CASA | Batch EOD | Ngày | ✓ |
| `IF-CORE-04` | Đọc | Xác nhận thanh toán real-time | API/event | < 5 phút | ✓ |
| `IF-CORE-05` | Đọc | Lịch sử thu nợ, xử lý rủi ro, ngoại bảng | Batch | Ngày | GĐ2 |

> **`IF-CORE-04` là interface có giá trị cao nhất so với chi phí.** Nó cho phép Guardrail G01 chặn cuộc gọi tới khách hàng vừa trả nợ vài giờ trước. Nếu không có, nguồn khiếu nại phổ biến nhất trong thu hồi nợ sẽ tồn tại vĩnh viễn. Yêu cầu độ trễ ≤ 5 phút; nếu Core không hỗ trợ event, phương án dự phòng là polling danh sách case đang hoạt động mỗi 5 phút.

### 4.2 Loan Management System (LMS/CLMS)

| ID | Hướng | Nội dung | Cơ chế | MVP |
|---|---|---|---|---|
| `IF-LMS-01` | Đọc | Lịch trả nợ, kỳ hạn, số tiền từng kỳ | Batch | ✓ |
| `IF-LMS-02` | Đọc | Lịch sử cơ cấu, gia hạn, điều chỉnh kỳ hạn | Batch | ✓ |
| `IF-LMS-03` | Đọc | Trạng thái ân hạn, tạm hoãn trả nợ | Batch + API | ✓ |
| `IF-LMS-04` | **Ghi** | **Yêu cầu cơ cấu / giãn kỳ hạn / miễn giảm lãi** | API có phê duyệt | GĐ2 |
| `IF-LMS-05` | Đọc | Kết quả xử lý yêu cầu cơ cấu | API callback / event | GĐ2 |

`IF-LMS-04` là interface ghi duy nhất có hệ quả tài chính. Thiết kế bắt buộc: B.Collection gửi **yêu cầu** kèm `case_id`, `approval_ref`, `guardrail_token`; LMS xác thực thẩm quyền phê duyệt độc lập chứ không tin B.Collection. Đây là nguyên tắc bảo mật cơ bản — hệ thống nhận lệnh không được ủy thác việc kiểm soát thẩm quyền cho hệ thống gửi lệnh.

### 4.3 LOS / RLOS / CLOS

| ID | Hướng | Nội dung | Cơ chế | MVP |
|---|---|---|---|---|
| `IF-LOS-01` | Đọc | Hồ sơ thẩm định gốc: mục đích vay, thu nhập khai báo, phương án kinh doanh | Batch | ✓ |
| `IF-LOS-02` | Đọc | Thông tin bên bảo lãnh, đồng vay, người liên quan đã khai báo | Batch | **✓ (quan trọng)** |
| `IF-LOS-03` | Đọc | Hồ sơ, chứng từ đính kèm (qua ECM) | API | GĐ2 |
| `IF-RLOS-01` | Đọc | Đặc thù bán lẻ: nguồn thu nhập, nơi làm việc khai báo, chu kỳ lương | Batch | ✓ |
| `IF-CLOS-01` | Đọc | Đặc thù KHDN: cơ cấu sở hữu, người đại diện, đối tác lớn, báo cáo tài chính | Batch | GĐ2 |
| `IF-LOS-04` | **Ghi** | **Vòng phản hồi**: dữ liệu hành vi thu hồi làm đầu vào cho mô hình chấm điểm tín dụng | Batch (mart chia sẻ) | GĐ2 |

**`IF-LOS-02` là interface rủi ro cao nhất trong danh mục.** Bảng `party_obligation` — nền tảng của Guardrail G02 — được dựng chủ yếu từ đây. Nếu dữ liệu bên bảo lãnh và đồng vay trong LOS không đầy đủ hoặc không chuẩn hoá, G02 sẽ chặn quá nhiều và đội vận hành sẽ đòi nới ngưỡng. Đây chính là rủi ro R4 trong tài liệu Tech Stack. **Phải khảo sát chất lượng dữ liệu này trong tuần 3 của dự án**, trước khi cam kết phạm vi.

**Về `IF-LOS-04`:** đây là interface hay bị bỏ quên nhất và có giá trị dài hạn cao nhất. Hành vi trong quá trình thu hồi (giữ cam kết, tự khỏi nợ, phản ứng với từng treatment) là tín hiệu dự báo rủi ro rất mạnh cho lần cấp tín dụng tiếp theo. Nếu không có chiều này, ngân hàng thu hồi được nợ nhưng không học được gì để cho vay tốt hơn.

### 4.4 EWS — xem Mục 5 (quan hệ phức tạp nhất)

| ID | Hướng | Nội dung | Cơ chế | MVP |
|---|---|---|---|---|
| `IF-EWS-01` | Đọc | Tín hiệu cảnh báo sớm theo khách hàng: mã tín hiệu, mức độ, thời điểm | Event + batch | GĐ2 |
| `IF-EWS-02` | Đọc | Điểm cảnh báo tổng hợp và lịch sử diễn biến | Batch | GĐ2 |
| `IF-EWS-03` | **Ghi** | Kết quả thu hồi để hiệu chỉnh độ chính xác tín hiệu EWS | Batch | GĐ2 |
| `IF-EWS-04` | Đọc | Danh sách khách hàng nhóm 1 có rủi ro cao (tiền quá hạn) | Batch | GĐ3 |

### 4.5 MIS / DWH

| ID | Hướng | Nội dung | Cơ chế | MVP |
|---|---|---|---|---|
| `IF-DWH-01` | Đọc | Dữ liệu lịch sử đã chuẩn hoá phục vụ huấn luyện mô hình | Batch / view | ✓ |
| `IF-DWH-02` | Đọc | Dữ liệu tham chiếu: danh mục sản phẩm, chi nhánh, mã ĐVHC | Batch | ✓ |
| `IF-DWH-03` | **Ghi** | Data mart kết quả thu hồi phục vụ báo cáo quản trị | Batch nightly | ✓ |
| `IF-DWH-04` | **Ghi** | Chỉ số tuân thủ (block rate, outcome MI phân tách theo nhóm) | Batch | GĐ2 |

**Quan hệ với DWH là quan hệ hai chiều và cần định vị rõ:**
- DWH là **nguồn dữ liệu huấn luyện** và nguồn dữ liệu tham chiếu → B.Collection đọc.
- DWH là **điểm hợp nhất báo cáo toàn hàng** → B.Collection ghi kết quả về, không tự làm báo cáo quản trị cấp ngân hàng.
- B.Collection **không** dùng DWH cho đường quyết định real-time (độ trễ và SLA không phù hợp). Dữ liệu nóng lấy trực tiếp từ Core.

Ranh giới cần giữ (nguyên tắc I4): B.Collection giữ dữ liệu ở mức đủ cho quyết định thu hồi trong vòng đời case; dữ liệu lịch sử dài hạn và phân tích toàn hàng thuộc về DWH.

### 4.6 Các hệ thống còn lại

| Hệ thống | ID | Hướng | Nội dung | MVP |
|---|---|---|---|---|
| **CIF / eKYC** | `IF-CIF-01` | Đọc | Định danh, số điện thoại, địa chỉ, người liên quan đã khai | ✓ |
| | `IF-CIF-02` | Ghi | Đề xuất cập nhật thông tin liên hệ đã xác minh (qua hàng đợi duyệt) | GĐ2 |
| **Collateral Mgmt** | `IF-COL-01` | Đọc | TSBĐ: loại, định giá, tình trạng pháp lý, thứ tự ưu tiên | ✓ |
| | `IF-COL-02` | Đọc | **`is_sole_residence`, `is_primary_work_tool`** (Guardrail G09) | GĐ3 |
| **CIC** | `IF-CIC-01` | Đọc | Quan hệ tín dụng toàn ngành, nhóm nợ tại TCTD khác | GĐ2 |
| **CRM** | `IF-CRM-01` | Đọc/Ghi | Lịch sử tương tác, ticket, khiếu nại (hai chiều) | ✓ |
| **Contact Center / CTI** | `IF-CC-01` | Ghi | Lệnh gọi có `guardrail_token`; screen-pop Persona Card | GĐ2 |
| | `IF-CC-02` | Đọc | Kết quả cuộc gọi, ghi âm, thời lượng | GĐ2 |
| **SMS / ZNS Gateway** | `IF-MSG-01` | Ghi | Gửi tin nhắn có token; nhận trạng thái gửi | ✓ |
| **Kênh số (Ngân hàng số)** | `IF-DIG-01` | Đọc | Tần suất đăng nhập (tín hiệu "còn hoạt động") | ✓ |
| | `IF-DIG-02` | Ghi | Thông báo in-app, kênh tự phục vụ trả nợ | GĐ2 |
| **AML / Fraud** | `IF-FRD-01` | Đọc | Cờ nghi ngờ gian lận → tách luồng xử lý riêng | GĐ2 |
| **GL / Kế toán** | `IF-GL-01` | Đọc | Xác nhận trích lập khoản bồi thường (G09, 12 tháng lương tối thiểu) | GĐ3 |
| **ECM** | `IF-ECM-01` | Đọc/Ghi | Chứng từ, biên bản field visit, bằng chứng đồng ý | GĐ2 |
| **HRM** | `IF-HR-01` | Đọc | Danh sách cán bộ, chi nhánh, phân quyền (**không lấy dữ liệu tính cách**) | ✓ |
| **Hệ thống KHLQ** | `IF-KHLQ-01` | Đọc | Graph nhóm khách hàng liên quan, entity resolution | GĐ2 |
| **CreditAgent** | `IF-CA-01` | Chia sẻ | LLM Gateway, Tool Gateway, khung audit hash-chain | GĐ2 |
| **Bán nợ / AMC** | `IF-AMC-01` | Ghi | Đóng gói danh mục, hồ sơ chuyển giao | GĐ3 |

---

## 5. Quan hệ với EWS — ranh giới cần chốt sớm

Đây là quan hệ dễ xung đột nhất, vì hai hệ thống dùng dữ liệu giống nhau, mô hình giống nhau, và cùng hướng tới việc "can thiệp sớm với khách hàng có rủi ro".

### 5.1 Phân định theo trục thời gian

```
      Trước quá hạn          │  DPD 0    │        Sau quá hạn
 ─────────────────────────────┼───────────┼──────────────────────────────►
   EWS SỞ HỮU                 │  VÙNG     │   B.COLLECTION SỞ HỮU
   · Phát hiện suy giảm       │  CHỒNG    │   · Chấm điểm khả năng/thiện chí
   · Cảnh báo cán bộ QHKH     │  LẤN      │   · Quyết định treatment
   · Đề xuất rà soát hạn mức  │           │   · Guardrail
   · Kích hoạt tái thẩm định  │           │   · Thu hồi, cơ cấu, pháp lý
```

### 5.2 Ba mô hình xử lý vùng chồng lấn — và khuyến nghị

| Mô hình | Mô tả | Đánh giá |
|---|---|---|
| **A. EWS làm hết tới DPD 30** | EWS mở rộng sang nhắc nợ sớm | ❌ EWS thường không có Guardrail, không có quản lý case, không có kênh. Mở rộng sẽ phải xây lại toàn bộ những thứ B.Collection đã có |
| **B. B.Collection lùi về trước DPD 0** | B.Collection tự phát hiện tín hiệu sớm | ❌ Trùng lặp mô hình với EWS, hai hệ thống cho hai kết luận khác nhau về cùng khách hàng → mất niềm tin |
| **C. EWS sở hữu tín hiệu, B.Collection sở hữu hành động** | EWS phát tín hiệu; B.Collection nhận và quyết định treatment | ✅ **Khuyến nghị** |

**Mô hình C hoạt động thế nào:**

```
EWS phát hiện tín hiệu (dòng tiền giảm, chậm trả nơi khác qua CIC,
    doanh nghiệp ngừng hoạt động, tài sản bị kê biên...)
        │
        ├──► Cán bộ QHKH  : rà soát quan hệ tín dụng, tái thẩm định  (EWS sở hữu)
        │
        └──► B.Collection : nhận qua IF-EWS-01 như một ĐẦU VÀO của Persona
                            → tạo "pre-delinquency case" (loại case riêng)
                            → treatment mềm: liên hệ tư vấn, chào cơ cấu chủ động
                            → VẪN đi qua Guardrail đầy đủ
```

**Bốn quy tắc bắt buộc của mô hình C:**

1. **B.Collection không xây mô hình dự báo trước quá hạn.** Nếu cần, đề nghị EWS bổ sung tín hiệu. Hai mô hình cùng dự báo một hiện tượng là nguồn xung đột không thể hoà giải.
2. **Tín hiệu EWS vào Persona như một feature, không phải như một quyết định.** Trục D1 (Ability) nhận `ews_signal_code`, `ews_severity`, `ews_first_raised_at`. NBA Engine tự quyết định treatment.
3. **Pre-delinquency case đi qua Guardrail đầy đủ.** Đây là điểm dễ bị bỏ sót: khách hàng chưa quá hạn thì cơ sở pháp lý để liên hệ về nghĩa vụ nợ *yếu hơn*, không phải mạnh hơn. G01 (Debt Validity) cần một nhánh riêng cho pre-delinquency, và nội dung liên hệ phải mang tính **tư vấn/chăm sóc**, không phải nhắc nợ.
4. **Vòng phản hồi hai chiều.** `IF-EWS-03` gửi kết quả thu hồi về để EWS đo độ chính xác tín hiệu của mình. Không có chiều này, EWS sẽ tiếp tục phát tín hiệu mà không biết tín hiệu nào hữu ích.

### 5.3 Việc cần chốt
| # | Câu hỏi | Người quyết |
|---|---|---|
| 1 | EWS hiện có phát tín hiệu ở mức khách hàng hay mức khoản vay? | Chủ quản EWS |
| 2 | Ai sở hữu quyết định "liên hệ chủ động trước quá hạn": QHKH hay đội thu hồi? | Ban Điều hành |
| 3 | Có cần loại case riêng `PRE_DELINQUENCY` trong workflow không? | PO + Pháp chế |
| 4 | Cơ sở pháp lý để liên hệ khách hàng chưa quá hạn về khoản vay? | Pháp chế |

---

## 6. Các luồng nghiệp vụ xuyên hệ thống

### 6.1 Tạo case thu hồi
```
Core Banking: khoản vay chuyển sang quá hạn (DPD 1)
   → IF-CORE-01 (batch EOD hoặc CDC)
   → B.Collection: tạo CollectionCase
   → Đọc IF-LOS-02 dựng party_obligation
   → Tính Persona (ability, contactability, willingness_matrix)
   → NBA chọn hành động (có thể là NO_ACTION)
   → Guardrail evaluate → token
   → IF-MSG-01 gửi SMS
   → Guardrail commit
   → IF-DWH-03 ghi kết quả về DWH
```

### 6.2 Khách hàng trả nợ giữa chiến dịch (luồng quan trọng nhất)
```
Khách hàng chuyển tiền lúc 16:20
   → Core Banking ghi nhận
   → IF-CORE-04 event (< 5 phút)
   → B.Collection: cập nhật dư nợ quá hạn = 0
   → Huỷ mọi intent đang chờ trong hàng đợi của case
   → Guardrail G01 sẽ BLOCK mọi lệnh mới (DEBT_NOT_FOUND / NO_OUTSTANDING)
   → Đóng case, ghi outcome
```
Nếu `IF-CORE-04` không tồn tại hoặc trễ, cuộc gọi lúc 19:00 vẫn diễn ra. Đây là lý do interface này được xếp P0 dù không hiển nhiên.

### 6.3 Chào và thực hiện cơ cấu nợ
```
NBA đề xuất RESTRUCTURE_OFFER (từ willingness_matrix)
   → Guardrail: ALLOW_WITH_CONDITIONS (trong khung chính sách đã duyệt)
   → Cán bộ đàm phán, khách hàng đồng ý
   → Workflow: hồ sơ cơ cấu → phê duyệt theo thẩm quyền
   → IF-LMS-04 gửi yêu cầu kèm approval_ref
   → LMS tự xác thực thẩm quyền, thực hiện, ghi sổ
   → IF-LMS-05 callback kết quả
   → B.Collection cập nhật case, Persona tính lại
   → IF-DWH-03 + IF-LOS-04 (phản hồi mô hình)
```

### 6.4 Thu giữ TSBĐ (GĐ3)
```
NBA đề xuất PROPOSE_SEIZURE
   → Guardrail G09: đọc IF-COL-02 (is_sole_residence)
       · NULL       → BLOCK: SOLE_RESIDENCE_UNVERIFIED
       · true       → kiểm tra IF-GL-01 (đã trích lập 12 tháng lương tối thiểu?)
                      → ESCALATE: phê duyệt Hội sở, không phân cấp
       · false      → ESCALATE: phê duyệt theo thẩm quyền thông thường
   → Sau phê duyệt: workflow thu giữ theo quy định nội bộ
   → ECM lưu biên bản; audit ghi internal_procedure_version
```

---

## 7. Cơ chế tích hợp theo loại dữ liệu

| Loại dữ liệu | Cơ chế | Lý do |
|---|---|---|
| Danh mục khoản vay, hồ sơ tín dụng | **Batch EOD** | Khối lượng lớn, không cần real-time |
| Thanh toán, dư nợ quá hạn | **Event / CDC** | Quyết định phụ thuộc trực tiếp; trễ = khiếu nại |
| Tín hiệu EWS | **Event** | Cần phản ứng trong ngày |
| Dữ liệu tham chiếu (danh mục, mã ĐVHC) | **Batch tuần/tháng** | Ít thay đổi |
| Lệnh ra kênh | **API đồng bộ** | Cần token và phản hồi tức thì |
| Yêu cầu cơ cấu | **API + callback bất đồng bộ** | Có bước phê duyệt của con người |
| Kết quả về DWH | **Batch nightly** | Phục vụ báo cáo |
| Dữ liệu huấn luyện | **Batch theo yêu cầu** | Không thuộc đường vận hành |

**Khuyến nghị MVP:** ưu tiên batch cho hầu hết interface; chỉ dùng event cho `IF-CORE-04` và (GĐ2) `IF-EWS-01`. Dựng Kafka cho toàn bộ tích hợp ở MVP là over-engineering — xem tài liệu Tech Stack, Mục 10.

---

## 8. Xử lý lỗi tích hợp

Nguyên tắc: **lỗi tích hợp không được biến thành hành động sai với khách hàng.**

| Interface lỗi | Hành vi |
|---|---|
| `IF-CORE-01/04` | Guardrail G01 fail-closed → **dừng toàn bộ liên hệ**. Không đòi nợ khi không biết dư nợ hiện tại |
| `IF-LOS-02` (party_obligation lệch) | G02 fail-closed → chặn. Không suy đoán ai có nghĩa vụ |
| `IF-EWS-01` | Suy giảm êm: pre-delinquency case không được tạo mới, case hiện có vẫn chạy |
| `IF-LMS-04` | Yêu cầu cơ cấu vào hàng đợi retry; **thông báo cho cán bộ**, không âm thầm thất bại — khách hàng đã được hứa |
| `IF-MSG-01` | Retry có giới hạn; mỗi lần retry **phải gọi lại Guardrail** (nguyên tắc GR7: kiểm tra tại thời điểm gửi) |
| `IF-DWH-03` | Suy giảm êm: dữ liệu tồn lại, gửi bù ngày hôm sau |
| `IF-COL-02` | G09 chặn thu giữ. Chấp nhận chặn nhầm hơn là thu giữ sai |

Điểm cần lưu ý ở `IF-MSG-01`: retry một tin nhắn đã bị Guardrail cho phép 3 giờ trước là **sai**, vì trong 3 giờ đó khách hàng có thể đã trả nợ, đã yêu cầu DNC, hoặc đã vượt quota tần suất. Token có TTL 5 phút chính là để chặn kiểu lỗi này.

---

## 9. Quản trị interface

| Hạng mục | Yêu cầu |
|---|---|
| **Hợp đồng** | Mỗi interface có tài liệu đặc tả: schema, SLA, khối lượng, cơ chế lỗi, chủ sở hữu hai đầu |
| **Version** | Semantic versioning; thay đổi phá vỡ tương thích cần thông báo trước 60 ngày |
| **Contract test** | Chạy trong CI hằng ngày trên môi trường UAT — phát hiện lệch schema trước production |
| **Giám sát** | Mỗi interface có dashboard: khối lượng, độ trễ, tỷ lệ lỗi, độ tươi dữ liệu |
| **Data freshness alert** | Cảnh báo khi dữ liệu Core cũ hơn ngưỡng — vì Guardrail sẽ fail-closed và dừng vận hành |
| **Chủ sở hữu** | Mỗi interface có một người chịu trách nhiệm ở mỗi đầu, ghi trong catalog |

**Contract test là hạng mục hay bị cắt khi gấp tiến độ, và là hạng mục tốn kém nhất khi bỏ.** Core Banking và LOS thay đổi theo nhịp riêng của chúng; nếu không phát hiện lệch schema trong CI, B.Collection sẽ phát hiện bằng một chiến dịch gửi sai cho vài nghìn khách hàng.

---

## 10. Phạm vi tích hợp cho MVP

**Bắt buộc (P0) — 12 interface:**
`IF-CORE-01`, `IF-CORE-02`, `IF-CORE-03`, `IF-CORE-04`, `IF-LMS-01`, `IF-LMS-02`, `IF-LMS-03`, `IF-LOS-01`, `IF-LOS-02`, `IF-RLOS-01`, `IF-CIF-01`, `IF-COL-01`, `IF-DWH-01`, `IF-DWH-02`, `IF-DWH-03`, `IF-MSG-01`, `IF-DIG-01`, `IF-CRM-01`, `IF-HR-01`

**Hoãn sang GĐ2 trở đi:** EWS, CIC, Contact Center/CTI, LMS ghi, KHLQ, CreditAgent, AML/Fraud, ECM, bán nợ, GL.

Lưu ý: MVP **không tích hợp EWS**. Không phải vì EWS không quan trọng, mà vì ranh giới ở Mục 5 cần được Ban Điều hành chốt trước, và cuộc thảo luận đó sẽ dễ hơn nhiều khi B.Collection đã chạy được và mọi người thấy rõ nó làm gì.

---

## 11. Rủi ro tích hợp

| # | Rủi ro | Mức | Biện pháp |
|---|---|---|---|
| R1 | `IF-LOS-02` dữ liệu bảo lãnh/đồng vay không đầy đủ → G02 chặn quá nhiều | **Cao** | Khảo sát tuần 3; chuẩn bị luồng bổ sung thủ công có kiểm soát |
| R2 | Core không hỗ trợ event real-time cho thanh toán | **Cao** | Phương án polling 5 phút; nếu vẫn không được, chấp nhận rủi ro và ghi vào risk register |
| R3 | Xung đột ranh giới với EWS kéo dài, chặn tiến độ | Trung bình | Hoãn tích hợp EWS khỏi MVP; đưa quyết định lên Ban Điều hành với 3 phương án ở Mục 5.2 |
| R4 | Quy trình cấp quyền truy cập nội bộ kéo dài | **Cao** | Xin quyền từ tuần 1 cho toàn bộ 19 interface P0 |
| R5 | Core/LOS thay đổi schema không báo trước | Trung bình | Contract test trong CI + thoả thuận thông báo 60 ngày |
| R6 | B.Collection dần tích luỹ dữ liệu thành DWH bóng | Trung bình | Rà soát định kỳ theo nguyên tắc I4; mọi bảng mới cần lý do và TTL |
| R7 | `IF-LMS-04` bị dùng để lách thẩm quyền phê duyệt | **Cao** | LMS tự xác thực thẩm quyền độc lập, không tin B.Collection |

---

## 12. Việc cần làm tiếp

| # | Hạng mục | Chủ trì | Hạn |
|---|---|---|---|
| 1 | Kiểm kê hệ thống thực tế của Ngân hàng và ánh xạ vào danh mục interface này | EA + Khối CNTT | Tuần 2 |
| 2 | **Khảo sát chất lượng dữ liệu `IF-LOS-02`** (bảo lãnh, đồng vay) | Data Engineer | Tuần 3 |
| 3 | Xác nhận Core có hỗ trợ event thanh toán real-time không (`IF-CORE-04`) | Khối CNTT | Tuần 2 |
| 4 | Chốt ranh giới EWS ↔ B.Collection theo 4 câu hỏi Mục 5.3 | Ban Điều hành | Tháng 2 |
| 5 | Xin quyền truy cập cho 19 interface P0 | PO + CNTT | Tuần 1 |
| 6 | Lập interface catalog với chủ sở hữu hai đầu | SA | Tuần 4 |
| 7 | Thiết lập contract test trong CI | DevOps | Tháng 2 |
| 8 | Xác nhận Collateral Mgmt có lưu `is_sole_residence` không (`IF-COL-02`) | Ban XLN | Tháng 3 |

---

*Tài liệu kiến trúc tích hợp, phiên bản đề xuất. Danh mục hệ thống dựa trên mô hình ứng dụng ngân hàng phổ biến — cần đối chiếu với bản đồ ứng dụng thực tế của Ngân hàng và điều chỉnh tương ứng.*
