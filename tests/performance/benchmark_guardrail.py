import time
import sys
import os
import concurrent.futures
from datetime import datetime

# Thêm đường dẫn guardrail vào path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../bcollection-guardrail')))

from src.guardrail.engine.orchestrator import GuardrailOrchestrator
from src.guardrail.repositories.obligation_repo import InMemoryObligationRepository
from src.guardrail.repositories.counter_repo import InMemoryCounterRepository
from src.guardrail.repositories.audit_repo import HashChainAuditRepository
from src.guardrail.api.schemas import EvaluateRequest, TargetParty, ActionIntentPayload, ChannelType

def run_guardrail_stress_benchmark(num_requests: int = 5000, max_workers: int = 8):
    """
    Micro-Benchmark kiểm thử tải và đo đạc độ trễ P50, P95, P99 cho L6 Guardrail Service.
    """
    print(f"🚀 BẮT ĐẦU CHẠY BENCHMARK GUARDRAIL SERVICE VỚI {num_requests:,} REQUESTS ({max_workers} WORKERS)...")
    
    obl_repo = InMemoryObligationRepository()
    cnt_repo = InMemoryCounterRepository()
    aud_repo = HashChainAuditRepository()

    # Nạp 1.000 hồ sơ nghĩa vụ mẫu
    for i in range(1, 1001):
        obl_repo.add_obligation(
            loan_id=f"LOAN-BENCH-{i:06d}",
            party_id=f"CIF-BENCH-{i:06d}",
            edge_type="BORROWED",
            contact_eligible="YES"
        )

    orchestrator = GuardrailOrchestrator(obl_repo, cnt_repo, aud_repo)

    latencies_ms = []

    def execute_single_request(idx: int):
        cif_idx = (idx % 1000) + 1
        req = EvaluateRequest(
            request_id=f"REQ-PERF-{idx:08d}",
            loan_id=f"LOAN-BENCH-{cif_idx:06d}",
            debtor_cif=f"CIF-BENCH-{cif_idx:06d}",
            target_party=TargetParty(party_id=f"CIF-BENCH-{cif_idx:06d}"),
            intent=ActionIntentPayload(
                action_type="VOICE_CALL",
                channel=ChannelType.VOICE,
                proposed_time=datetime(2026, 9, 1, 10, 30) # Trong giờ hợp lệ
            ),
            case_context={"overdue_amount": 5000000.0}
        )
        
        t0 = time.perf_counter()
        res = orchestrator.evaluate(req)
        t1 = time.perf_counter()
        
        latency = (t1 - t0) * 1000.0 # ms
        return latency, res.decision.value

    start_total_time = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(execute_single_request, i) for i in range(num_requests)]
        for f in concurrent.futures.as_completed(futures):
            lat, dec = f.result()
            latencies_ms.append(lat)

    total_time = time.perf_counter() - start_total_time
    throughput_tps = num_requests / total_time

    latencies_ms.sort()
    p50 = latencies_ms[int(len(latencies_ms) * 0.50)]
    p90 = latencies_ms[int(len(latencies_ms) * 0.90)]
    p95 = latencies_ms[int(len(latencies_ms) * 0.95)]
    p99 = latencies_ms[int(len(latencies_ms) * 0.99)]
    max_lat = latencies_ms[-1]

    print("\n" + "="*70)
    print("📊 KẾT QUẢ KIỂM THỬ HIỆU NĂNG GUARDRAIL SERVICE L6 (BENCHMARK REPORT)")
    print("="*70)
    print(f"• Tổng số Yêu cầu (Total Requests):   {num_requests:,}")
    print(f"• Tổng thời gian thực thi:           {total_time:.3f} giây")
    print(f"• Năng lực Xử lý Thực tế (Throughput): {throughput_tps:,.1f} TPS (Giao dịch/giây)")
    print(f"• Độ trễ Trung vị (P50 Median):      {p50:.3f} ms")
    print(f"• Độ trễ 90% (P90 Latency):          {p90:.3f} ms")
    print(f"• Độ trễ 95% (P95 Latency):          {p95:.3f} ms")
    print(f"• Độ trễ 99% (P99 Latency):          {p99:.3f} ms (SLA yêu cầu < 15 ms)")
    print(f"• Độ trễ Cao nhất (Max Latency):     {max_lat:.3f} ms")
    print(f"• Tính toàn vẹn Sổ cái Audit:        {'100% TOÀN VẸN' if aud_repo.verify_integrity() else 'LỖI'}")
    print("="*70)

    # Khẳng định SLA
    assert p99 < 15.0, f"P99 latency {p99}ms vượt quá SLA 15ms"
    assert throughput_tps > 500, f"Throughput {throughput_tps} TPS chưa đạt yêu cầu"
    print("🎉 KẾT QUẢ: ĐẠT 100% TIÊU CHUẨN HIỆU NĂNG CHO NGÂN HÀNG LỚN (TIER-1 BANK GRADE)!\n")

if __name__ == "__main__":
    run_guardrail_stress_benchmark(num_requests=5000, max_workers=8)
