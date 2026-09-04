# B.COLLECTION — ĐỀ XUẤT TECH STACK CHO MVP
**Phiên bản:** v0.1 | **Ngày:** 01/09/2026
**Tài liệu liên quan:** Kiến trúc tổng thể · Collection Graph · Persona & Manual Enrichment · Đặc tả Guardrail Service

---

## 0. Quan điểm chủ đạo

MVP của B.Collection **không phải là bản thu nhỏ của kiến trúc đích**. Nếu cố làm bản thu nhỏ của kiến trúc 9 tầng, đội sẽ mất 9 tháng để dựng hạ tầng và chưa thu hồi được đồng nào.

MVP nên trả lời đúng một câu hỏi: **liệu việc chấm điểm và phân luồng bằng dữ liệu, chạy qua một tầng kiểm soát tuân thủ, có thu hồi tốt hơn cách làm hiện tại không?** Để trả lời câu đó cần ít công nghệ hơn nhiều so với tưởng tượng.

Ba nguyên tắc chọn stack cho MVP:
1. **Tái sử dụng thứ đội đã biết.** Đội đã có kinh nghiệm Python, Temporal, PostgreSQL, FastAPI qua dự án CreditAgent. Mỗi công nghệ mới thêm vào là 2–4 tuần học phí.
2. **Trì hoãn mọi thứ có thể trì hoãn.** Graph database, vector store, feature store, LLM — tất cả đều bị loại khỏi MVP. Không phải vì không cần, mà vì chưa cần *để trả lời câu hỏi trên*.
3. **Không trì hoãn Guardrail và đo lường.** Hai thứ này phải có từ ngày đầu. Guardrail vì không được ra kênh khi chưa có; đo lường vì holdout group không thể thiết lập hồi tố.

---

## 1. Phạm vi MVP

### 1.1 Trong phạm vi
| # | Hạng mục | Lý do |
|---|---|---|
| 1 | **Làm sạch dữ liệu liên hệ** (chuẩn hoá số điện thoại, địa chỉ, dedupe) | Giá trị nhanh nhất và rẻ nhất; mọi thứ sau đều phụ thuộc |
| 2 | **Guardrail GR-P1** (G01, G02, G03, G05, G12 + API + audit) | Ràng buộc cứng — không ra kênh nếu chưa có |
| 3 | **Debtor 360 tối giản + Persona Card v0** | 3 điểm số: ability, willingness, contactability |
| 4 | **2 mô hình ML**: self-cure propensity (ML1), best-time-to-contact (ML4) | Hai mô hình có ROI cao nhất, dữ liệu sẵn có |
| 5 | **Digital-first cho bucket B1** (SMS + Zalo ZNS) | Kênh rẻ nhất, rủi ro thấp nhất |
| 6 | **Case Workflow tối giản** + Collector Workspace | Đủ để phân công và ghi nhận kết quả |
| 7 | **Manual Enrichment** — 8 fact type đầu tiên | Structured-first ngay từ đầu, không để lỡ |
| 8 | **Holdout group 10% + khung đo uplift** | Không thể bổ sung hồi tố |

### 1.2 Ngoài phạm vi MVP (có chủ đích)
| Hạng mục | Vì sao hoãn | Đưa vào giai đoạn |
|---|---|---|
| Neo4j / Collection Graph đầy đủ | G02 chỉ cần 4 loại cạnh, 1-hop — PostgreSQL làm được (xem Mục 3.3) | GĐ2 |
| Vector store, Case Reference Engine | Cần kho case lịch sử đã chuẩn hoá; MVP chưa có | GĐ2 |
| LLM / ASR / Copilot | Không cần để chứng minh giả thuyết cốt lõi | GĐ2–3 |
| Feature Store (Feast) | 2 mô hình, batch scoring — bảng dbt là đủ | GĐ2 |
| Dialer/CTI integration | Tích hợp tổng đài mất 3–4 tháng đàm phán nội bộ; khởi động song song nhưng không chặn MVP | GĐ2 |
| Uplift model, NBA optimization | Cần dữ liệu thí nghiệm tích luỹ trước | GĐ2–3 |
| G09 Collateral Gate | Chỉ liên quan bucket muộn, MVP làm B1 | GĐ3 |
| OSINT Collector | Phải có DPIA và ý kiến Pháp chế trước | GĐ2 |
| Lakehouse đầy đủ (Iceberg + Trino) | Dùng EDW hiện có + PostgreSQL | GĐ2 |

