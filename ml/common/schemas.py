"""ML Common Schemas & Data Contracts."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class RankingStrategy(str, Enum):
    RISK_FIRST = "RISK_FIRST"
    FAST_FEEDBACK = "FAST_FEEDBACK"
    SEVERITY_FIRST = "SEVERITY_FIRST"
    BALANCED = "BALANCED"


@dataclass
class TestFeatureVector:
    sample_id: str
    project_id: str
    test_case_id: str
    test_run_id: str
    commit_sha: Optional[str]
    historical_failure_rate_prev: float = 0.0
    recent_failure_rate_5runs: float = 0.0
    transition_entropy_prev: float = 0.0
    avg_latency_prev_ms: float = 0.0
    latency_std_prev_ms: float = 0.0
    code_churn_score: float = 0.0
    category_severity_weight: float = 0.5
    target_failed: int = 0  # Binary target: 1 if failed, 0 if passed


@dataclass
class PrioritizedItem:
    test_case_id: str
    failure_probability: float
    execution_cost_ms: float
    severity_weight: float
    priority_score: float
    rank_order: int
    strategy: str = "BALANCED"
    rationale: str = ""


@dataclass
class FlakinessEvalResult:
    test_case_id: str
    flakiness_score: float
    observation_count: int
    transition_count: int
    pass_count: int
    fail_count: int
    latency_mean_ms: float
    latency_std_ms: float
    recommend_quarantine: bool
    status: str = "ACTIVE"


@dataclass
class SemanticClusterResult:
    cluster_id: str
    cluster_name: str
    affected_test_ids: List[str]
    member_count: int
    match_precision: str  # EXACT_MATCH, LIKELY_SAME, POSSIBLY_SAME
    representative_failure_id: str
    confidence: float


@dataclass
class HealingPatchProposal:
    test_case_id: str
    failure_analysis_id: str
    source_run_id: str
    original_specification: Dict[str, Any]
    proposed_specification: Dict[str, Any]
    patch_operations: List[Dict[str, Any]]
    confidence: float
    is_safe: bool
    rejection_reason: Optional[str] = None
