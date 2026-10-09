import pytest
from engine.regression.git_diff_parser import FileDiff
from engine.regression.safety_gate import SafetyGate, UnknownImpactCategory


def test_safety_gate_triggers_migration_and_global_util():
    diffs = [
        FileDiff(old_path=None, new_path="backend/app/db/migrations/versions/0008_schema.py", change_type="ADDED"),
        FileDiff(old_path=None, new_path="backend/app/core/auth.py", change_type="MODIFIED"),
    ]
    test_cases = [
        {"id": "tc-1", "name": "test_login", "tags": ["smoke"]},
        {"id": "tc-2", "name": "test_profile", "tags": []},
    ]

    gate = SafetyGate(fallback_to_full_suite_on_trigger=False)
    res = gate.evaluate_safety(diffs, test_cases, targeted_test_ids=set())

    assert res.expansion_triggered is True
    assert UnknownImpactCategory.SCHEMA_OR_MIGRATION_CHANGE in res.triggers
    assert UnknownImpactCategory.GLOBAL_UTILITY_MODIFIED in res.triggers
    assert "tc-1" in res.expanded_test_ids  # Smoke test expanded
