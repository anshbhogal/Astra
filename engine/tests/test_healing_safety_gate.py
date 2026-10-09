"""Unit tests for Human-in-the-Loop Test Spec Healing Safety Gate & Candidate Generator."""

import pytest
from ml.healing.patch_operations import PatchOperationEnforcer
from ml.healing.safety_validator import HealingSafetyValidator
from ml.healing.candidate_generator import CandidateGenerator


def test_patch_operation_enforcer_whitelist_blacklist():
    valid_ops = [
        {"op_type": "REPLACE_EXPECTED_STATUS", "field": "expected_status", "old_value": 200, "new_value": 201},
        {"op_type": "ADD_EXPECTED_HEADER", "field": "x-api-version", "new_value": "v2"},
    ]
    is_valid, violations = PatchOperationEnforcer.validate_patch_operations(valid_ops)
    assert is_valid is True
    assert len(violations) == 0

    forbidden_ops = [
        {"op_type": "REMOVE_AUTH_ASSERTION", "field": "authorization"},
    ]
    is_valid_f, violations_f = PatchOperationEnforcer.validate_patch_operations(forbidden_ops)
    assert is_valid_f is False
    assert any("Forbidden operation" in v for v in violations_f)


def test_safety_validator_server_crash_rejection():
    orig_spec = {"expected_status": 200}
    prop_spec = {"expected_status": 500}
    ops = [{"op_type": "REPLACE_EXPECTED_STATUS"}]

    is_safe, reason = HealingSafetyValidator.validate_healing_candidate(
        orig_spec, prop_spec, ops, failure_category="SERVER_CRASH"
    )
    assert is_safe is False
    assert "SERVER_CRASH" in reason


def test_candidate_generator_valid_status_shift():
    orig_spec = {"expected_status": 200, "expected_headers": {"content-type": "application/json"}}
    proposal = CandidateGenerator.generate_candidate(
        test_case_id="tc_1",
        failure_analysis_id="fa_1",
        source_run_id="run_1",
        original_spec=orig_spec,
        actual_response_data={"status": "created"},
        actual_status_code=201,
        failure_category="CONTRACT_VIOLATION",
        diff_items=[],
    )

    assert proposal is not None
    assert proposal.is_safe is True
    assert proposal.proposed_specification["expected_status"] == 201
    assert proposal.patch_operations[0]["op_type"] == "REPLACE_EXPECTED_STATUS"
