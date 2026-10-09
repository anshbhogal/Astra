"""Dataset Builder querying DB history and building ML DataFrames."""

import uuid
from typing import List, Dict, Any, Optional
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import TestResult, TestCase, TestRun, FailureAnalysisModel
from ml.features.feature_extractor import FeatureExtractor
from ml.dataset.validator import LeakageValidator


class DatasetBuilder:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_project_dataset(self, project_id: uuid.UUID) -> pd.DataFrame:
        """
        Queries all historical TestResult records for a project, joins FailureAnalysisModel category data,
        and constructs a leakage-free feature DataFrame.
        """
        stmt = (
            select(
                TestResult.id.label("result_id"),
                TestResult.test_run_id,
                TestResult.test_case_id,
                TestResult.outcome,
                TestResult.execution_time_ms,
                TestResult.created_at,
                TestRun.project_id,
                FailureAnalysisModel.category,
            )
            .join(TestRun, TestResult.test_run_id == TestRun.id)
            .outerjoin(
                FailureAnalysisModel,
                (FailureAnalysisModel.run_id == TestResult.test_run_id) &
                (FailureAnalysisModel.test_result_id == TestResult.id)
            )
            .where(TestRun.project_id == project_id)
            .order_by(TestResult.created_at.asc())
        )

        res = await self.db.execute(stmt)
        rows = res.mappings().all()

        if not rows:
            return pd.DataFrame()

        history_list = []
        for r in rows:
            history_list.append({
                "result_id": str(r["result_id"]),
                "test_run_id": str(r["test_run_id"]),
                "test_case_id": str(r["test_case_id"]),
                "project_id": str(r["project_id"]),
                "outcome": str(r["outcome"]).split(".")[-1].upper(),  # Convert Enum or str to FAIL/PASS
                "execution_time_ms": float(r["execution_time_ms"] or 100.0),
                "created_at": r["created_at"],
                "category": r["category"] or "UNKNOWN_FAILURE",
                "code_churn": 0.0,
            })

        features_df = FeatureExtractor.extract_features_from_history(history_list)
        if not features_df.empty:
            LeakageValidator.assert_no_data_leakage(features_df)

        return features_df
