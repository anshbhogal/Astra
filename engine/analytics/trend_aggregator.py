"""Time-Series Trend Aggregator for Project Quality Telemetry."""

from datetime import datetime, timezone
from typing import Any, Dict, List


class TrendAggregator:
    """Aggregates test run execution history into structured daily/weekly trend series."""

    @staticmethod
    def aggregate_daily_trends(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Groups historical test runs by day (YYYY-MM-DD) computing pass rate & duration trends."""
        if not runs:
            return []

        buckets: Dict[str, Dict[str, Any]] = {}

        for run in runs:
            created_at = run.get("created_at")
            if isinstance(created_at, datetime):
                date_str = created_at.strftime("%Y-%m-%d")
            elif isinstance(created_at, str):
                date_str = created_at.split("T")[0]
            else:
                date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            if date_str not in buckets:
                buckets[date_str] = {
                    "date": date_str,
                    "total_tests": 0,
                    "passed_tests": 0,
                    "failed_tests": 0,
                    "total_duration_ms": 0.0,
                    "run_count": 0
                }

            b = buckets[date_str]
            total = run.get("total_tests", 0)
            passed = run.get("passed_tests", 0)
            failed = run.get("failed_tests", 0)
            dur = run.get("duration_ms", 0.0)

            b["total_tests"] += total
            b["passed_tests"] += passed
            b["failed_tests"] += failed
            b["total_duration_ms"] += dur
            b["run_count"] += 1

        # Format into sorted list
        trend_series = []
        for date_str in sorted(buckets.keys()):
            b = buckets[date_str]
            pass_rate = round((b["passed_tests"] / max(1, b["total_tests"])) * 100.0, 1)
            avg_duration = round(b["total_duration_ms"] / max(1, b["run_count"]), 1)
            trend_series.append({
                "date": date_str,
                "pass_rate": pass_rate,
                "total_tests": b["total_tests"],
                "passed_tests": b["passed_tests"],
                "failed_tests": b["failed_tests"],
                "avg_duration_ms": avg_duration,
                "runs_count": b["run_count"]
            })

        return trend_series
