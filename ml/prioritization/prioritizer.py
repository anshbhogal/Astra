"""Binary Classification Test Prioritizer (XGBoost / RandomForest)."""

import os
import joblib
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier

from ml.common.schemas import PrioritizedItem, RankingStrategy
from ml.prioritization.baseline import HeuristicPrioritizerBaseline

FEATURE_COLUMNS = [
    "historical_failure_rate_prev",
    "recent_failure_rate_5runs",
    "transition_entropy_prev",
    "avg_latency_prev_ms",
    "latency_std_prev_ms",
    "category_severity_weight",
    "code_churn_score",
]


class XGBoostTestPrioritizer:
    def __init__(self, model_dir: str = "ml/models"):
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)
        self.model: Optional[Any] = None
        self.is_trained: bool = False
        self.algorithm: str = "XGBClassifier"

    def train(self, train_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Trains XGBClassifier or RandomForestClassifier on leakage-free training feature DataFrames.
        """
        if train_df.empty or len(train_df) < 10:
            return {"status": "INSUFFICIENT_DATA", "sample_count": len(train_df)}

        X = train_df[FEATURE_COLUMNS].fillna(0.0)
        y = train_df["target_failed"].astype(int)

        # Require at least one positive and one negative sample
        if len(y.unique()) < 2:
            return {"status": "SINGLE_CLASS_ONLY", "sample_count": len(train_df)}

        try:
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                random_state=42,
                eval_metric="logloss",
            )
            self.model.fit(X, y)
            self.algorithm = "XGBClassifier"
        except Exception:
            # Fallback to RandomForest if XGBoost fails or is missing C libraries
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=4,
                random_state=42,
            )
            self.model.fit(X, y)
            self.algorithm = "RandomForestClassifier"

        self.is_trained = True

        # Extract feature importances
        feature_importances = {}
        if hasattr(self.model, "feature_importances_"):
            for col, imp in zip(FEATURE_COLUMNS, self.model.feature_importances_):
                feature_importances[col] = float(np.round(imp, 4))

        return {
            "status": "TRAINED",
            "algorithm": self.algorithm,
            "sample_count": len(train_df),
            "feature_importances": feature_importances,
        }

    def save_model(self, project_id: str, version: str = "v1.0") -> str:
        """Serializes model weights to disk via joblib."""
        if not self.is_trained or self.model is None:
            raise ValueError("Cannot save un-trained model.")

        file_name = f"prioritizer_{project_id}_{version}.joblib"
        file_path = os.path.join(self.model_dir, file_name)
        joblib.dump({"model": self.model, "algorithm": self.algorithm}, file_path)
        return file_path

    def load_model(self, project_id: str, version: str = "v1.0") -> bool:
        """Loads serialized model artifact from disk."""
        file_name = f"prioritizer_{project_id}_{version}.joblib"
        file_path = os.path.join(self.model_dir, file_name)
        if not os.path.exists(file_path):
            return False

        try:
            data = joblib.load(file_path)
            self.model = data["model"]
            self.algorithm = data.get("algorithm", "XGBClassifier")
            self.is_trained = True
            return True
        except Exception:
            return False

    def predict_priorities(
        self,
        features_df: pd.DataFrame,
        strategy: str = RankingStrategy.BALANCED.value,
    ) -> List[PrioritizedItem]:
        """
        Generates binary classification failure probabilities predict_proba()[:, 1]
        and ranks tests according to the selected strategy. Fallbacks to heuristic if un-trained.
        """
        if features_df.empty:
            return []

        if not self.is_trained or self.model is None:
            return HeuristicPrioritizerBaseline.rank_heuristic(features_df, strategy=strategy)

        X = features_df[FEATURE_COLUMNS].fillna(0.0)

        try:
            probs = self.model.predict_proba(X)[:, 1]
        except Exception:
            return HeuristicPrioritizerBaseline.rank_heuristic(features_df, strategy=strategy)

        items = []
        for idx, row in features_df.reset_index(drop=True).iterrows():
            prob = float(probs[idx])
            cost_ms = max(1.0, float(row.get("avg_latency_prev_ms", 100.0)))
            sev = float(row.get("category_severity_weight", 0.5))

            if strategy == RankingStrategy.RISK_FIRST.value:
                score = prob
                rationale = f"ML {self.algorithm} failure probability {prob*100:.1f}%"
            elif strategy == RankingStrategy.FAST_FEEDBACK.value:
                score = prob / (cost_ms / 1000.0 + 0.1)
                rationale = f"ML probability {prob*100:.1f}% prioritized for fast latency ({cost_ms:.0f}ms)"
            elif strategy == RankingStrategy.SEVERITY_FIRST.value:
                score = prob * sev
                rationale = f"ML probability {prob*100:.1f}% weighted by severity {sev:.2f}"
            else:  # BALANCED
                score = (prob * sev) / (cost_ms / 1000.0 + 0.5)
                rationale = f"ML probability {prob*100:.1f}%, severity {sev:.2f}, latency {cost_ms:.0f}ms"

            items.append({
                "test_case_id": str(row["test_case_id"]),
                "failure_probability": float(np.round(prob, 4)),
                "execution_cost_ms": float(np.round(cost_ms, 2)),
                "severity_weight": float(np.round(sev, 2)),
                "priority_score": float(np.round(score, 4)),
                "strategy": strategy,
                "rationale": rationale,
            })

        items.sort(key=lambda x: x["priority_score"], reverse=True)

        results = []
        for rank, item in enumerate(items, start=1):
            results.append(
                PrioritizedItem(
                    test_case_id=item["test_case_id"],
                    failure_probability=item["failure_probability"],
                    execution_cost_ms=item["execution_cost_ms"],
                    severity_weight=item["severity_weight"],
                    priority_score=item["priority_score"],
                    rank_order=rank,
                    strategy=item["strategy"],
                    rationale=item["rationale"],
                )
            )

        return results
