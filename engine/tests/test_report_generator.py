"""Unit tests for HTML/PDF Report Generators, MetricsCalculator, and TrendAggregator."""

import pytest
from engine.analytics.metrics_calculator import MetricsCalculator, QualityScorePolicy
from engine.analytics.trend_aggregator import TrendAggregator
from engine.reporting.html_report_generator import HTMLReportGenerator
from engine.reporting.pdf_report_generator import PDFReportGenerator


def test_metrics_calculator():
    """Verify mathematical formulations and score clamping."""
    # 1. 100% pass, 0 flaky, 100 coverage, 0 defects = 100.0 score
    score1 = MetricsCalculator.calculate_quality_score(
        pass_rate=100.0,
        flaky_ratio=0.0,
        requirement_coverage=100.0,
        defect_density=0.0
    )
    assert score1 == 100.0

    # 2. 50% pass rate, high defects
    score2 = MetricsCalculator.calculate_quality_score(
        pass_rate=50.0,
        flaky_ratio=20.0,
        requirement_coverage=60.0,
        defect_density=3.0
    )
    assert 0.0 <= score2 <= 100.0

    # Custom policy weights
    custom_policy = QualityScorePolicy(
        pass_rate_weight=0.50,
        reliability_weight=0.10,
        coverage_weight=0.20,
        defect_health_weight=0.20
    )
    score3 = MetricsCalculator.calculate_quality_score(
        pass_rate=100.0,
        flaky_ratio=0.0,
        requirement_coverage=100.0,
        defect_density=0.0,
        policy=custom_policy
    )
    assert score3 == 100.0


def test_trend_aggregator():
    """Verify daily aggregation of test runs."""
    runs = [
        {"created_at": "2026-10-01T10:00:00Z", "total_tests": 10, "passed_tests": 9, "failed_tests": 1, "duration_ms": 100.0},
        {"created_at": "2026-10-01T14:00:00Z", "total_tests": 20, "passed_tests": 18, "failed_tests": 2, "duration_ms": 200.0},
        {"created_at": "2026-10-02T09:00:00Z", "total_tests": 30, "passed_tests": 30, "failed_tests": 0, "duration_ms": 300.0},
    ]

    trends = TrendAggregator.aggregate_daily_trends(runs)
    assert len(trends) == 2
    assert trends[0]["date"] == "2026-10-01"
    assert trends[0]["total_tests"] == 30
    assert trends[0]["passed_tests"] == 27
    assert trends[0]["pass_rate"] == 90.0

    assert trends[1]["date"] == "2026-10-02"
    assert trends[1]["pass_rate"] == 100.0


def test_html_report_generator_sanitization():
    """Verify XSS sanitization and HTML structure."""
    malicious_project_name = "<script>alert('xss')</script>Banking Core"
    analytics_data = {
        "quality_score": 85.5,
        "test_pass_rate": 92.4,
        "total_tests_executed": 150,
        "passed_tests": 138,
        "failed_tests": 12,
        "defect_density_per_endpoint": 1.2,
        "requirement_coverage_percent": 90.0,
        "failure_category_breakdown": [{"category": "APPLICATION_BUG", "count": 10, "color": "#ef4444"}],
        "pass_rate_trend": [{"date": "2026-10-01", "pass_rate": 92.4, "total_tests": 150, "avg_duration_ms": 120.0}]
    }

    html_out = HTMLReportGenerator.generate_report_html(
        project_name=malicious_project_name,
        analytics_data=analytics_data
    )

    # Must be sanitized
    assert "<script>alert('xss')</script>" not in html_out
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in html_out
    assert "85.5" in html_out
    assert "92.4%" in html_out
    assert "APPLICATION_BUG" in html_out


def test_pdf_report_generator():
    """Verify PDF generator produces bytes and proper MIME type."""
    analytics_data = {
        "quality_score": 88.0,
        "test_pass_rate": 95.0,
        "total_tests_executed": 100,
        "defect_density_per_endpoint": 0.5,
        "requirement_coverage_percent": 92.0
    }

    content_bytes, mime = PDFReportGenerator.generate_report(
        project_name="Test Project",
        analytics_data=analytics_data
    )

    assert len(content_bytes) > 0
    assert mime in ("application/pdf", "text/html; charset=utf-8")