**Thời gian mục tiêu: 4 tháng.** Nếu vượt quá 5 tháng, phạm vi đã sai chứ không phải đội chậm.

---

## 2. Giả định cần xác nhận

Ba giả định dưới đây quyết định 30% nội dung đề xuất. Nếu sai, tôi sẽ điều chỉnh tương ứng.

| # | Giả định | Nếu sai thì sao |
|---|---|---|
| A1 | Ngân hàng có kho dữ liệu tập trung (EDW/DWH) chứa dữ liệu khoản vay, giao dịch, CIF ở mức ngày | Nếu không → phải bổ sung tầng ingestion Spark + CDC, cộng 6–8 tuần |
| A2 | Ngân hàng có nền tảng container (Kubernetes hoặc OpenShift) đang vận hành | Nếu không → MVP chạy VM + Docker Compose, chấp nhận được, nhưng cần kế hoạch chuyển đổi |
| A3 | Toàn bộ dữ liệu phải nằm on-premise, không dùng cloud công cộng | Nếu được dùng cloud → có thể rút ngắn 4–6 tuần bằng managed services |

Đề xuất dưới đây viết theo hướng **A1 đúng, A2 đúng, A3 đúng** — tức trường hợp thận trọng nhất trong môi trường ngân hàng Việt Nam.

---

## 3. Stack đề xuất

### 3.1 Tổng quan

```
┌─ KÊNH ─────────────────────────────────────────────────────────┐
│  SMS Gateway (nội bộ)  ·  Zalo ZNS API  ·  Email               │
├─ ỨNG DỤNG ─────────────────────────────────────────────────────┤
│  Collector Workspace : React 18 + TypeScript + Vite            │
│  Backend API         : Python 3.12 + FastAPI + Pydantic v2     │
│  Workflow            : Temporal (self-hosted)                  │
│  Guardrail Service   : FastAPI riêng + Redis + Postgres        │
├─ DỮ LIỆU ──────────────────────────────────────────────────────┤
│  OLTP & Serving      : PostgreSQL 16                           │
│  Bộ đếm & cache      : Redis 7                                 │
│  Biến đổi dữ liệu    : dbt-core + Airflow (hoặc Temporal cron) │
│  Nguồn               : EDW hiện hữu (đọc) + file batch         │
├─ ML ───────────────────────────────────────────────────────────┤
│  Training            : Python, LightGBM, scikit-learn          │
│  Tracking            : MLflow                                  │
│  Serving             : Batch scoring hằng đêm → bảng Postgres  │
├─ VẬN HÀNH ─────────────────────────────────────────────────────┤
│  Kubernetes · OpenTelemetry · Prometheus · Grafana · Loki      │
│  GitLab CI (hoặc Jenkins) · Vault/KMS · Keycloak (OIDC)        │
└────────────────────────────────────────────────────────────────┘
```

### 3.2 Lý do chọn từng thành phần

