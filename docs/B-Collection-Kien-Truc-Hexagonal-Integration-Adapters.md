# B.COLLECTION — KIẾN TRÚC TÍCH HỢP HỆ THỐNG BACKEND (HEXAGONAL PORTS & ADAPTERS)
### Thiết kế Phân tách Độc lập Giữa Adapter Nghiệp vụ và Client Kết nối Backend (Core Banking, LOS, Messaging, CIC)
**Dự án:** Hệ thống Quản lý & Tối ưu Thu hồi nợ B.Collection — BIDV  
**Tác giả:** Lead Enterprise Architect  
**Phiên bản:** v1.0 | **Ngày ban hành:** 02/09/2026

---

## 🎯 1. NGUYÊN TẮC THIẾT KẾ: ADAPTER BẤT BIẾN KHI GO-LIVE (ZERO ADAPTER CODE CHANGE)

Trong các dự án ngân hàng trước đây, việc "Mock" thường bị nhúng trực tiếp vào Adapter (`MockCoreBankingAdapter`), dẫn đến khi đấu nối hệ thống thật, đội ngũ kỹ sư phải:
* Viết lại một Adapter mới (`HttpCoreBankingAdapter`).
* Sửa đổi toàn bộ mã nguồn gọi Adapter trong tầng nghiệp vụ (`Collection API`, `Workflow Service`).
* Nguy cơ phát sinh lỗi sai lệch DTO hoặc logic xử lý dữ liệu.

**Kiến trúc Hexagonal Mới của B.Collection giải quyết dứt điểm vấn đề này:**
1. **Một Adapter Duy Nhất Cho Mỗi Hệ Thống Ngoại Vi:** 
   * `CoreBankingAdapter`, `LOSAdapter`, `MessagingGatewayAdapter`, `CICAdapter` là các Adapter nghiệp vụ chuẩn duy nhất của hệ thống.
   * Chứa 100% logic chuyển đổi DTO, xác thực hợp đồng dữ liệu (*JSON Schema Contracts*), kiểm tra Guardrail Token và cơ chế chống đòi nợ oan.
2. **Adapter Chỉ Ủy Nhiệm Cho `ApiClient`:**
   * Adapter không trực tiếp thực hiện gọi mạng hay lưu dữ liệu mock. Thay vào đó, Adapter gọi qua Interface `ApiClient`.
3. **Khi Chuyển Từ Mock Sang Thật:**
   * **Mã nguồn Adapter và Core API GIỮ NGUYÊN 100%**.
   * Chỉ cần thay đổi biến môi trường cấu hình (Ví dụ: `CORE_BANKING_MODE=http`, `CORE_BANKING_API_URL=https://esb.bidv.vn/api/core/v1`).

---

## 🏗️ 2. SƠ ĐỒ KIẾN TRÚC TỔNG THỂ (PORTS & ADAPTERS)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     TẦNG ỨNG DỤNG NGHIỆP VỤ (APPLICATION CORE)                         │
│                  (Collection API, Case Workflow State Machine, Balance Check Service)                   │
└───────────────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              TẦNG ADAPTER NGHIỆP VỤ (HEXAGONAL ADAPTERS - BẤT BIẾN)                    │
├──────────────────────────┬──────────────────────────┬──────────────────────────┬───────────────────────┤
│ CoreBankingAdapter       │ LOSAdapter               │ MessagingGatewayAdapter  │ CICAdapter            │
│ • Validate IF-CORE-01/04 │ • Validate IF-LOS-02     │ • Validate IF-MSG-01     │ • Báo cáo nợ CIC      │
│ • Chuyển đổi DTO số dư   │ • Lọc bên có nghĩa vụ    │ • Kiểm tra Token L6      │ • Nhóm nợ xấu nhất    │
│ • Kiểm tra nợ quá hạn    │ • Tài sản thế chấp LTV   │ • Định dạng mẫu VietQR   │ • Tín hiệu trả nợ     │
└────────────┬─────────────┴────────────┬─────────────┴────────────┬─────────────┴───────────┬───────────┘
             │                          │                          │                         │
             ▼                          ▼                          ▼                         ▼
┌──────────────────────────┐┌──────────────────────────┐┌──────────────────────────┐┌──────────────────────────┐
│ CoreBankingApiClient     ││ LOSApiClient             ││ MessagingApiClient       ││ CICApiClient             │
│ (Interface trừu tượng)   ││ (Interface trừu tượng)   ││ (Interface trừu tượng)   ││ (Interface trừu tượng)   │
└────────────┬─────────────┘└───────────┬──────────────┘└──────────┬───────────────┘└───────────┬──────────────┘
             │                          │                          │                            │
   ┌─────────┴─────────┐      ┌─────────┴─────────┐      ┌─────────┴─────────┐        ┌─────────┴─────────┐
   ▼                   ▼      ▼                   ▼      ▼                   ▼        ▼                   ▼
