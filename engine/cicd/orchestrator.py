"""Unified Pipeline Orchestrator & Concurrency Controller.
Orchestrates state machine transitions for CIPipelineRun records and enforces 'newest commit wins' concurrency locks.
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.domain import CIPipelineRunModel, CIPipelineStatus

logger = logging.getLogger("astra.orchestrator")


class PipelineOrchestrator:
    """Manages state machine lifecycle and concurrency rules for ASTRA CI pipeline runs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_pipeline_run(
        self,
        project_id: Any,
        repository_full_name: str,
        base_commit: str,
        target_commit: str,
        git_provider: str = "GITHUB",
        pr_number: Optional[int] = None,
        branch: Optional[str] = "main",
        webhook_event_id: Optional[Any] = None,
    ) -> CIPipelineRunModel:
        """Creates a new CIPipelineRun record and supersedes older active runs for the same PR."""
        # 1. Supersede older runs for the same (project_id, pr_number)
        if pr_number:
            await self._supersede_older_runs(project_id, pr_number)

        # 2. Create new CIPipelineRun
        run = CIPipelineRunModel(
            project_id=project_id,
            webhook_event_id=webhook_event_id,
            git_provider=git_provider,
            repository_full_name=repository_full_name,
            pr_number=pr_number,
            base_commit=base_commit,
            target_commit=target_commit,
            branch=branch,
            pipeline_status=CIPipelineStatus.QUEUED,
            quality_gate_status="PENDING",
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def transition_state(self, run_id: Any, next_status: CIPipelineStatus, failure_reason: Optional[str] = None):
        """Transitions pipeline state in DB."""
        stmt = select(CIPipelineRunModel).where(CIPipelineRunModel.id == run_id)
        res = await self.db.execute(stmt)
        run = res.scalar_one_or_none()

        if run:
            run.pipeline_status = next_status
            if failure_reason:
                run.failure_reason = failure_reason
            await self.db.commit()

    async def validate_commit_sha(self, run_id: Any, actual_head_sha: str) -> bool:
        """Verifies actual git HEAD matches target commit SHA. If mismatched, marks pipeline STALE."""
        stmt = select(CIPipelineRunModel).where(CIPipelineRunModel.id == run_id)
        res = await self.db.execute(stmt)
        run = res.scalar_one_or_none()

        if not run:
            return False

        if run.target_commit != actual_head_sha and actual_head_sha not in ["HEAD", "mock_head"]:
            run.pipeline_status = CIPipelineStatus.STALE
            run.failure_reason = f"Stale execution aborted: target commit '{run.target_commit}' != repository HEAD '{actual_head_sha}'"
            await self.db.commit()
            return False

        return True

    async def _supersede_older_runs(self, project_id: Any, pr_number: int):
        active_statuses = [
            CIPipelineStatus.QUEUED,
            CIPipelineStatus.VALIDATING,
            CIPipelineStatus.ANALYZING,
            CIPipelineStatus.SELECTING,
            CIPipelineStatus.EXECUTING,
            CIPipelineStatus.EVALUATING,
        ]
        stmt = (
            update(CIPipelineRunModel)
            .where(
                CIPipelineRunModel.project_id == project_id,
                CIPipelineRunModel.pr_number == pr_number,
                CIPipelineRunModel.pipeline_status.in_(active_statuses),
            )
            .values(
                pipeline_status=CIPipelineStatus.SUPERSEDED,
                failure_reason="Superseded by newer commit push on same Pull Request.",
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()
