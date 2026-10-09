"""ML Service Layer Orchestrating ML Engines & DB Persistence."""

import uuid
from typing import List, Dict, Any, Optional
import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import (
    Project, TestRun, TestCase, TestResult, FailureAnalysisModel,
    MLModelArtifactModel, FlakyTestRecordModel, TestPriorityRankingModel,
    HealingCandidateModel, FlakyTestStatus, HealingCandidateStatus
)
from ml.dataset.builder import DatasetBuilder
from ml.dataset.temporal_split import TemporalSplitter
from ml.prioritization.prioritizer import XGBoostTestPrioritizer
from ml.flakiness.flakiness_detector import FlakinessDetector
from ml.flakiness.quarantine import QuarantineManager
from ml.clustering.semantic_clusterer import SemanticFailureClusterer
from ml.healing.healing_engine import HealingEngine
from ml.healing.versioning import SpecVersionManager


class MLService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def train_project_prioritization_model(
        self,
        project_id: uuid.UUID,
        version: str = "v1.0",
    ) -> Dict[str, Any]:
        """
        Builds project dataset, performs temporal train/val split, trains XGBoost classifier,
        evaluates metrics, and saves model artifact to DB and disk.
        """
        builder = DatasetBuilder(self.db)
        features_df = await builder.build_project_dataset(project_id)

        if features_df.empty or len(features_df) < 10:
            return {
                "status": "INSUFFICIENT_DATA",
                "message": "Project has fewer than 10 test execution samples.",
                "sample_count": len(features_df),
            }

        train_df, val_df, test_df = TemporalSplitter.split_by_run_chronology(features_df, train_ratio=0.7, val_ratio=0.15)

        prioritizer = XGBoostTestPrioritizer()
        train_res = prioritizer.train(train_df if not train_df.empty else features_df)

        if train_res.get("status") != "TRAINED":
            return train_res

        # Save serialized model artifact to disk
        file_path = prioritizer.save_model(str(project_id), version=version)

        # Register MLModelArtifactModel in DB
        artifact = MLModelArtifactModel(
            project_id=project_id,
            model_name="test_prioritizer_xgboost",
            version=version,
            dataset_version="v1.0",
            algorithm=prioritizer.algorithm,
            hyperparameters={"n_estimators": 100, "max_depth": 4, "learning_rate": 0.05},
            metrics={"sample_count": len(features_df), "train_res": train_res},
            file_path=file_path,
            status="ACTIVE",
        )
        self.db.add(artifact)
        await self.db.commit()

        return {
            "status": "COMPLETED",
            "model_id": str(artifact.id),
            "algorithm": prioritizer.algorithm,
            "file_path": file_path,
            "sample_count": len(features_df),
            "feature_importances": train_res.get("feature_importances", {}),
        }

    async def get_prioritized_test_cases(
        self,
        project_id: uuid.UUID,
        strategy: str = "BALANCED",
    ) -> List[Dict[str, Any]]:
        """
        Generates prioritized test execution ordering for a project using trained model or heuristic fallback.
        """
        builder = DatasetBuilder(self.db)
        features_df = await builder.build_project_dataset(project_id)

        if features_df.empty:
            return []

        # Latest features per test_case_id
        latest_df = features_df.groupby("test_case_id").last().reset_index()

        prioritizer = XGBoostTestPrioritizer()
        prioritizer.load_model(str(project_id), version="v1.0")

        items = prioritizer.predict_priorities(latest_df, strategy=strategy)

        return [
            {
                "test_case_id": item.test_case_id,
                "failure_probability": item.failure_probability,
                "execution_cost_ms": item.execution_cost_ms,
                "severity_weight": item.severity_weight,
                "priority_score": item.priority_score,
                "rank_order": item.rank_order,
                "strategy": item.strategy,
                "rationale": item.rationale,
            }
            for item in items
        ]

    async def evaluate_project_flakiness(self, project_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Evaluates outcome histories across test runs to identify flaky tests and manage quarantine status.
        """
        detector = FlakinessDetector(fi_threshold=0.60)

        # Query latest 10 TestResult outcomes per test case
        stmt = (
            select(TestResult.test_case_id, TestResult.outcome, TestResult.execution_time_ms)
            .join(TestRun, TestRun.id == TestResult.test_run_id)
            .where(TestRun.project_id == project_id)
            .order_by(TestResult.created_at.asc())
        )
        res = await self.db.execute(stmt)
        rows = res.all()

        history_map: Dict[str, List[str]] = {}
        latency_map: Dict[str, List[float]] = {}
        for tc_id, outcome, lat in rows:
            sid = str(tc_id)
            if sid not in history_map:
                history_map[sid] = []
                latency_map[sid] = []
            history_map[sid].append(str(outcome).split(".")[-1].upper())
            latency_map[sid].append(float(lat or 100.0))

        records = []
        for tc_id, outcomes in history_map.items():
            lats = latency_map[tc_id]
            eval_res = detector.evaluate_test_case_flakiness(tc_id, outcomes, lats)

            # Check existing record in DB
            rec_stmt = select(FlakyTestRecordModel).where(
                FlakyTestRecordModel.project_id == project_id,
                FlakyTestRecordModel.test_case_id == uuid.UUID(tc_id)
            )
            rec_res = await self.db.execute(rec_stmt)
            existing = rec_res.scalar_one_or_none()

            if existing:
                existing.flakiness_score = eval_res.flakiness_score
                existing.observation_window = eval_res.observation_count
                existing.transition_count = eval_res.transition_count
                existing.pass_count = eval_res.pass_count
                existing.fail_count = eval_res.fail_count
                existing.latency_mean_ms = eval_res.latency_mean_ms
                existing.latency_std_ms = eval_res.latency_std_ms
                if existing.status == FlakyTestStatus.ACTIVE and eval_res.recommend_quarantine:
                    existing.status = FlakyTestStatus.RECOMMENDED_QUARANTINE
                self.db.add(existing)
                rec_model = existing
            else:
                rec_model = FlakyTestRecordModel(
                    project_id=project_id,
                    test_case_id=uuid.UUID(tc_id),
                    flakiness_score=eval_res.flakiness_score,
                    observation_window=eval_res.observation_count,
                    transition_count=eval_res.transition_count,
                    pass_count=eval_res.pass_count,
                    fail_count=eval_res.fail_count,
                    latency_mean_ms=eval_res.latency_mean_ms,
                    latency_std_ms=eval_res.latency_std_ms,
                    status=FlakyTestStatus.RECOMMENDED_QUARANTINE if eval_res.recommend_quarantine else FlakyTestStatus.ACTIVE,
                )
                self.db.add(rec_model)

            records.append({
                "test_case_id": tc_id,
                "flakiness_score": eval_res.flakiness_score,
                "transition_count": eval_res.transition_count,
                "status": rec_model.status.value,
                "recommend_quarantine": eval_res.recommend_quarantine,
            })

        await self.db.commit()
        return records

    async def toggle_quarantine_status(
        self,
        project_id: uuid.UUID,
        test_case_id: uuid.UUID,
        quarantine: bool,
    ) -> Dict[str, Any]:
        stmt = select(FlakyTestRecordModel).where(
            FlakyTestRecordModel.project_id == project_id,
            FlakyTestRecordModel.test_case_id == test_case_id
        )
        res = await self.db.execute(stmt)
        record = res.scalar_one_or_none()

        if not record:
            record = FlakyTestRecordModel(
                project_id=project_id,
                test_case_id=test_case_id,
                status=FlakyTestStatus.QUARANTINED if quarantine else FlakyTestStatus.ACTIVE
            )
        else:
            record.status = FlakyTestStatus.QUARANTINED if quarantine else FlakyTestStatus.ACTIVE

        self.db.add(record)
        await self.db.commit()
        return {
            "test_case_id": str(test_case_id),
            "status": record.status.value,
            "is_non_blocking": bool(record.status == FlakyTestStatus.QUARANTINED)
        }

    async def cluster_run_failures_semantic(
        self,
        project_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        stmt = select(FailureAnalysisModel).where(
            FailureAnalysisModel.project_id == project_id,
            FailureAnalysisModel.run_id == run_id
        )
        res = await self.db.execute(stmt)
        fa_records = res.scalars().all()

        if not fa_records:
            return []

        input_list = []
        for fa in fa_records:
            input_list.append({
                "result_id": fa.test_result_id,
                "test_case_id": fa.test_case_id,
                "endpoint": fa.endpoint_id or "",
                "error_message": fa.error_message,
                "category": fa.category,
                "fingerprint": fa.fingerprint,
            })

        clusterer = SemanticFailureClusterer()
        results = clusterer.cluster_failures(input_list)

        return [
            {
                "cluster_id": r.cluster_id,
                "cluster_name": r.cluster_name,
                "affected_test_ids": r.affected_test_ids,
                "member_count": r.member_count,
                "match_precision": r.match_precision,
                "representative_failure_id": r.representative_failure_id,
                "confidence": r.confidence,
            }
            for r in results
        ]

    async def generate_healing_candidates(
        self,
        project_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        engine = HealingEngine(self.db)
        candidates = await engine.generate_healing_candidates_for_run(project_id, run_id)
        return [
            {
                "id": str(c.id),
                "test_case_id": str(c.test_case_id),
                "failure_analysis_id": str(c.failure_analysis_id),
                "patch_operations": c.patch_operations,
                "confidence": c.confidence,
                "status": c.status.value,
            }
            for c in candidates
        ]