| Thành phần | Chọn | Vì sao | Đã cân nhắc & loại |
|---|---|---|---|
| Ngôn ngữ backend | **Python 3.12** | Đội đã dùng ở CreditAgent; cùng ngôn ngữ với ML tránh việc dịch mô hình sang Java | Java/Spring — mạnh hơn về hiệu năng nhưng tách rời khỏi tầng ML, và đội chưa có lợi thế |
| API framework | **FastAPI + Pydantic v2** | Validation schema chặt — quan trọng với Guardrail; async native; OpenAPI tự sinh | Django — nặng và không cần ORM đầy đủ |
| Workflow | **Temporal** | Đội đã có POC chạy được ở CreditAgent; durable execution đúng bài toán case lifecycle nhiều bước, có chờ người | Camunda 8 — mạnh về BPMN nhưng đội phải học lại từ đầu; Airflow — không phù hợp workflow có tương tác người |
| CSDL chính | **PostgreSQL 16** | Một CSDL cho OLTP, audit, serving ML output, và cả quan hệ đồ thị 1-hop (Mục 3.3); JSONB cho payload linh hoạt; đội đã dùng | Oracle — chi phí và độ nặng không cần cho MVP; MongoDB — mất tính toàn vẹn giao dịch mà Guardrail cần |
| Bộ đếm tần suất | **Redis 7** | Sorted set là cấu trúc đúng cho cửa sổ trượt; độ trễ sub-ms | Postgres — làm được nhưng chậm và tạo tải ghi không cần thiết |
| Biến đổi dữ liệu | **dbt-core** | SQL có version, có test, có lineage — hợp với đội phân tích ngân hàng vốn mạnh SQL | Spark — chưa cần ở quy mô MVP nếu A1 đúng |
| Điều phối batch | **Airflow** hoặc **Temporal cron** | Nếu Ngân hàng đã có Airflow thì dùng luôn; nếu không, dùng Temporal để bớt một hệ thống | — |
| ML | **LightGBM + scikit-learn** | Nhanh, giải thích được bằng SHAP, phù hợp dữ liệu bảng; yêu cầu MRM về explainability được đáp ứng | Deep learning — không có lợi thế trên dữ liệu bảng, khó qua thẩm định mô hình |
| ML tracking | **MLflow** | Model registry + versioning là yêu cầu bắt buộc của MRM | — |
| Frontend | **React 18 + TypeScript + Vite** | Persona Card cần tương tác; TypeScript giảm lỗi khi schema đổi | — |
| Xác thực | **Keycloak (OIDC)** hoặc AD nội bộ | SSO + RBAC; tránh tự xây | — |
| Bí mật | **HashiCorp Vault** hoặc KMS/HSM sẵn có | Bắt buộc với môi trường ngân hàng | — |
| Quan trắc | **OpenTelemetry → Prometheus/Grafana/Loki** | Chuẩn mở, không khoá vendor | — |

### 3.3 Quyết định gây tranh cãi nhất: MVP không dùng Neo4j

Tầng Guardrail G02 — control quan trọng nhất — chỉ cần trả lời: *đối tượng này có nghĩa vụ pháp lý với khoản nợ không?* Whitelist chỉ có 4 loại cạnh (`BORROWED`, `GUARANTEES`, `CO_BORROWER_WITH`, `LEGAL_REP_OF`), tất cả đều **1-hop từ khoản nợ**.

Đây không phải bài toán đồ thị. Đây là một bảng quan hệ có chỉ mục.

```sql
CREATE TABLE party_obligation (
    obligation_id   BIGSERIAL PRIMARY KEY,
    loan_id         TEXT NOT NULL,
    party_id        TEXT NOT NULL,
    party_type      TEXT NOT NULL CHECK (party_type IN ('PERSON','ORG')),
    edge_type       TEXT NOT NULL CHECK (edge_type IN
                      ('BORROWED','GUARANTEES','CO_BORROWER_WITH','LEGAL_REP_OF')),
    contact_eligible TEXT NOT NULL DEFAULT 'NO'
                      CHECK (contact_eligible IN ('YES','NO','CONDITIONAL')),
    source          TEXT NOT NULL,
    source_ref      TEXT NOT NULL,
    valid_from      DATE NOT NULL,
    valid_to        DATE,
    status          TEXT NOT NULL DEFAULT 'ACTIVE',
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_po_lookup ON party_obligation (loan_id, party_id)
    WHERE status = 'ACTIVE';
```

Truy vấn G02 trở thành một câu SELECT có chỉ mục, p99 dưới 5ms, thay vì một lượt gọi mạng tới Neo4j với p99 vài chục ms và một hệ thống nữa phải vận hành, sao lưu, vá lỗi.

**Điều kiện để quyết định này đúng:** phải viết tầng dữ liệu sau một interface (`ObligationRepository`) để GĐ2 thay bằng Neo4j mà không sửa logic Guardrail. Schema `party_obligation` được thiết kế **khớp trực tiếp** với schema cạnh trong tài liệu Collection Graph, nên việc di trú là ETL, không phải viết lại.

**Khi nào phải chuyển sang Neo4j:** khi cần skip-tracing (`SHARES_PHONE`/`SHARES_ADDRESS`, nhiều hop), phát hiện nhóm liên đới (Louvain), cảnh báo tẩu tán tài sản (đường đi nhiều bước). Toàn bộ đều thuộc GĐ2. Đừng dựng Neo4j để chạy một câu SELECT.

