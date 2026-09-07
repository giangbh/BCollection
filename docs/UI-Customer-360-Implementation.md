# Khách hàng 360 — triển khai theo mock doanh nghiệp

Nhánh `codex/ui-customer-360`, kế thừa `codex/ui-case-workspace` tại `6870e2e`.
Không thay đổi hoặc merge `main`. Đây là UI ứng dụng React nối API POC, không phải ảnh
hoặc HTML prototype. Mock là tham chiếu bố cục, không phải nguồn dữ liệu nghiệp vụ.

## Phạm vi nghiệm thu

| Nhóm kế hoạch | Kết quả |
|---|---|
| UI-01 | Sidebar BIDV, tìm kiếm trên topbar, breadcrumb, header khách hàng/case, 9 tab, desktop/tablet/mobile, sáng/tối |
| UI-02 | Hồ sơ cá nhân/doanh nghiệp theo party_type nguồn; chọn case cùng CIF; phạm vi case/khách hàng ghi nhận; chống đổi case khi còn bản nháp |
| UI-03 | Thẻ tài chính, bảng khoản vay với chỉ báo thuộc case, cơ cấu dư nợ, DPD 12 tháng từ quan sát hợp lệ, PTP gần nhất, timeline |
| UI-04 | Cột việc tiếp theo + lịch hẹn, guardrail, phản hồi đề xuất, ghi chú lưu bền vững bằng lệnh versioned/idempotent |
| UI-05 | Hợp đồng đọc bằng chứng EWS, policy handoff; liên kết tường minh quyết định → interaction → PTP → payment/reversal. Chưa có nguồn ngoài hoặc event publisher |
| UI-06 | Backend, unit frontend, browser regression; ảnh QA nhiều kích thước; hướng dẫn API/migration và giới hạn tích hợp |

### Chưa kích hoạt vì chưa có nguồn/hệ thống đích

- Không tạo điểm rủi ro, khả năng trả nợ hoặc xác suất thành công AI. Vòng tròn đánh giá
  nhanh là **độ bao phủ snapshot xác minh**, không phải điểm rủi ro hay độ mới.
- Không kết nối EWS realtime, không xây policy decision engine, không phát outcome bus,
  không tự huấn luyện mô hình/CBR. Bảng bằng chứng có dữ liệu không đồng nghĩa ingress đã kết nối.
- Hồ sơ doanh nghiệp là hợp đồng projection cho adapter CRM/CDP; không có form giả
  sửa MST, phân công RM hoặc suy loại khách hàng từ tên. Không seed ngầm hồ sơ doanh nghiệp.
- Chưa có lịch trả nợ, sản phẩm chi tiết từng exposure hoặc ngày đến hạn từ Core.
  Không suy ngày đến hạn từ DPD. Không hiển thị CCCD search khi nguồn chưa hỗ trợ.
- Tab tài sản bảo đảm/tài liệu có trạng thái chưa kết nối; chưa upload/download, valuation,
  chuyển giao cán bộ, SMS, @mention hoặc thông báo thật. Không có nút giả báo thành công.
- Chưa có SSO/RBAC/maker-checker. Integration tiếp tục **chỉ đọc**. Masking UI không thay
  thế authorization của API; không dùng POC với dữ liệu khách hàng thật.

## Bố cục và tương tác

- Khách hàng và case có header riêng. Chọn case trong dropdown chỉ đổi case đang xem,
  không phân công/chuyển giao công việc. Số khoản trong header lấy từ case_scope; chỉ báo
  “thuộc case này” dùng case_ids, không phải checkbox sửa phạm vi trực tiếp.
- Tổng quan mặc định là case; người dùng có thể xem các khoản vay của CIF đã ghi nhận.
  Case/PTP/payment/tác nghiệp vẫn gắn case đang chọn. EWS là tín hiệu khách hàng, có cột
  cho biết bằng chứng policy nào bàn giao vào case này.
- Desktop có lưới phân tích và action rail. Tablet/narrow: hành động tiếp theo lên trước,
  các khối xếp dọc; bảng/tab được cuộn ngang trong vùng riêng, không tràn toàn trang.
