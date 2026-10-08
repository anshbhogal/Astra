"""
ASTRA Backend - Phase 6 Analysis Service

Service managing database persistence of failure analysis reports and defect clusters,
correctly retrieving TestCase specifications and TestResult outcome fields.
"""

from typing import List, Optional, Dict, Any
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.domain import FailureAnalysisModel, DefectClusterModel, TestResult, TestCase, TestOutcome
from engine.analysis.root_cause_analyzer import RootCauseAnalyzer
from engine.analysis.fingerprint import FingerprintEngine
from engine.analysis.models import FailureAnalysis, DefectCluster


class FailureAnalysisService:
    """Orchestrates Phase 6 failure diagnosis and DB persistence."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.analyzer = RootCauseAnalyzer()
        self.fingerprint_engine = FingerprintEngine()

    async def analyze_run_failures(
        self,
        project_id: uuid.UUID,
        run_id: uuid.UUID,
        target_commit_sha: Optional[str] = None,
    ) -> List[FailureAnalysisModel]:
        """Analyzes all failed TestResults for a run and persists FailureAnalysisModel records."""
        
        # 1. Fetch failed TestResults joined with TestCase specification
        stmt = (
            select(TestResult, TestCase)
            .join(TestCase, TestResult.test_case_id == TestCase.id)
            .where(
                TestResult.test_run_id == run_id,
                TestResult.outcome.in_([TestOutcome.FAIL, TestOutcome.ERROR, TestOutcome.TIMEOUT])
            )
        )
        res = await self.db.execute(stmt)
        pairs = res.all()

        analyses_to_db: List[FailureAnalysisModel] = []
        domain_analyses: List[FailureAnalysis] = []

        for tr, tc in pairs:
            spec = tc.specification or {}
            exp_status = spec.get("expected_status", 200)
            exp_body = spec.get("expected_body")
            exp_headers = spec.get("expected_headers")
            max_lat = spec.get("max_latency_ms")
            ep_id = str(tc.endpoint_id) if tc.endpoint_id else f"{tr.method} {tr.endpoint}"

            outcome_str = tr.outcome.value if hasattr(tr.outcome, "value") else str(tr.outcome)

            domain_analysis = self.analyzer.analyze(
                test_result_id=str(tr.id),
                test_case_id=str(tc.id),
                expected_status=exp_status,
                actual_status=tr.status_code or 500,
                expected_body=exp_body,
                actual_body=tr.response_data,
                expected_headers=exp_headers,
                actual_headers=None,
                raw_stack_trace=tr.error_message or "",
                raw_logs=str(tr.response_data) if tr.response_data else "",
                endpoint_id=ep_id,
                latency_ms=tr.execution_time_ms,
                max_latency_ms=max_lat,
                execution_result=outcome_str,
                execution_commit_sha=target_commit_sha,
            )
            domain_analyses.append(domain_analysis)

            db_model = FailureAnalysisModel(
                project_id=project_id,
                run_id=run_id,
                test_result_id=domain_analysis.test_result_id,
                test_case_id=domain_analysis.test_case_id,
                endpoint_id=domain_analysis.endpoint_id,
                category=domain_analysis.category.value,
                summary=domain_analysis.summary,
                error_message=domain_analysis.error_message,
                exception_type=domain_analysis.exception_type,
                failing_file=domain_analysis.failing_file,
                failing_line=domain_analysis.failing_line,
                failing_function=domain_analysis.failing_function,
                commit_sha=domain_analysis.commit_sha,
                source_mismatch=domain_analysis.source_mismatch,
                evidence=[e.to_dict() for e in domain_analysis.evidence],
                fault_locations=[f.to_dict() for f in domain_analysis.fault_locations],
                root_cause_candidates=[c.to_dict() for c in domain_analysis.root_cause_candidates],
                diff_items=[d.to_dict() for d in domain_analysis.diff_items],
                parsed_exception=domain_analysis.parsed_exception.to_dict() if domain_analysis.parsed_exception else None,
                fingerprint=domain_analysis.fingerprint,
                classification_confidence=domain_analysis.classification_confidence,
                attribution_confidence=domain_analysis.attribution_confidence,
                root_cause_confidence=domain_analysis.root_cause_confidence,
            )
            self.db.add(db_model)
            analyses_to_db.append(db_model)

        # 2. Defect Clustering Persistence
        if domain_analyses:
            clusters = self.fingerprint_engine.cluster_failures(domain_analyses, run_id=str(run_id))
            for cluster in clusters:
                cl_stmt = select(DefectClusterModel).where(
                    DefectClusterModel.project_id == project_id,
                    DefectClusterModel.fingerprint == cluster.fingerprint
                )
                cl_res = await self.db.execute(cl_stmt)
                existing_cl = cl_res.scalar_one_or_none()

                if existing_cl:
                    existing_cl.occurrence_count += cluster.member_count
                    existing_cl.member_count += cluster.member_count
                    existing_cl.last_seen_run_id = str(run_id)
                else:
                    new_cl = DefectClusterModel(
                        project_id=project_id,
                        fingerprint=cluster.fingerprint,
                        category=cluster.category.value,
                        summary=cluster.summary,
                        representative_failure_id=cluster.representative_failure_id,
                        member_failure_ids=cluster.member_failure_ids,
                        member_count=cluster.member_count,
                        similarity_score=cluster.similarity_score,
                        confidence=cluster.confidence,
                        match_precision=cluster.match_precision.value,
                        occurrence_count=cluster.occurrence_count,
                        first_seen_run_id=str(run_id),
                        last_seen_run_id=str(run_id),
                    )
                    self.db.add(new_cl)

        await self.db.commit()
        return analyses_to_db

    async def get_run_failure_analyses(
        self,
        project_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> List[FailureAnalysisModel]:
        stmt = select(FailureAnalysisModel).where(
            FailureAnalysisModel.project_id == project_id,
            FailureAnalysisModel.run_id == run_id
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_project_defects(
        self,
        project_id: uuid.UUID,
    ) -> List[DefectClusterModel]:
        stmt = select(DefectClusterModel).where(
            DefectClusterModel.project_id == project_id
        ).order_by(DefectClusterModel.occurrence_count.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
