"""
Multi-Cycle Benchmark Execution Simulator for ASTRA Phase P2 Evaluation.

Simulates 50 sequential repository commits and test execution cycles across all 4 benchmark
microservices (Auth, Banking, Ecommerce, Student) using the 50 ground-truth injected bugs
and negative controls from BenchmarkBugCatalog.

Generates realistic, chronologically ordered execution records with explicit test-to-fault
mappings, code churn, and latency metrics for temporal train/val/test evaluation.
"""

import json
import os
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
import pandas as pd

from benchmark_apps.catalog import BenchmarkBugCatalog, GroundTruthBug, NegativeControl


@dataclass
class SimulatedTestDefinition:
    test_case_id: str
    service: str
    target_bug_ids: Set[str]  # Bugs this test can detect if active
    static_category: str
    is_negative_control: bool
    base_latency_ms: float
    description: str


class BenchmarkSimulator:
    """Simulates 50 chronological execution cycles across benchmark microservices."""

    SERVICES = ["auth", "banking", "ecommerce", "student"]

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        self.bugs = BenchmarkBugCatalog.get_all_bugs()
        self.controls = BenchmarkBugCatalog.get_all_controls()
        self.test_suite: List[SimulatedTestDefinition] = self._build_test_suite()

    def _build_test_suite(self) -> List[SimulatedTestDefinition]:
        """Constructs a deterministic suite of 100 test cases with realistic multi-fault coverage."""
        tests: List[SimulatedTestDefinition] = []

        # 1. Fifty dedicated bug probe tests (one primary probe per bug)
        for bug in self.bugs:
            # Latency varies realistically by service and complexity (15ms - 85ms)
            if bug.service == "auth":
                base_lat = random.uniform(15.0, 45.0)
            elif bug.service == "banking":
                base_lat = random.uniform(25.0, 65.0)
            elif bug.service == "ecommerce":
                base_lat = random.uniform(20.0, 55.0)
            else:  # student
                base_lat = random.uniform(18.0, 50.0)

            # Performance SLA bugs take longer
            if "sla_timeout_exceeded" in bug.detection_signatures:
                base_lat += 90.0

            tests.append(
                SimulatedTestDefinition(
                    test_case_id=f"tc_probe_{bug.bug_id.lower().replace('-', '_')}",
                    service=bug.service,
                    target_bug_ids={bug.bug_id},
                    static_category=bug.category.value,
                    is_negative_control=False,
                    base_latency_ms=round(base_lat, 2),
                    description=f"Probe for {bug.bug_id}: {bug.description[:60]}"
                )
            )

        # 2. Ten compound integration tests detecting multiple related bugs
        # E.g. compound auth test detecting both login backdoor & token crash
        service_bugs = {s: [b for b in self.bugs if b.service == s] for s in self.SERVICES}
        for s in self.SERVICES:
            s_bugs = service_bugs[s]
            if len(s_bugs) >= 4:
                pair_1 = {s_bugs[0].bug_id, s_bugs[1].bug_id}
                pair_2 = {s_bugs[2].bug_id, s_bugs[3].bug_id}
                tests.append(
                    SimulatedTestDefinition(
                        test_case_id=f"tc_compound_{s}_flow_1",
                        service=s,
                        target_bug_ids=pair_1,
                        static_category="BUSINESS_LOGIC",
                        is_negative_control=False,
                        base_latency_ms=round(random.uniform(60.0, 110.0), 2),
                        description=f"Compound workflow test for {s} (targets {sorted(pair_1)})"
                    )
                )
                tests.append(
                    SimulatedTestDefinition(
                        test_case_id=f"tc_compound_{s}_flow_2",
                        service=s,
                        target_bug_ids=pair_2,
                        static_category="DATA_INTEGRITY",
                        is_negative_control=False,
                        base_latency_ms=round(random.uniform(65.0, 120.0), 2),
                        description=f"Compound workflow test for {s} (targets {sorted(pair_2)})"
                    )
                )

        # 3. Forty negative control / regression tests (never detect bugs; always pass)
        for i, ctrl in enumerate(self.controls[:42]):
            tests.append(
                SimulatedTestDefinition(
                    test_case_id=f"tc_control_{ctrl.service}_{ctrl.control_id.lower().replace('-', '_')}",
                    service=ctrl.service,
                    target_bug_ids=set(),
                    static_category="HAPPY_PATH",
                    is_negative_control=True,
                    base_latency_ms=round(random.uniform(12.0, 40.0), 2),
                    description=f"Negative control {ctrl.control_id}: {ctrl.description[:60]}"
                )
            )

        return tests

    def simulate_multicycle_history(self, total_cycles: int = 50) -> Tuple[List[Dict[str, Any]], Dict[int, Set[str]]]:
        """
        Generates 50 sequential execution cycles simulating software repository evolution.

        Returns:
            (raw_history_records, cycle_active_bugs_map)
        """
        random.seed(self.seed)
        start_time = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        all_bug_ids = [b.bug_id for b in self.bugs]

        # Model realistic bug lifecycles:
        # Each bug has an introduction cycle, persistence duration (2-7 commits), and regression chance
        bug_lifecycles = {}
        for b_id in all_bug_ids:
            intro = random.randint(1, 45)
            duration = random.randint(2, 7)
            regresses = random.random() < 0.25  # 25% chance of recurring later
            # Duration spans exactly `duration` cycles via inclusive interval [intro, intro + duration - 1]
            intro_end = min(total_cycles, intro + duration - 1)
            bug_lifecycles[b_id] = {
                "active_spans": [(intro, intro_end)]
            }
            if regresses and intro_end + 3 <= total_cycles:
                re_intro = intro_end + random.randint(3, 8)
                re_duration = random.randint(2, 5)
                re_end = min(total_cycles, re_intro + re_duration - 1)
                bug_lifecycles[b_id]["active_spans"].append((re_intro, re_end))

        history: List[Dict[str, Any]] = []
        cycle_active_bugs: Dict[int, Set[str]] = {}

        for cycle in range(1, total_cycles + 1):
            cycle_time = start_time + timedelta(hours=(cycle - 1) * 4)
            commit_sha = f"c_{cycle:03d}_{random.randint(1000, 9999):x}"

            # Determine which bugs are active in this commit cycle
            active_in_cycle: Set[str] = set()
            for b_id, life in bug_lifecycles.items():
                for start_c, end_c in life["active_spans"]:
                    if start_c <= cycle <= end_c:
                        active_in_cycle.add(b_id)
                        break

            cycle_active_bugs[cycle] = active_in_cycle

            # Model code churn: 1-2 services have code churned in this commit
            churned_services = set(random.sample(self.SERVICES, k=random.randint(1, 2)))

            # Execute all test cases for this cycle
            for test in self.test_suite:
                # Is test service churned in this commit?
                is_churned = test.service in churned_services
                churn_score = round(random.uniform(0.4, 0.95), 2) if is_churned else round(random.uniform(0.0, 0.15), 2)

                # Check if test triggers an active bug
                detected_in_test = test.target_bug_ids.intersection(active_in_cycle)
                outcome = "FAIL" if detected_in_test else "PASS"

                # Latency with slight random jitter (and SLA delay on failures)
                jitter = random.gauss(0.0, 3.0)
                exec_time = max(5.0, test.base_latency_ms + jitter)

                record = {
                    "cycle_id": cycle,
                    "commit_sha": commit_sha,
                    "service": test.service,
                    "test_case_id": test.test_case_id,
                    "outcome": outcome,
                    "execution_time_ms": round(exec_time, 2),
                    "created_at": cycle_time.isoformat(),
                    "category": test.static_category,
                    "static_test_category": test.static_category,
                    "code_churn": churn_score,
                    "detected_faults": sorted(list(detected_in_test)),
                }
                history.append(record)

        return history, cycle_active_bugs

    def export_dataset(
        self,
        output_dir: str = "ml/benchmark_data",
        total_cycles: int = 50
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Saves simulation dataset to JSON and CSV artifacts."""
        os.makedirs(output_dir, exist_ok=True)
        history, active_bugs = self.simulate_multicycle_history(total_cycles=total_cycles)

        json_path = os.path.join(output_dir, "multicycle_execution_history.json")
        csv_path = os.path.join(output_dir, "multicycle_execution_history.csv")
        meta_path = os.path.join(output_dir, "benchmark_metadata.json")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

        df = pd.DataFrame(history)
        df["detected_faults"] = df["detected_faults"].apply(lambda x: ",".join(x))
        df.to_csv(csv_path, index=False)

        # Build test-to-fault static mapping
        test_fault_coverage = {t.test_case_id: sorted(list(t.target_bug_ids)) for t in self.test_suite}

        probe_count = len([t for t in self.test_suite if t.test_case_id.startswith("tc_probe_")])
        compound_count = len([t for t in self.test_suite if t.test_case_id.startswith("tc_compound_")])
        control_count = len([t for t in self.test_suite if t.test_case_id.startswith("tc_control_")])

        metadata = {
            "benchmark_dataset_type": "SIMULATED_REPRESENTATIVE_BENCHMARK_HISTORY",
            "seed": self.seed,
            "total_cycles": total_cycles,
            "total_records": len(history),
            "total_test_cases": len(self.test_suite),
            "composition": {
                "dedicated_bug_probes": probe_count,
                "compound_integration_tests": compound_count,
                "negative_control_tests": control_count,
                "total_suite_size": probe_count + compound_count + control_count,
            },
            "total_ground_truth_bugs": len(self.bugs),
            "bug_persistence_definition": "Inclusive interval [start_commit, end_commit] spanning exactly duration commit cycles",
            "test_to_fault_coverage": test_fault_coverage,
            "temporal_split": {
                "training_cycles": [1, 30],
                "validation_cycles": [31, 40],
                "testing_cycles": [41, 50],
            },
            "cycle_active_fault_counts": {c: len(active_bugs[c]) for c in active_bugs}
        }

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return json_path, csv_path, metadata