### 3.4 Guardrail Service tách riêng ngay từ MVP

Đây là ngoại lệ duy nhất tôi cho phép về việc "thêm dịch vụ" trong MVP. Lý do: Guardrail phải là một **process boundary** thật, không phải một module trong ứng dụng chính.

- Repo riêng, pipeline riêng, quyền deploy riêng
- Chỉ có Compliance Officer phê duyệt merge vào nhánh policy
- Ứng dụng chính không có quyền ghi vào audit log của Guardrail
- Adapter kênh (SMS/ZNS) từ chối mọi lệnh không có `guardrail_token` hợp lệ

Nếu Guardrail nằm chung codebase với NBA, sớm muộn sẽ có người "tạm bỏ qua kiểm tra để chạy kịp chiến dịch". Ranh giới tiến trình khiến việc đó khó hơn nhiều so với ranh giới module.

### 3.5 Audit log cho MVP

Không dùng WORM storage ở MVP (tốn kém, chậm triển khai). Dùng PostgreSQL với:

```sql
CREATE TABLE guardrail_audit (
    audit_id     TEXT PRIMARY KEY,
    ts           TIMESTAMPTZ NOT NULL,
    payload      JSONB NOT NULL,
    prev_hash    TEXT NOT NULL,
    hash         TEXT NOT NULL
);
REVOKE UPDATE, DELETE ON guardrail_audit FROM ALL;
```

Hash-chain (kế thừa đúng cơ chế đã làm ở CreditAgent) + thu hồi quyền UPDATE/DELETE ở cấp DB + snapshot hash gốc gửi sang hệ thống độc lập hằng ngày. Đủ để chứng minh tính toàn vẹn ở MVP; chuyển sang WORM ở GĐ2.

---

## 4. Kiến trúc triển khai MVP

```
                    ┌─────────────────────────────┐
   EDW hiện hữu ───►│ dbt (staging → marts)       │
   File batch   ───►│ chạy hằng đêm               │
                    └──────────┬──────────────────┘
                               ▼
                    ┌─────────────────────────────┐
                    │ PostgreSQL 16               │
                    │ · debtor_360   · persona    │
                    │ · party_obligation          │
                    │ · case, contact_attempt     │
                    │ · enrichment_fact           │
                    │ · guardrail_audit           │
                    └──────┬───────────────┬──────┘
                           │               │
        ┌──────────────────▼───┐   ┌───────▼─────────────┐
        │ Collection API       │   │ Guardrail Service   │
        │ FastAPI + Temporal   │──►│ FastAPI + Redis     │
        └──────────┬───────────┘   └─────────────────────┘
                   │ (chỉ khi có token)
        ┌──────────▼───────────┐
        │ Channel Adapters     │
        │ SMS · Zalo ZNS       │
        └──────────────────────┘
                   ▲
        ┌──────────┴───────────┐
        │ Collector Workspace  │
        │ React + TS           │
        └──────────────────────┘

   ML: Python job hằng đêm → ghi điểm vào bảng persona (MLflow tracking)
```

Không có Kafka, không có Spark, không có graph DB, không có vector DB. Bốn dịch vụ chạy được, một CSDL, một cache.

---

## 5. Ước lượng hạ tầng MVP

| Thành phần | Cấu hình | Ghi chú |
|---|---|---|
| PostgreSQL | 16 vCPU, 64GB RAM, 2TB NVMe, 1 primary + 1 standby | Đủ cho ~5 triệu case + audit 12 tháng |
| Redis | 4 vCPU, 16GB, sentinel 3 node | Bộ đếm tần suất |
| App pods (API + Guardrail + Worker) | 3×4 vCPU/8GB mỗi service, tối thiểu 3 replica Guardrail | |
| Temporal | Cụm nhỏ + Postgres backend riêng | |
| ML training | 1 node 16 vCPU/64GB, chạy theo lịch | Không cần GPU |
| Quan trắc | Prometheus + Grafana + Loki, ~200GB retention | |

Tổng: khoảng 60–80 vCPU và 300GB RAM. Với môi trường DEV/UAT/PROD thì nhân ba, nhưng DEV/UAT có thể giảm 50%.

---

## 6. Cấu trúc đội

