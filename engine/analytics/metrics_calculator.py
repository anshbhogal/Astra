"""Quality Metrics Calculator and Policy Engine for ASTRA Phase 10.

Calculates standardized software quality metrics including:
- Overall Quality Score (0-100) using configurable policy weights
- Pass Rate (%)
- Defect Density (Confirmed defects per KLOC or per endpoint)
- Flakiness Ratio (%)
- Requirement & Endpoint Coverage (%)
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class QualityScorePolicy:
    """Configurable policy defining weight distribution for overall Quality Score calculation."""
    pass_rate_weight: float = 0.40      # Default 40%
    reliability_weight: float = 0.20    # Default 20% (100 - FlakyRatio)
    coverage_weight: float = 0.20       # Default 20% (Requirement Coverage)
    defect_health_weight: float = 0.20  # Default 20% (100 - Confirmed Defect Penalty)

    def __post_init__(self):
        total = self.pass_rate_weight + self.reliability_weight + self.coverage_weight + self.defect_health_weight
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"QualityScorePolicy weights must sum to 1.0, got {total}")


class MetricsCalculator:
    """Pure mathematical formulations for software quality telemetry."""

    DEFAULT_POLICY = QualityScorePolicy()

    @classmethod
    def calculate_quality_score(
        cls,
        pass_rate: float,
        flaky_ratio: float,
        requirement_coverage: float,
        defect_density: float,
        policy: Optional[QualityScorePolicy] = None
    ) -> float:
        """Computes comprehensive project quality score clamped strictly between 0.0 and 100.0."""
        p = policy or cls.DEFAULT_POLICY

        # Components
        pass_comp = max(0.0, min(100.0, pass_rate)) * p.pass_rate_weight
        rel_comp = max(0.0, min(100.0, 100.0 - flaky_ratio)) * p.reliability_weight
        cov_comp = max(0.0, min(100.0, requirement_coverage)) * p.coverage_weight
        
        # Defect health: penalty grows with defect density (e.g. 5 defects per KLOC = 0 score)
        defect_health = max(0.0, min(100.0, 100.0 - (defect_density * 20.0)))
        defect_comp = defect_health * p.defect_health_weight

        total_score = pass_comp + rel_comp + cov_comp + defect_comp
        return round(max(0.0, min(100.0, total_score)), 1)

    @staticmethod
    def calculate_pass_rate(passed: int, total: int) -> float:
        if total <= 0:
            return 100.0
        return round((passed / total) * 100.0, 2)

    @staticmethod
    def calculate_defect_density(defect_count: int, kloc_or_endpoints: float) -> float:
        if kloc_or_endpoints <= 0.0:
            return 0.0
        return round(defect_count / kloc_or_endpoints, 2)

    @staticmethod
    def calculate_flakiness_ratio(flaky_count: int, total_unique_tests: int) -> float:
        if total_unique_tests <= 0:
            return 0.0
        return round((flaky_count / total_unique_tests) * 100.0, 2)
