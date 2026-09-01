Tôi đề xuất B.Collection là một “nền tảng quyết định thu hồi nợ có kiểm soát”, không chỉ là phần mềm quản lý hồ sơ hay một mô hình AI đơn lẻ. Kiến trúc phải khép kín vòng lặp:

**Dữ liệu → Customer 360/Graph → dự báo → chiến lược → thực thi → kết quả → học lại.**

![Kiến trúc đích B.Collection](/Users/giangbh/Documents/New%20project/B.Collection-Target-Architecture.visual-check.1440x900.light.png)

Mở bản tương tác: [B.Collection Target Architecture](/Users/giangbh/Documents/New%20project/B.Collection-Target-Architecture.html)

## 1. Các năng lực nghiệp vụ cốt lõi

B.Collection nên cung cấp 8 nhóm năng lực:

1. Quản lý danh mục nợ, hồ sơ và vòng đời collection case.
2. Customer 360 cho cá nhân, hộ gia đình, doanh nghiệp và nhóm liên quan.
3. Debt Knowledge Graph biểu diễn quan hệ giữa khách hàng, tổ chức, khoản vay, tài sản, người bảo lãnh và các bên liên quan.
4. Làm giàu dữ liệu thủ công và tự động có kiểm soát.
5. Phân khúc động, dự báo rủi ro và đề xuất next-best-action.
6. Điều phối chiến lược đa kênh, SLA, phê duyệt và pháp lý.
7. Case Memory học từ các hồ sơ thành công lẫn thất bại.
8. Kiểm soát dữ liệu cá nhân, mô hình AI, truy cập và bằng chứng kiểm toán.

## 2. Kiến trúc logic đề xuất

### Lớp nguồn dữ liệu

Nguồn nội bộ nên được ưu tiên vì có độ tin cậy cao:

- Core Banking, LOS, CRM, CIC và hồ sơ tín dụng.
- Dư nợ, DPD, lịch sử cơ cấu, cam kết thanh toán.
- Luồng tiền, biến động số dư, hành vi thanh toán.
- Lịch sử cuộc gọi, SMS, app, email, chi nhánh.
- Tài sản bảo đảm, định giá, bảo hiểm, pháp lý.
- Quan hệ người bảo lãnh, đồng sở hữu và beneficial owner.
- Kết quả các biện pháp thu hồi trước đây.

Nguồn ngoài chỉ đi qua một **OSINT/Data Enrichment Gateway**:

- API hoặc nguồn dữ liệu được cấp phép.
- Cổng thông tin doanh nghiệp, tài sản, pháp lý công khai.
- Social/internet khi có căn cứ xử lý, đúng mục đích và phù hợp điều khoản của nguồn.
- Không vượt CAPTCHA, không sử dụng tài khoản giả, không mua dữ liệu không rõ nguồn gốc.

### Data Platform

Nên áp dụng kiến trúc lakehouse kết hợp event-driven:

- API Gateway, CDC, batch ingestion và event streaming.
- Các vùng raw, curated, trusted.
- Data quality, schema registry, lineage và data contracts.
- Operational Data Store cho xử lý case thời gian thực.
- Immutable event log để tái tạo toàn bộ quyết định và lịch sử case.
- Tokenization/masking dữ liệu định danh trước khi cấp cho môi trường phân tích.

Không nên dùng Graph Database thay cho lakehouse. Lakehouse là hệ thống lịch sử và phân tích lớn; Graph là projection chuyên biệt phục vụ quan hệ và suy luận.

### Customer 360 và Debt Knowledge Graph

Trước khi tạo graph phải có entity resolution và Golden Customer ID.

Các node chính:

- Person, Organization, Household.
- Loan, Contract, Account, Collection Case.
- Asset, Collateral, Address, Phone, Device.
- Guarantor, Legal Representative, Beneficial Owner.
- Branch, Collector, Channel, Interaction.
- Promise-to-pay, Action, Outcome, Legal Event.

Mỗi edge/thuộc tính phải có:

- Nguồn dữ liệu.
- Thời điểm hiệu lực.
- Thời điểm thu thập.
- Độ tin cậy.
- Mục đích được phép sử dụng.
- Thời hạn lưu giữ.
- Người hoặc hệ thống tạo.