- Tab hỗ trợ ArrowLeft/ArrowRight/Home/End. Cmd/Ctrl+K focus tìm kiếm. Escape đóng kết quả.
  Không giả danh cán bộ trong topbar; nhãn runtime mô phỏng/readonly luôn hiển thị.
- Ghi chú chưa lưu hoặc biểu mẫu/cuộc gọi đang mở khóa đổi case, kể cả qua URL hash.
  Lỗi 409 giữ bản nháp và yêu cầu reload/rà soát. Mất phản hồi mạng giữ command_id ban đầu.
  Lưu thành công nhưng refresh lỗi được báo riêng. Integration khóa cả nút lưu và ô ghi chú.

## API và dữ liệu

### Read model mở rộng

`GET /api/cases/{case_id}/workspace` vẫn đọc trong cùng transaction SQLite; bổ sung:

- `customer_profile`: null hoặc hồ sơ có party_type INDIVIDUAL/ORGANIZATION, legal_name,
  tax_id, industry, region, rm_name, source, source_as_of, data_origin.
- `customer_cases`: các case cùng CIF, không chỉ case OPEN.
- `case_notes`: ghi chú của case hiện tại, mới nhất trước.
- `dpd_history.case`, `dpd_history.customer`: mỗi nhóm 12 tháng, cùng phạm vi exposure hiện tại.
- `ews.signals`, `policy_handoffs`: nguồn, mã bằng chứng, thời điểm, xác minh, phiên bản policy.
- `outcome_feedback.links`: các liên kết đã được cán bộ chọn khi wrapup; gồm PTP hiện hành,
  payment và reversal. `causal_attribution=false`, `status=LOCAL_TRACE_ONLY`.
- `capabilities`: trạng thái các nguồn/tích hợp, không suy tính sẵn sàng từ số lượng bản ghi.

`GET /api/customer-search?q=...`: 2–100 ký tự (sau trim tối thiểu 2); tìm không dấu theo
tên khách hàng/hồ sơ nguồn, CIF, MST nguồn, case ID, điện thoại, **mọi khoản vay đã liên kết**.
Trả tối đa 25 kết quả case + has_more, không khẳng định đầy đủ danh mục Core. Ký tự `%` và
`_` được tìm literal; không nội suy SQL. Tìm kiếm trên queue cũ cũng hỗ trợ tên không dấu.

### Ghi chú

`POST /api/cases/{case_id}/commands/add_note`:

```json
{
  "command_id": "uuid-do-client-tao",
  "expected_version": 7,
  "payload": { "reason": "Thông tin được ghi nhận để xác minh tiếp." }
}
```

Nội dung 1–2000 ký tự, trim khoảng trắng. Server xác định case/CIF, timestamp, data_origin;
không nhận author do client tự khai. Trong demo/test, author được ghi đúng là
`Demo collector (unauthenticated)`. Trước production phải thay bằng principal xác thực
và authorization theo case. Ghi chú append-only; không có xóa/sửa trong UI này.

Lệnh đi qua CaseService: cùng transaction với audit, case_version và idempotency receipt.
Không thay balance, lifecycle, resolution, payment hoặc PTP. Cho phép ghi chú trên case
đã đóng nhưng không mở lại case hoặc cho phép liên hệ.

### Liên kết quyết định với kết quả

`POST /api/cases/{case_id}/call-wrapup` bổ sung `decision_feedback_id` optional.
UI cho phép chọn phản hồi ACCEPT/ADJUST thuộc case; mặc định không liên kết.
Backend từ chối ID khác case, ID không tồn tại hoặc DECLINE và rollback toàn bộ wrapup.
Link được lưu atomically với interaction/PTP. Retry cùng command không nhân đôi link.

Payment chỉ theo PTP allocation đã có từ PR-02; reversal giữ event gốc. Không lấy tất cả
payment xuất hiện sau một đề xuất để quy công cho đề xuất. Chấp nhận đề xuất, tạo PTP,
payment một phần, PTP KEPT và case CURED là các sự kiện khác nhau. UI chỉ hiển thị trace;
việc đánh giá hiệu quả chiến lược/nhân quả hoặc phát dữ liệu học phải có thiết kế riêng.

