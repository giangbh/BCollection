# ADP-02 — Dữ liệu Customer 360 qua REST

## Kết quả và ranh giới

Triển khai trên nền ADP-01, không thay các command tài chính PR-02:

- CRM: hồ sơ cá nhân/doanh nghiệp, MST demo, ngành, khu vực, RM ID.
- Core: danh mục khoản vay khách hàng (gồm khoản không quá hạn), lịch trả nợ.
- DWH/Core history: quan sát DPD 12 tháng, độc lập với snapshot số dư hiện tại.
- LOS/TSĐB: tài sản, khoản vay liên quan, định giá và ngày định giá.
- Directory: tên và đơn vị của RM; **không giả lập đăng nhập hay phân công collector**.
- Ingestion theo yêu cầu từ UI/CLI, dữ liệu đọc lưu bền và có lịch sử lần đồng bộ.
- Import portfolio quá hạn từ REST vào case demo bằng lệnh CLI tường minh.

Không tự nhập khoản vay ngoài case vào case. Không đổi dư nợ đang xử lý, vòng đời
case, payment/PTP, lịch hẹn hay phiên bản case khi sync Customer 360. Không mở
integration writes, EWS/policy handoff, outcome publisher, CIC, gọi điện hoặc AI.

## Chạy với DB ADP-01 đã có

Giữ các cấu hình demo-http ở [ADP-01](ADP-01-REST-Adapter-Foundation.md). Tại repo root,
mở rộng nguồn mock tường minh (idempotent, không reset dữ liệu):

```sh
.venv/bin/python scripts/legacy_mock.py --database .runtime/legacy-mock/core.sqlite3 seed-360
```

Khởi động lại mock service để có route ADP-02. `seed-360` tạo dữ liệu synthetic
cho từng CIF đã seed, thêm một khoản vay trong hạn cho khách hàng đầu tiên để
kiểm tra khác biệt customer/case scope. Chỉ nên chạy trên DB demo, không đọc hoặc
ghi DB B.Collection. Lệnh `observe` của ADP-01 cập nhật version/as-of nguồn; không
tự sinh thêm lịch sử hoặc dịch ngày trả nợ mỗi lần đọc.

Terminal chạy Collection API bổ sung:

```sh
export CRM_API_URL=http://127.0.0.1:8099/crm/v1
export DIRECTORY_API_URL=http://127.0.0.1:8099/directory/v1
.venv/bin/python scripts/bcollection.py --mode demo-http serve --port 8088
```

Trong UI mở case → **Đồng bộ Customer 360**. Xem:

1. Hồ sơ và RM tại header/Thông tin khách hàng.
2. Bảng **Nguồn dữ liệu Customer 360 · Trạng thái đồng bộ**.
3. Tab Nghĩa vụ tín dụng: **Danh mục khoản vay từ Core**, lịch trả nợ và thuộc case hay không.
4. Lịch sử DPD: quan sát cuối cùng mỗi tháng theo khoản trong phạm vi đang chọn.
5. Tab Tài sản bảo đảm: tài sản nguồn hoặc danh sách rỗng có xác nhận.

Tổng trên dashboard vẫn theo các khoản đã ghi nhận trong B.Collection. Danh mục
Core được hiển thị riêng, có coverage/as-of; không thay đổi ngầm phạm vi tổng tiền.
Kỳ trả nợ sắp tới chỉ hiển thị khi nguồn đủ lịch cho toàn bộ khoản trong phạm vi,
không được coi là PTP hoặc bằng chứng khách hàng đã thanh toán.

## Chạy từ DB B.Collection mới — không seed case nội bộ

Seed Core rồi `seed-360` như trên, cấu hình demo-http đầy đủ như ADP-01, dùng đường
dẫn B.Collection mới tách khỏi DB legacy mock:

```sh
export BCOLLECTION_DB_PATH="$PWD/.runtime/demo-http-adp02/bcollection.sqlite3"
.venv/bin/python scripts/bcollection.py --mode demo-http import-demo-portfolio
.venv/bin/python scripts/bcollection.py --mode demo-http sync-customer --cif CIF100001
.venv/bin/python scripts/bcollection.py --mode demo-http serve --port 8088
```

Import chỉ lấy DPD 1–30 theo contract portfolio hiện có. Mỗi khoản chưa có case
được tạo một case synthetic có ID ổn định; không tự gom theo CIF, không tái mở
case đóng, không tự tạo reference case hay phân nhóm thử nghiệm. Dữ liệu ban đầu
chưa được gắn `balance_verified`; cần nút kiểm tra số dư của ADP-01 trước đối soát.
Replay bỏ qua khoản đã liên kết; sai định danh giữa loan/CIF làm rollback batch.
Đây là bootstrap demo được yêu cầu rõ, **không phải policy handoff tự động**.

