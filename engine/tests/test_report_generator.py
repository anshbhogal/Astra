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
