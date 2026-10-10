"""Quality Analytics & Benchmark Service for ASTRA Phase 10.

Executes PostgreSQL aggregation queries across test runs, failure analyses,
flakiness records, regression runs, and CI pipelines to compute near-real-time
quality metrics, and manages benchmark evaluation persistence.
"""

from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import (
    Project,
    TestRun,
    TestResult,
    TestSuite,
    TestCase,
    DiscoveredEndpoint,
    FailureAnalysisModel,
    FlakyTestRecordModel,
    SelectiveExecutionRunModel,
    CIPipelineRunModel,
    BenchmarkRunModel,
    BenchmarkBugResultModel,
    BenchmarkRunStatus,
    QualityReportModel,
)
from engine.analytics.metrics_calculator import MetricsCalculator, QualityScorePolicy
from engine.analytics.trend_aggregator import TrendAggregator
from engine.evaluation.benchmark_runner import BenchmarkRunReport


class AnalyticsService:
    """Computes project software quality metrics and manages benchmark results."""

    @staticmethod
    async def get_project_analytics(
        db: AsyncSession,
        project_id: uuid.UUID,
        time_range: str = "30d",
        policy: Optional[QualityScorePolicy] = None
    ) -> Dict[str, Any]:
        """Calculates project quality KPIs and historical trends."""
        # 1. Date window filtering
        now = datetime.now(timezone.utc)
        start_date = None
        if time_range == "7d":
            start_date = now - timedelta(days=7)
        elif time_range == "30d":
            start_date = now - timedelta(days=30)
        elif time_range == "90d":
            start_date = now - timedelta(days=90)

        # 2. Test Runs & Pass Rate Aggregation
        runs_query = select(TestRun).where(TestRun.project_id == project_id)
        if start_date:
            runs_query = runs_query.where(TestRun.created_at >= start_date)
        runs_query = runs_query.order_by(TestRun.created_at.asc())

        runs_res = await db.execute(runs_query)
        runs = runs_res.scalars().all()

        total_runs_count = len(runs)
        total_tests_executed = sum(r.total_tests for r in runs)
        passed_tests = sum(r.passed_tests for r in runs)
        failed_tests = sum(r.failed_tests for r in runs)
        error_tests = sum(r.error_tests for r in runs)
        total_duration = sum(r.duration_ms for r in runs)

        mean_duration_ms = round(total_duration / max(1, total_runs_count), 1)
        pass_rate = MetricsCalculator.calculate_pass_rate(passed_tests, total_tests_executed)

        # 3. Discovered Endpoints & Requirement Coverage
        ep_query = (
            select(func.count(DiscoveredEndpoint.id))
            .select_from(DiscoveredEndpoint)
            .join(TestSuite, TestSuite.project_id == project_id, isouter=True)
        )
        ep_res = await db.execute(ep_query)
        endpoint_count = ep_res.scalar() or 0
        if endpoint_count == 0:
            endpoint_count = 10  # Baseline normalization

        # Tests count
        tc_query = (
            select(func.count(TestCase.id))
            .select_from(TestCase)
            .join(TestSuite, TestCase.suite_id == TestSuite.id)
            .where(TestSuite.project_id == project_id)
        )
        tc_res = await db.execute(tc_query)
        unique_test_count = tc_res.scalar() or max(1, total_tests_executed)

        requirement_coverage = round(min(100.0, (unique_test_count / max(1, endpoint_count * 3)) * 100.0), 1)

        # 4. Phase 6 Failure Root Causes & Defect Breakdown
        fa_query = (
            select(FailureAnalysisModel.failure_category, func.count(FailureAnalysisModel.id))
            .join(TestRun, FailureAnalysisModel.test_run_id == TestRun.id)
            .where(TestRun.project_id == project_id)
            .group_by(FailureAnalysisModel.failure_category)
        )
        fa_res = await db.execute(fa_query)
        failure_rows = fa_res.all()

        failure_breakdown = []
        color_map = {
            "APPLICATION_BUG": "#ef4444",
            "SERVER_CRASH": "#dc2626",
            "BUSINESS_LOGIC_DEFECT": "#f97316",
            "TEST_SCRIPT_ISSUE": "#f59e0b",
            "SCHEMA_VIOLATION": "#eab308",
            "ENVIRONMENT_ISSUE": "#3b82f6",
            "ENVIRONMENT_FLAKE": "#60a5fa",
            "AUTHENTICATION_DEFECT": "#8b5cf6",
            "TIMEOUT_PERFORMANCE": "#a855f7"
        }

        total_confirmed_bugs = 0
        for category, count in failure_rows:
            cat_name = category.value if hasattr(category, "value") else str(category)
            if "BUG" in cat_name or "CRASH" in cat_name or "BUSINESS_LOGIC" in cat_name:
                total_confirmed_bugs += count
            failure_breakdown.append({
                "category": cat_name,
                "count": count,
                "color": color_map.get(cat_name, "#64748b")
            })

        if not failure_breakdown:
            failure_breakdown = [
                {"category": "APPLICATION_BUG", "count": max(1, failed_tests), "color": "#ef4444"},
                {"category": "TEST_SCRIPT_ISSUE", "count": 0, "color": "#f59e0b"},
                {"category": "ENVIRONMENT_ISSUE", "count": 0, "color": "#3b82f6"}
            ]

        defect_density = MetricsCalculator.calculate_defect_density(
            total_confirmed_bugs if total_confirmed_bugs > 0 else failed_tests,
            float(endpoint_count)
        )

        # 5. Phase 7 Flakiness Telemetry
        flaky_query = (
            select(func.count(FlakyTestRecordModel.id))
            .where(FlakyTestRecordModel.project_id == project_id)
            .where(FlakyTestRecordModel.state.in_(["QUARANTINED", "RECOMMENDED_QUARANTINE"]))
        )
        flaky_res = await db.execute(flaky_query)
        flaky_count = flaky_res.scalar() or 0
        flaky_ratio = MetricsCalculator.calculate_flakiness_ratio(flaky_count, unique_test_count)

        # 6. Phase 8 Selective Regression Telemetry
        reg_query = (
            select(
                func.sum(SelectiveExecutionRunModel.tests_avoided),
                func.avg(SelectiveExecutionRunModel.test_reduction_percent),
                func.sum(SelectiveExecutionRunModel.estimated_time_avoided_ms)
            )
            .join(TestRun, SelectiveExecutionRunModel.test_run_id == TestRun.id)
            .where(TestRun.project_id == project_id)
        )
        reg_res = await db.execute(reg_query)
        reg_row = reg_res.first()
        tests_avoided = reg_row[0] or 0 if reg_row else 0
        avg_reduction_percent = round(reg_row[1] or 0.0, 1) if reg_row else 0.0
        time_saved_ms = reg_row[2] or 0.0 if reg_row else 0.0

        # 7. Phase 9 CI/CD Quality Gate Compliance
        ci_query = (
            select(
                func.count(CIPipelineRunModel.id),
                func.sum(func.case((CIPipelineRunModel.quality_gate_status == "PASSED", 1), else_=0))
            )
            .where(CIPipelineRunModel.project_id == project_id)
        )
        ci_res = await db.execute(ci_query)
        ci_row = ci_res.first()
        total_ci_runs = ci_row[0] or 0 if ci_row else 0
        passed_ci_gates = ci_row[1] or 0 if ci_row else 0
        quality_gate_pass_rate = round((passed_ci_gates / max(1, total_ci_runs)) * 100.0, 1) if total_ci_runs > 0 else 100.0

        # 8. Overall Quality Score
        quality_score = MetricsCalculator.calculate_quality_score(
            pass_rate=pass_rate,
            flaky_ratio=flaky_ratio,
            requirement_coverage=requirement_coverage,
            defect_density=defect_density,
            policy=policy
        )

        # 9. Time-Series Trends
        runs_dicts = [
            {
                "created_at": r.created_at,
                "total_tests": r.total_tests,
                "passed_tests": r.passed_tests,
                "failed_tests": r.failed_tests,
                "duration_ms": r.duration_ms
            }
            for r in runs
        ]
        trend_series = TrendAggregator.aggregate_daily_trends(runs_dicts)

        return {
            "project_id": str(project_id),
            "quality_score": quality_score,
            "test_pass_rate": pass_rate,
            "total_runs": total_runs_count,
            "total_tests_executed": total_tests_executed,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "error_tests": error_tests,
            "mean_execution_time_ms": mean_duration_ms,
            "requirement_coverage_percent": requirement_coverage,
            "flaky_test_count": flaky_count,
            "flaky_ratio_percent": flaky_ratio,
            "defect_density_per_endpoint": defect_density,
            "total_confirmed_bugs": total_confirmed_bugs if total_confirmed_bugs > 0 else failed_tests,
            "regression_telemetry": {
                "tests_avoided_count": tests_avoided,
                "avg_reduction_percent": avg_reduction_percent,
                "estimated_time_saved_ms": time_saved_ms
            },
            "ci_quality_gate": {
                "total_ci_runs": total_ci_runs,
                "passed_gates": passed_ci_gates,
                "pass_rate_percent": quality_gate_pass_rate
            },
            "failure_category_breakdown": failure_breakdown,
            "pass_rate_trend": trend_series
        }

    @staticmethod
    async def get_platform_overview(db: AsyncSession) -> Dict[str, Any]:
        """Calculates platform-wide aggregate metrics across all tracked repositories."""
        projects_res = await db.execute(select(func.count(Project.id)))
        total_projects = projects_res.scalar() or 0

        runs_res = await db.execute(
            select(
                func.count(TestRun.id),
                func.sum(TestRun.total_tests),
                func.sum(TestRun.passed_tests),
                func.sum(TestRun.failed_tests),
                func.avg(TestRun.duration_ms)
            )
        )
        row = runs_res.first()
        total_runs = row[0] or 0 if row else 0
        total_tests = row[1] or 0 if row else 0
        passed_tests = row[2] or 0 if row else 0
        failed_tests = row[3] or 0 if row else 0
        avg_dur = round(row[4] or 0.0, 1) if row else 0.0

        pass_rate = round((passed_tests / max(1, total_tests)) * 100.0, 1)

        return {
            "total_projects": total_projects,
            "total_test_runs": total_runs,
            "total_tests_executed": total_tests,
            "overall_pass_rate": pass_rate,
            "mean_execution_time_ms": avg_dur
        }

    @staticmethod
    async def save_benchmark_run(db: AsyncSession, report: BenchmarkRunReport) -> BenchmarkRunModel:
        """Persists a complete benchmark ablation run and its 50 bug results."""
        run_record = BenchmarkRunModel(
            mode=report.mode,
            benchmark_version=report.benchmark_version,
            catalog_version=report.catalog_version,
            oracle_version=report.oracle_version,
            astra_commit_sha="HEAD",
            seed=report.seed,
            status=BenchmarkRunStatus.COMPLETED,
            total_injected_bugs=report.total_injected_bugs,
            true_positives=report.true_positives,
            false_positives=report.false_positives,
            true_negatives=report.true_negatives,
            false_negatives=report.false_negatives,
            recall=report.recall,
            precision=report.precision,
            specificity=report.specificity,
            f1_score=report.f1_score,
            false_positive_rate=report.false_positive_rate,
            weighted_recall=report.weighted_recall,
            category_coverage=report.category_coverage,
            tests_generated=report.tests_generated,
            tests_executed=report.tests_executed,
            detection_efficiency=report.detection_efficiency,
            time_efficiency=report.time_efficiency,
            generation_time_s=report.generation_time_s,
            execution_time_s=report.execution_time_s,
            cost_usd=report.cost_usd,
            offline_resilient=report.offline_resilient,
            repetition_index=report.repetitions,
            summary_metrics=report.summary_metrics,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(run_record)
        await db.flush()

        for bug_res in report.bug_results:
            item = BenchmarkBugResultModel(
                benchmark_run_id=run_record.id,
                bug_id=bug_res["bug_id"],
                service=bug_res["service"],
                category=bug_res["category"],
                severity=bug_res["severity"],
                is_triggered=bug_res["is_triggered"],
                is_detected=bug_res["is_detected"],
                is_attributed=bug_res["is_attributed"],
                attribution_confidence=bug_res["attribution_confidence"],
                detection_method=bug_res["detection_method"],
                evidence=bug_res["evidence"],
                execution_time_ms=bug_res["execution_time_ms"]
            )
            db.add(item)

        await db.commit()
        await db.refresh(run_record)
        return run_record

    @staticmethod
    async def get_latest_benchmark_matrix(db: AsyncSession) -> List[Dict[str, Any]]:
        """Retrieves the latest ablation benchmark run per operational mode."""
        modes = [
            "MODE_0_BASELINE",
            "MODE_A_RULES",
            "MODE_B_ML",
            "MODE_C_AI",
            "MODE_D_HYBRID"
        ]

        matrix = []
        for m in modes:
            query = (
                select(BenchmarkRunModel)
                .where(BenchmarkRunModel.mode == m)
                .order_by(BenchmarkRunModel.created_at.desc())
                .limit(1)
            )
            res = await db.execute(query)
            run = res.scalar_one_or_none()
            if run:
                matrix.append({
                    "id": str(run.id),
                    "mode": run.mode,
                    "recall": run.recall,
                    "precision": run.precision,
                    "specificity": run.specificity,
                    "f1_score": run.f1_score,
                    "false_positive_rate": run.false_positive_rate,
                    "weighted_recall": run.weighted_recall,
                    "category_coverage": run.category_coverage,
                    "detection_efficiency": run.detection_efficiency,
                    "time_efficiency": run.time_efficiency,
                    "generation_time_s": run.generation_time_s,
                    "execution_time_s": run.execution_time_s,
                    "cost_usd": run.cost_usd,
                    "offline_resilient": run.offline_resilient,
                    "created_at": run.created_at.isoformat()
                })

        return matrix

    @staticmethod
    async def create_quality_report(
        db: AsyncSession,
        project_id: uuid.UUID,
        title: str,
        quality_score: float,
        summary_metrics: Dict[str, Any],
        html_content: str
    ) -> QualityReportModel:
        """Persists a new executive audit report artifact with SHA256 checksum."""
        content_hash = hashlib.sha256(html_content.encode("utf-8")).hexdigest()
        report = QualityReportModel(
            project_id=project_id,
            title=title,
            report_type="EXECUTIVE_QUALITY_AUDIT",
            quality_score=quality_score,
            sha256_hash=content_hash,
            summary_metrics=summary_metrics,
            html_content=html_content
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report

    @staticmethod
    async def list_quality_reports(db: AsyncSession, project_id: uuid.UUID) -> List[QualityReportModel]:
        """Lists generated audit reports for a project."""
        query = (
            select(QualityReportModel)
            .where(QualityReportModel.project_id == project_id)
            .order_by(QualityReportModel.created_at.desc())
        )
        res = await db.execute(query)
        return list(res.scalars().all())
