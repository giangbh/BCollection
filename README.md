# B.Collection POC

Collector Workbench và nền móng tích hợp EWS cho POC. **Không dùng cho thu hồi nợ
thật hoặc đưa ra kết luận về khách hàng thật.** Persona, CBR, speech và kênh liên hệ
hiện còn mô phỏng; EWS intake, policy handoff và outcome feedback chưa triển khai.

## Ranh giới kiến trúc

EWS thuộc monitoring của Smart Lending Hub; Collection sở hữu case và treatment
thu hồi. Hai domain sử dụng intelligence dùng chung, tích hợp qua contract/API/event.
Xem [ADR-002](docs/adr/ADR-002-ews-collection-runtime-foundation.md) để biết ownership,
phạm vi PR-01 và các gate trước khi mở rộng. ADR này làm rõ ranh giới theo quyết định
nghiệp vụ, không chia cứng theo DPD trước/sau quá hạn.

PR-02 bổ sung writer nghiệp vụ thống nhất, case nhiều exposure, payment ledger,
PTP đối soát và optimistic versioning. Xem [ADR-003](docs/adr/ADR-003-case-payment-ptp-correctness.md)
cho semantics, API, migration và giới hạn. Đây vẫn là POC demo/test; không mở ghi
Core thật, EWS/policy handoff/outcome bus vẫn thuộc các bước tiếp theo.

## Cài đặt từ checkout mới

Yêu cầu Python **3.12**, Node.js **22** và npm. Chạy tại repo root:

```sh
python3.12 -m venv .venv
make install
make test
make frontend-install frontend-build
```

`requirements.txt` và `requirements-dev.txt` ghim dependency trực tiếp; constraints
trong `requirements.lock` ghim dependency bắc cầu đã kiểm thử với Python 3.12.
Frontend dùng `package-lock.json` và `npm ci`.
Không cần activate venv: Makefile sử dụng `.venv/bin/python`. Có thể override
`make test PYTHON=/path/to/python` hoặc chạy `python -m pytest -q`.

## Chạy demo: seed là một hành động riêng

```sh
make init-db
make seed-demo
make api
```

API: `http://127.0.0.1:8088`, Swagger: `/docs`, health: `/health`, runtime: `/api/runtime`.
Terminal khác để chạy UI:

```sh
npm --prefix bcollection-platform/apps/collector-workspace run dev
```

UI: `http://localhost:3000`; Vite proxy `/api` tới API port 8088.
Nếu chỉ chạy `make api`, schema được tạo nhưng queue vẫn rỗng: đây là hành vi đúng.
Không cần seed để health/API khởi động thành công.

Demo mặc định nằm ở `.runtime/demo/bcollection.sqlite3` (Git ignore).
Seed mặc định: `42`, as-of `2026-09-01T09:00:00`, gồm 500 case, lịch sử mẫu và
1.000 CBR reference. Những con số recovery/confidence không phải kết quả đo thực tế.
`data_origin=SYNTHETIC` được lưu cho ba nhóm dữ liệu này.

Tùy chỉnh fixture bằng một database **mới**, không overwrite fixture hiện có:

```sh
.venv/bin/python scripts/bcollection.py --mode demo --database .runtime/demo/scenario-b.sqlite3 seed-demo --seed 43 --as-of 2026-09-02T09:00:00
.venv/bin/python scripts/bcollection.py --mode demo --database .runtime/demo/scenario-b.sqlite3 serve
```

Seed chạy offline, một process, trước khi bật API. Rerun cùng manifest không đổi dữ
liệu, kể cả sau khi demo đã ghi tương tác; muốn reset hãy chọn path mới. Manifest
khác hoặc DB không rỗng/chưa seed hoàn tất bị từ chối, không xóa dữ liệu để retry.
Chỉ fixture được cố định; điểm persona phụ thuộc thời điểm hiện tại vẫn có thể thay đổi.

## Ba chế độ runtime

| Chế độ | Database | Backend | Hành vi |
|---|---|---|---|
| `demo` (mặc định) | `.runtime/demo/...` | Mock bắt buộc | Seed thủ công; hành động mô phỏng |
| `test` | DB tạm riêng từng test | Mock | Không đụng DB demo/integration |
| `integration` | Path riêng, bắt buộc khai báo | HTTP cấu hình rõ cho Core/LOS/CIC | Chỉ đọc trong PR-01; không seed, persona/CBR hoặc mutation |

`BCOLLECTION_MODE` ngoài ba giá trị bị từ chối. Mỗi DB được bind vào một profile;
không dùng DB demo để chạy integration. Metadata chỉ bảo vệ cấu hình, không thay
thế phân quyền/database isolation production.

File `.env.example` là mẫu cấu hình; chương trình **không tự load `.env`**.
Cấu hình qua environment hoặc CLI. Ví dụ integration (thay URLs bằng sandbox đã
được cấp quyền; không tự gửi traffic tới production):

```sh
BCOLLECTION_MODE=integration \
BCOLLECTION_DB_PATH=/absolute/path/to/integration.sqlite3 \
CORE_BANKING_MODE=http LOS_MODE=http CIC_MODE=http MESSAGING_MODE=mock \
CORE_BANKING_API_URL=https://approved-esb.example/core/v1 \
LOS_API_URL=https://approved-esb.example/los/v1 \
CIC_GATEWAY_URL=https://approved-esb.example/cic/v1 \
.venv/bin/python scripts/bcollection.py serve
```

Integration startup chưa gọi network và chưa ingest dữ liệu ngoài. `/api/cases` đọc
database cục bộ; HTTP adapters mới được cấu hình, không có nghĩa đã tích hợp BIDV.
PR-01 chặn mutation và các endpoint intelligence còn mô phỏng bằng HTTP 503.
Không bật HTTP messaging. Không publish cổng này ra ngoài: authentication,
authorization và guardrail end-to-end là công việc còn phải hoàn thiện.

## Database cũ và canonical domain

Database cũ ở `services/collection-api/bcollection.db` được giữ nguyên, không tự
copy hoặc sử dụng. Muốn kiểm tra migration, sao lưu và chạy trên **bản sao** với
`--database`: migration chỉ bổ sung provenance/metadata, không sửa record cũ.
Record cũ có `data_origin=UNKNOWN`, không mặc định là dữ liệu thật; integration
từ chối chúng. Chưa có importer dữ liệu EXTERNAL trong PR-01.

Import domain chuẩn: `from bc_domain.models import CollectionCase`.
Hai file trùng dưới `libs/bc-domain/` đã bỏ; nội dung vẫn có trong Git history.
Không đổi các namespace dịch vụ khác trong PR-01.

## Kiểm thử và phạm vi chưa giải quyết

`make test` chạy unit tests cũ (kể cả guardrail unittest) và regression tests bootstrap:
import/startup rỗng, seed deterministic/idempotent, restart, profile isolation,
integration fail-closed và canonical domain. Tests không cần backend ngoài.
CI có hai job: Python test và TypeScript/Vite build.

PR-02 sẽ xử lý payment một phần, PTP agreed/kept, state machine và outcome correctness.
PR-03 trở đi mới có inbox/outbox, EWS intake, policy handoff, lifecycle và feedback.
SQLite, global service instances và in-memory counters/audit hiện chỉ phù hợp POC
một process; không suy diễn khả năng multi-worker hoặc production từ test suite này.
