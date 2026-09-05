# ADR-002: Ranh giới EWS, Collection và nền móng runtime

- Trạng thái: Chấp nhận cho thiết kế POC; không thay thế phê duyệt kiến trúc/nghiệp vụ của BIDV.
- Phạm vi triển khai: PR-01, dựa trên baseline `96175d2`.
- Tham chiếu: tài liệu BIDV EWS & Smart Collection Target Architecture do chủ dự án cung cấp; `docs/B-Collection-kien-truc-tich-hop.md`.

## Bối cảnh

POC đang hỗ trợ queue, persona, tương tác và PTP cho nợ quá hạn bán lẻ.
Trước PR-01, import API tự tạo/seed SQLite, thuật toán và dữ liệu synthetic dễ bị hiểu
nhầm là intelligence đã kiểm chứng. Hai thư mục `bc-domain` và `bc_domain` chứa cùng
định nghĩa, tạo nguy cơ lệch domain model.

## Quyết định ownership

| Chủ quản | Sở hữu | Không sở hữu |
|---|---|---|
| Smart Lending Hub / EWS | Monitoring liên tục, assessment/alert, watchlist, credit intervention; phê duyệt và thực thi cơ cấu qua năng lực Lending Hub | Case/treatment thu hồi của Collection |
| B.Collection | Admission của handoff, case, treatment, engagement, PTP/arrangement, recovery và outcome do Collection quan sát | Customer/loan master, số liệu ghi sổ, engine giám sát EWS toàn danh mục, phê duyệt cơ cấu |
| Shared Credit Intelligence | Data products, features/graph, model serving, engine decisioning, lineage/MLOps | Một policy hoặc risk score duy nhất áp cho mọi domain |

EWS không phải module con của B.Collection. Repo này sẽ chỉ có adapter/contract và
simulator phía EWS để kiểm thử tích hợp; engine EWS thật nằm ngoài bounded context.
EWS tiếp tục monitoring trong và sau Collection. Không chia ownership chỉ theo
"trước/sau DPD 0". Một alert có thể dẫn đến monitor, credit action hoặc pre-collection;
không mặc nhiên tạo case thu hồi.

### Policy handoff (định hướng cho PR tiếp theo, chưa triển khai trong PR-01)

1. EWS intervention policy chọn hướng can thiệp, dưới ownership EWS/Lending Hub.
2. Collection admission policy kiểm tra yêu cầu và mở/cập nhật/từ chối case.
3. Collection treatment policy chọn hành động cho case được nhận.

Dùng chung engine được phép; version, approval và trách nhiệm domain phải tách biệt.
Quyết định handoff có identity, reason, scope exposure, policy version và snapshot
tham chiếu. ACK kỹ thuật không thay thế kết quả chấp nhận nghiệp vụ.
Guardrail tại điểm thực thi không được bypass bởi handoff, model hay agent.

### Outcome feedback (định hướng cho PR tiếp theo)

Collection cung cấp quan sát có nguồn gốc, không tự ghi lại EWS threshold/model.
Tách operational event khỏi outcome đã đủ cửa sổ quan sát; PTP agreed khác PTP kept,
trả một phần khác cure, cure khác tất toán. Feedback hỗ trợ correction/reversal và
phải giữ snapshot tại thời điểm quyết định. EWS/shared analytics đánh giá toàn danh
mục, kể cả nhóm không handoff. Cure sau can thiệp không tự chứng minh alert sai.

## Quyết định triển khai PR-01

- Giữ cấu trúc monorepo/modular POC; không tách thêm microservice hoặc dựng Kafka.
- `bcollection-platform/libs/bc_domain` là định nghĩa domain Python duy nhất.
- Import API không mở database, seed hoặc gọi backend. Lifespan tạo schema rỗng và
  khôi phục mock state từ dữ liệu demo đã lưu; không tự tạo case/reference mới.
- Seed là lệnh offline rõ ràng, có random seed, thời điểm cố định, nhãn SYNTHETIC và
  manifest. Không tự xóa, overwrite hoặc reset database cũ.
- `demo`, `test`, `integration` có database riêng, được ràng buộc profile trong metadata.
- Integration yêu cầu DB path và HTTP endpoints rõ ràng; không silent fallback sang
  mock. PR-01 chỉ cho phép đọc, chặn mutation và persona/CBR/ASR còn mô phỏng.
- Header/API/UI hiển thị runtime; nhãn dữ liệu không đồng nghĩa chứng nhận chất lượng.

## Giới hạn và hệ quả

- Integration ở PR-01 là scaffold đọc dữ liệu cục bộ, chưa có EWS intake, ingest dữ
  liệu thật, live handoff hay feedback. Không phải production/pilot approval.
- Các lỗi nghiệp vụ payment/PTP/state machine được theo dõi cho PR-02, không sửa
  lẫn vào thay đổi bootstrap này. Guardrail, auth, counter/audit persistence và việc
  kiểm chứng model chưa đạt production. Chỉ bind API vào localhost theo CLI.
- Mock state/counters còn in-memory. Chạy một API process; không bảo đảm multi-worker.
- Database cũ không được tự di chuyển. Additive schema giữ nguyên record cũ, gán
  UNKNOWN cho dữ liệu chưa có provenance. Integration từ chối UNKNOWN/SYNTHETIC.
- Trước khi reuse engine/graph/workflow của Lending Hub phải khảo sát năng lực thực;
  tài liệu mục tiêu không phải bằng chứng hạ tầng đã sẵn sàng.

## Tiêu chí chấp nhận

- Import không tạo file DB; startup không seed; restart không làm tăng số record.
- Cùng seed + as-of + dependency lock cho cùng dữ liệu fixture; rerun không đổi dữ liệu.
- Không dùng chung DB giữa profile; integration chặn seed, mock fallback và action.
- Test dùng DB tạm riêng; CI chạy Python suite và frontend build từ manifest/lock.
