"""
Module thu thập chỉ số hiệu năng và trạng thái (Prometheus Metrics Collector).
Cung cấp định dạng chuẩn Prometheus Text Exposition Format (OpenMetrics):
- Tần suất request (RPS, Traffic)
- Phân phối độ trễ P50, P90, P99
- Thống kê tỷ lệ lỗi HTTP 2xx, 4xx, 5xx
- Lượt gọi Adapter và thời gian đáp ứng từng Legacy Microservice
- Lượt thẩm định pháp chế L6 Guardrail
"""

import time
import threading
from typing import Dict, Any, List, Tuple
from collections import defaultdict


class MetricsCollector:
    def __init__(self, service_name: str = "bcollection"):
        self.service_name = service_name
        self._lock = threading.Lock()

        # Counter: (service, method, path, status) -> count
        self.http_requests_total: Dict[Tuple[str, str, str, int], int] = defaultdict(int)

        # Durations: (service, path) -> list of duration_seconds (last 1000 samples)
        self.http_request_durations: Dict[Tuple[str, str], List[float]] = defaultdict(list)

        # Counter: (adapter, method, status) -> count
        self.adapter_calls_total: Dict[Tuple[str, str, str], int] = defaultdict(int)

        # Durations: (adapter, method) -> list of duration_seconds
        self.adapter_durations: Dict[Tuple[str, str], List[float]] = defaultdict(list)

        # Counter: verdict -> count
        self.guardrail_evaluations_total: Dict[str, int] = defaultdict(int)

        # Uptime timestamp
        self.start_time = time.time()

    def record_http_request(self, service: str, method: str, path: str, status_code: int, duration_seconds: float):
        with self._lock:
            key = (service, method, path, status_code)
            self.http_requests_total[key] += 1

            dur_key = (service, path)
            samples = self.http_request_durations[dur_key]
            samples.append(duration_seconds)
            if len(samples) > 1000:
                samples.pop(0)

    def record_adapter_call(self, adapter: str, method: str, status: str, duration_seconds: float):
        with self._lock:
            key = (adapter, method, status)
            self.adapter_calls_total[key] += 1

            dur_key = (adapter, method)
            samples = self.adapter_durations[dur_key]
            samples.append(duration_seconds)
            if len(samples) > 500:
                samples.pop(0)

    def record_guardrail_eval(self, verdict: str):
        with self._lock:
            self.guardrail_evaluations_total[verdict] += 1

    def get_aggregated_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_reqs = sum(self.http_requests_total.values())
            total_errors = sum(count for (_, _, _, status), count in self.http_requests_total.items() if status >= 400)
            all_durations = [d for samples in self.http_request_durations.values() for d in samples]

            p50 = 0.0
            p95 = 0.0
            p99 = 0.0
            avg_ms = 0.0

            if all_durations:
                sorted_d = sorted(all_durations)
                n = len(sorted_d)
                p50 = round(sorted_d[int(n * 0.50)] * 1000, 2)
                p95 = round(sorted_d[int(n * 0.95)] * 1000, 2)
                p99 = round(sorted_d[min(int(n * 0.99), n - 1)] * 1000, 2)
                avg_ms = round((sum(sorted_d) / n) * 1000, 2)

            uptime_seconds = round(time.time() - self.start_time, 1)
            error_rate_pct = round((total_errors / total_reqs * 100), 2) if total_reqs > 0 else 0.0

            # Phân bổ theo service
            service_counts: Dict[str, int] = defaultdict(int)
            for (svc, _, _, _), count in self.http_requests_total.items():
                service_counts[svc] += count

            # Phân bổ theo adapter
            adapter_stats: Dict[str, Dict[str, Any]] = {}
            for (adp, mtd), samples in self.adapter_durations.items():
                if samples:
                    adapter_stats[f"{adp}.{mtd}"] = {
                        "count": len(samples),
                        "avg_ms": round((sum(samples) / len(samples)) * 1000, 2),
                        "p95_ms": round(sorted(samples)[int(len(samples) * 0.95)] * 1000, 2) if len(samples) >= 20 else round(max(samples) * 1000, 2)
                    }

            return {
                "uptime_seconds": uptime_seconds,
                "total_requests": total_reqs,
                "total_errors": total_errors,
                "error_rate_pct": error_rate_pct,
                "latency_p50_ms": p50,
                "latency_p95_ms": p95,
                "latency_p99_ms": p99,
                "latency_avg_ms": avg_ms,
                "service_breakdown": dict(service_counts),
                "adapter_breakdown": adapter_stats,
                "guardrail_evaluations": dict(self.guardrail_evaluations_total)
            }

    def render_prometheus_text(self) -> str:
        """Sinh chuỗi Prometheus exposition format chuẩn."""
        lines = [
            "# HELP http_requests_total Total number of HTTP requests processed.",
            "# TYPE http_requests_total counter"
        ]
        with self._lock:
            for (service, method, path, status), count in self.http_requests_total.items():
                # Escape quotes in path
                p = path.replace('"', '\\"')
                lines.append(f'http_requests_total{{service="{service}",method="{method}",path="{p}",status="{status}"}} {count}')

            lines.extend([
                "",
                "# HELP http_request_duration_seconds HTTP request duration in seconds.",
                "# TYPE http_request_duration_seconds summary"
            ])
            for (service, path), samples in self.http_request_durations.items():
                if not samples:
                    continue
                p = path.replace('"', '\\"')
                cnt = len(samples)
                total = sum(samples)
                sorted_s = sorted(samples)
                lines.append(f'http_request_duration_seconds_count{{service="{service}",path="{p}"}} {cnt}')
                lines.append(f'http_request_duration_seconds_sum{{service="{service}",path="{p}"}} {total:.6f}')
                lines.append(f'http_request_duration_seconds{{service="{service}",path="{p}",quantile="0.5"}} {sorted_s[int(cnt*0.5)]:.6f}')
                lines.append(f'http_request_duration_seconds{{service="{service}",path="{p}",quantile="0.95"}} {sorted_s[int(cnt*0.95)]:.6f}')

            lines.extend([
                "",
                "# HELP adapter_calls_total Total calls made by integration adapters to external systems.",
                "# TYPE adapter_calls_total counter"
            ])
            for (adapter, method, status), count in self.adapter_calls_total.items():
                lines.append(f'adapter_calls_total{{adapter="{adapter}",method="{method}",status="{status}"}} {count}')

            lines.extend([
                "",
                "# HELP guardrail_evaluations_total Total L6 compliance guardrail evaluations.",
                "# TYPE guardrail_evaluations_total counter"
            ])
            for verdict, count in self.guardrail_evaluations_total.items():
                lines.append(f'guardrail_evaluations_total{{verdict="{verdict}"}} {count}')

            lines.extend([
                "",
                "# HELP process_uptime_seconds Process uptime in seconds.",
                "# TYPE process_uptime_seconds gauge",
                f'process_uptime_seconds{{service="{self.service_name}"}} {time.time() - self.start_time:.1f}',
                ""
            ])

        return "\n".join(lines)


# Singleton MetricsCollector toàn cục
global_metrics = MetricsCollector()
