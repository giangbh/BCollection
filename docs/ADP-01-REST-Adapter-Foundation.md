# ADP-01 — Nền tảng REST adapter và Core mock độc lập

## Phạm vi đã triển khai

- Profile `demo-http`: Core/LOS/CIC sử dụng HTTP clients, chỉ chấp nhận base URL
  `http://127.0.0.1:<port>/...`. Không proxy, không theo redirect, không fallback mock.
- Transport đọc chung: timeout, request ID, giới hạn response, phân loại lỗi và
  kiểm tra nhãn `X-Data-Origin: SYNTHETIC` trong demo-http. Nhãn này phục vụ phân
  biệt môi trường, **không thay thế xác thực nguồn production**.
  API key production kế thừa từ môi trường không được gửi sang mock local.
- Contract Core snapshot có validation số nguyên VND, version, định danh và timestamp
  có timezone tại `core_banking/contracts.py`; `CoreSnapshot.model_json_schema()`
  là schema sinh từ cùng model đang được thực thi. Các contract payment/LOS/EWS
  đầy đủ thuộc ADP-02/03/04, không tuyên bố đã hoàn thành ở đây.
- Core mock REST sử dụng SQLite riêng; seed tường minh, idempotent, không reset ngầm.
  GET không tăng source version/as_of. `observe` là thao tác CLI cập nhật quan sát.
- `GET /api/integrations/readiness` kiểm tra nguồn khi được yêu cầu trong demo-http;
  `/health` vẫn chỉ là liveness, startup không gọi mạng.
- UI có nút kiểm tra số dư qua REST Core trong demo-http. Các thao tác khác tiếp tục
  khóa trên UI; backend khóa persona/CBR/speech/call-intent/call-wrapup.
- Integration vẫn chỉ đọc, outbound messaging HTTP vẫn bị cấm.

## Chạy demo tại repo root

Mỗi terminal dùng cùng virtualenv. Không sử dụng DB demo/integration cũ cho profile mới.

Terminal 1 — hệ thống nguồn mock, không đọc DB của B.Collection:

```sh
.venv/bin/python scripts/legacy_mock.py --database .runtime/legacy-mock/core.sqlite3 seed
.venv/bin/python scripts/legacy_mock.py --database .runtime/legacy-mock/core.sqlite3 serve --port 8099
```

Terminal 2 — B.Collection:

```sh
export BCOLLECTION_MODE=demo-http
export BCOLLECTION_DB_PATH="$PWD/.runtime/demo-http/bcollection.sqlite3"
export CORE_BANKING_MODE=http
export CORE_BANKING_API_URL=http://127.0.0.1:8099/core/v1
export LOS_MODE=http
export LOS_API_URL=http://127.0.0.1:8099/los/v1
export CIC_MODE=http
export CIC_GATEWAY_URL=http://127.0.0.1:8099/cic/v1
export MESSAGING_MODE=mock
.venv/bin/python scripts/bcollection.py --mode demo-http seed-demo
.venv/bin/python scripts/bcollection.py --mode demo-http serve --port 8088
```

Hai lệnh seed dùng chung generator, mặc định seed 42 / fixture-as-of
`2026-09-01T09:00:00`, nên CIF/loan ID và số tiền khớp. Đây là bootstrap synthetic
độc lập, **chưa phải nhập portfolio qua REST**; ingestion tự động thuộc ADP-02.
Đổi seed/as-of phải dùng cùng giá trị cho cả hai và đường dẫn DB mới.

Terminal 3 — UI (Vite proxy hiện có trỏ Collection API 8088):

```sh
cd bcollection-platform/apps/collector-workspace
npm run dev -- --host 127.0.0.1
```

Mở case, bấm **Kiểm tra số dư qua REST Core**. Nút không thực hiện cuộc gọi.
Snapshot hết hạn sau 15 phút theo nghiệp vụ hiện có. Chủ động cập nhật nguồn:

```sh
.venv/bin/python scripts/legacy_mock.py --database .runtime/legacy-mock/core.sqlite3 observe
```

Lệnh observe không đổi tiền/DPD, chỉ tạo quan sát mới. Không dùng nó để che giấu
độ trễ dữ liệu nguồn thật. Mock có thể phục vụ dữ liệu cũ để thử cơ chế từ chối.

## Contract REST được phục vụ

| Route | Trạng thái |
| --- | --- |
| `GET /core/v1/loans/{id}/balance` | Snapshot xác định, unknown loan trả 404 |
| `GET /core/v1/loans/{id}/payments?lookback_minutes=15` | Cửa sổ gần đây; mặc định rỗng, không phải ledger đầy đủ |
| `GET /core/v1/portfolio/delinquent?max_dpd=30` | Lọc DPD đúng trong scenario đã seed |
| `GET /{core,los,cic}/v1/readiness` | Core READY/NO_DATA; LOS/CIC NOT_IMPLEMENTED |
| Core cashflows, LOS parties/collaterals, CIC reports | 501 tường minh; không sinh dữ liệu thay thế |

Response Core có `data_origin`, `contract_version`; snapshot có `source_system`,
`source_record_id`, `source_version`, `as_of`. Version gắn với snapshot persisted,
không phải số lần GET. Tiền được chuẩn hóa thành integer VND.

Transport không tự retry. `AdapterError` phân biệt NOT_FOUND, HTTP_ERROR,
SOURCE_UNAVAILABLE, INVALID_JSON, INVALID_CONTRACT và UNTRUSTED_DEMO_SOURCE;
429/502/503/504 và lỗi kết nối được đánh dấu retryable cho tầng điều phối sau này.
Log lỗi không chứa URL truy vấn, token, payload hay CIF. Chưa có OAuth refresh,
circuit breaker, metrics production hay authentication cho mock local-only.

## Kiểm thử và giới hạn

```sh
.venv/bin/python -m pytest -q
cd bcollection-platform/apps/collector-workspace
npm test
npm run build
npm run test:e2e
```

Nếu máy chưa có browser bundle của Playwright, có thể đặt `PLAYWRIGHT_CHROME_PATH`
trỏ đến executable Chrome đã cài (profile test độc lập), như hướng dẫn UI hiện có.

Test backend mới mở socket loopback tạm thời và tự dừng; cần môi trường cho phép
bind localhost. Kiểm chứng Collection API → HTTP adapter → mock REST, replay command,
restart, persistence, contract lỗi, redirect, provenance và tách DB. Browser tests
kiểm tra UI bằng API fixture; không gọi đó là browser-to-legacy end-to-end.

Chưa có payment simulation/reversal/cursor ingestion, CRM/history import, EWS/handoff,
outcome publisher hay kênh liên hệ. `mock_payments` là schema dự phòng ADP-03;
không có admin HTTP ghi dữ liệu, không có API reset. Readiness toàn hệ thống DEGRADED
là kết quả đúng khi LOS/CIC chưa triển khai. Không mở production bằng cách bỏ các gate.

## Bước tiếp theo

ADP-02: CRM profile + Core portfolio/loan terms/history + LOS/TSĐB + ingestion/projection.
ADP-03: payment cursor/reversal/watermark qua CaseService, không ghi trực tiếp ledger.
ADP-04: EWS → policy handoff → case/action → outcome outbox.
