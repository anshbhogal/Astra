"""
TestGenerationStrategy: Presets, options, deterministic seed, and configuration hash.
"""

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any


class StrategyPreset(str, Enum):
    MINIMAL = "MINIMAL"
    STANDARD = "STANDARD"
    THOROUGH = "THOROUGH"
    SECURITY = "SECURITY"
    MAXIMUM = "MAXIMUM"


@dataclass
class TestGenerationStrategy:
    """Configurable generation options for advanced test suite generation."""
    preset: StrategyPreset = StrategyPreset.STANDARD
    include_happy_path: bool = True
    include_boundary_tests: bool = True
    include_missing_required: bool = True
    include_invalid_types: bool = True
    include_format_violations: bool = True
    include_security_probes: bool = False  # Opt-in default OFF
    pairwise_strength: int = 2
    max_cases_per_endpoint: int = 20
    max_total_cases: int = 500
    seed: int = 42

    def compute_configuration_hash(self) -> str:
        """Calculates deterministic SHA256 hash of configuration + seed."""
        raw = {
            "preset": self.preset.value,
            "include_happy_path": self.include_happy_path,
            "include_boundary_tests": self.include_boundary_tests,
            "include_missing_required": self.include_missing_required,
            "include_invalid_types": self.include_invalid_types,
            "include_format_violations": self.include_format_violations,
            "include_security_probes": self.include_security_probes,
            "pairwise_strength": self.pairwise_strength,
            "max_cases_per_endpoint": self.max_cases_per_endpoint,
            "max_total_cases": self.max_total_cases,
            "seed": self.seed
        }
        serialized = json.dumps(raw, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def from_preset(cls, preset: StrategyPreset, **overrides) -> "TestGenerationStrategy":
        """Factory creating strategy config initialized from predefined preset."""
        if preset == StrategyPreset.MINIMAL:
            cfg = cls(
                preset=preset,
                include_happy_path=True,
                include_boundary_tests=False,
                include_missing_required=True,
                include_invalid_types=False,
                include_format_violations=False,
                include_security_probes=False,
                pairwise_strength=1,
                max_cases_per_endpoint=10
            )
        elif preset == StrategyPreset.THOROUGH:
            cfg = cls(
                preset=preset,
                include_happy_path=True,
                include_boundary_tests=True,
                include_missing_required=True,
                include_invalid_types=True,
                include_format_violations=True,
                include_security_probes=False,
                pairwise_strength=2,
                max_cases_per_endpoint=35
            )
        elif preset == StrategyPreset.SECURITY:
            cfg = cls(
                preset=preset,
                include_happy_path=True,
                include_boundary_tests=True,
                include_missing_required=True,
                include_invalid_types=True,
                include_format_violations=True,
                include_security_probes=True,  # Opt-in explicitly enabled
                pairwise_strength=2,
                max_cases_per_endpoint=40
            )
        elif preset == StrategyPreset.MAXIMUM:
            cfg = cls(
                preset=preset,
                include_happy_path=True,
                include_boundary_tests=True,
                include_missing_required=True,
                include_invalid_types=True,
                include_format_violations=True,
                include_security_probes=True,
                pairwise_strength=3,
                max_cases_per_endpoint=100
            )
        else:  # STANDARD
            cfg = cls(preset=StrategyPreset.STANDARD)

        for k, v in overrides.items():
            if hasattr(cfg, k) and v is not None:
                setattr(cfg, k, v)

        return cfg
