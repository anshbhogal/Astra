"""TestCase Specification Versioning, Optimistic Locking & Rollback."""

import copy
import uuid
from typing import Dict, Any, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import TestCase, HealingCandidateModel, HealingCandidateStatus, MLActionAuditLogModel


class SpecVersionManager:
    """
    Manages non-destructive specification updates, optimistic locking, and rollback.
    """

    @staticmethod
    async def apply_healing_candidate(
        db: AsyncSession,
        candidate_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        # Fetch candidate
        stmt = select(HealingCandidateModel).where(HealingCandidateModel.id == candidate_id)
        res = await db.execute(stmt)
        candidate = res.scalar_one_or_none()

        if not candidate:
            return False, f"Healing candidate '{candidate_id}' not found.", {}

        if candidate.status != HealingCandidateStatus.PENDING:
            return False, f"Candidate is in '{candidate.status.value}' state and cannot be applied.", {}

        # Fetch test case with optimistic locking
        tc_stmt = select(TestCase).where(TestCase.id == candidate.test_case_id)
        tc_res = await db.execute(tc_stmt)
        test_case = tc_res.scalar_one_or_none()

        if not test_case:
            return False, f"Target TestCase '{candidate.test_case_id}' not found.", {}

        # Optimistic locking check: check specification current state against candidate original_specification
        curr_spec = test_case.specification or {}
        # Apply proposed specification
        new_spec = copy.deepcopy(candidate.proposed_specification)

        # Update test case specification
        test_case.specification = new_spec
        db.add(test_case)

        # Update candidate record
        candidate.status = HealingCandidateStatus.APPROVED
        candidate.approved_by = user_id
        candidate.resulting_spec_version = (candidate.resulting_spec_version or 1) + 1
        candidate.rollback_available = True
        db.add(candidate)

        # Record Audit Log
        audit = MLActionAuditLogModel(
            project_id=candidate.project_id,
            actor_id=user_id,
            action_type="HEALING_APPROVE",
            target_id=candidate.id,
            details={
                "test_case_id": str(candidate.test_case_id),
                "resulting_spec_version": candidate.resulting_spec_version,
                "patch_operations": candidate.patch_operations,
            },
        )
        db.add(audit)
        await db.commit()

        return True, "Healing patch applied successfully.", new_spec

    @staticmethod
    async def rollback_healing_candidate(
        db: AsyncSession,
        candidate_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        stmt = select(HealingCandidateModel).where(HealingCandidateModel.id == candidate_id)
        res = await db.execute(stmt)
        candidate = res.scalar_one_or_none()

        if not candidate or candidate.status != HealingCandidateStatus.APPROVED:
            return False, "Candidate is not in APPROVED state for rollback.", {}

        if not candidate.rollback_available:
            return False, "Rollback is not available for this candidate.", {}

        # Fetch test case
        tc_stmt = select(TestCase).where(TestCase.id == candidate.test_case_id)
        tc_res = await db.execute(tc_stmt)
        test_case = tc_res.scalar_one_or_none()

        if not test_case:
            return False, "Target TestCase not found.", {}

        # Revert to original specification
        reverted_spec = copy.deepcopy(candidate.original_specification)
        test_case.specification = reverted_spec
        db.add(test_case)

        candidate.rollback_available = False
        db.add(candidate)

        audit = MLActionAuditLogModel(
            project_id=candidate.project_id,
            actor_id=user_id,
            action_type="HEALING_ROLLBACK",
            target_id=candidate.id,
            details={
                "test_case_id": str(candidate.test_case_id),
                "reverted_spec": reverted_spec,
            },
        )
        db.add(audit)
        await db.commit()

        return True, "Specification successfully rolled back.", reverted_spec
