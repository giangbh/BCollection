# ADR-003 — PR-02: tính đúng của case, payment và PTP

Trạng thái: triển khai trong POC demo/test. Kế tiếp PR-01; chưa có EWS intake,
policy handoff, outcome feedback bus hoặc quyền ghi dữ liệu Core thật.

## Quyết định nghiệp vụ

| Khái niệm | Nguồn sự thật và ý nghĩa |
|---|---|
| Contact hold | Tạm dừng liên hệ khi phát hiện payment hoặc cần đối soát; không xóa nợ |
| Case lifecycle | OPEN / SUSPENDED / PROBATION / CLOSED, độc lập với stage và PTP |
| Case stage | PRE_COLLECTION / EARLY_COLLECTION / RECOVERY; migration mặc định EARLY_COLLECTION, chưa có policy tự chuyển stage |
| Exposure obligation | UNVERIFIED / OVERDUE / CURRENT / SETTLED, projection từ số dư Core |
| CURED | Tất cả exposure của case có bằng chứng Core còn mới, overdue=0 và DPD=0; không đồng nghĩa tất toán khoản vay |
| PTP KEPT | Tổng payment POSTED được gắn đúng PTP, đúng khoản vay, phát sinh trong cửa sổ từ lúc hứa đến hạn, chưa bị đảo, đủ số tiền cam kết |
| PTP BROKEN | Chưa đủ số tiền đúng hạn **và** nguồn payment xác nhận đã quan sát đầy đủ qua thời điểm đến hạn |

CaseService là writer nghiệp vụ duy nhất. Workflow mutation cũ bị vô hiệu hóa;
wrapper database chuyển sang CaseService và bắt buộc command_id / expected_version.
CaseStatus cũ chỉ còn là projection tương thích cho UI, không phải nguồn quyết định.
Mọi wrapup sau khi case đóng hoặc bị hold trả 409; không âm thầm mở lại case.

## Transaction, thứ tự và idempotency

Mỗi command dùng SQLite BEGIN IMMEDIATE, kiểm tra case_version và ghi đồng thời
projection, ledger/PTP, interaction, transition audit, kết quả idempotency.
Hai người cập nhật cùng phiên bản: một thành công, một nhận 409. command_id giống
nhau và nội dung giống nhau trả kết quả đã lưu; tái sử dụng ID với nội dung khác trả 409.
expected_version không nằm trong fingerprint để retry của command đã commit vẫn an toàn.

Payment có event_id duy nhất toàn ledger. Gửi trùng dưới command_id khác cũng không
ghi tiền lần nữa, không tăng case_version và không bật lại hold sau đối soát.
Payload khác nhưng cùng event_id bị từ chối. Chỉ hỗ trợ full reversal, tham chiếu
đúng payment gốc, đúng loan/CIF/case và số tiền. Reversal đến trước payment gốc trả
409, producer phải phát lại sau; chưa có hàng đợi pending/DLQ trong PR này.

Core snapshot bắt buộc có identity, whole-VND, DPD, source_version tăng đơn điệu
theo khoản vay và as_of có timezone. Snapshot quá 15 phút hoặc tương lai quá 30 giây
bị từ chối. Version cũ không ghi đè version mới; cùng version khác nội dung là lỗi.
Snapshot mới không được có timestamp cũ hơn snapshot trước hoặc payment đã nhận.
Hợp đồng yêu cầu source_version mới cho một lần xác nhận số dư/as_of mới.

Payment không tự trừ số dư cục bộ: chỉ snapshot Core thay đổi số dư. Khi reversal
ảnh hưởng case đã cure, chuyển PROBATION, vô hiệu xác nhận số dư của loan đó và hold.
Core snapshot mới cùng command reconcile có lý do là điều kiện để tiếp tục xử lý.
Số dư mới phát sinh sau cure cũng chuyển PROBATION; không tự cho phép gọi lại.

## PTP và dữ liệu học

- PTP mới gắn rõ một exposure; một exposure chỉ có một PTP đang mở. Một case có thể
  có nhiều PTP trên các exposure khác nhau. Không phân bổ cùng một payment sang hai PTP.
- ptp_id trong payment là liên kết đối soát tường minh; không tự đoán chỉ từ số tiền.
  Payment chưa liên kết vẫn được ghi nhận nhưng không làm PTP thành KEPT.
- Ngày YYYY-MM-DD từ UI được hiểu là 23:59:59 Asia/Ho_Chi_Minh, lưu UTC. Hạn mới
  phải ở tương lai; tiền là số nguyên VND dương, không làm tròn âm thầm.
- PARTIALLY_KEPT là trạng thái chưa kết luận khi có một phần payment nhưng chưa đủ
  bằng chứng đúng hạn; chỉ KEPT/BROKEN đi vào mẫu số ptp_kept_rate.