| Vai trò | Số lượng | Ghi chú |
|---|---|---|
| Tech Lead / SA | 1 | |
| Backend (Python/FastAPI/Temporal) | 3 | 1 người chuyên trách Guardrail |
| Data Engineer (dbt/SQL) | 2 | Trọng tâm giai đoạn đầu là làm sạch dữ liệu liên hệ |
| Data Scientist | 2 | ML1, ML4 + khung đo uplift |
| Frontend | 2 | |
| BA nghiệp vụ thu hồi | 2 | Bắt buộc — không thể thiếu người hiểu nghiệp vụ XLN |
| QA | 2 | 1 người chuyên bộ test Guardrail |
| DevOps/SRE | 1 | Chia sẻ với đội hạ tầng |
| **Tổng** | **15** | + Product Owner từ Khối XLN (không toàn thời gian) |

Vai trò khó tuyển nhất là BA hiểu sâu nghiệp vụ thu hồi nợ. Nếu thiếu, MVP sẽ ra một hệ thống kỹ thuật đúng nhưng nghiệp vụ sai — đây là kiểu thất bại tốn kém nhất vì chỉ phát hiện sau khi đã xong.

---

## 7. Lộ trình 4 tháng

| Tháng | Trọng tâm | Mốc kiểm chứng |
|---|---|---|
| **T1** | Hạ tầng, CI/CD, kết nối EDW, dbt staging; **khởi động làm sạch dữ liệu liên hệ**; thiết kế chi tiết Guardrail | Pipeline dữ liệu chạy end-to-end với dữ liệu thật |
| **T2** | Guardrail GR-P1 (G01/G02/G03/G05/G12) + audit hash-chain; `party_obligation` từ nguồn; Case Workflow trên Temporal | **Bộ test Guardrail 150 case pass 100%**, gồm nhóm bypass attempt |
| **T3** | Persona v0 + 3 điểm số; ML1 & ML4; Collector Workspace; Manual Enrichment 8 fact type | Persona Card hiển thị được, cán bộ dùng thử |
| **T4** | Tích hợp SMS/ZNS; thiết lập holdout 10%; UAT; go-live giới hạn 1–2 chi nhánh | **Chiến dịch B1 đầu tiên chạy qua Guardrail** |

**Cột mốc chặn:** không tích hợp kênh ra ngoài trước khi bộ test Guardrail ở T2 pass. Đây là ràng buộc cứng đã nêu trong đặc tả Guardrail.

---

## 8. Rủi ro kỹ thuật của MVP

| # | Rủi ro | Mức | Biện pháp |
|---|---|---|---|
| R1 | Dữ liệu liên hệ tệ hơn dự kiến, số điện thoại chết nhiều | **Cao** | Đo ngay tháng 1; nếu tỷ lệ số hợp lệ < 60% thì đây trở thành nội dung chính của MVP, không phải ML |
| R2 | Truy cập EDW bị chậm do quy trình nội bộ | Cao | Xin quyền đọc từ tuần 1; chuẩn bị phương án nhận file batch dự phòng |
| R3 | Đàm phán tích hợp Zalo ZNS / SMS Gateway kéo dài | Trung bình | Khởi động từ tuần 1, song song; MVP có thể demo bằng kênh nội bộ trước |
| R4 | `party_obligation` không dựng được đầy đủ từ hệ thống nguồn | **Cao** | Nếu dữ liệu bảo lãnh/đồng vay không sạch, G02 sẽ chặn quá nhiều → phải có luồng bổ sung thủ công có kiểm soát |
| R5 | Ranh giới Guardrail bị phá vì áp lực tiến độ | Trung bình | Repo riêng + quyền merge riêng + test bypass trong CI |
| R6 | Thiết lập holdout bị phản đối ("sao lại bỏ mặc 10% khách hàng?") | Trung bình | Giải thích: holdout vẫn nhận treatment hiện hành, chỉ không nhận treatment mới. Cần Ban lãnh đạo hậu thuẫn từ đầu |

R4 đáng lo hơn vẻ ngoài. Nếu dữ liệu bên bảo lãnh và đồng vay trong hệ thống nguồn không đầy đủ, Guardrail sẽ chặn đúng theo thiết kế nhưng chặn quá nhiều, và đội vận hành sẽ đòi nới. Cần khảo sát chất lượng dữ liệu này **ngay trong tháng 1**, trước khi cam kết phạm vi.

