"""Human-in-the-Loop Test Healing Engine Orchestrator."""

import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import (
    TestCase, TestResult, FailureAnalysisModel, HealingCandidateModel, HealingCandidateStatus
)
from ml.healing.candidate_generator import CandidateGenerator


class HealingEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_healing_candidates_for_run(
        self,
        project_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> List[HealingCandidateModel]:
        """
        Analyzes all failure analyses for a test run and generates safety-validated HealingCandidate records.
        """
        stmt = (
            select(FailureAnalysisModel, TestCase, TestResult)
            .join(TestCase, TestCase.id == FailureAnalysisModel.test_case_id)
            .join(TestResult, TestResult.id == FailureAnalysisModel.test_result_id)
            .where(
                FailureAnalysisModel.project_id == project_id,
                FailureAnalysisModel.run_id == run_id,
            )
        )

        res = await self.db.execute(stmt)
        records = res.all()

        candidates = []
        for fa, tc, tr in records:
            spec = tc.specification or {}
            resp_data = tr.response_data or {}
            diff_items = fa.diff_items or []

            proposal = CandidateGenerator.generate_candidate(
                test_case_id=str(tc.id),
                failure_analysis_id=str(fa.id),
                source_run_id=str(run_id),
                original_spec=spec,
                actual_response_data=resp_data,
                actual_status_code=tr.status_code,
                failure_category=fa.category,
                diff_items=diff_items,
            )

            if proposal and proposal.is_safe:
                # Create DB Candidate Model
                cand_model = HealingCandidateModel(
                    project_id=project_id,
                    test_case_id=tc.id,
                    failure_analysis_id=fa.id,
                    source_run_id=run_id,
                    original_specification=proposal.original_specification,
                    proposed_specification=proposal.proposed_specification,
                    patch_operations=proposal.patch_operations,
                    confidence=proposal.confidence,
                    status=HealingCandidateStatus.PENDING,
                    resulting_spec_version=1,
                    rollback_available=True,
                )
                self.db.add(cand_model)
                candidates.append(cand_model)

        if candidates:
            await self.db.commit()

        return candidates