def test_html_technical_report_full_sections():
    """Verify that Tests Performed, Metrics Checked, and Bugs Found sections render with technical detail."""
    analytics_data = {
        "quality_score": 91.2,
        "test_pass_rate": 98.4,
        "total_tests_executed": 128,
        "passed_tests": 126,
        "failed_tests": 2,
        "flaky_test_count": 0,
        "flaky_ratio_percent": 0.0,
        "defect_density_per_endpoint": 0.12,
        "requirement_coverage_percent": 94.2,
        "mean_execution_time_ms": 142.5,
        "evaluated_metrics_ledger": [
            {
                "metric_name": "Test Suite Pass Rate",
                "measured_value": "98.4%",
                "threshold_target": "≥ 90.0%",
                "status": "COMPLIANT",
                "description": "Ratio of passed synthetic invariant test cases to total executed tests."
            },
            {
                "metric_name": "SSRF Boundary Enforcement",
                "measured_value": "100.0%",
                "threshold_target": "100.0% (Zero private IP egress)",
                "status": "COMPLIANT",
                "description": "Loopback and cloud metadata address egress blocking verified."
            }
        ],
        "executed_tests": [
            {
                "id": "t-1",
                "endpoint": "/api/v1/auth/login",
                "method": "POST",
                "test_type": "AUTHENTICATION_INVARIANT",
                "status_code": 200,
                "execution_time_ms": 115.4,
                "outcome": "PASSED",
                "assertion_failures": []
            },
            {
                "id": "t-2",
                "endpoint": "/api/v1/projects",
                "method": "GET",
                "test_type": "SCHEMA_CONFORMANCE",
                "status_code": 200,
                "execution_time_ms": 42.1,
                "outcome": "PASSED",
                "assertion_failures": []
            }
        ],
        "detailed_bugs_found": [
            {
                "id": "fa-9988",
                "category": "BUSINESS_LOGIC_DEFECT",
                "summary": "State transition race condition on concurrent reservation",
                "error_message": "ReservationConflictError: Overlapping seat allocated",
                "exception_type": "ReservationConflictError",
                "failing_file": "app/services/booking_service.py",
                "failing_line": 142,
                "failing_function": "reserve_seat",
                "fingerprint": "a9f8b2c4e1d3",
                "confidence": 0.96,
                "evidence": [{"seat_id": 42, "user_a": "u-1", "user_b": "u-2"}]
            }
        ],
        "benchmark_summary": {
            "mode": "HYBRID",
            "total_injected_bugs": 50,
            "true_positives": 46,
            "false_positives": 2,
            "true_negatives": 48,
            "false_negatives": 4,
            "recall": 92.0,
            "precision": 95.8,
            "specificity": 96.0,
            "f1_score": 0.939
        }
    }

    html_out = HTMLReportGenerator.generate_report_html(
        project_name="ASTRA Enterprise Core",
        analytics_data=analytics_data,
        report_title="Comprehensive Technical Quality & Defect Audit"
    )

    # 1. Header & KPIs
    assert "ASTRA Enterprise Core" in html_out
    assert "Comprehensive Technical Quality &amp; Defect Audit" in html_out
    assert "91.2" in html_out
    assert "GRADE A" in html_out

    # 2. Metrics Checked Ledger
    assert "Technical Metrics Checked &amp; SLA Ledger" in html_out
    assert "Test Suite Pass Rate" in html_out
    assert "SSRF Boundary Enforcement" in html_out
    assert "COMPLIANT" in html_out

    # 3. Tests Performed Ledger
    assert "Test Execution Ledger (Tests Performed Sample)" in html_out
    assert "/api/v1/auth/login" in html_out
    assert "/api/v1/projects" in html_out
    assert "POST" in html_out
    assert "115.4 ms" in html_out

    # 4. Bugs Found Disclosures
    assert "Technical Defect Disclosures &amp; Root Causes (Bugs Found)" in html_out
    assert "BUSINESS_LOGIC_DEFECT" in html_out
    assert "app/services/booking_service.py:142 in reserve_seat()" in html_out
    assert "ReservationConflictError" in html_out
    assert "96%</strong>" in html_out

    # 5. Benchmark & Security
    assert "Multi-Modal Benchmark Evaluation &amp; Ablation" in html_out
    assert "Zero-Egress SSRF Boundary Guard" in html_out

    # 6. Cryptographic Attestation
    assert "Cryptographic Audit Attestation (SHA-256)" in html_out
