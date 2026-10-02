# Phase 7 — Machine Learning Intelligence Module Implementation Guide

> **Module Focus:** Test Prioritization (XGBoost / Random Forest), Flaky Test Detection, TF-IDF + DBSCAN Failure Clustering, Feature Engineering Pipelines, and Offline Model Training Workflows.

---

## 1. Phase Overview & Objectives

Phase 7 introduces machine learning models to Astra to optimize testing efficiency and reduce noise. Rather than running hundreds of tests in arbitrary order or treating every intermittent test failure as a critical bug, Astra uses ML algorithms to **prioritize high-risk tests**, **detect flaky tests**, and **cluster duplicate failure root causes**.

### Key Deliverables
1. **Feature Engineering Pipeline:** Dataset builder computing historical failure rate, code line churn, execution latency variance, component risk, and failure entropy per test case.
2. **Test Prioritization Model (XGBoost):** Predictive model scoring test failure probability to schedule high-risk tests first in CI/CD pipelines.
3. **Flaky Test Detection Model:** Classifier evaluating execution outcome variance (`PASS` -> `FAIL` -> `PASS`) and retry consistency to flag flaky test scripts.
4. **Failure Clustering Engine (DBSCAN / K-Means):** Unsupervised clustering pipeline vectorizing stack traces with TF-IDF and grouping $N$ test failures into $M$ distinct root-cause clusters.
5. **ML Training & Inference API:** Endpoints to train models on historical test run data and fetch real-time prioritization scores.

---

## 2. Technical Stack Specifications

- **ML Frameworks:** `scikit-learn` `1.4+`, `xgboost` `2.0+`.
- **Data Manipulation:** `pandas` `2.2+`, `numpy` `1.26+`.
- **Vectorization & Clustering:** `TfidfVectorizer`, `DBSCAN`, `KMeans` from `sklearn.feature_extraction.text` and `sklearn.cluster`.

---

## 3. Architecture & Data Flow

```text
Historical Test Results & Code Changes
                 │
                 ▼
┌─────────────────────────────────┐
│   Feature Engineering Engine    │ Computes failure rates, churn, latency variance
└────────────────┬────────────────┘
                 ▼
       ┌─────────┴─────────────────────────┬─────────────────────────┐
       ▼                                   ▼                         ▼
┌───────────────┐                  ┌───────────────┐         ┌───────────────┐
│ XGBoost Model │                  │  Flaky Model  │         │ TF-IDF +      │
│ (Prioritized) │                  │ (Oscillations)│         │ DBSCAN        │
└──────┬────────┘                  └──────┬────────┘         └──────┬────────┘
       ▼                                  ▼                         ▼
Ranked Test Suite                 Flaky Test Alerts         Clustered Failures
(Runs high risk tests 1st)        (quarantine candidate)    (Groups 31 fails -> 3 groups)
```

---

## 4. Feature Extraction Engine (`ml/feature_extractor.py`)

```python
import pandas as pd
import numpy as np
from typing import List, Dict, Any

class FeatureExtractor:
    @staticmethod
    def extract_test_features(historical_results: List[Dict[str, Any]]) -> pd.DataFrame:
        """Converts raw database test run history into ML feature vectors."""
        df = pd.DataFrame(historical_results)
        
        # Aggregate features per test_case_id
        features = df.groupby("test_case_id").agg(
            total_runs=("outcome", "count"),
            failure_count=("outcome", lambda x: (x == "FAIL").sum()),
            historical_failure_rate=("outcome", lambda x: (x == "FAIL").mean()),
            avg_execution_time_ms=("execution_time_ms", "mean"),
            std_execution_time_ms=("execution_time_ms", lambda x: np.std(x) if len(x) > 1 else 0.0),
            recent_failure_rate=("outcome", lambda x: (x.tail(5) == "FAIL").mean())
        ).reset_index()

        # Compute Outcome Flakiness Index (Frequency of outcome transitions PASS -> FAIL -> PASS)
        features["flaky_score"] = features.apply(
            lambda row: 1.0 if row["historical_failure_rate"] > 0.1 and row["historical_failure_rate"] < 0.9 and row["std_execution_time_ms"] > 50.0 else 0.0,
            axis=1
        )
        
        return features
```

