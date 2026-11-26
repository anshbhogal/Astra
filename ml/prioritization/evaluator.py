"""
Prioritization Metrics Evaluator (APFD vs Baseline Comparison & Multi-Cycle Experiment).
"""

import json
import math
import os
import random
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np
import pandas as pd
from scipy import stats

from ml.common.metrics import compute_apfd, compute_apfd_distinct_faults, compute_ndcg_at_k
from ml.common.schemas import PrioritizedItem, RankingStrategy
from ml.features.feature_extractor import FeatureExtractor
from ml.prioritization.baseline import HeuristicPrioritizerBaseline
from ml.prioritization.prioritizer import XGBoostTestPrioritizer


class PrioritizationEvaluator:
    @staticmethod
    def evaluate_model_vs_baselines(
        test_df: pd.DataFrame,
        trained_prioritizer: XGBoostTestPrioritizer,
    ) -> Dict[str, Any]:
        """
        Legacy single-slice evaluator comparing XGBoost vs Heuristic and Random.
        """
        if test_df.empty or "target_failed" not in test_df.columns:
            return {"status": "NO_DATA"}

        actual_fails = test_df[test_df["target_failed"] == 1]["test_case_id"].unique().tolist()

        # 1. Model Ranking
        model_rankings = trained_prioritizer.predict_priorities(test_df)
        model_order = [item.test_case_id for item in model_rankings]
        model_apfd = compute_apfd(model_order, actual_fails)

        # 2. Heuristic Baseline Ranking
        heuristic_rankings = HeuristicPrioritizerBaseline.rank_heuristic(test_df)
        heuristic_order = [item.test_case_id for item in heuristic_rankings]
        heuristic_apfd = compute_apfd(heuristic_order, actual_fails)

        # 3. Random Ranking Baseline
        all_test_ids = test_df["test_case_id"].unique().tolist()
        random_order = list(all_test_ids)
        random.seed(42)
        random.shuffle(random_order)
        random_apfd = compute_apfd(random_order, actual_fails)

        # 4. Compute NDCG@10 for model predictions
        predicted_probs = [item.failure_probability for item in model_rankings]
        actual_targets = [1 if item.test_case_id in actual_fails else 0 for item in model_rankings]
        ndcg_10 = compute_ndcg_at_k(actual_targets, predicted_probs, k=10)

        return {
            "model_apfd": float(model_apfd),
            "heuristic_apfd": float(heuristic_apfd),
            "random_apfd": float(random_apfd),
            "ndcg_at_10": float(ndcg_10),
            "total_test_cases": len(all_test_ids),
            "actual_failed_count": len(actual_fails),
            "model_beats_heuristic": bool(model_apfd >= heuristic_apfd),
            "model_beats_random": bool(model_apfd > random_apfd),
        }

    @classmethod
    def run_multicycle_experiment(
        cls,
        history_records: List[Dict[str, Any]],
        test_fault_map: Dict[str, List[str]],
        train_cycles: Tuple[int, int] = (1, 30),
        val_cycles: Tuple[int, int] = (31, 40),
        test_cycles: Tuple[int, int] = (41, 50),
        random_seeds: List[int] = [42, 101, 202, 303, 404, 505, 606, 707, 808, 909],
        model_dir: str = "ml/models",
        output_dir: str = "ml/benchmark_data",
    ) -> Dict[str, Any]:
        """
        Executes a rigorous, leakage-free chronological train/val/test evaluation comparing:
        1. Random Prioritization (10 fixed seeds)
        2. Heuristic Risk-First Prioritization
        3. ASTRA XGBoost Prioritizer
        """
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(model_dir, exist_ok=True)

        # Normalize test_fault_map so all values are sets
        test_fault_map = {
            str(k): set(v) if isinstance(v, (list, tuple, set)) else ({str(v)} if v else set())
            for k, v in test_fault_map.items()
        }

        full_df = pd.DataFrame(history_records)

        # 1. Feature Extraction for Training Set (Cycles 1 to 30)
        train_records = [r for r in history_records if train_cycles[0] <= r["cycle_id"] <= train_cycles[1]]
        train_features_df = FeatureExtractor.extract_features_from_history(train_records)

        # 2. Model Selection & Feature Ablation on Validation Cycles (Cycles 31 to 40)
        # Tests candidate hyperparameter sets and feature ablations on val_cycles strictly before touching test_cycles
        candidate_configs = [
            {
                "config_id": "cfg_shallow",
                "params": {"max_depth": 3, "learning_rate": 0.08, "n_estimators": 60, "subsample": 0.8},
                "features": None,
                "description": "Shallow depth (max_depth=3, n_estimators=60, all features)"
            },
            {
                "config_id": "cfg_standard",
                "params": {"max_depth": 4, "learning_rate": 0.05, "n_estimators": 100, "subsample": 0.8},
                "features": None,
                "description": "Standard configuration (max_depth=4, n_estimators=100, all features)"
            },
            {
                "config_id": "cfg_regularized",
                "params": {"max_depth": 5, "learning_rate": 0.03, "n_estimators": 120, "subsample": 0.7},
                "features": None,
                "description": "Deeper regularized (max_depth=5, n_estimators=120, subsample=0.7, all features)"
            },
            {
                "config_id": "ablation_history_only",
                "params": {"max_depth": 4, "learning_rate": 0.05, "n_estimators": 100, "subsample": 0.8},
                "features": ["recent_failure_rate_5runs", "historical_failure_rate_prev", "transition_entropy_prev"],
                "description": "Feature Ablation: Failure & Transition History Only (3 features)"
            },
            {
                "config_id": "ablation_recent_only",
                "params": {"max_depth": 3, "learning_rate": 0.05, "n_estimators": 80, "subsample": 0.8},
                "features": ["recent_failure_rate_5runs"],
                "description": "Feature Ablation: Recent 5-Run Failure Rate Only (1 feature)"
            },
        ]

        validation_results = []
        for cand in candidate_configs:
            cand_prioritizer = XGBoostTestPrioritizer(model_dir=model_dir)
            cand_prioritizer.train(
                train_features_df,
                hyperparameters=cand["params"],
                feature_columns=cand["features"],
            )

            val_apfds = []
            for v_cycle in range(val_cycles[0], val_cycles[1] + 1):
                hist_up_to_v = [r for r in history_records if r["cycle_id"] <= v_cycle]
                features_v = FeatureExtractor.extract_features_from_history(hist_up_to_v)

                v_cycle_df = features_v[features_v["test_run_id"] == str(v_cycle)].copy()
                if v_cycle_df.empty:
                    v_records = [r for r in history_records if r["cycle_id"] == v_cycle]
                    v_tids = set(r["test_case_id"] for r in v_records)
                    v_cycle_df = features_v[features_v["test_case_id"].isin(v_tids)].tail(len(v_tids)).copy()

                active_v_faults = set()
                for r in [r for r in history_records if r["cycle_id"] == v_cycle]:
                    active_v_faults.update(r.get("detected_faults", []))

                if not active_v_faults:
                    continue

                v_items = cand_prioritizer.predict_priorities(v_cycle_df, strategy=RankingStrategy.RISK_FIRST.value)
                v_order = [item.test_case_id for item in v_items]
                v_eval = compute_apfd_distinct_faults(v_order, test_fault_map, active_v_faults)
                val_apfds.append(v_eval["apfd"])

            mean_val_apfd = float(np.mean(val_apfds)) if val_apfds else 0.0
            std_val_apfd = float(np.std(val_apfds)) if val_apfds else 0.0

            validation_results.append({
                "config_id": cand["config_id"],
                "description": cand["description"],
                "mean_validation_apfd": round(mean_val_apfd, 4),
                "std_validation_apfd": round(std_val_apfd, 4),
                "hyperparameters": cand["params"],
                "feature_columns": cand["features"] if cand["features"] else "all_7_features",
            })

        # Save validation tuning and ablation artifact
        val_df = pd.DataFrame(validation_results)
        val_csv_path = os.path.join(output_dir, "validation_tuning_results.csv")
        val_df.to_csv(val_csv_path, index=False)

        # Select best candidate model based strictly on validation cycles 31-40 APFD
        best_cand = max(validation_results, key=lambda x: x["mean_validation_apfd"])
        selected_cand_def = next(c for c in candidate_configs if c["config_id"] == best_cand["config_id"])

        # 3. Train Selected Winning Model on Training Set
        prioritizer = XGBoostTestPrioritizer(model_dir=model_dir)
        train_result = prioritizer.train(
            train_features_df,
            hyperparameters=selected_cand_def["params"],
            feature_columns=selected_cand_def["features"],
        )
        prioritizer.save_model("benchmark_suite_validated", version="v2.0")

        # 4. Evaluate Across Held-Out Test Cycles (Cycles 41 to 50)
        cycle_results: List[Dict[str, Any]] = []

        # Track cumulative metrics across test cycles
        xgboost_apfds: List[float] = []
        heuristic_apfds: List[float] = []
        random_mean_apfds: List[float] = []

        xgboost_ndcgs: List[float] = []
        heuristic_ndcgs: List[float] = []

        # Time budget detection metrics
        xgboost_budget_25: List[float] = []
        heuristic_budget_25: List[float] = []
        random_budget_25: List[float] = []

        xgboost_budget_50: List[float] = []
        heuristic_budget_50: List[float] = []
        random_budget_50: List[float] = []

        # Cost (ms) to detect 100% of faults
        xgboost_time_to_all_faults: List[float] = []
        heuristic_time_to_all_faults: List[float] = []
        random_time_to_all_faults: List[float] = []

        # Per-service tracking
        per_service_apfd: Dict[str, Dict[str, List[float]]] = {
            s: {"xgboost": [], "heuristic": [], "random": []} for s in ["auth", "banking", "ecommerce", "student"]
        }

        suite_percent_points = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        xgboost_curve: Dict[int, List[float]] = {p: [] for p in suite_percent_points}
        heuristic_curve: Dict[int, List[float]] = {p: [] for p in suite_percent_points}
        random_curve: Dict[int, List[float]] = {p: [] for p in suite_percent_points}

        for cycle_id in range(test_cycles[0], test_cycles[1] + 1):
            # Extract features strictly up to cycle_id using chronological history
            history_up_to_cycle = [r for r in history_records if r["cycle_id"] <= cycle_id]
            features_up_to_cycle = FeatureExtractor.extract_features_from_history(history_up_to_cycle)

            # Current cycle candidate tests
            cycle_features_df = features_up_to_cycle[features_up_to_cycle["test_run_id"] == str(cycle_id)].copy()
            if cycle_features_df.empty:
                cycle_records = [r for r in history_records if r["cycle_id"] == cycle_id]
                cycle_test_ids = set(r["test_case_id"] for r in cycle_records)
                cycle_features_df = features_up_to_cycle[features_up_to_cycle["test_case_id"].isin(cycle_test_ids)].tail(len(cycle_test_ids)).copy()

            # Active ground truth faults in this cycle
            cycle_raw_rows = [r for r in history_records if r["cycle_id"] == cycle_id]
            active_faults_in_cycle: Set[str] = set()
            test_latency_map: Dict[str, float] = {}
            test_service_map: Dict[str, str] = {}
            actual_failed_test_ids: Set[str] = set()

            for r in cycle_raw_rows:
                tid = r["test_case_id"]
                faults = set(r.get("detected_faults", []))
                active_faults_in_cycle.update(faults)
                test_latency_map[tid] = float(r.get("execution_time_ms", 50.0))
                test_service_map[tid] = r.get("service", "unknown")
                if r.get("outcome") == "FAIL":
                    actual_failed_test_ids.add(tid)

            all_cycle_tests = list(cycle_features_df["test_case_id"].unique())
            total_tests = len(all_cycle_tests)
            distinct_faults_count = len(active_faults_in_cycle)

            # Skip cycles where no faults occurred (APFD undefined)
            if distinct_faults_count == 0:
                continue

            total_cycle_cost_ms = sum(test_latency_map.get(t, 50.0) for t in all_cycle_tests)

            # ── 1. Random Prioritization (10 Seeds) ───────────────────────────
            seed_apfds = []
            seed_ndcgs = []
            seed_costs_to_all = []
            seed_b25 = []
            seed_b50 = []

            for seed in random_seeds:
                rnd_order = list(all_cycle_tests)
                rng = random.Random(seed)
                rng.shuffle(rnd_order)

                rnd_eval = compute_apfd_distinct_faults(rnd_order, test_fault_map, active_faults_in_cycle)
                seed_apfds.append(rnd_eval["apfd"])

                rnd_targets = [1 if tid in actual_failed_test_ids else 0 for tid in rnd_order]
                rnd_scores = [total_tests - i for i in range(total_tests)]
                seed_ndcgs.append(compute_ndcg_at_k(rnd_targets, rnd_scores, k=10))

                c_cost, b25_f, b50_f = cls._calc_budget_and_cost(
                    rnd_order, test_fault_map, active_faults_in_cycle, test_latency_map, total_cycle_cost_ms
                )
                seed_costs_to_all.append(c_cost)
                seed_b25.append(b25_f)
                seed_b50.append(b50_f)

            rnd_apfd_mean = float(np.mean(seed_apfds))
            rnd_apfd_std = float(np.std(seed_apfds))
            rnd_ndcg_mean = float(np.mean(seed_ndcgs))
            rnd_cost_mean = float(np.mean(seed_costs_to_all))
            rnd_b25_mean = float(np.mean(seed_b25))
            rnd_b50_mean = float(np.mean(seed_b50))

            random_mean_apfds.append(rnd_apfd_mean)
            random_time_to_all_faults.append(rnd_cost_mean)
            random_budget_25.append(rnd_b25_mean)
            random_budget_50.append(rnd_b50_mean)

            # ── 2. Heuristic Prioritization ───────────────────────────────────
            heuristic_items = HeuristicPrioritizerBaseline.rank_heuristic(
                cycle_features_df, strategy=RankingStrategy.RISK_FIRST.value
            )
            heuristic_order = [item.test_case_id for item in heuristic_items]
            heur_eval = compute_apfd_distinct_faults(heuristic_order, test_fault_map, active_faults_in_cycle)
            heur_apfd = heur_eval["apfd"]
            heuristic_apfds.append(heur_apfd)

            heur_targets = [1 if tid in actual_failed_test_ids else 0 for tid in heuristic_order]
            heur_scores = [item.priority_score for item in heuristic_items]
            heur_ndcg = compute_ndcg_at_k(heur_targets, heur_scores, k=10)
            heuristic_ndcgs.append(heur_ndcg)

            heur_cost, heur_b25, heur_b50 = cls._calc_budget_and_cost(
                heuristic_order, test_fault_map, active_faults_in_cycle, test_latency_map, total_cycle_cost_ms
            )
            heuristic_time_to_all_faults.append(heur_cost)
            heuristic_budget_25.append(heur_b25)
            heuristic_budget_50.append(heur_b50)

            # ── 3. ASTRA XGBoost Prioritizer (Selected Model) ──────────────────
            xgb_items = prioritizer.predict_priorities(
                cycle_features_df, strategy=RankingStrategy.RISK_FIRST.value
            )
            xgb_order = [item.test_case_id for item in xgb_items]
            xgb_eval = compute_apfd_distinct_faults(xgb_order, test_fault_map, active_faults_in_cycle)
            xgb_apfd = xgb_eval["apfd"]
            xgboost_apfds.append(xgb_apfd)

            xgb_targets = [1 if tid in actual_failed_test_ids else 0 for tid in xgb_order]
            xgb_scores = [item.failure_probability for item in xgb_items]
            xgb_ndcg = compute_ndcg_at_k(xgb_targets, xgb_scores, k=10)
            xgboost_ndcgs.append(xgb_ndcg)

            xgb_cost, xgb_b25, xgb_b50 = cls._calc_budget_and_cost(
                xgb_order, test_fault_map, active_faults_in_cycle, test_latency_map, total_cycle_cost_ms
            )
            xgboost_time_to_all_faults.append(xgb_cost)
            xgboost_budget_25.append(xgb_b25)
            xgboost_budget_50.append(xgb_b50)

            # Cumulative fault detection curves
            for pct in suite_percent_points:
                cutoff = max(1, int(total_tests * (pct / 100.0)))
                xgb_subset = xgb_order[:cutoff]
                xgb_detected = set()
                for tid in xgb_subset:
                    xgb_detected.update(test_fault_map.get(tid, set()).intersection(active_faults_in_cycle))
                xgboost_curve[pct].append(len(xgb_detected) / distinct_faults_count * 100.0)

                heur_subset = heuristic_order[:cutoff]
                heur_detected = set()
                for tid in heur_subset:
                    heur_detected.update(test_fault_map.get(tid, set()).intersection(active_faults_in_cycle))
                heuristic_curve[pct].append(len(heur_detected) / distinct_faults_count * 100.0)

                rnd_pct_detected = []
                for seed in random_seeds:
                    rng = random.Random(seed)
                    ro = list(all_cycle_tests)
                    rng.shuffle(ro)
                    ro_sub = ro[:cutoff]
                    r_det = set()
                    for tid in ro_sub:
                        r_det.update(test_fault_map.get(tid, set()).intersection(active_faults_in_cycle))
                    rnd_pct_detected.append(len(r_det) / distinct_faults_count * 100.0)
                random_curve[pct].append(float(np.mean(rnd_pct_detected)))

            # ── Per-Service Tracking (Averaged Across All 10 Random Seeds) ─────
            for service in ["auth", "banking", "ecommerce", "student"]:
                srv_faults = set(f for f in active_faults_in_cycle if f.lower().startswith(f"bug-{service[:4]}"))
                if srv_faults:
                    srv_tests = [t for t in all_cycle_tests if test_service_map.get(t) == service]
                    xgb_srv_order = [t for t in xgb_order if t in srv_tests]
                    heur_srv_order = [t for t in heuristic_order if t in srv_tests]

                    # Fixed: Average random order over all 10 random seeds
                    srv_rnd_seed_apfds = []
                    for s_seed in random_seeds:
                        rnd_srv_order = [t for t in all_cycle_tests if t in srv_tests]
                        random.Random(s_seed).shuffle(rnd_srv_order)
                        srv_eval = compute_apfd_distinct_faults(rnd_srv_order, test_fault_map, srv_faults)
                        srv_rnd_seed_apfds.append(srv_eval["apfd"])

                    per_service_apfd[service]["xgboost"].append(
                        compute_apfd_distinct_faults(xgb_srv_order, test_fault_map, srv_faults)["apfd"]
                    )
                    per_service_apfd[service]["heuristic"].append(
                        compute_apfd_distinct_faults(heur_srv_order, test_fault_map, srv_faults)["apfd"]
                    )
                    per_service_apfd[service]["random"].append(
                        float(np.mean(srv_rnd_seed_apfds))
                    )

            cycle_results.append({
                "cycle_id": cycle_id,
                "distinct_faults": distinct_faults_count,
                "total_tests": total_tests,
                "total_cycle_cost_ms": round(total_cycle_cost_ms, 1),
                "random_apfd_mean": round(rnd_apfd_mean, 4),
                "random_apfd_std": round(rnd_apfd_std, 4),
                "heuristic_apfd": round(heur_apfd, 4),
                "xgboost_apfd": round(xgb_apfd, 4),
                "xgboost_vs_heuristic_apfd_diff": round(xgb_apfd - heur_apfd, 4),
                "xgboost_vs_random_apfd_diff": round(xgb_apfd - rnd_apfd_mean, 4),
                "heuristic_ndcg_10": round(heur_ndcg, 4),
                "xgboost_ndcg_10": round(xgb_ndcg, 4),
                "xgboost_time_to_all_faults_ms": round(xgb_cost, 1),
                "heuristic_time_to_all_faults_ms": round(heur_cost, 1),
                "random_time_to_all_faults_ms": round(rnd_cost_mean, 1),
                "xgboost_faults_at_25pct_budget": round(xgb_b25, 1),
                "heuristic_faults_at_25pct_budget": round(heur_b25, 1),
                "random_faults_at_25pct_budget": round(rnd_b25_mean, 1),
            })

        # Statistical Reliability & Significance Analysis
        # 1. XGBoost vs Heuristic (Paired across 10 test cycles)
        xgb_vs_heur_diffs = [x - h for x, h in zip(xgboost_apfds, heuristic_apfds)]
        t_stat_heur, p_val_heur = stats.ttest_rel(xgboost_apfds, heuristic_apfds)
        try:
            wilc_res_heur = stats.wilcoxon(xgboost_apfds, heuristic_apfds)
            wilc_stat_heur = float(wilc_res_heur.statistic)
            wilc_p_heur = float(wilc_res_heur.pvalue)
        except Exception:
            wilc_stat_heur, wilc_p_heur = None, None

        std_diff_heur = float(np.std(xgb_vs_heur_diffs, ddof=1)) if len(xgb_vs_heur_diffs) > 1 else 0.0
        cohens_d_heur = float(np.mean(xgb_vs_heur_diffs) / std_diff_heur) if std_diff_heur > 0 else 0.0

        # 2. XGBoost vs Random (Paired across 10 test cycles)
        xgb_vs_rnd_diffs = [x - r for x, r in zip(xgboost_apfds, random_mean_apfds)]
        t_stat_rnd, p_val_rnd = stats.ttest_rel(xgboost_apfds, random_mean_apfds)
        try:
            wilc_res_rnd = stats.wilcoxon(xgboost_apfds, random_mean_apfds)
            wilc_stat_rnd = float(wilc_res_rnd.statistic)
            wilc_p_rnd = float(wilc_res_rnd.pvalue)
        except Exception:
            wilc_stat_rnd, wilc_p_rnd = None, None

        std_diff_rnd = float(np.std(xgb_vs_rnd_diffs, ddof=1)) if len(xgb_vs_rnd_diffs) > 1 else 0.0
        cohens_d_rnd = float(np.mean(xgb_vs_rnd_diffs) / std_diff_rnd) if std_diff_rnd > 0 else 0.0

        # Summary statistics across all evaluated test cycles
        valid_cycles_count = len(cycle_results)
        summary = {
            "experiment_version": "v2.0-validated-audit",
            "dataset_nature": "SIMULATED_REPRESENTATIVE_BENCHMARK_HISTORY",
            "execution_times_nature": "SIMULATED_EXECUTION_LATENCIES",
            "ndcg_relevance_nature": "BINARY_FAILED_TEST_RELEVANCE",
            "metric_variant": "penalized_distinct_faults_apfd",
            "evaluation_period": f"Cycles {test_cycles[0]} to {test_cycles[1]}",
            "evaluated_cycles_count": valid_cycles_count,
            "training_samples_count": len(train_features_df),
            "model_algorithm": train_result.get("algorithm", "XGBClassifier"),
            "selected_model_config": best_cand,
            "model_feature_importances": train_result.get("feature_importances", {}),
            "validation_selection_summary": validation_results,

            # APFD Metrics
            "apfd_xgboost_mean": round(float(np.mean(xgboost_apfds)), 4),
            "apfd_xgboost_std": round(float(np.std(xgboost_apfds)), 4),
            "apfd_heuristic_mean": round(float(np.mean(heuristic_apfds)), 4),
            "apfd_heuristic_std": round(float(np.std(heuristic_apfds)), 4),
            "apfd_random_mean": round(float(np.mean(random_mean_apfds)), 4),
            "apfd_random_std": round(float(np.std(random_mean_apfds)), 4),
            "apfd_gain_over_heuristic": round(float(np.mean(xgboost_apfds) - np.mean(heuristic_apfds)), 4),
            "apfd_gain_over_random": round(float(np.mean(xgboost_apfds) - np.mean(random_mean_apfds)), 4),

            # Statistical Significance Tests
            "statistical_significance_tests": {
                "xgboost_vs_heuristic": {
                    "sample_size_cycles": valid_cycles_count,
                    "mean_apfd_difference": round(float(np.mean(xgb_vs_heur_diffs)), 4),
                    "paired_t_statistic": round(float(t_stat_heur), 4) if t_stat_heur is not None else None,
                    "paired_t_p_value": round(float(p_val_heur), 4) if p_val_heur is not None else None,
                    "wilcoxon_statistic": round(float(wilc_stat_heur), 4) if wilc_stat_heur is not None else None,
                    "wilcoxon_p_value": round(float(wilc_p_heur), 4) if wilc_p_heur is not None else None,
                    "cohens_d_effect_size": round(cohens_d_heur, 4),
                    "statistically_significant_alpha_005": bool(p_val_heur is not None and p_val_heur < 0.05),
                },
                "xgboost_vs_random": {
                    "sample_size_cycles": valid_cycles_count,
                    "mean_apfd_difference": round(float(np.mean(xgb_vs_rnd_diffs)), 4),
                    "paired_t_statistic": round(float(t_stat_rnd), 4) if t_stat_rnd is not None else None,
                    "paired_t_p_value": round(float(p_val_rnd), 6) if p_val_rnd is not None else None,
                    "wilcoxon_statistic": round(float(wilc_stat_rnd), 4) if wilc_stat_rnd is not None else None,
                    "wilcoxon_p_value": round(float(wilc_p_rnd), 6) if wilc_p_rnd is not None else None,
                    "cohens_d_effect_size": round(cohens_d_rnd, 4),
                    "statistically_significant_alpha_005": bool(p_val_rnd is not None and p_val_rnd < 0.05),
                }
            },

            # NDCG@10 Metrics (Binary Failed-Test Relevance)
            "ndcg10_xgboost_mean": round(float(np.mean(xgboost_ndcgs)), 4),
            "ndcg10_xgboost_std": round(float(np.std(xgboost_ndcgs)), 4),
            "ndcg10_heuristic_mean": round(float(np.mean(heuristic_ndcgs)), 4),
            "ndcg10_heuristic_std": round(float(np.std(heuristic_ndcgs)), 4),

            # Time to 100% Fault Detection (Latency Cost in ms)
            "cost_ms_to_all_faults_xgboost": round(float(np.mean(xgboost_time_to_all_faults)), 1),
            "cost_ms_to_all_faults_heuristic": round(float(np.mean(heuristic_time_to_all_faults)), 1),
            "cost_ms_to_all_faults_random": round(float(np.mean(random_time_to_all_faults)), 1),
            "time_saved_vs_random_pct": round(
                (np.mean(random_time_to_all_faults) - np.mean(xgboost_time_to_all_faults)) / np.mean(random_time_to_all_faults) * 100.0, 1
            ),
            "time_saved_vs_heuristic_pct": round(
                (np.mean(heuristic_time_to_all_faults) - np.mean(xgboost_time_to_all_faults)) / np.mean(heuristic_time_to_all_faults) * 100.0, 1
            ),

            # Budget Detection Rates (Mean % of active faults found under 25% and 50% time budget)
            "faults_detected_at_25pct_budget": {
                "xgboost": round(float(np.mean(xgboost_budget_25)), 1),
                "heuristic": round(float(np.mean(heuristic_budget_25)), 1),
                "random": round(float(np.mean(random_budget_25)), 1),
            },
            "faults_detected_at_50pct_budget": {
                "xgboost": round(float(np.mean(xgboost_budget_50)), 1),
                "heuristic": round(float(np.mean(heuristic_budget_50)), 1),
                "random": round(float(np.mean(random_budget_50)), 1),
            },

            # Cumulative Fault Detection Curve Points
            "fault_detection_curve": {
                "suite_percent_points": suite_percent_points,
                "xgboost": [round(float(np.mean(xgboost_curve[p])), 1) for p in suite_percent_points],
                "heuristic": [round(float(np.mean(heuristic_curve[p])), 1) for p in suite_percent_points],
                "random": [round(float(np.mean(random_curve[p])), 1) for p in suite_percent_points],
            },

            # Per-Service APFD Breakdown
            "per_service_apfd": {
                s: {
                    "xgboost_mean": round(float(np.mean(per_service_apfd[s]["xgboost"])), 4) if per_service_apfd[s]["xgboost"] else 0.0,
                    "heuristic_mean": round(float(np.mean(per_service_apfd[s]["heuristic"])), 4) if per_service_apfd[s]["heuristic"] else 0.0,
                    "random_mean": round(float(np.mean(per_service_apfd[s]["random"])), 4) if per_service_apfd[s]["random"] else 0.0,
                }
                for s in ["auth", "banking", "ecommerce", "student"]
            }
        }

        # Export cycle-by-cycle CSV
        df_cycles = pd.DataFrame(cycle_results)
        cycle_csv_path = os.path.join(output_dir, "cycle_comparison.csv")
        df_cycles.to_csv(cycle_csv_path, index=False)

        # Export summary JSON
        summary_json_path = os.path.join(output_dir, "evaluation_results.json")
        with open(summary_json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        # Generate standalone SVG visualization
        svg_path = os.path.join(output_dir, "prioritization_evaluation_results.svg")
        cls._generate_svg_visualization(summary, svg_path)

        return summary

    @staticmethod
    def _calc_budget_and_cost(
        ordered_tests: List[str],
        test_fault_map: Dict[str, Any],
        active_faults: Set[str],
        latency_map: Dict[str, float],
        total_cycle_cost_ms: float
    ) -> Tuple[float, float, float]:
        """Calculates cost to detect 100% of faults and % of faults detected under 25% and 50% budget."""
        accum_cost = 0.0
        detected_so_far: Set[str] = set()
        cost_to_all = total_cycle_cost_ms
        found_all = False

        faults_at_25 = 0.0
        faults_at_50 = 0.0
        b25_budget = total_cycle_cost_ms * 0.25
        b50_budget = total_cycle_cost_ms * 0.50

        for tid in ordered_tests:
            test_cost = latency_map.get(tid, 50.0)
            accum_cost += test_cost
            detected_so_far.update(set(test_fault_map.get(tid, [])).intersection(active_faults))

            if not found_all and len(detected_so_far) >= len(active_faults):
                cost_to_all = accum_cost
                found_all = True

            if accum_cost <= b25_budget:
                faults_at_25 = len(detected_so_far) / max(1, len(active_faults)) * 100.0
            if accum_cost <= b50_budget:
                faults_at_50 = len(detected_so_far) / max(1, len(active_faults)) * 100.0

        return cost_to_all, faults_at_25, faults_at_50

    @classmethod
    def _generate_svg_visualization(cls, summary: Dict[str, Any], output_path: str):
        """Generates a clean vector SVG graphic comparing the 3 strategies for report presentation."""
        # SVG dimensions
        width = 880
        height = 480

        # Bar chart metrics
        xgb_apfd = summary["apfd_xgboost_mean"]
        heur_apfd = summary["apfd_heuristic_mean"]
        rnd_apfd = summary["apfd_random_mean"]

        curve = summary["fault_detection_curve"]
        curve_pts = curve["suite_percent_points"]
        xgb_c = curve["xgboost"]
        heur_c = curve["heuristic"]
        rnd_c = curve["random"]

        # Build clean SVG lines
        svg_lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%" style="background:#0f172a; font-family:Inter,system-ui,sans-serif;">',
            '  <!-- Header -->',
            '  <text x="30" y="38" fill="#f8fafc" font-size="20" font-weight="700">ASTRA ML Test Prioritizer — Empirical Benchmark Evaluation</text>',
            f'  <text x="30" y="60" fill="#94a3b8" font-size="12">Evaluated on {summary["evaluated_cycles_count"]} Chronological Test Cycles (4 Microservices, 50 Injected Faults)</text>',
            '',
            '  <!-- Panel 1: APFD Bar Comparison -->',
            '  <rect x="30" y="80" width="380" height="360" rx="8" fill="#1e293b" stroke="#334155" stroke-width="1"/>',
            '  <text x="50" y="112" fill="#e2e8f0" font-size="15" font-weight="600">Average Percentage of Faults Detected (APFD)</text>',
            '  <text x="50" y="130" fill="#94a3b8" font-size="11">Higher score = Earlier fault discovery</text>',
            '',
            '  <!-- Bar 1: Random -->',
            '  <text x="50" y="175" fill="#94a3b8" font-size="13">Random Baseline (10 Seeds)</text>',
            f'  <rect x="50" y="185" width="{rnd_apfd * 300:.1f}" height="28" rx="4" fill="#64748b"/>',
            f'  <text x="{55 + rnd_apfd * 300:.1f}" y="204" fill="#f8fafc" font-size="13" font-weight="600">{rnd_apfd:.4f} (±{summary["apfd_random_std"]:.3f})</text>',
            '',
            '  <!-- Bar 2: Heuristic -->',
            '  <text x="50" y="245" fill="#94a3b8" font-size="13">Deterministic Risk-First Heuristic</text>',
            f'  <rect x="50" y="255" width="{heur_apfd * 300:.1f}" height="28" rx="4" fill="#38bdf8"/>',
            f'  <text x="{55 + heur_apfd * 300:.1f}" y="274" fill="#f8fafc" font-size="13" font-weight="600">{heur_apfd:.4f} (±{summary["apfd_heuristic_std"]:.3f})</text>',
            '',
            '  <!-- Bar 3: XGBoost -->',
            '  <text x="50" y="315" fill="#38bdf8" font-size="13" font-weight="600">ASTRA XGBoost Prioritizer (Ours)</text>',
            f'  <rect x="50" y="325" width="{xgb_apfd * 300:.1f}" height="28" rx="4" fill="#4f46e5"/>',
            f'  <text x="{55 + xgb_apfd * 300:.1f}" y="344" fill="#f8fafc" font-size="13" font-weight="700">{xgb_apfd:.4f} (±{summary["apfd_xgboost_std"]:.3f})</text>',
            '',
            '  <!-- Metrics Callout Box -->',
            '  <rect x="50" y="375" width="340" height="48" rx="6" fill="#0f172a" stroke="#334155" stroke-width="1"/>',
            f'  <text x="65" y="396" fill="#10b981" font-size="13" font-weight="600">APFD Improvement: +{summary["apfd_gain_over_random"]*100:.1f}% vs Random | +{summary["apfd_gain_over_heuristic"]*100:.1f}% vs Heuristic</text>',
            f'  <text x="65" y="412" fill="#94a3b8" font-size="11">Time to 100% faults: {summary["cost_ms_to_all_faults_xgboost"]}ms (XGB) vs {summary["cost_ms_to_all_faults_heuristic"]}ms (Heur)</text>',
            '',
            '  <!-- Panel 2: Fault Detection Cumulative Curve -->',
            '  <rect x="440" y="80" width="410" height="360" rx="8" fill="#1e293b" stroke="#334155" stroke-width="1"/>',
            '  <text x="460" y="112" fill="#e2e8f0" font-size="15" font-weight="600">Cumulative Fault Detection vs Suite Executed</text>',
            '  <text x="460" y="130" fill="#94a3b8" font-size="11">Steeper curve = faster early fault discovery</text>',
            '',
            '  <!-- Curve Axes -->',
            '  <line x1="480" y1="380" x2="810" y2="380" stroke="#475569" stroke-width="1"/>',
            '  <line x1="480" y1="380" x2="480" y2="160" stroke="#475569" stroke-width="1"/>',
            '  <text x="800" y="398" fill="#64748b" font-size="10">100% Tests</text>',
            '  <text x="480" y="398" fill="#64748b" font-size="10">0%</text>',
            '  <text x="450" y="165" fill="#64748b" font-size="10">100%</text>',
            '  <text x="450" y="270" fill="#64748b" font-size="10">50%</text>',
            '  <text x="450" y="380" fill="#64748b" font-size="10">0%</text>',
        ]

        # Draw gridlines & curves
        # X: 480 to 810 (width 330, each 10% is 33px)
        # Y: 380 to 160 (height 220, 100% is 220px, 1% is 2.2px)
        def map_coords(pct_x, pct_y):
            cx = 480 + (pct_x / 100.0) * 330
            cy = 380 - (pct_y / 100.0) * 220
            return f"{cx:.1f},{cy:.1f}"

        rnd_pts_str = " ".join([map_coords(p, y) for p, y in zip(curve_pts, rnd_c)])
        heur_pts_str = " ".join([map_coords(p, y) for p, y in zip(curve_pts, heur_c)])
        xgb_pts_str = " ".join([map_coords(p, y) for p, y in zip(curve_pts, xgb_c)])

        svg_lines.append(f'  <polyline points="480,380 {rnd_pts_str}" fill="none" stroke="#64748b" stroke-width="2" stroke-dasharray="4"/>')
        svg_lines.append(f'  <polyline points="480,380 {heur_pts_str}" fill="none" stroke="#38bdf8" stroke-width="2.5"/>')
        svg_lines.append(f'  <polyline points="480,380 {xgb_pts_str}" fill="none" stroke="#4f46e5" stroke-width="3"/>')

        # Legend
        svg_lines.append('  <!-- Legend -->')
        svg_lines.append('  <circle cx="490" cy="415" r="4" fill="#4f46e5"/>')
        svg_lines.append('  <text x="500" y="418" fill="#e2e8f0" font-size="11">ASTRA XGBoost</text>')
        svg_lines.append('  <circle cx="610" cy="415" r="4" fill="#38bdf8"/>')
        svg_lines.append('  <text x="620" y="418" fill="#e2e8f0" font-size="11">Heuristic Baseline</text>')
        svg_lines.append('  <circle cx="735" cy="415" r="4" fill="#64748b"/>')
        svg_lines.append('  <text x="745" y="418" fill="#e2e8f0" font-size="11">Random (10 Seeds)</text>')

        svg_lines.append('</svg>')

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(svg_lines))
