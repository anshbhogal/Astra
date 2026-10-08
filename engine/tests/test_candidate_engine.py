"""
Unit tests for Phase 6 Root Cause Candidate Engine
"""

import pytest
from engine.analysis.candidate_engine import RootCauseCandidateEngine
from engine.analysis.models import (
    FailureCategory,
    FailureEvidence,
    EvidenceType,
    FaultLocation,
    ParsedException,
    StackFrame,
    ReasoningType,
)


def test_candidate_engine_insufficient_evidence():
    engine = RootCauseCandidateEngine()
    
    evidence = [
        FailureEvidence(
            evidence_type=EvidenceType.HTTP_STATUS,
            source="http_client",
            description="HTTP 500 Internal Server Error",
        )
    ]
    
    candidates, root_cause_conf = engine.generate_candidates(
        category=FailureCategory.SERVER_CRASH,
        evidence_items=evidence,
        fault_locations=[],
        diff_items=[],
        parsed_exception=None,
    )

    assert len(candidates) == 1
    assert candidates[0].reasoning_type == ReasoningType.INSUFFICIENT_EVIDENCE
    assert root_cause_conf == 0.0


def test_candidate_engine_exception_origin():
    engine = RootCauseCandidateEngine()
    
    evidence = [
        FailureEvidence(
            evidence_type=EvidenceType.STACK_TRACE,
            source="python_parser",
            description="KeyError: 'discount'",
        )
    ]
    fault_locs = [
        FaultLocation(
            file_path="services/orders.py",
            line_number=143,
            function_name="calculate_discount",
            confidence=0.95,
            reason=ReasoningType.EXCEPTION_ORIGIN,
        )
    ]
    parsed = ParsedException(
        exception_type="KeyError",
        message="'discount'",
        frames=[StackFrame(file_path="services/orders.py", line_number=143, function_name="calculate_discount")],
    )

    candidates, root_cause_conf = engine.generate_candidates(
        category=FailureCategory.BUSINESS_LOGIC_DEFECT,
        evidence_items=evidence,
        fault_locations=fault_locs,
        diff_items=[],
        parsed_exception=parsed,
    )

    assert len(candidates) == 1
    assert candidates[0].reasoning_type == ReasoningType.EXCEPTION_ORIGIN
    assert root_cause_conf == 0.95