## Quy tắc biểu đồ

**Cơ cấu dư nợ:** tổng = principal + interest; phần quá hạn và phần còn lại = tổng − quá hạn.
Phần còn lại **không** được gọi là dư nợ trong hạn, vì khoản vay quá hạn vẫn có gốc chưa đến hạn.
Chỉ vẽ khi mọi exposure xác minh, không xung đột, số tiền nguyên an toàn và 0 ≤ overdue ≤ total.
Total=0 có trạng thái riêng, không chia cho 0; thiếu dữ liệu không thay bằng 0.

**DPD:** ghi `exposure_observations` trong cùng transaction với Core snapshot đã qua kiểm tra
identity/version/time/amount của PR-02. Không backfill 12 tháng từ snapshot hiện tại.
Mỗi tháng giờ Việt Nam: lấy quan sát có source_version mới nhất từng loan, loại trùng giữa
các case, cùng version khác snapshot_hash thì không đủ bằng chứng. Chỉ tính max/trung bình
cộng không trọng số khi tất cả loan trong phạm vi **hiện tại** có dữ liệu. Tháng thiếu là null,
không phải 0. Đây là lịch sử quan sát, không khẳng định snapshot cuối tháng hay danh mục lịch sử.
UI có bảng dữ liệu chi tiết, số khoản bao phủ và thời điểm nguồn cũ nhất/mới nhất trong tháng.

## Migration và tích hợp tiếp theo

Startup/init-db tạo thêm sáu bảng theo cơ chế additive trong transaction:
`customer_profiles`, `case_notes`, `exposure_observations`, `workspace_ews_signals`,
`workspace_policy_handoffs`, `decision_action_links`. Không ghi đè case hiện có hoặc tự seed.
Sao lưu database và dừng writer trước migration. Rollback code giữ bảng để bảo toàn lịch sử;
không drop bảng hoặc truncate dữ liệu khi rollback.

Các bảng hồ sơ/EWS/handoff là **projection contract nội bộ**, chưa phải public ingestion API.
Adapter thật phải xác thực nguồn, kiểm tra CIF/case/signal identity, timestamp, phiên bản,
idempotency và provenance trước khi ghi. Read model loại các handoff không cùng khách hàng.
Không cấp quyền SQL trực tiếp cho collector. Tài sản/tài liệu cần ACL và nguồn chuyên trách;
policy handoff engine và outcome publisher vẫn là hạng mục tích hợp sau khi có nguồn.

## Kiểm thử và chạy

Giữ các lệnh [hướng dẫn workspace trước](UI-Case-Workspace-Implementation.md#chạy-và-kiểm-thử).

```sh
make test
npm --prefix bcollection-platform/apps/collector-workspace test
make frontend-build
npm --prefix bcollection-platform/apps/collector-workspace run test:e2e
```

Browser fixtures dùng dữ liệu SYNTHETIC, bao gồm hồ sơ doanh nghiệp/EWS/DPD để kiểm tra hợp đồng
hiển thị; không được coi là dữ liệu ngân hàng hoặc mô hình đã kết nối. Ảnh kiểm thử được ghi vào
`apps/collector-workspace/test-results/customer360-*.png` (ignored), các kích thước
1440/1920/1024/360 và dark mode. Backend kiểm tra persistence, multi-case scope, invalid/replayed
commands, tháng theo giờ Việt Nam, history conflict, explicit attribution và payment reversal.

Ngoài fixture browser, đã smoke-test giao diện qua Vite proxy → API POC thật với database
TEST tạm, seed SYNTHETIC riêng: ghi chú tồn tại sau reload, metadata không sửa số dư/lifecycle,
tìm kiếm khoản vay trả đúng case, đối soát Core sinh quan sát DPD và không sinh EWS giả.
Không sử dụng database của người dùng cho kiểm thử này.

Vẫn áp dụng các giới hạn POC/toolchain đã ghi ở tài liệu trước: chỉ bind dev server localhost;
không mở môi trường thật trước khi hoàn thiện security, nâng cấp dev tooling và kiểm thử lại.