## Các interface mới

| Backend | REST mock |
| --- | --- |
| CRM | `GET /crm/v1/customers/{cif}/profile` |
| Core | `GET /core/v1/customers/{cif}/loans` |
| DWH qua gateway Core demo | `GET /core/v1/customers/{cif}/history` |
| LOS/TSĐB | `GET /los/v1/customers/{cif}/collaterals` |
| Directory | `GET /directory/v1/customers/{cif}/staff` |
| B.Collection | `POST /api/cases/{case_id}/sync-customer` |

Endpoint nguồn là contract demo, không khẳng định trùng API legacy BIDV. Adapter
logic độc lập trong `customer_sources.py`; mapping hệ thống thật được bổ sung
theo API bàn giao. `GET /api/cases/{id}/workspace` chỉ đọc DB, không gọi nguồn.

Mỗi response có `contract_version`, `debtor_cif`, `source_system`, `source_version`,
`as_of`, `data_origin`, `coverage` và `items`. Model Pydantic thực thi contract:
tiền VND nguyên không âm, timezone, định danh từng item, item trùng, nguồn synthetic,
quan sát không vượt thời điểm nguồn. Thiếu trường bắt buộc không có fallback.

## Persistence, consistency và lỗi

Migration additive thêm `customer_source_snapshots` và `customer_source_attempts`.
Hồ sơ CRM đồng thời cập nhật projection `customer_profiles` trong cùng transaction
để tìm kiếm tên/MST làm việc với dữ liệu mới. Không thay nguồn tác giả ghi chú.

- Mỗi resource commit riêng: lỗi LOS không xóa hồ sơ CRM đã nhập thành công.
- Version mới và thời điểm không lùi: thay snapshot đọc trong transaction.
- Cùng version/cùng payload chuẩn hóa: UNCHANGED, không ghi lại snapshot.
- Cùng version/khác payload: VERSION_CONFLICT, giữ bản cũ.
- Version hoặc thời gian lùi: OUT_OF_ORDER, giữ bản cũ.
- Source system đổi: SOURCE_CONFLICT; không so version chéo hệ thống.
- HTTP 404: NOT_FOUND, khác với EMPTY có response hợp lệ.
- Mất kết nối/contract sai: giữ bản hợp lệ trước đó và hiển thị lỗi lần đồng bộ.
- Snapshot quá 24 giờ: STALE khi lần đồng bộ thành công gần nhất; nếu có lỗi thì
  giữ trạng thái lỗi, vẫn hiển thị as-of bản đang dùng. Đây là ngưỡng demo cho read
  projections, **không thay ngưỡng 15 phút kiểm tra số dư**.

DPD nguồn được lưu riêng trong snapshot history; không nạp lịch sử qua balance
command, không điền tháng thiếu thành 0. Khi đã có snapshot history nguồn, chart
dùng nguồn đó và không trộn version với chuỗi local exposure observations. Nguồn
history rỗng vẫn là dữ liệu rỗng, không tự fallback thành biểu đồ có vẻ đầy đủ.

Chưa có polling scheduler, phân trang/cursor theo thay đổi, SSO, maker-checker,
schema production hay cam kết consistency giữa các backend. Các resource hiển thị
as-of độc lập, không tuyên bố một snapshot toàn ngân hàng cùng thời điểm. CLI có
thể gọi lại an toàn; thiết kế ingestion payment/cursor thuộc ADP-03.

## Kiểm thử

`tests/test_customer_ingestion.py` mở REST server loopback thật, kiểm tra bootstrap,
replay, restart, đồng bộ trên case có PTP, phạm vi ngoài case, tìm kiếm MST,
contract/identity/origin lỗi, nguồn đổi, version xung đột, empty/missing/stale và
lịch sử thiếu. Test UI mới kiểm tra profile/schedule/collateral bằng API fixture;
không gọi đó là browser-to-legacy end-to-end.

```sh
.venv/bin/python -m pytest -q
cd bcollection-platform/apps/collector-workspace
npm test
npm run build
npm run test:e2e
```

Test REST cần quyền bind localhost. Chrome đã cài có thể được chọn bằng
`PLAYWRIGHT_CHROME_PATH`, với profile test riêng. Không có cuộc gọi hoặc tin nhắn thật.
