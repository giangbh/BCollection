# ADP-04 — EWS, policy handoff và outcome feedback

Phạm vi: REST mock, SQLite inbox/outbox bền vững, **policy demo**, không mở production.
Tiếp nối [ADP-03](ADP-03-Payment-Ingestion.md).

## Cấu hình và REST

Ngoài cấu hình ADP-02, terminal chạy B.Collection cần:

```sh
export EWS_API_URL=http://127.0.0.1:8099/ews/v1
```

Khởi động lại mock/API để nhận route và migration mới. CRM_API_URL cần được cấu hình
để policy xác nhận customer identity. Không dùng API key thật; transport demo không
forward credential kế thừa, không proxy/redirect hoặc gửi ngoài 127.0.0.1.

| Interface | Mục đích |
| --- | --- |
| `GET /ews/v1/customers/{cif}/signals?cursor=...&limit=100` | Feed có sequence, signal/version, CIF, loan scope, severity, verification, occurred_at |
| `POST /ews/v1/collection-outcomes` | Nhận event với Idempotency-Key, trả accepted/event_id/receipt_id |
| `GET /ews/v1/collection-outcomes/{case_id}` | Xem outcome revision mới nhất tại mock EWS |
| `POST /api/cases/{id}/sync-ews` | Nhập và đánh giá EWS của CIF thuộc case |
| `POST /api/cases/{id}/publish-outcomes` | Gửi outbox của case đang chọn |

## Policy DEMO_HANDOFF_V1

- UNVERIFIED: DEFER_VERIFICATION, không tạo case.
- DISMISSED: NO_ACTION; handoff cũ là lịch sử audit, không bị xóa.
- LOW: MONITOR.
- VERIFIED HIGH/MEDIUM: cần Core snapshot mới, đúng CIF và CRM identity; thiếu thì
  DEFER_SOURCE. Không có nghĩa vụ quá hạn trong loan scope thì MONITOR.
- Tất cả loan scope cùng thuộc một case OPEN không bị hold: ghi handoff review.
- Scope gắn một phần/nhiều case/sai CIF: DEFER_SCOPE, không tự merge/link.
- Case đã đóng/held: DEFER_CASE_STATE, không tự mở lại.
- Chưa loan nào có case: tạo case synthetic gồm đúng loan scope, dùng CaseService
  ghi balance và handoff trong một transaction. Không bịa phone, collector, experiment
  hay PTP. Không thực hiện liên hệ.

Mỗi handoff lưu signal version trong reason và bảng decisions, policy version,
case đích, thời gian, quyết định và lý do. Case command id, handoff id ổn định chống
trùng. Case version tăng qua writer; outbox cùng transaction. Signal version cũ,
đổi CIF hoặc xung đột được quarantine, không đánh giá handoff tiếp khi còn pending.
DEFER có thể được đánh giá lại ở lần sync sau; APPLIED không tạo lại case/handoff.

Đây không phải policy BIDV đã phê duyệt hoặc external policy engine. Chưa có maker-
checker, ownership/routing collector, pre-delinquency treatment hay automatic contact.
Định nghĩa MONITOR/DEFER không có nghĩa khách hàng chắc chắn không có rủi ro.

## Demo EWS → case → payment → outcome

Lấy CIF/loan từ scenario Core. Có thể dùng DB B.Collection mới để thấy EWS tạo case,
hoặc case đã import ở ADP-02 để thấy handoff gắn vào case đó. Thực hiện trước payment
để case chưa bị contact hold:

```sh
export DEMO_CIF='CIF_TU_SCENARIO'
export DEMO_LOAN_ID='LOAN_ID_TU_SCENARIO'
.venv/bin/python scripts/legacy_mock.py --database .runtime/legacy-mock/core.sqlite3 emit-ews \
  --cif "$DEMO_CIF" --loan "$DEMO_LOAN_ID" --signal-id DEMO-SIGNAL-001 \
  --event-id DEMO-EWS-001 --title 'Dòng tiền giảm — dữ liệu mô phỏng'
.venv/bin/python scripts/bcollection.py --mode demo-http sync-ews --cif "$DEMO_CIF"
```

