# B.COLLECTION — CHIẾN LƯỢC KIỂM THỬ HIỆU NĂNG & KHẢ NĂNG MỞ RỘNG (SCALABILITY BLUEPRINT)
### Thẩm định Kiến trúc Tải Lớn, Kế hoạch Kiểm thử Hiệu năng & Phương án Sizing Production cho Ngân hàng Top 1
**Dự án:** Hệ thống Quản lý & Tối ưu Thu hồi nợ B.Collection — BIDV  
**Tác giả:** Lead Enterprise Architect (30 năm kinh nghiệm Core Banking & High-Throughput Systems)  
**Phiên bản:** v1.0 | **Ngày thẩm định:** 01/09/2026

---

## 📑 MỤC LỤC
1. [Bài toán Tải Thực tế tại Ngân hàng Bán lẻ Lớn nhất Việt Nam](#1-bài-toán-tải-thực-tế-tại-ngân-hàng-bán-lẻ-lớn-nhất-việt-nam)
2. [Đánh giá Khả năng Đáp ứng Scale của Kiến trúc Hiện tại](#2-đánh-giá-khả-năng-đáp-ứng-scale-của-kiến-trúc-hiện-tại)
3. [Chiến lược 4 Kịch bản Kiểm thử Tải (Performance Test Scenarios)](#3-chiến-lược-4-kịch-bản-kiểm-thử-tải)
4. [Bộ Chỉ số SLA & Tiêu chí Nghiệm thu Hiệu năng (Performance DoD)](#4-bộ-chỉ-số-sla--tiêu-chí-nghiệm-thu-hiệu-năng)
5. [Kiến trúc Triển khai Production Sizing (K8s / OpenShift & Database Partitioning)](#5-kiến-trúc-triển-khai-production-sizing)
6. [Bộ Script Kiểm thử Tải Tự động (Locust Benchmark Engine)](#6-bộ-script-kiểm-thử-tải-tự-động)

---

## 1. BÀI TOÁN TẢI THỰC TẾ TẠI NGÂN HÀNG BÁN LẺ LỚN NHẤT VIỆT NAM

Để đảm bảo hệ thống không bị "nghẽn cổ chai" khi triển khai diện rộng, chúng ta mô hình hóa dung lượng dữ liệu và lưu lượng giao dịch thực tế của BIDV:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               MÔ HÌNH DUNG LƯỢNG TẢI PRODUCTION (BIDV SCALE PROFILE)                   │
├──────────────────────────────────────┬──────────────────────┬──────────────────────────┤
│ Tham số Quy mô                       │ Giá trị Ước tính     │ Tác động Tải Hệ thống    │
├──────────────────────────────────────┼──────────────────────┼──────────────────────────┤
│ **Tổng Khách hàng Cá nhân (Retail)** │ ~15 – 18 Triệu CIFs  │ Bảng Golden ID           │
│ **Hồ sơ Quá hạn Nhóm sớm (B1)**      │ 500.000 – 800.000/ngày│ Chạy AI Scoring ban đêm  │
│ **Số Chuyên viên Thu nợ đồng thời**  │ 1.500 – 2.500 Users  │ WebSocket & Softphone    │
│ **Lưu lượng Batch Zalo/SMS buổi sáng**│ 300.000 tin / 60 phút│ **Peak Throughput: 150 TPS│
│ **Lưu lượng Guardrail L6 Giờ cao điểm│ Toàn bộ Batch + Call │ **Peak Throughput: 500-1000 TPS**│
│ **Dung lượng Audit Log tích lũy**    │ ~20 Triệu records/năm│ Phân vùng Storage WORM   │
└──────────────────────────────────────┴──────────────────────┴──────────────────────────┘
```

---

## 2. ĐÁNH GIÁ KHẢ NĂNG ĐÁP ỨNG SCALE CỦA KIẾN TRÚC HIỆN TẠI

Giải pháp kiến trúc hiện tại của **B.Collection** được thiết kế có chủ đích cho việc Scale mở rộng từ MVP lên Toàn hàng (100% Horizontal Scalability):

```
                                  ┌────────────────────────────────────────────────────────┐
                                  │      MÔ HÌNH MỞ RỘNG KHẢ NĂNG CHỊU TẢI (HORIZONTAL)    │
                                  └────────────────────────────────────────────────────────┘
                                                              │
          ┌───────────────────────────────────────────────────┼───────────────────────────────────────────────────┐
          ▼                                                   ▼                                                   ▼
┌───────────────────────────────────┐       ┌───────────────────────────────────┐       ┌───────────────────────────────────┐
│ 1. L6 GUARDRAIL (STATELESS)       │       │ 2. REDIS 7 CLUSTER (SUB-MILLISECOND│      │ 3. POSTGRESQL PARTITIONING        │
├───────────────────────────────────┤       ├───────────────────────────────────┤       ├───────────────────────────────────┤
│ • FastAPI ASGI (Non-blocking I/O) │       │ • Sliding Window Sorted Sets      │       │ • Bảng `party_obligation`:        │
│ • Whitelist nạp In-Memory RAM     │       │ • Tra cứu tần suất trong < 1ms    │       │   Point lookup qua B-Tree < 1ms   │
│ • Không giữ session (Stateless)   │       │ • 1 Node Redis cân 80.000 ops/sec │       │ • Bảng Audit & Interaction:       │
│ • Scale tuyến tính theo Pods (K8s)│       │ • Master-Replica + Sentinel HA    │       │   Range Partitioning theo Tháng   │
│ • 1 Pod (2 vCPU) = 1.200 TPS      │       │                                   │       │ • Connection Pooler (PgBouncer)   │
└───────────────────────────────────┘       └───────────────────────────────────┘       └───────────────────────────────────┘
```

### Tại sao Kiến trúc này đáp ứng được Ngân hàng Lớn?
1. **L6 Guardrail là Stateless & Sub-15ms:** Logic kiểm soát G01–G12 không gọi I/O đĩa cứng. Dữ liệu quan hệ nợ được cache/lookup qua Index B-Tree, biến đếm tần suất gọi trong ngày lưu trên RAM Redis $\rightarrow$ Độ trễ xử lý thực tế chỉ mất **$2 – 5\text{ms}$** cho mỗi request.
2. **Không có Khóa Dữ liệu (No Pessimistic Lock):** Việc cấp phát Token ES256 được tính toán độc lập, không lock bảng Database, tránh tình trạng Deadlock khi hàng ngàn chuyên viên gọi điện đồng thời.
3. **Phân tách Rõ ràng OLTP và OLAP:**
   * OLTP (Guardrail, Case Workflow, Workspace UI) chạy trên PostgreSQL/Redis.
   * OLAP (AI Scoring, ML1/ML4, dbt Marts, Báo cáo ROI) chạy tách biệt qua Batch Job ban đêm và Data Warehouse, **hoàn toàn không ảnh hưởng tới hiệu năng hệ thống ban ngày**.

---

## 3. CHIẾN LƯỢC 4 KỊCH BẢN KIỂM THỬ TẢI (PERFORMANCE SCENARIOS)

Trước khi Go-Live Production, hệ thống bắt buộc phải trải qua 4 kịch bản kiểm thử tải nghiêm ngặt:

```
┌────┬────────────────────────────┬─────────────────────────────┬────────────────────────────────────────┐
│ STT│ Kịch bản Kiểm thử (Test)   │ Mức Tải Áp đặt (Workload)   │ Mục tiêu Thẩm định (Verification Goal) │
├────┼────────────────────────────┼─────────────────────────────┼────────────────────────────────────────┤
│ 01 │ **Baseline Load Test**     │ 100 TPS liên tục trong 2 giờ │ Đảm bảo hệ thống hoạt động ổn định ở   │
│    │ *(Tải thường ngày)*        │ (80% Evaluate + 20% Commit) │ mức tải chuẩn; CPU < 25%, RAM phẳng.   │
├────┼────────────────────────────┼─────────────────────────────┼────────────────────────────────────────┤
│ 02 │ **Peak Stress Test**       │ **Tăng vọt lên 1.000 TPS**  │ Mô phỏng đợt bắn 300.000 tin Zalo sáng;│
│    │ *(Tải giờ cao điểm)*       │ trong 15 phút               │ Đảm bảo $P_{99} < 15\text{ms}$, 0 lỗi. │
├────┼────────────────────────────┼─────────────────────────────┼────────────────────────────────────────┤
│ 03 │ **Soak / Endurance Test**  │ 250 TPS liên tục trong      │ Phát hiện rò rỉ bộ nhớ (Memory Leak),  │
│    │ *(Tải bền bỉ 24 giờ)*      │ **24 giờ liên tục**         │ kiểm tra phình to sổ cái Hash-chain.   │
├────┼────────────────────────────┼─────────────────────────────┼────────────────────────────────────────┤
│ 04 │ **Spike & Chaos Test**     │ Đang ở mức 500 TPS $\rightarrow$  │ Đảm bảo hệ thống kích hoạt Fail-Closed │
│    │ *(Sự cố bất thường)*       │ Tắt đột ngột 1 Node DB/Redis│ tức thì, không bị rò rỉ cuộc gọi cấm.  │
└────┴────────────────────────────┴─────────────────────────────┴────────────────────────────────────────┘
```

---

## 4. BỘ CHỈ SỐ SLA & TIÊU CHÍ NGHIỆM THU HIỆU NĂNG

```
┌─────────────────────────────────────────────────────────────┬─────────────────────┬──────────────────┐
│ Chỉ số Đo lường Hiệu năng (Performance Metric)              │ Ngưỡng Chuẩn (SLA)  │ Ngưỡng Nguy hiểm │
├─────────────────────────────────────────────────────────────┼─────────────────────┼──────────────────┤
│ **Thời gian phản hồi Guardrail L6 ($P_{50}$ Median)**       │ **< 5 ms**          │ > 10 ms          │
│ **Thời gian phản hồi Guardrail L6 ($P_{95}$)**              │ **< 10 ms**         │ > 20 ms          │
│ **Thời gian phản hồi Guardrail L6 ($P_{99}$)**              │ **< 15 ms**         │ > 30 ms          │
│ **Thời gian tải Persona Card v0 trên Workspace ($P_{95}$)** │ **< 300 ms**        │ > 800 ms         │
│ **Thời gian Real-time Balance Check với Core Banking**      │ **< 300 ms**        │ > 1.000 ms       │
│ **Tỷ lệ Lỗi Hệ thống (Error Rate / HTTP 5xx) khi Peak Tải** │ **0.00% (Zero)**    │ > 0.01%          │
│ **Mức chiếm dụng CPU trên Pods khi Peak 1.000 TPS**         │ **< 60%**           │ > 80%            │
└─────────────────────────────────────────────────────────────┴─────────────────────┴──────────────────┘
```

---

## 5. KIẾN TRÚC TRIỂN KHAI PRODUCTION SIZING (K8S & DB)

Để phục vụ toàn bộ 15–18 triệu khách hàng của BIDV, cấu hình hạ tầng khuyến nghị cho Production (Giai đoạn 2):

### 5.1 Cụm Kubernetes / OpenShift (Stateless Services)
* **`bcollection-guardrail` Service:**
  * 4 Pods tối thiểu (Auto-scale lên tối đa 12 Pods khi có chiến dịch lớn).
  * Tài nguyên mỗi Pod: 2 vCPU, 4GB RAM $\rightarrow$ Tổng năng lực chịu tải: **~6.000 TPS**.
* **`bcollection-platform-api` Service:**
  * 4 Pods (Auto-scale lên 8 Pods), tài nguyên 2 vCPU, 4GB RAM.

### 5.2 Cơ sở Dữ liệu & Caching (Stateful Tier)
* **PostgreSQL 16 High-Availability Cluster:**
  * 1 Primary Node + 2 Read Replicas (Sync Replication cho An toàn Dữ liệu).
  * Cấu hình: 32 vCPU, 128GB RAM, NVMe SSD Storage.
  * Tích hợp **PgBouncer Connection Pooler** (Hỗ trợ 10.000 active client connections).
  * Áp dụng **Declarative Table Partitioning** theo Tháng cho các bảng: `audit_ledger`, `call_interaction_log`, `message_outbound_log`.
* **Redis 7 Cluster:**
  * Cụm 3 Master - 3 Replica Nodes (Bộ nhớ: 32GB RAM/Node).

---

## 6. BỘ SCRIPT KIỂM THỬ TẢI TỰ ĐỘNG (LOCUST BENCHMARK ENGINE)

Chúng ta đã hiện thực hóa script kiểm thử tải tự động bằng công cụ **Locust** phân tán để có thể chạy stress test trực tiếp ngay trong môi trường phát triển và CI/CD:

* File thực thi: `tests/performance/locustfile.py`
* Giả lập đồng thời 500 – 1.000 Virtual Users bắn liên tục các yêu cầu `/v1/guardrail/evaluate` và `/commit` để đo đạc chính xác Response Time Distribution ($P_{50}, P_{95}, P_{99}$).
