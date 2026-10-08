"""
Unit tests for Phase 6 Fault Localizer & PKG Integration
"""

import pytest
from engine.analysis.localization import FaultLocalizer
from engine.analysis.models import ParsedException, StackFrame, ReasoningType
from engine.analyzer.knowledge_graph import ProjectKnowledgeGraph


def test_fault_localization_origin_and_caller():
    frames = [
        StackFrame(file_path="services/orders.py", line_number=91, function_name="calculate_discount", is_in_project=True),
        StackFrame(file_path="routes/orders.py", line_number=42, function_name="create_order", is_in_project=True),
    ]
    parsed = ParsedException(
        exception_type="KeyError",
        message="'discount'",
        frames=frames,
    )

    localizer = FaultLocalizer()
    fault_locations, attribution_conf, source_mismatch = localizer.localize(
        parsed_exception=parsed,
        analysis_commit_sha="abc123",
        execution_commit_sha="abc123",
    )

    assert not source_mismatch
    assert len(fault_locations) == 2
    assert fault_locations[0].reason == ReasoningType.EXCEPTION_ORIGIN
    assert fault_locations[0].confidence == 0.95
    assert fault_locations[1].reason == ReasoningType.CALLER_FRAME
    assert fault_locations[1].confidence == 0.75


def test_fault_localization_commit_mismatch():
    frames = [
        StackFrame(file_path="services/orders.py", line_number=91, function_name="calculate_discount", is_in_project=True),
    ]
    parsed = ParsedException(
        exception_type="KeyError",
        message="'discount'",
        frames=frames,
    )

    localizer = FaultLocalizer()
    fault_locations, attribution_conf, source_mismatch = localizer.localize(
        parsed_exception=parsed,
        analysis_commit_sha="abc123",
        execution_commit_sha="def456",  # Mismatch!
    )

    assert source_mismatch
    assert fault_locations[0].confidence == round(0.95 * 0.70, 2)