Kết quả trả decisions và targets/case_id. Mở case trên UI, xem EWS và nhật ký policy.
Sau đó chạy kịch bản PTP/payment/reversal của ADP-03 rồi:

```sh
export DEMO_CASE_ID='CASE_ID_TU_KET_QUA'
.venv/bin/python scripts/bcollection.py --mode demo-http publish-outcomes --case "$DEMO_CASE_ID"
```

UI có **Đồng bộ EWS**, **Gửi outcome**, và **Payment / EWS / Outcome · Nhật ký tích hợp**.
Muốn cập nhật tín hiệu, dùng event-id mới và tăng `--version`; có thể đổi
`--verification UNVERIFIED|VERIFIED|DISMISSED` hoặc `--severity HIGH|MEDIUM|LOW`.

## Outbox và đảm bảo xử lý

CaseService hỗ trợ tham gia transaction của ingestion. Commit event financial hoặc
metadata đồng thời ghi immutable outcome payload. Replay command không phát thêm event.
Outcome gồm case version/lifecycle, PTP amounts/status/completeness, handoff IDs,
payment/reversal gây cập nhật và `causal_attribution=false`.

Publisher claim row bằng lease/token, không giữ DB lock trong lúc gọi REST. Lease
30 giây cho phép phục hồi sau crash. Khi lỗi, event về PENDING, backoff 2–60 giây;
gọi lại UI/CLI sau mốc retry (chưa có scheduler tự chạy). Mỗi lần tối đa 50 event
mặc định. Không tự retry POST ngay trong transport.

Receiver chống trùng theo event ID và payload hash: cùng ID/cùng nội dung trả lại
receipt; cùng ID/khác nội dung trả 409. Receiver giữ revision cao nhất, không lùi khi
outcome cũ đến muộn. Đây là at-least-once + idempotent processing, **không tuyên bố
distributed exactly-once**. ACK sai/mất không được đánh dấu DELIVERED. Reversal làm
phát outcome revision mới phản ánh PTP/financial state đã điều chỉnh.

Không khẳng định payment là do AI gây ra. Receipt chỉ xác nhận nhận dữ liệu, không
chứng nhận thu hồi thành công. Chưa huấn luyện AI/CBR hoặc xuất case tham chiếu tự động.

## Storage và vận hành

Migration additive: integration_streams/inbox, ews_signal_versions/decisions,
outcome_outbox. Workspace đọc các bảng này nhất quán cùng snapshot hiện có. Mock có
event streams, persisted effects cho reversal, receipt store và latest-outcome projection
trong DB riêng. Không tự reset DB/cursor, không xóa case, không cần Kafka cho demo.

Các giới hạn còn lại: REST contract thực của legacy, xác thực producer/consumer,
policy phê duyệt, quarantine resolution workflow, scheduler, rate limiting/circuit
breaker, retention/DLQ operations, SSO và kênh liên hệ. Không mở các chức năng đó bằng
cách đổi profile integration; integration vẫn read-only.

## Kiểm thử

Backend kiểm thử qua socket loopback thật: EWS tạo case/replay/revision/quarantine,
case đóng, monitoring, outbox rollback, lost ACK, lease recovery, receiver conflict,
out-of-order outcome, CLI và API workflow. Browser tests dùng API fixture để kiểm tra
nút/cursor/policy/receipt; không coi đó là browser-to-legacy end-to-end.

```sh
.venv/bin/python -m pytest -q
cd bcollection-platform/apps/collector-workspace
npm test
npm run build
PLAYWRIGHT_CHROME_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm run test:e2e
```

Đường dẫn Chrome là ví dụ macOS, dùng profile test riêng; CI có thể dùng browser bundle.
