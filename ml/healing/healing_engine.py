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
        fa_stmt = select(FailureAnalysisModel).where(
            FailureAnalysisModel.project_id == project_id,
            FailureAnalysisModel.run_id == run_id,
        )
        fa_res = await self.db.execute(fa_stmt)
        fa_records = fa_res.scalars().all()

        candidates = []
        for fa in fa_records:
            tc_stmt = select(TestCase).where(TestCase.id == uuid.UUID(fa.test_case_id))
            tc_res = await self.db.execute(tc_stmt)
            tc = tc_res.scalar_one_or_none()

            tr_stmt = select(TestResult).where(TestResult.id == uuid.UUID(fa.test_result_id))
            tr_res = await self.db.execute(tr_stmt)
            tr = tr_res.scalar_one_or_none()

            if not tc or not tr:
                continue

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
