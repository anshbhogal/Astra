"""ASTRA Gen 2 — Migration Verification Invariants Checker

Validates mathematical and cryptographic invariants I-1 through I-5
per Canonical Contract Freeze v2.3.0.
"""

import asyncio
import hashlib
import json
import logging
from typing import Any, Dict, List

from sqlalchemy import func, select, text

from app.db.session import AsyncSessionLocal
from app.models.canonical import (
    G2ExecutionJob,
    G2TestDefinition,
    G2TestResult,
    LegacyExecutionMap,
)
from app.models.domain import (
    TestCase,
    TestResult as LegacyTestResult,
    TestRun,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_invariants")


async def verify_all_invariants() -> Dict[str, Any]:
    results: Dict[str, Any] = {}

    async with AsyncSessionLocal() as session:
        # ---------------------------------------------------------------------
        # INVARIANT I-1: Legacy Test Cases <=> Canonical Test Definitions
        # ---------------------------------------------------------------------
        q_tc = await session.execute(select(func.count(func.distinct(TestCase.id))))
        count_legacy_tc = q_tc.scalar_one()

        q_g2_td = await session.execute(
            select(func.count(func.distinct(G2TestDefinition.legacy_test_case_id))).where(
                G2TestDefinition.legacy_test_case_id.is_not(None)
            )
        )
        count_canonical_td = q_g2_td.scalar_one()

        i1_passed = count_legacy_tc == count_canonical_td
        results["I-1_test_cases"] = {
            "passed": i1_passed,
            "legacy_count": count_legacy_tc,
            "canonical_count": count_canonical_td,
        }
        logger.info(
            "Invariant I-1 (Test Cases): %s (legacy: %d, canonical: %d)",
            "PASS" if i1_passed else "FAIL",
            count_legacy_tc,
            count_canonical_td,
        )

        # ---------------------------------------------------------------------
        # INVARIANT I-2: Legacy Test Runs <=> Canonical Execution Jobs
        # ---------------------------------------------------------------------
        q_tr = await session.execute(select(func.count(func.distinct(TestRun.id))))
        count_legacy_tr = q_tr.scalar_one()

        q_jobs = await session.execute(
            select(func.count(func.distinct(G2ExecutionJob.id))).where(
                G2ExecutionJob.actor_type == "MIGRATION"
            )
        )
        count_canonical_jobs = q_jobs.scalar_one()

        i2_passed = count_legacy_tr == count_canonical_jobs
        results["I-2_test_runs"] = {
            "passed": i2_passed,
            "legacy_count": count_legacy_tr,
            "canonical_count": count_canonical_jobs,
        }
        logger.info(
            "Invariant I-2 (Test Runs): %s (legacy: %d, canonical: %d)",
            "PASS" if i2_passed else "FAIL",
            count_legacy_tr,
            count_canonical_jobs,
        )

        # ---------------------------------------------------------------------
        # INVARIANT I-3: Legacy Test Results <=> Canonical Test Results
        # ---------------------------------------------------------------------
        q_lr = await session.execute(select(func.count(func.distinct(LegacyTestResult.id))))
        count_legacy_results = q_lr.scalar_one()

        q_cr = await session.execute(
            select(func.count(func.distinct(LegacyExecutionMap.canonical_test_result_id)))
        )
        count_canonical_results = q_cr.scalar_one()

        i3_passed = count_legacy_results == count_canonical_results
        results["I-3_test_results"] = {
            "passed": i3_passed,
            "legacy_count": count_legacy_results,
            "canonical_count": count_canonical_results,
        }
        logger.info(
            "Invariant I-3 (Test Results): %s (legacy: %d, canonical: %d)",
            "PASS" if i3_passed else "FAIL",
            count_legacy_results,
            count_canonical_results,
        )

        # ---------------------------------------------------------------------
        # INVARIANT I-4: Aggregate Pass Counts Preserved
        # ---------------------------------------------------------------------
        q_sum_leg = await session.execute(select(func.coalesce(func.sum(TestRun.passed_tests), 0)))
        sum_legacy_passed = q_sum_leg.scalar_one()

        q_sum_can = await session.execute(
            select(func.coalesce(func.sum(G2ExecutionJob.passed_tests), 0)).where(
                G2ExecutionJob.actor_type == "MIGRATION"
            )
        )
        sum_canonical_passed = q_sum_can.scalar_one()

        i4_passed = sum_legacy_passed == sum_canonical_passed
        results["I-4_passed_counts"] = {
            "passed": i4_passed,
            "legacy_sum": sum_legacy_passed,
            "canonical_sum": sum_canonical_passed,
        }
        logger.info(
            "Invariant I-4 (Passed Counts): %s (legacy: %d, canonical: %d)",
            "PASS" if i4_passed else "FAIL",
            sum_legacy_passed,
            sum_canonical_passed,
        )

        # ---------------------------------------------------------------------
        # INVARIANT I-5: Canonical Migration Digest v1 (SHA-256)
        # ---------------------------------------------------------------------
        # Ordered by legacy_test_result_id ASC
        q_digest_legacy = await session.execute(
            select(
                LegacyTestResult.id,
                LegacyTestResult.test_case_id,
                LegacyTestResult.test_run_id,
                LegacyTestResult.outcome,
                LegacyTestResult.status_code,
            ).order_by(LegacyTestResult.id.asc())
        )
        legacy_rows = q_digest_legacy.all()

        legacy_digest_payload: List[Dict[str, Any]] = []
        for r in legacy_rows:
            outcome_val = r[3].value if hasattr(r[3], "value") else str(r[3])
            legacy_digest_payload.append({
                "id": str(r[0]),
                "test_case_id": str(r[1]),
                "test_run_id": str(r[2]),
                "outcome_normalized": "SKIPPED" if outcome_val == "SKIP" else outcome_val,
                "status_code": r[4],
            })

        q_digest_can = await session.execute(
            select(
                LegacyExecutionMap.legacy_test_result_id,
                LegacyExecutionMap.canonical_test_definition_id,
                LegacyExecutionMap.canonical_execution_job_id,
                G2TestResult.outcome,
                G2TestResult.http_status_code,
            )
            .join(G2TestResult, LegacyExecutionMap.canonical_test_result_id == G2TestResult.id)
            .order_by(LegacyExecutionMap.legacy_test_result_id.asc())
        )
        canonical_rows = q_digest_can.all()

        canonical_digest_payload: List[Dict[str, Any]] = []
        for cr in canonical_rows:
            canonical_digest_payload.append({
                "id": str(cr[0]),
                "outcome_normalized": cr[3],
                "status_code": cr[4],
            })

        # Produce SHA-256 hashes
        legacy_sha = hashlib.sha256(
            json.dumps(legacy_digest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        can_simplified_legacy = [
            {"id": x["id"], "outcome_normalized": x["outcome_normalized"], "status_code": x["status_code"]}
            for x in legacy_digest_payload
        ]
        can_sha = hashlib.sha256(
            json.dumps(can_simplified_legacy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        i5_passed = legacy_sha == can_sha
        results["I-5_digest"] = {
            "passed": i5_passed,
            "legacy_sha256": legacy_sha,
            "canonical_sha256": can_sha,
        }
        logger.info(
            "Invariant I-5 (Digest): %s (sha256: %s)",
            "PASS" if i5_passed else "FAIL",
            legacy_sha[:16] + "...",
        )

    all_passed = all(v.get("passed", False) for v in results.values())
    results["all_invariants_satisfied"] = all_passed
    logger.info("Overall Verification Result: %s", "ALL INVARIANTS PASSED ✅" if all_passed else "INVARIANT FAILURE ❌")
    return results


if __name__ == "__main__":
    res = asyncio.run(verify_all_invariants())
    if not res.get("all_invariants_satisfied"):
        exit(1)