---

## 5. Test Prioritization Model Engine (`ml/prioritization/prioritizer.py`)

```python
import xgboost as xgb
import numpy as np
import pandas as pd
from typing import List, Dict, Any

class TestPrioritizationModel:
    def __init__(self):
        self.model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            random_state=42
        )
        self.is_trained = False

    def train(self, feature_df: pd.DataFrame):
        X = feature_df[["historical_failure_rate", "avg_execution_time_ms", "std_execution_time_ms", "recent_failure_rate"]]
        y = feature_df["recent_failure_rate"]  # Target: predict likelihood of failure in next run
        
        self.model.fit(X, y)
        self.is_trained = True

    def predict_priorities(self, feature_df: pd.DataFrame) -> List[Dict[str, Any]]:
        if not self.is_trained:
            # Fallback to simple heuristic sorting if model is un-trained
            feature_df["priority_score"] = feature_df["historical_failure_rate"]
        else:
            X = feature_df[["historical_failure_rate", "avg_execution_time_ms", "std_execution_time_ms", "recent_failure_rate"]]
            feature_df["priority_score"] = self.model.predict(X)

        # Sort descending by failure probability
        sorted_df = feature_df.sort_values(by="priority_score", ascending=False)
        
        results = []
        for _, row in sorted_df.iterrows():
            results.append({
                "test_case_id": row["test_case_id"],
                "priority_score": float(np.round(row["priority_score"], 4)),
                "rank_reason": f"Historical failure rate: {row['historical_failure_rate']*100:.1f}%"
            })
        return results
```

---

## 6. TF-IDF + DBSCAN Failure Clustering Engine (`ml/clustering/failure_clusterer.py`)

When 50 tests fail during a single test run, displaying 50 separate bug reports overwhelms QA engineers. DBSCAN clusters failures based on stack trace text similarity:

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
from typing import List, Dict, Any

class FailureClusterer:
    @staticmethod
    def cluster_failures(failures: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not failures:
            return {"clusters": []}

        # Extract text representations (stack traces + error messages)
        texts = [
            f"{f.get('endpoint')} {f.get('error_message', '')} {str(f.get('assertion_failures', ''))}"
            for f in failures
        ]

        # Vectorize using TF-IDF
        vectorizer = TfidfVectorizer(stop_words="english", max_features=500)
        X = vectorizer.fit_transform(texts)

        # Apply DBSCAN clustering
        db = DBSCAN(eps=0.5, min_samples=2, metric="cosine")
        labels = db.fit_predict(X)

        clustered_groups = {}
        for idx, label in enumerate(labels):
            cluster_id = f"Cluster_{label}" if label != -1 else "Unclustered_Outliers"
            if cluster_id not in clustered_groups:
                clustered_groups[cluster_id] = []
            clustered_groups[cluster_id].append(failures[idx]["test_case_id"])

        summary = []
        for group_id, test_ids in clustered_groups.items():
            summary.append({
                "cluster_name": group_id,
                "affected_test_count": len(test_ids),
                "affected_test_ids": test_ids
            })

        return {"clusters": summary}
```

---

## 7. API Controllers (`backend/app/api/v1/ml.py`)

- `POST /ml/train/{project_id}` — Triggers training pipeline on historical test run data; saves serialized XGBoost model artifact to disk.
- `GET /ml/prioritize/{project_id}` — Returns ordered test cases ranked by failure probability score.
- `POST /ml/cluster-failures` — Accepts list of failed test results from a run and returns grouped failure clusters.

---

## 8. Verification & Test Plan

1. **Failure Clustering Verification:**
   - Input 10 failed test results (5 containing `KeyError: user_id` in `auth.py`, 5 containing `httpx.TimeoutException`). Verify DBSCAN groups them into exactly 2 distinct clusters.
2. **Flaky Test Identification Test:**
   - Input synthetic test run history with oscillating outcomes (`PASS, FAIL, PASS, FAIL, PASS`). Verify feature extractor assigns `flaky_score = 1.0`.
3. **XGBoost Model Pipeline Test:**
   - Execute model training script on 200 synthetic historical runs. Verify feature importance weights `historical_failure_rate` as top priority feature and predicts scores between `0.0` and `1.0`.
