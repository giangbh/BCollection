# Case Workspace — triển khai thiết kế tương tác

Nhánh: `codex/ui-case-workspace`, kế tiếp `codex/pr-02-case-payment-ptp`.
Đây là ứng dụng React nối API POC, không nhúng HTML hoặc số liệu cố định từ prototype.

## Phạm vi đã triển khai

- Danh sách hồ sơ có tìm kiếm, phân trang, mở chi tiết và điều hướng bằng URL hash.
- Case Workspace theo thiết kế BIDV: sidebar, header, tổng nghĩa vụ, việc tiếp theo,
  tab tác nghiệp / PTP–payment / EWS–bằng chứng, rail hỗ trợ quyết định và guardrail.
- Phạm vi case và phạm vi các khoản vay của CIF **đã ghi nhận trong B.Collection**.
  Không gọi dữ liệu này là toàn bộ danh mục khách hàng khi chưa có nguồn đầy đủ.
- Đọc case, exposure, PTP, payment, audit, lịch hẹn và phản hồi trong cùng snapshot SQLite.
- Lên lịch / thay thế / hủy lịch và phản hồi đề xuất được lưu backend. Không chỉ alert
  hay bản nháp mất khi reload. Mọi lệnh đi qua CaseService, có version và idempotency.
- Đối soát số dư; rà soát để bỏ hold trong demo/test; kiểm tra trước cuộc gọi mô phỏng;
  kết thúc cuộc gọi và ghi wrapup/PTP đúng khoản vay. Không có cuộc gọi/tin nhắn thật.
- Giao diện sáng/tối, responsive; masking CIF/điện thoại; loading, empty, stale, error.

## Quy tắc dữ liệu và UX

1. Tổng tiền / DPD và bảng exposure dùng cùng read model. Dữ liệu thiếu hoặc xung đột
   không được thay bằng 0. Khoản vay mới liên kết chưa có số dư được thể hiện chưa có dữ liệu.
2. Customer scope loại trùng theo loan_id. Ưu tiên source_version cao nhất. Cùng version
   mà bằng chứng khác nhau: đánh dấu CONFLICT, không cộng tổng. Giữ danh sách case_ids.
3. Case lifecycle, obligation_status và PTP status độc lập. Payment một phần không cure;
   số dư bằng 0 không tự tạo payment/PTP KEPT; tiền liên kết và tiền đúng hạn là hai chỉ số riêng.
4. Thời gian có timezone hiển thị Asia/Ho_Chi_Minh. Dữ liệu cũ thiếu timezone được gắn nhãn,
   không âm thầm giả định đó là giờ UTC đã xác minh. Không suy ngày đến hạn từ DPD.
5. Tác nghiệp luôn thuộc case đang mở dù người dùng đang xem customer scope.
6. Thông tin chưa có nguồn (người phụ trách, nghề nghiệp, ưu tiên giờ gọi) hiển thị chưa có.
   Lịch do cán bộ tạo không được gắn nhãn là khách hàng đã đồng ý.
7. Đổi case hủy read request cũ; kết quả đến muộn không thay thế case hiện tại. Đang nhập
   hoặc gọi thì chặn đổi case. HTTP 409 giữ nội dung, yêu cầu tải lại và rà soát trước gửi lại.
8. Retry khi chưa biết kết quả mạng giữ command_id và expected_version ban đầu. Lưu thành
   công nhưng refresh lỗi được báo riêng, không khuyến khích gửi lại một lệnh đã commit.
9. Chưa xác định runtime / read lỗi / integration => khóa mutation. Snapshot quá 15 phút
   làm việc tiếp theo chuyển sang đối soát; điều này cập nhật theo đồng hồ mà không cần reload.

## Luồng đề xuất và guardrail

Ưu tiên quy tắc: CLOSED → xem kết quả; hold / non-OPEN → rà soát; số dư thiếu/cũ →
balance-check; lịch tương lai → chờ lịch; còn lại → kiểm tra điều kiện và gọi mô phỏng.

Workspace recommendation là **quy tắc trạng thái**, có ID `WORKSPACE_RULES_V1`, không
phải AI. Phản hồi ACCEPT/ADJUST/DECLINE lưu kèm snapshot đề xuất và phiên bản case được
đánh giá. Nếu đề xuất đã đổi (kể cả do thời gian trôi), backend trả 409. Không tạo outcome
thanh toán hoặc thông tin thành công cho CBR chỉ vì cán bộ chấp nhận đề xuất.

Call-intent kiểm tra phiên bản nếu client gửi, target đúng debtor, lịch tương lai, Core
cho mọi exposure và guardrail. Cuối kiểm tra xác nhận case_version chưa đổi. Quyền chỉ
dùng cho cuộc gọi mô phỏng vừa mở, không cache để dùng cho lần sau. Lịch đến hạn không
tự thực hiện cuộc gọi. Đây chưa phải cơ chế authorization/channel-execution production.

## API

### Đọc

- `GET /api/cases`: queue hiện hữu.
- `GET /api/cases/{case_id}/workspace`: cùng snapshot cho các panel, trả case_scope,
  customer_scope, next_action, schedules, feedback, ledger/PTP, history/audit và metadata.
- `GET /api/customers/{cif}/exposures`: tổng hợp theo CIF, không merge case; trả
  `coverage=RECORDED_IN_BCOLLECTION_ONLY`, `complete_core_portfolio=false`.
