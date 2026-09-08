# ADP-03 — Payment ingestion và đối soát PTP

Chỉ chạy `demo-http`, REST localhost, dữ liệu synthetic. Không mở Core hoặc messaging thật.

## Luồng và contract

`GET /core/v1/loans/{loan}/payment-events?cursor=0&limit=100` trả contract 1.0:
source system/origin, loan stream, CIF, after/next cursor, has_more, complete_through
và events. Mỗi event có event_id, sequence liên tục theo loan, CIF, loan_id, kind
POSTED/REVERSED, integer amount_vnd, occurred_at có timezone và reverses_event_id.
Không nhận case_id/PTP allocation do nguồn tự chỉ định.

1. Nhận page qua adapter, kiểm tra contract/identity/sequence, lưu inbox và cursor
   trong một transaction. Giới hạn 20 page mỗi lần chạy; lần sau tiếp tục cursor.
2. Inbox được chuyển thành command qua CaseService. Ledger, PTP, case version,
   transition, command receipt, outbox và dấu APPLIED của inbox cùng transaction.
3. Reversal đến trước original được giữ PENDING_REVIEW, thử lại sau các posted event.
   Không bỏ qua sự kiện lỗi. Restart có thể tiếp tục từ inbox đã nhận.
4. Chỉ observe PTP khi đã nhận hết page, không còn pending/source error và nguồn
   cung cấp watermark hợp lệ. Payment chưa phân bổ trong cửa sổ PTP chặn kết luận BROKEN.
5. Lấy snapshot Core mới qua command balance riêng. Lỗi bước này không làm mất ledger.
   Không tự xóa contact hold; reconcile bị chặn nếu còn source error/pending event.

Payment có đúng một PTP còn thiếu tiền, cùng loan/case và thời điểm trong cửa sổ
created_at..due_at được phân bổ theo **PTP_UNIQUE_WINDOW_V1** (quy tắc demo).
Không có hoặc có nhiều ứng viên: ghi payment unallocated, không đoán. Có CLI phân bổ
thủ công với reason. Chưa hỗ trợ chia một payment cho nhiều PTP, partial reversal,
maker-checker hay policy phân bổ production.

Watermark là cam kết nguồn về dữ liệu đã đầy đủ, không phải thời gian poll.
Mock `seal-payments` cấm thêm sự kiện có occurred_at nằm trước/trùng mốc đã seal.
Nếu phát hiện nguồn vi phạm seal/version/identity, giữ cursor, báo lỗi, giữ liên hệ
và vô hiệu hóa completeness PTP bị ảnh hưởng khi cần. Không tự reset cursor hoặc sửa
nguồn bị lỗi. Cần xử lý nguồn/quarantine trước khi reconcile.

## Demo

Chạy môi trường ADP-01/02; lấy CIF, case ID, loan ID từ UI. Các ID dưới đây phải thay
bằng ID thật của **scenario synthetic**, không phải khách hàng thật:

```sh
export DEMO_CASE_ID='CASE_ID_TU_UI'
export DEMO_LOAN_ID='LOAN_ID_TU_UI'
.venv/bin/python scripts/bcollection.py --mode demo-http create-demo-ptp \
  --case "$DEMO_CASE_ID" --loan "$DEMO_LOAN_ID" --command-id DEMO-PTP-001 \
  --amount 1000000 --due '2026-12-31T18:00:00+07:00'
.venv/bin/python scripts/legacy_mock.py --database .runtime/legacy-mock/core.sqlite3 post-payment \
  --loan "$DEMO_LOAN_ID" --event-id DEMO-PAY-001 --amount 400000
.venv/bin/python scripts/bcollection.py --mode demo-http sync-payments --case "$DEMO_CASE_ID"
.venv/bin/python scripts/legacy_mock.py --database .runtime/legacy-mock/core.sqlite3 post-payment \
  --loan "$DEMO_LOAN_ID" --event-id DEMO-PAY-002 --amount 600000
.venv/bin/python scripts/bcollection.py --mode demo-http sync-payments --case "$DEMO_CASE_ID"
.venv/bin/python scripts/legacy_mock.py --database .runtime/legacy-mock/core.sqlite3 reverse-payment \
  --loan "$DEMO_LOAN_ID" --event-id DEMO-REV-002 --reverses DEMO-PAY-002
.venv/bin/python scripts/legacy_mock.py --database .runtime/legacy-mock/core.sqlite3 seal-payments --loan "$DEMO_LOAN_ID"
.venv/bin/python scripts/bcollection.py --mode demo-http sync-payments --case "$DEMO_CASE_ID"
```

Chọn due còn ở tương lai tại lúc chạy. Cam kết manual ghi channel MANUAL, không
bịa cuộc gọi. ID lệnh/event cố định chống trùng; thay nội dung thì dùng ID mới.
Mock trừ lãi trước rồi gốc, giảm phần quá hạn, tăng source version; reversal hoàn
lại đúng các delta đã ghi. Đây là mô hình kế toán demo, không đại diện mapping SIBS.

PTP lần lượt PARTIALLY_KEPT → KEPT → PARTIALLY_KEPT. Hết quá hạn không đồng nghĩa
tất toán khoản vay; PTP không tự KEPT chỉ vì balance bằng 0. Muốn kiểm tra BROKEN,
watermark phải qua due; test dùng clock synthetic, không cần sửa đồng hồ máy.

Phân bổ payment đã được kiểm tra:

```sh
.venv/bin/python scripts/bcollection.py --mode demo-http allocate-payment \
  --case "$DEMO_CASE_ID" --event-id PAYMENT_ID --ptp-id PTP_ID \
  --command-id ALLOCATION-001 --reason 'Đã kiểm tra khoản vay và thời điểm thanh toán'
```

UI có **Đồng bộ thanh toán**, POST `/api/cases/{id}/sync-payments`, và nhật ký cursor,
mốc đầy đủ/pending. CLI/mutation nguồn chỉ dành cho demo. Chưa có background scheduler;
gọi lại UI/CLI để tiếp tục nhận và thử lại. Không có retry vô hạn hoặc outbound liên hệ.

## Kiểm thử

`tests/test_payment_ews_events.py` kiểm tra REST thật, partial/full/reversal, late
arrival trước seal, reversal trước original, 101-event pagination, restart, rollback
ledger/outbox khi crash, sai CIF, pending dependency, allocation mơ hồ và gate reconcile.
Các test PR-02 cũ tiếp tục chạy. Xem ADP-04 cho publisher và phản hồi điều chỉnh.