┌──────────────┐┌────────────┐┌─────────┐┌────────────┐┌─────────┐┌────────────┐ ┌─────────┐┌────────────┐
│ Mock Client  ││ Http Client││Mock     ││ Http Client││Mock     ││ Http Client│ │Mock     ││ Http Client│
│ (DEV/UAT)    ││ (ESB Thật) ││Client   ││ (LOS Thật) ││Client   ││ (Gateway)  │ │Client   ││ (CIC Thật) │
└──────────────┘└────────────┘└─────────┘└────────────┘└─────────┘└────────────┘ └─────────┘└────────────┘
```

---

## 📦 3. ĐẶC TẢ 4 ADAPTERS ĐÃ ĐƯỢC TÁI CẤU TRÚC HOÀN CHỈNH

### 3.1 `CoreBankingAdapter` (Core Banking Integration)
* **Thư mục:** `bcollection-platform/services/integration-adapters/src/core_banking/`
* **Hợp đồng Tuân thủ:** `IF-CORE-01.loan-portfolio.schema.json`, `IF-CORE-04.payment-event.schema.json`
* **Nghiệp vụ cốt lõi:**
  * `get_realtime_balance(loan_id)`: Kiểm tra số dư nợ quá hạn thời gian thực.
  * `check_recent_payment(loan_id, lookback_minutes=15)`: Bắt sự kiện khách vừa chuyển tiền để hủy nhắc nợ ngay lập tức.
  * `get_overdue_portfolio(max_dpd=30)`: Trích xuất danh mục nợ B1 vào Case Queue.
  * `get_customer_inflow_profile(cif)`: Lấy dữ liệu dòng tiền và lương phục vụ điểm D1.
* **Cấu hình Go-Live:**
  ```bash
  CORE_BANKING_MODE=http
  CORE_BANKING_API_URL=https://esb.bidv.vn/api/core/v1
  CORE_BANKING_API_KEY=secret_production_token
  ```

---

### 3.2 `LOSAdapter` (Loan Origination Integration)
* **Thư mục:** `bcollection-platform/services/integration-adapters/src/los/`
* **Hợp đồng Tuân thủ:** `IF-LOS-02.party-obligation.schema.json`
* **Nghiệp vụ cốt lõi:**
  * `get_loan_party_obligations(loan_id)`: Trích xuất danh sách bên vay, bên bảo lãnh và đồng vay từ hồ sơ tín dụng.
  * `get_loan_collateral(loan_id)`: Trích xuất thông tin tài sản thế chấp và tỷ lệ $LTV$.
* **Cấu hình Go-Live:**
  ```bash
  LOS_MODE=http
  LOS_API_URL=https://esb.bidv.vn/api/los/v1
  LOS_API_KEY=secret_los_token
  ```

---

### 3.3 `MessagingGatewayAdapter` (SMS & Zalo ZNS Gateway)
* **Thư mục:** `bcollection-platform/services/integration-adapters/src/messaging/`
* **Hợp đồng Tuân thủ:** `IF-MSG-01.message-send.schema.json`
* **Nghiệp vụ cốt lõi:**
  * `send_sms_notification(phone, message, guardrail_token)`: Gửi SMS Brandname BIDV.
  * `send_zns_notification(phone, template_id, template_data, guardrail_token)`: Gửi Zalo ZNS kèm link VietQR.
  * **Ràng buộc cứng:** Bắt buộc phải có `guardrail_token` hợp lệ do L6 Guardrail cấp, nếu không hệ thống sẽ ném ngoại lệ và chặn gửi tin 100%.
* **Cấu hình Go-Live:**
  ```bash
  MESSAGING_MODE=http
  MSG_GATEWAY_URL=https://esb.bidv.vn/api/messaging/v1
  MSG_GATEWAY_KEY=secret_gateway_token
  ```

---

### 3.4 `CICAdapter` (Credit Information Center)
* **Thư mục:** `bcollection-platform/services/integration-adapters/src/cic/`
* **Nghiệp vụ cốt lõi:**
  * `get_credit_report(debtor_cif, national_id)`: Lấy nhóm nợ xấu nhất tại các TCTD khác, số lượng TCTD đang có dư nợ và tín hiệu ưu tiên trả nợ chéo.
* **Cấu hình Go-Live:**
  ```bash
  CIC_MODE=http
  CIC_GATEWAY_URL=https://esb.bidv.vn/api/cic/v1
  CIC_GATEWAY_KEY=secret_cic_token
  ```

---

## 🧪 4. KẾT QUẢ KIỂM THỬ TÍCH HỢP TỰ ĐỘNG (28/28 TESTS PASSED)

Toàn bộ 28 bài kiểm thử (Bao gồm Compliance Guardrail, Case Workflow, Manual Enrichment, VietQR, Realtime Balance Check và 4 Hexagonal Adapters) đã được chạy kiểm thử thành công:

```text
============================= test session starts ==============================
bcollection-guardrail/tests/compliance/test_guardrail_suite.py (7 passed)
bcollection-data/tests/test_holdout_and_synthetic.py (3 passed)
bcollection-data/tests/test_ml_models.py (3 passed)
bcollection-platform/services/case-workflow/tests/test_workflow.py (2 passed)
bcollection-platform/services/enrichment-api/tests/test_enrichment.py (2 passed)
bcollection-platform/services/channel-adapters/tests/test_adapters.py (3 passed)
bcollection-platform/services/collection-api/tests/test_vietqr_and_balance.py (4 passed)
bcollection-platform/services/integration-adapters/tests/test_hexagonal_adapters.py (4 passed)
============================== 28 passed in 0.15s ==============================
```

> 🏆 **KẾT LUẬN KIẾN TRÚC:**  
> Hệ thống hiện tại đã đạt độ hoàn thiện cao nhất về mặt kiến trúc phần mềm doanh nghiệp: **Toàn bộ Mock API đã được chuyển thành Client độc lập, Adapter trở thành thành phần bất biến và sẵn sàng đấu nối với ESB thực tế của ngân hàng chỉ bằng một dòng cấu hình môi trường!**
