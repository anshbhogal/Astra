"""
Pydantic v2 Schemas for Advanced Test Suite Generation & Generation Jobs.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from engine.generator.strategy import StrategyPreset


class AdvancedSuiteGenerationRequest(BaseModel):
    name: str = Field(default="Advanced Synthetic Suite", description="Human readable name for test suite")
    preset: StrategyPreset = Field(default=StrategyPreset.STANDARD, description="Generation strategy preset")
    include_happy_path: bool = Field(default=True)
    include_boundary_tests: bool = Field(default=True)
    include_missing_required: bool = Field(default=True)
    include_invalid_types: bool = Field(default=True)
    include_format_violations: bool = Field(default=True)
    include_security_probes: bool = Field(default=False, description="Opt-in security safety probes")
    pairwise_strength: int = Field(default=2, ge=1, le=4, description="N-wise combinatorial strength (1, 2, or 3)")
    max_cases_per_endpoint: int = Field(default=20, ge=1, le=100)
    max_total_cases: int = Field(default=500, ge=1, le=5000)
    seed: int = Field(default=42, description="Deterministic seed for reproducible generation")


class GenerationReportResponse(BaseModel):
    generator_version: str = "4.0.0"
    configuration_hash: str
    seed: int
    total_candidates: int
    total_generated: int
    total_deduplicated: int
    total_truncated: int
    breakdown_by_type: Dict[str, int]


class GenerationJobResponse(BaseModel):
    id: str
    project_id: str
    analysis_id: Optional[str] = None
    status: str
    configuration: Dict[str, Any]
    configuration_hash: str
    seed: int
    total_candidates: int
    total_generated: int
    total_deduplicated: int
    total_truncated: int
    generation_report: Dict[str, Any]
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