---

## 9. Đường tiến hoá lên kiến trúc đích

| Thành phần MVP | Tiến hoá GĐ2–3 | Có phải viết lại không? |
|---|---|---|
| `party_obligation` (Postgres) | → Neo4j Collection Graph | Không — đổi implementation của `ObligationRepository`, schema đã khớp |
| dbt trên EDW | → Lakehouse Iceberg + Spark | Không — mô hình dbt chuyển sang Spark SQL phần lớn giữ nguyên |
| Batch scoring → bảng Postgres | → Feature Store + online serving | Một phần — cần thêm tầng serving, logic mô hình giữ nguyên |
| Guardrail FastAPI | Giữ nguyên, thêm G04/G06/G07/G09/G10 | Không — thiết kế control là plug-in |
| Temporal workflow | Giữ nguyên hoặc chuyển sang nền tảng L7 mua ngoài | Tuỳ quyết định buy-vs-build ở GĐ2 |
| Postgres audit hash-chain | → WORM storage | Không — chỉ đổi nơi lưu |

Điểm cần kiểm tra ở cuối MVP: **có nên mua nền tảng L7 (case management + dialer + campaign) thay vì tự xây tiếp không?** Các ngân hàng lớn phần lớn mua tầng này và tự xây tầng dữ liệu/quyết định. Sau MVP, đội sẽ có đủ hiểu biết để đánh giá — trước MVP thì chưa.

---

## 10. Những gì tôi khuyên đừng làm trong MVP

| Cám dỗ | Vì sao đừng |
|---|---|
| Dựng Kafka "vì sau này cần streaming" | MVP chỉ cần dữ liệu ngày. Kafka thêm một hệ thống phải vận hành mà chưa giải quyết vấn đề nào |
| Dựng Neo4j "vì kiến trúc có graph" | Xem Mục 3.3 |
| Đưa LLM vào để "có AI" | Giả thuyết cốt lõi của MVP không cần LLM. Thêm vào là thêm rủi ro tuân thủ và một tầng gateway phải xây |
| Xây Feature Store cho 2 mô hình | Bảng dbt là đủ. Feast có ý nghĩa từ ~10 mô hình trở lên |
| Tích hợp dialer ngay | Đàm phán nội bộ dài, và B1 nên digital-first chứ không nên gọi |
| Làm cả bán lẻ lẫn KHDN | Chọn bán lẻ B1. KHDN cần graph và đàm phán nhóm — đó là GĐ2 |
| Bỏ qua holdout để "tối đa thu hồi ngay" | Đây là sai lầm đắt nhất có thể mắc. Không có holdout thì sau 2 năm không chứng minh được hệ thống tạo ra giá trị gì |

---

## 11. Việc cần quyết trước khi bắt đầu

| # | Quyết định | Người quyết | Hạn |
|---|---|---|---|
| 1 | Xác nhận 3 giả định ở Mục 2 | EA + Khối CNTT | Tuần 1 |
| 2 | Phạm vi MVP: bán lẻ bucket B1, 1–2 chi nhánh thí điểm | PO + Khối XLN | Tuần 1 |
| 3 | Cấp quyền đọc EDW và các bảng nguồn | Khối Dữ liệu | Tuần 1 |
| 4 | Chấp thuận thiết lập holdout 10% | Ban lãnh đạo Khối XLN | Tuần 2 |
| 5 | Chốt câu hỏi 1–3 trong danh mục chờ Pháp chế (tự áp TT 18/2019, mẫu hợp đồng, khung giờ email) | Pháp chế | Tuần 4 |
| 6 | Khởi động đàm phán tích hợp SMS/ZNS | PO + CNTT | Tuần 1 |
| 7 | Khảo sát chất lượng dữ liệu bảo lãnh/đồng vay (rủi ro R4) | Data Engineer | Tuần 3 |

---

*Đề xuất kỹ thuật, phiên bản thảo luận. Các lựa chọn công nghệ phụ thuộc vào chuẩn kỹ thuật và danh mục công nghệ được phê duyệt của Ngân hàng — cần đối chiếu trước khi chốt.*