- payments_complete_through là watermark của nguồn dữ liệu, không phải đồng hồ UI.
  Đến hạn không tự kết luận BROKEN. Payment đến muộn nhưng thực sự trả đúng hạn có
  thể sửa BROKEN thành KEPT. Payment trả sau hạn không được tính đúng hạn.
- PTP_AGREED, SMS_SENT, sentiment tích cực không tạo bằng chứng thanh toán.
  historical_on_time_ratio và app_logins trả null khi chưa có nguồn phù hợp.
  Mô hình demo dùng prior trung tính cho dữ liệu thiếu và khai báo missing_features;
  không nhận đây là lịch sử trả nợ thật hay prior self-cure đã xác minh.

Ledger và transition audit là cơ sở cho outcome feedback sau này, chưa phải bus học
trực tuyến hay bằng chứng causal về hiệu quả một chiến lược thu hồi.

## API demo/test

GET /api/cases/{case_id}/financial-state trả case, case_exposures (kèm obligation_status),
ptps, payment_ledger, case_transition_log. GET queue vẫn giữ loan_id/status cũ, thêm
case_version/lifecycle/stage/resolution/contact_hold_reason.

POST /api/cases/{case_id}/call-wrapup bắt buộc thêm command_id, expected_version vào
payload cũ; loan_id tùy chọn, mặc định legacy loan của case. UI giữ ID khi retry,
không đóng modal nếu server báo lỗi, và cập nhật phiên bản khi lưu thành công.

POST /api/cases/{case_id}/balance-check lấy Core evidence cho mọi exposure:

```json
{"command_id":"balance-check-01","expected_version":0}
```

POST /api/cases/{case_id}/commands/{kind} là ingress **mô phỏng** với envelope:

```json
{
  "command_id": "payment-command-01",
  "expected_version": 1,
  "payload": {
    "event_id": "core-payment-01",
    "loan_id": "LOAN-001",
    "debtor_cif": "CIF-001",
    "kind": "POSTED",
    "amount_vnd": 500000,
    "occurred_at": "2026-09-06T10:00:00+07:00",
    "ptp_id": "PTP-ID-from-financial-state"
  }
}
```

kind được hỗ trợ:

| kind | payload |
|---|---|
| payment | Ví dụ trên; reversal dùng kind=REVERSED, reverses_event_id, không truyền ptp_id |
| balance | snapshots: danh sách loan_id, debtor_cif, overdue_amount, outstanding_principal, outstanding_interest, dpd, as_of, source_version; recent_payment tùy chọn |
| observe_ptp | ptp_id, payments_complete_through có timezone |
| link_exposure | loan_id, debtor_cif; phải cùng CIF, không tự merge case/loan đã liên kết |
| reconcile | reason không rỗng; mọi exposure phải có snapshot đã xác nhận còn mới, không trước payment |

HTTP 404: case không tồn tại; 409: xung đột trạng thái/phiên bản/bằng chứng;
422: payload không hợp lệ; 503: Core không sẵn sàng hoặc mutation ở integration mode.
Call-intent kiểm tra case hold/lifecycle và Core cho mọi exposure, fail closed khi
thiếu dữ liệu. balance-check lỗi không xóa số dư hoặc chuyển CURED.

## Migration và rollout

1. Dừng API đang ghi, sao lưu file SQLite bằng công cụ backup SQLite.
2. Checkout PR-02 trên nền PR-01; chạy make init-db với đúng profile/path hiện hữu.
3. Migration additive chạy trong transaction, không seed hoặc reset; tạo một link
   cho loan_id cũ của mỗi case, balance_verified=0. Không tự gộp case cùng CIF.
4. PTP cũ chuyển thành UNVERIFIED, không đi vào tỷ lệ giữ cam kết. Giữ nguyên record
   case/history gốc và provenance. Dữ liệu tiền cũ không nguyên VND khiến migration
   dừng và rollback để đối soát; không tự làm tròn hoặc xóa dữ liệu.
5. Chạy make test, make frontend-build; xác minh financial-state trước demo.

Rollback bằng checkout phiên bản cũ chỉ dùng cho kiểm tra code; muốn quay về nghiệp
vụ cũ phải phục hồi backup đã đối soát. Không drop các ledger/PTP/audit mới.

## Giới hạn còn lại

Integration mode vẫn chỉ đọc; không mở endpoint nhập tiền từ Internet/nguồn thật.
Chưa có authentication/authorization cho ingress Core, maker-checker reconciliation,
distributed outbox, scheduler watermark, lịch trả góp, multi-currency, partial reversal,
PTP amendment/cancellation UI, hoặc phân bổ tự động nhiều PTP. Guardrail attempt
counter vẫn là mô phỏng trong bộ nhớ, chưa transactional với durable command.
Những điều kiện này phải được bổ sung trước pilot vận hành thật.

Regression suite: partial/full payment, duplicate, conflict, out-of-order snapshot,
late wrapup, multi-exposure atomicity, matching PTP/on-time/late payment, reversal,
watermark, migration/restart và hai cập nhật đồng thời. Xem tests/test_case_correctness.py.