- `GET /api/cases/{case_id}/persona`: chỉ tải khi người dùng yêu cầu và ở demo/test;
  hiển thị PTP metrics / missing data, không tô điểm bằng các điểm số thiếu nguồn.

### Metadata command mới

`POST /api/cases/{case_id}/commands/{kind}` dùng envelope PR-02:

```json
{
  "command_id": "unique-client-command-id",
  "expected_version": 7,
  "payload": {
    "scheduled_at": "2026-09-10T18:00:00+07:00",
    "channel": "VOICE",
    "reason": "Kế hoạch của cán bộ, cần xác nhận khả năng trả"
  }
}
```

| kind | payload / điều kiện |
|---|---|
| schedule_contact | scheduled_at có timezone, tương lai trong 365 ngày; channel=VOICE; reason 1–2000 ký tự; case OPEN và không hold |
| cancel_schedule | schedule_id đang PLANNED trong case và reason; được hủy cả khi case đã đóng |
| decision_feedback | recommendation_id, recommendation_kind khớp next_action hiện tại; decision ACCEPT/ADJUST/DECLINE; reason |

Mỗi case có tối đa một lịch PLANNED. Thay lịch giữ bản cũ SUPERSEDED. Hủy lịch giữ
CANCELLED và lý do trong case_transition_log. Không có hard delete hoặc scheduler.
Metadata command không viết lại projection số dư, lifecycle hay legacy PTP.

Các lệnh balance-check, reconcile và call-wrapup tiếp tục dùng API PR-02. Client mới
gửi expected_version cho call-intent; field vẫn optional cho client cũ.

## Cấu trúc mã

- `services/collection-api/src/workspace.py`: read model, migration metadata, quy tắc
  next_action và thao tác metadata trong transaction do CaseService điều phối.
- `apps/collector-workspace/src/workspace/types.ts`, `api.ts`, `model.ts`: contract,
  lỗi API, format/label, quy tắc hiển thị và độ mới.
- `CaseQueuePage.tsx`, `CaseWorkspacePage.tsx`: màn hình, luồng dữ liệu và tác nghiệp.
- `Panels.tsx`: header, summary, exposure, PTP/payment, timeline, bằng chứng, guardrail.
- `workspace.css`: chuyển ngôn ngữ thị giác của prototype thành stylesheet ứng dụng.
- Các component cũ không còn được App import nhưng vẫn giữ trong repo để đối chiếu;
  không tiếp tục hiển thị nút enrichment giả “đã lưu” khi chưa có API tích hợp.

## Chạy và kiểm thử

Chạy từ repo root với Python 3.12 / Node 22 như PR-01:

```sh
make install
make frontend-install
make test
npm --prefix bcollection-platform/apps/collector-workspace test
make frontend-build
```

Kiểm thử trình duyệt, tại thư mục `bcollection-platform/apps/collector-workspace`:

```sh
npx playwright install chromium
npm run test:e2e
```

CI cài Chromium bằng `--with-deps`. Khi dùng Chrome đã cài trên máy để QA, có thể
đặt `PLAYWRIGHT_CHROME_PATH` thành đường dẫn executable; không dùng profile cá nhân.
E2E fixtures mô phỏng API để kiểm tra UI xác định; backend có pytest riêng. Ngoài ra
đã kiểm tra thủ công đầu-cuối bằng API POC thật, database test tạm seed riêng: lịch
hẹn và feedback tồn tại sau reload, số dư/lifecycle không đổi bởi metadata, lịch
tương lai vẫn chặn liên hệ sau khi đã refresh Core.

Chạy demo ở hai terminal:

```sh
make seed-demo
make api
```

```sh
npm --prefix bcollection-platform/apps/collector-workspace run dev -- --host 127.0.0.1
```

Mở `http://127.0.0.1:3000`. Chọn hồ sơ từ danh sách; không có seed mới ngầm khi startup.
Đối soát số dư trước để thấy trạng thái Core mới, sau đó lập lịch hoặc phản hồi đề xuất.

## Migration / rollback

Sao lưu SQLite và dừng writer trước khi cập nhật. `make init-db` hoặc startup áp dụng
migration additive trong transaction, tạo `contact_schedules`, `decision_feedback`
và index lịch PLANNED. Không thay seed manifest hoặc ghi lại dữ liệu tài chính cũ.
Rollback code không drop các bảng mới; giữ lịch sử hoặc phục hồi backup đã đối soát
nếu cần khôi phục nghiệp vụ. Database của người dùng không được dùng cho QA.

## Chưa nằm trong phạm vi

- EWS intake, policy handoff engine, outcome bus/học tự động, CDP/Core portfolio đầy đủ.
- Phân công cán bộ, authentication/RBAC, maker-checker, lưu ưu tiên/consent đã xác minh,
  tổng đài thật, scheduler tự gọi, cancellation notification, PTP amendment UI.
- Guardrail counter hiện vẫn in-memory từ POC. Masking UI không thay thế authorization
  hoặc bảo vệ dữ liệu API. Không coi read-only integration là đã sẵn sàng production.
- `npm audit` tại thời điểm triển khai báo 2 cảnh báo kế thừa Vite 5/esbuild (1 high,
  1 moderate); không phát sinh từ Playwright. Không chạy `audit fix --force` để thay
  major toolchain ngoài phạm vi này. Chỉ bind dev server vào localhost; phải nâng cấp
  toolchain và kiểm tra lại trước khi chia sẻ môi trường hoặc pilot vận hành.

Xem thêm [ADR-003](adr/ADR-003-case-payment-ptp-correctness.md) về tính đúng tài chính.