Graph được dùng cho entity resolution, phát hiện nhóm liên quan, ownership chain, cộng đồng, tài sản chung và graph embeddings. Không được mặc định rằng một người “có trách nhiệm trả nợ” chỉ vì có quan hệ trong graph.

## 3. Chân dung khách hàng nên là hồ sơ động

Không nên tạo một điểm số duy nhất. Mỗi khách hàng/case cần một hồ sơ đa chiều:

- **Ability to pay:** năng lực tài chính và dòng tiền.
- **Willingness to pay:** hành vi hợp tác, lịch sử cam kết.
- **Contactability:** khả năng liên hệ, kênh và thời điểm phù hợp.
- **Recoverability:** giá trị kỳ vọng có thể thu hồi.
- **Affordability:** mức trả góp khả thi.
- **Hardship/vulnerability:** khó khăn và dấu hiệu cần đối xử đặc biệt.
- **Relationship context:** bảo lãnh, tài sản, doanh nghiệp và hộ gia đình.
- **Legal readiness:** trạng thái hồ sơ và điều kiện chuyển pháp lý.
- **Preferred treatment:** kênh, giọng điệu và phương án từng hiệu quả.

Khái niệm “cái gì tạo ra áp lực thu nợ” nên được đổi thành **động lực hợp tác hợp pháp**: lịch trả phù hợp, ưu đãi, tái cơ cấu, cảnh báo hậu quả hợp đồng/pháp lý chính xác. Không hồ sơ hóa đời tư để đe dọa, bêu tên hoặc gây sức ép lên người không có nghĩa vụ.

## 4. Làm giàu thông tin thủ công

Collector Workbench không nên cho phép ghi chú tự do không giới hạn. Mỗi thông tin nhập mới cần:

- Loại quan hệ hoặc tín hiệu theo taxonomy chuẩn.
- Nguồn/bằng chứng.
- Ngày ghi nhận và ngày hết hạn.
- Confidence score.
- Mức nhạy cảm.
- Purpose code.
- Người nhập và người phê duyệt nếu cần.
- Cơ chế khách hàng yêu cầu kiểm tra, đính chính.
- Phát hiện xung đột với dữ liệu hiện hữu.

Các ghi chú chứa ngôn từ xúc phạm, suy đoán không có căn cứ hoặc thuộc blacklist phải bị chặn/cảnh báo bằng DLP và NLP moderation.

## 5. AI Decisioning

Nên chia thành nhiều mô hình nhỏ, giải thích được:

- Propensity-to-pay.
- Promise-to-pay kept probability.
- Contactability/channel/time optimization.
- Cure probability theo từng biện pháp.
- Expected recovery amount/time.
- Khả năng chấp nhận phương án cơ cấu.
- Hardship/vulnerability detection.
- Next-best-action và collector prioritization.

LLM phù hợp cho:

- Tóm tắt hồ sơ và timeline.
- Giải thích graph.
- Soạn kịch bản giao tiếp từ playbook đã phê duyệt.
- Trích xuất dữ liệu từ tài liệu.
- Tra cứu chính sách bằng RAG.

LLM không được tự quyết định kiện tụng, xử lý tài sản, công khai thông tin, liên hệ bên thứ ba hoặc tạo nội dung mang tính đe dọa.

Mỗi khuyến nghị phải trả về:

```text
recommended_action
expected_recovery
confidence
reason_codes
supporting_evidence
similar_cases
prohibited_actions
required_approval
model_version
```

## 6. Case Memory: học từ hồ sơ tương đồng

Mỗi reference case phải lưu cả bối cảnh và kết quả:

- Chân dung tại thời điểm ra quyết định.
- DPD, sản phẩm, dư nợ, tài sản, phân khúc.
- Hành động, kênh, tần suất, collector.
- Phương án được đề nghị.
- Outcome, số tiền, thời gian và chi phí thu hồi.
- Khiếu nại, vi phạm hoặc negative outcome.
- Rule/model version và người phê duyệt.

Cơ chế áp dụng:

1. Hard filter theo sản phẩm, DPD, pháp lý và điều kiện áp dụng.
2. Tìm case tương đồng bằng tabular features, graph embeddings và semantic retrieval.
3. Chỉ dùng case đã qua quality gate.
4. Ước lượng uplift của từng biện pháp, không chỉ chọn biện pháp phổ biến nhất.
5. Trình bày 3–5 case gần nhất cùng khác biệt quan trọng.
6. Collector lựa chọn hoặc từ chối; lý do trở thành feedback.

Không nên chỉ học từ case thành công, vì sẽ tạo survivorship bias. Case thất bại, khiếu nại và “không hành động” cũng là dữ liệu huấn luyện quan trọng.

## 7. Điều phối chiến lược

Strategy Orchestration nên kết hợp:

- Business rules bắt buộc.
- AI recommendation.
- Customer contact policy.
- SLA và workload.
- Champion–challenger/A/B testing.
- Approval matrix.
- Legal and vulnerability guardrails.

Ví dụ:

- Có khả năng trả nhưng quên hạn → nhắc nhẹ qua app/SMS.
- Có dòng tiền nhưng thường thất hứa → collector call và phương án thanh toán cụ thể.
- Khó khăn tạm thời → affordability assessment và tái cơ cấu.
- Khách hàng doanh nghiệp có chuỗi sở hữu phức tạp → relationship manager và graph investigation.
- Hồ sơ đầy đủ, không hợp tác kéo dài → chuyển quy trình pháp lý có phê duyệt.

## 8. Kiểm soát pháp lý và đạo đức

Tại thời điểm 01/09/2026, baseline cần đối chiếu gồm:

- Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15, hiệu lực từ 01/01/2026. [Văn bản Chính phủ](https://vanban.chinhphu.vn/?classid=1&docid=214590&pageid=27160&typegroup=)
- Nghị định 356/2025/NĐ-CP hướng dẫn Luật, hiệu lực từ 01/01/2026. [Công báo Chính phủ](https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-356-2025-nd-cp-468371.htm)
- Luật Dữ liệu 60/2024/QH15, hiệu lực từ 01/07/2025. [Văn bản Chính phủ](https://vanban.chinhphu.vn/?docid=212488&pageid=27160)
- Luật Các tổ chức tín dụng 32/2024/QH15, hiệu lực từ 01/07/2024. [Văn bản Chính phủ](https://vanban.chinhphu.vn/?classid=1&docid=211190&pageid=27160&typegroupid=)
- Nghị định 330/2026/NĐ-CP về xử phạt trong an ninh mạng và bảo vệ dữ liệu cá nhân, hiệu lực từ 19/08/2026. [Văn bản Chính phủ](https://vanban.chinhphu.vn/?classid=1&docid=219266&pageid=27160&typegroupid=4)

BIDV nên yêu cầu Legal/DPO phê duyệt từng data source và use case, thực hiện DPIA/đánh giá tác động, purpose limitation, retention, phân quyền ABAC, audit bất biến và kill switch cho model/nguồn dữ liệu.

## 9. Lộ trình triển khai

- **0–3 tháng:** blueprint, data inventory, legal assessment, taxonomy, MVP case management.
- **4–9 tháng:** lakehouse, Customer 360, graph MVP, collector workbench, rules-based strategy.
- **10–15 tháng:** propensity/contactability models, Case Memory, next-best-action có human approval.
- **16–24 tháng:** graph embeddings, uplift modeling, champion–challenger và tối ưu toàn danh mục.

KPI nên đo: recovery rate, cure rate, promise-kept rate, cost-to-collect, time-to-resolution, right-party-contact, complaint rate, override rate, model uplift và số vi phạm policy — không chỉ đo số tiền thu được.

Sơ đồ đã qua 9/9 kiểm tra kiến trúc showcase, 0 lỗi, 0 cảnh báo; kiểm tra trình duyệt đạt tại 1440×900, 1600×1000, 1920×1080 và 2048×1320, cả light/dark. Đã review trực quan sau 1 vòng hiệu chỉnh. Viewer dùng giao diện điều khiển tiếng Anh, nội dung kiến trúc bằng tiếng Việt.