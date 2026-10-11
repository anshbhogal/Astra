"""ASTRA Gen 2 — Idempotent Backfill Runner

Implements batched migration (Phases A through G) from Gen 1 to Gen 2 Canonical tables
per Canonical Contract Freeze v2.3.0.
"""

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from app.db.session import AsyncSessionLocal
from app.models.canonical import (
    G2Build,
    G2Defect,
    G2DefectOccurrence,
    G2Environment,
    G2ExecutionAttempt,
    G2ExecutionJob,
    G2Requirement,
    G2RequirementVersion,
    G2TestDefinition,
    G2TestDefinitionVersion,
    G2TestResult,
    G2TestSuite,
    LegacyExecutionMap,
    Workspace,
)
from app.models.domain import (
    DefectClusterModel,
    FailureAnalysisModel,
    Project,
    TestCase,
    TestResult as LegacyTestResult,
    TestRun,
    TestSuite as LegacyTestSuite,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill_gen2")


def canonical_json_hash(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def run_backfill() -> Dict[str, int]:
    counts: Dict[str, int] = {
        "workspaces_created": 0,
        "projects_attached": 0,
        "suites_migrated": 0,
        "definitions_migrated": 0,
        "environments_created": 0,
        "builds_created": 0,
        "jobs_migrated": 0,
        "results_migrated": 0,
        "defects_migrated": 0,
    }

    async with AsyncSessionLocal() as session:
        # ---------------------------------------------------------------------
        # PHASE A: Workspaces & Project Assignment
        # ---------------------------------------------------------------------
        logger.info("[Phase A] Migrating Workspaces & Project Attachment...")
        q_ws = await session.execute(select(Workspace).where(Workspace.slug == "default-org"))
        default_ws = q_ws.scalar_one_or_none()

        if not default_ws:
            default_ws = Workspace(
                id=uuid.uuid4(),
                name="Default Organization",
                slug="default-org",
                plan_tier="ENTERPRISE",
                settings={"retention_days": 90, "quality_gate_defaults": {"min_pass_rate": 0.95}},
                actor_type="MIGRATION",
            )
            session.add(default_ws)
            await session.flush()
            counts["workspaces_created"] += 1
            logger.info("Created Default Organization workspace %s", default_ws.id)

        # Attach projects
        q_projects = await session.execute(
            select(Project).where(Project.workspace_id.is_(None))
        )
        unattached_projects = q_projects.scalars().all()
        for p in unattached_projects:
            p.workspace_id = default_ws.id
            p.actor_type = "MIGRATION"
            counts["projects_attached"] += 1

        await session.commit()

        # ---------------------------------------------------------------------
        # PHASE B: Test Suites Mirroring
        # ---------------------------------------------------------------------
        logger.info("[Phase B] Mirroring Test Suites...")
        q_legacy_suites = await session.execute(select(LegacyTestSuite))
        legacy_suites = q_legacy_suites.scalars().all()

        suite_project_map: Dict[uuid.UUID, uuid.UUID] = {}
        for s in legacy_suites:
            suite_project_map[s.id] = s.project_id
            q_existing = await session.execute(select(G2TestSuite).where(G2TestSuite.id == s.id))
            if not q_existing.scalar_one_or_none():
                g2_suite = G2TestSuite(
                    id=s.id,
                    project_id=s.project_id,
                    parent_suite_id=None,
                    name=s.name,
                    description=s.description,
                    suite_type="STANDARD",
                    order_index=0,
                    actor_type="MIGRATION",
                    created_at=s.created_at,
                )
                session.add(g2_suite)
                counts["suites_migrated"] += 1

        await session.commit()

        # ---------------------------------------------------------------------
        # PHASE C: Test Cases -> Test Definitions & Versions
        # ---------------------------------------------------------------------
        logger.info("[Phase C] Migrating Test Cases to Canonical Definitions...")
        q_legacy_cases = await session.execute(select(TestCase))
        legacy_cases = q_legacy_cases.scalars().all()

        case_def_map: Dict[uuid.UUID, uuid.UUID] = {}
        case_ver_map: Dict[uuid.UUID, uuid.UUID] = {}

        for tc in legacy_cases:
            q_exist_def = await session.execute(
                select(G2TestDefinition).where(G2TestDefinition.legacy_test_case_id == tc.id)
            )
            existing_def = q_exist_def.scalar_one_or_none()
            if existing_def:
                case_def_map[tc.id] = existing_def.id
                case_ver_map[tc.id] = existing_def.current_version_id
                continue

            project_id = suite_project_map.get(tc.suite_id)
            if not project_id:
                q_p = await session.execute(select(LegacyTestSuite.project_id).where(LegacyTestSuite.id == tc.suite_id))
                project_id = q_p.scalar_one_or_none()

            def_id = uuid.uuid4()
            ver_id = uuid.uuid4()
            test_code = f"TC-API-{str(tc.id)[:8].upper()}"

            spec = tc.specification or {}
            if isinstance(spec, dict) and any(k in spec for k in ("path", "endpoint", "method")):
                coerced_spec = {
                    "schema_version": "http.v1",
                    "adapter": "sandbox_http",
                    "method": spec.get("method", "GET"),
                    "path": spec.get("path") or spec.get("endpoint", "/"),
                    "headers": spec.get("headers", {}),
                    "query": spec.get("query", {}),
                    "body": spec.get("body"),
                    "expected_status": spec.get("expected_status", 200),
                    "assertions": spec.get("assertions", []),
                }
                mig_status = "MIGRATED"
            else:
                coerced_spec = {"schema_version": "unknown.v0", "raw": spec}
                mig_status = "UNSUPPORTED"

            ver_hash = canonical_json_hash(coerced_spec)

            g2_def = G2TestDefinition(
                id=def_id,
                project_id=project_id,
                suite_id=tc.suite_id,
                test_code=test_code,
                category="SYNTHETIC_API",
                execution_type="AUTOMATED",
                priority="MEDIUM",
                status="APPROVED",
                current_version_id=None,
                source_type="MIGRATED",
                legacy_test_case_id=tc.id,
                actor_type="MIGRATION",
            )
            session.add(g2_def)
            await session.flush()

            g2_ver = G2TestDefinitionVersion(
                id=ver_id,
                test_definition_id=def_id,
                version_number=1,
                title=tc.name,
                description=f"Migrated from legacy test case {tc.id}",
                estimated_duration_s=60,
                adapter_type="sandbox_http",
                specification=coerced_spec,
                version_hash=ver_hash,
                is_approved=True,
                migration_status=mig_status,
                migration_notes="Backfilled by ASTRA Gen 2 migration",
            )
            session.add(g2_ver)
            await session.flush()

            g2_def.current_version_id = ver_id
            counts["definitions_migrated"] += 1
            case_def_map[tc.id] = def_id
            case_ver_map[tc.id] = ver_id

        await session.commit()

        # ---------------------------------------------------------------------
        # PHASE D: Environments, Builds & Execution Jobs
        # ---------------------------------------------------------------------
        logger.info("[Phase D] Migrating Environments, Builds & Execution Jobs...")
        q_all_projects = await session.execute(select(Project.id))
        all_project_ids = q_all_projects.scalars().all()

        project_env_map: Dict[uuid.UUID, uuid.UUID] = {}
        project_build_map: Dict[uuid.UUID, uuid.UUID] = {}

        for pid in all_project_ids:
            # Environment
            q_env = await session.execute(
                select(G2Environment).where(
                    G2Environment.project_id == pid, G2Environment.name == "MIGRATION_ENV"
                )
            )
            env = q_env.scalar_one_or_none()
            if not env:
                env = G2Environment(
                    id=uuid.uuid4(),
                    project_id=pid,
                    name="MIGRATION_ENV",
                    env_type="LOCAL",
                    base_url="http://localhost:8000",
                    is_active=True,
                    actor_type="MIGRATION",
                )
                session.add(env)
                counts["environments_created"] += 1
                await session.flush()
            project_env_map[pid] = env.id

            # Build
            q_b = await session.execute(
                select(G2Build).where(
                    G2Build.project_id == pid, G2Build.version_name == "v1.0.0-migration"
                )
            )
            build = q_b.scalar_one_or_none()
            if not build:
                build = G2Build(
                    id=uuid.uuid4(),
                    project_id=pid,
                    version_name="v1.0.0-migration",
                    commit_sha="0000000000000000000000000000000000000000",
                    branch="main",
                    status="REGISTERED",
                    build_metadata={"provenance": "DERIVED_FROM_MIGRATION"},
                    actor_type="MIGRATION",
                )
                session.add(build)
                counts["builds_created"] += 1
                await session.flush()
            project_build_map[pid] = build.id

        await session.commit()

        # Jobs
        q_legacy_runs = await session.execute(select(TestRun))
        legacy_runs = q_legacy_runs.scalars().all()

        run_job_map: Dict[uuid.UUID, uuid.UUID] = {}
        for tr in legacy_runs:
            idempotency_key = f"migrated-run-{tr.id}"
            q_job = await session.execute(
                select(G2ExecutionJob).where(
                    G2ExecutionJob.project_id == tr.project_id,
                    G2ExecutionJob.idempotency_key == idempotency_key,
                )
            )
            job = q_job.scalar_one_or_none()
            if not job:
                status_val = tr.status.value if hasattr(tr.status, "value") else str(tr.status)
                job = G2ExecutionJob(
                    id=uuid.uuid4(),
                    project_id=tr.project_id,
                    idempotency_key=idempotency_key,
                    job_type="AUTOMATED_BATCH",
                    status=status_val,
                    priority=10,
                    total_tests=tr.total_tests,
                    passed_tests=tr.passed_tests,
                    failed_tests=tr.failed_tests,
                    error_tests=tr.error_tests,
                    started_at=tr.started_at,
                    completed_at=tr.completed_at,
                    created_at=tr.created_at,
                    actor_type="MIGRATION",
                )
                session.add(job)
                counts["jobs_migrated"] += 1
                await session.flush()
            run_job_map[tr.id] = job.id

        await session.commit()

        # ---------------------------------------------------------------------
        # PHASE E: Test Results -> Attempts, Canonical Results & Map
        # ---------------------------------------------------------------------
        logger.info("[Phase E] Migrating Test Results & Populating Legacy Map...")
        q_legacy_results = await session.execute(select(LegacyTestResult))
        legacy_results = q_legacy_results.scalars().all()

        for lr in legacy_results:
            q_map = await session.execute(
                select(LegacyExecutionMap).where(
                    LegacyExecutionMap.legacy_test_result_id == lr.id
                )
            )
            if q_map.scalar_one_or_none():
                continue

            job_id = run_job_map.get(lr.test_run_id)
            def_id = case_def_map.get(lr.test_case_id)
            ver_id = case_ver_map.get(lr.test_case_id)

            if not job_id or not def_id or not ver_id:
                logger.warning(
                    "Skipping legacy result %s: missing parent job %s or def %s",
                    lr.id,
                    job_id,
                    def_id,
                )
                continue

            # Project lookup
            q_pr = await session.execute(select(TestRun.project_id).where(TestRun.id == lr.test_run_id))
            pid = q_pr.scalar_one()

            env_id = project_env_map[pid]
            build_id = project_build_map[pid]

            attempt_id = uuid.uuid4()
            result_id = uuid.uuid4()

            attempt = G2ExecutionAttempt(
                id=attempt_id,
                job_id=job_id,
                definition_version_id=ver_id,
                environment_id=env_id,
                build_id=build_id,
                attempt_number=1,
                status="COMPLETED",
                duration_ms=lr.execution_time_ms,
                started_at=lr.created_at,
                completed_at=lr.created_at,
            )
            session.add(attempt)
            await session.flush()

            outcome_str = lr.outcome.value if hasattr(lr.outcome, "value") else str(lr.outcome)
            if outcome_str == "SKIP":
                outcome_str = "SKIPPED"

            adapter_res = {
                "request_data": lr.request_data,
                "response_data": lr.response_data,
            }

            g2_res = G2TestResult(
                id=result_id,
                attempt_id=attempt_id,
                outcome=outcome_str,
                assertion_results=lr.assertion_failures or [],
                http_status_code=lr.status_code,
                http_method=lr.method,
                http_path=lr.endpoint,
                response_body_truncated=lr.response_body_truncated,
                error_message=lr.error_message,
                execution_time_ms=lr.execution_time_ms,
                adapter_result=adapter_res,
                created_at=lr.created_at,
            )
            session.add(g2_res)

            map_entry = LegacyExecutionMap(
                legacy_test_run_id=lr.test_run_id,
                legacy_test_case_id=lr.test_case_id,
                legacy_test_result_id=lr.id,
                canonical_test_definition_id=def_id,
                canonical_version_id=ver_id,
                canonical_execution_job_id=job_id,
                canonical_execution_attempt_id=attempt_id,
                canonical_test_result_id=result_id,
                migration_status="MIGRATED",
            )
            session.add(map_entry)
            counts["results_migrated"] += 1

        await session.commit()

        # ---------------------------------------------------------------------
        # PHASE F & G: Defect Clusters -> Inferred Defects
        # ---------------------------------------------------------------------
        logger.info("[Phase F & G] Migrating Defect Clusters to Inferred Defects...")
        q_clusters = await session.execute(select(DefectClusterModel))
        clusters = q_clusters.scalars().all()

        for c in clusters:
            q_def = await session.execute(
                select(G2Defect).where(
                    G2Defect.project_id == c.project_id,
                    G2Defect.defect_key == f"DEF-{str(c.id)[:8].upper()}",
                )
            )
            if not q_def.scalar_one_or_none():
                g2_defect = G2Defect(
                    id=uuid.uuid4(),
                    project_id=c.project_id,
                    defect_key=f"DEF-{str(c.id)[:8].upper()}",
                    title=f"Inferred Defect: {c.error_category or 'Error'}",
                    description=f"Auto-inferred from cluster {c.fingerprint}. Root cause: {c.sample_error_message or 'N/A'}",
                    severity="MAJOR",
                    priority="P2",
                    status="NEW",
                    fingerprint=c.fingerprint,
                    source="MIGRATED_INFERRED",
                    actor_type="MIGRATION",
                )
                session.add(g2_defect)
                counts["defects_migrated"] += 1

        await session.commit()

    logger.info("Backfill complete! Summary: %s", counts)
    return counts


if __name__ == "__main__":
    asyncio.run(run_backfill())
