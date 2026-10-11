"""
ASTRA Engine - Unit & Integration Tests for Gen 2 Phase 2 (Phase 12) APR

Tests AST Statement Pinpointing, Preconditioned Deterministic Mutators,
Patch Validation, Anti-Tampering, Zero-Observed-Regression Gate, and PR Dispatching.
"""

import pytest
import os
import tempfile
from uuid import uuid4

from engine.repair.ast_pinpointer import ASTPinpointer
from engine.repair.context import (
    FaultLocationSnapshot,
    RepairContext,
    RepairScope,
    compute_candidate_hash,
    compute_sha256_text,
)
from engine.repair.eligibility_policy import RepairEligibilityPolicy
from engine.repair.mutators import (
    BoundaryConditionMutator,
    HTTPExceptionWrapperMutator,
    KeyErrorGuardMutator,
    NullSafetyGuardMutator,
)
from engine.repair.patch_validator import PatchValidator
from engine.repair.pr_dispatcher import AutonomousPRDispatcher
from engine.repair.regression_gate import ZeroObservedRegressionGate
from engine.repair.sandbox_executor import SandboxExecutor
from engine.repair.service import RepairJobService


SAMPLE_PYTHON_CODE = """import os
import sys

def calculate_discount(price, user):
    if price < 0:
        raise ValueError("Price cannot be negative")
    # Faulty attribute dereference
    tier = user.profile.tier
    if tier == "VIP":
        return price * 0.8
    return price
"""


SAMPLE_DICT_CODE = """def parse_order_items(payload):
    items = payload["items"]
    return len(items)
"""


SAMPLE_BOUNDARY_CODE = """def check_index_bounds(items, idx):
    if idx > len(items):
        return items[idx]
    return None
"""


class TestASTPinpointer:
    def test_pinpoint_attribute_statement(self):
        pinpointer = ASTPinpointer()
        ctx = pinpointer.pinpoint(SAMPLE_PYTHON_CODE, "services/billing.py", target_line=8)
        assert ctx is not None
        assert ctx.file_path == "services/billing.py"
        assert ctx.enclosing_function_name == "calculate_discount"
        assert ctx.start_line == 8
        assert "user.profile.tier" in ctx.statement_snippet
        assert "price" in ctx.local_variable_names
        assert "user" in ctx.local_variable_names
        assert "os" in ctx.imported_symbols
        assert ctx.source_ast_hash is not None

    def test_pinpoint_invalid_syntax_returns_none(self):
        pinpointer = ASTPinpointer()
        ctx = pinpointer.pinpoint("def broken(: syntax", "bad.py", target_line=1)
        assert ctx is None


class TestRepairEligibilityPolicy:
    def test_eligible_application_file(self):
        eligible, reason = RepairEligibilityPolicy.evaluate("MAJOR", "app/services/order.py")
        assert eligible is True
        assert reason == "ELIGIBLE"

    def test_ineligible_critical_severity(self):
        eligible, reason = RepairEligibilityPolicy.evaluate("CRITICAL", "app/services/order.py")
        assert eligible is False
        assert "CRITICAL" in reason

    def test_ineligible_auth_path(self):
        eligible, reason = RepairEligibilityPolicy.evaluate("MAJOR", "app/api/auth_controller.py")
        assert eligible is False
        assert "security" in reason.lower() or "forbidden" in reason.lower()

    def test_ineligible_docker_path(self):
        eligible, reason = RepairEligibilityPolicy.evaluate("MAJOR", "docker/start.py")
        assert eligible is False

    def test_ineligible_exception_type(self):
        eligible, reason = RepairEligibilityPolicy.evaluate(
            "MAJOR", "app/services/user.py", exception_type="AuthenticationError"
        )
        assert eligible is False
        assert "auth" in reason.lower()


class TestPatchValidator:
    def test_valid_patch_passes(self):
        pinpointer = ASTPinpointer()
        ctx = pinpointer.pinpoint(SAMPLE_DICT_CODE, "app/order.py", target_line=2)
        assert ctx is not None

        diff = (
            "--- a/app/order.py\n"
            "+++ b/app/order.py\n"
            "@@ -2,1 +2,1 @@\n"
            "-    items = payload[\"items\"]\n"
            "+    items = payload.get(\"items\", [])\n"
        )
        res = PatchValidator.validate(diff, SAMPLE_DICT_CODE, ctx, "c0ffee")
        assert res.is_valid is True
        assert res.syntax_valid is True
        assert res.candidate_hash is not None
        assert res.scope == RepairScope.SCOPE_1

    def test_anti_tampering_rejects_test_suite_edits(self):
        pinpointer = ASTPinpointer()
        ctx = pinpointer.pinpoint(SAMPLE_DICT_CODE, "tests/test_order.py", target_line=2)
        assert ctx is not None

        diff = (
            "--- a/tests/test_order.py\n"
            "+++ b/tests/test_order.py\n"
            "@@ -2,1 +2,1 @@\n"
            "-    assert res == 200\n"
            "+    assert True\n"
        )
        res = PatchValidator.validate(diff, SAMPLE_DICT_CODE, ctx, "c0ffee")
        assert res.is_valid is False
        assert "Anti-tampering violation" in res.rejection_reason

    def test_no_op_whitespace_rejected(self):
        pinpointer = ASTPinpointer()
        ctx = pinpointer.pinpoint(SAMPLE_DICT_CODE, "app/order.py", target_line=2)
        assert ctx is not None

        diff = (
            "--- a/app/order.py\n"
            "+++ b/app/order.py\n"
            "@@ -2,1 +2,1 @@\n"
            "-    items = payload[\"items\"]\n"
            "+    items = payload[\"items\"]  \n"
        )
        res = PatchValidator.validate(diff, SAMPLE_DICT_CODE, ctx, "c0ffee")
        assert res.is_valid is False
        assert "No-op" in res.rejection_reason

    def test_no_op_comment_only_rejected(self):
        pinpointer = ASTPinpointer()
        ctx = pinpointer.pinpoint(SAMPLE_DICT_CODE, "app/order.py", target_line=2)
        assert ctx is not None

        diff = (
            "--- a/app/order.py\n"
            "+++ b/app/order.py\n"
            "@@ -2,1 +2,1 @@\n"
            "-    items = payload[\"items\"]\n"
            "+    # just a comment\n"
        )
        res = PatchValidator.validate(diff, SAMPLE_DICT_CODE, ctx, "c0ffee")
        assert res.is_valid is False


class TestDeterministicMutators:
    def test_null_safety_guard_mutator(self):
        mutator = NullSafetyGuardMutator()
        pinpointer = ASTPinpointer()
        ctx = pinpointer.pinpoint(SAMPLE_PYTHON_CODE, "app/billing.py", target_line=8)
        assert ctx is not None

        can_mutate = mutator.can_mutate(ctx, "AttributeError", "'NoneType' object has no attribute 'tier'")
        assert can_mutate is True

        patches = mutator.generate_patches(ctx, SAMPLE_PYTHON_CODE)
        assert len(patches) > 0
        assert any("is None" in p or "if user is not None" in p for p in patches)

    def test_key_error_guard_mutator(self):
        mutator = KeyErrorGuardMutator()
        pinpointer = ASTPinpointer()
        ctx = pinpointer.pinpoint(SAMPLE_DICT_CODE, "app/order.py", target_line=2)
        assert ctx is not None

        can_mutate = mutator.can_mutate(ctx, "KeyError", "'items'")
        assert can_mutate is True

        patches = mutator.generate_patches(ctx, SAMPLE_DICT_CODE)
        assert len(patches) > 0
        assert any(".get(" in p for p in patches)

    def test_boundary_condition_mutator(self):
        mutator = BoundaryConditionMutator()
        pinpointer = ASTPinpointer()
        ctx = pinpointer.pinpoint(SAMPLE_BOUNDARY_CODE, "app/index.py", target_line=2)
        assert ctx is not None

        can_mutate = mutator.can_mutate(ctx, "IndexError", "list index out of range")
        assert can_mutate is True

        patches = mutator.generate_patches(ctx, SAMPLE_BOUNDARY_CODE)
        assert len(patches) > 0
        assert any(" >=" in p for p in patches)

    def test_http_exception_wrapper_mutator(self):
        mutator = HTTPExceptionWrapperMutator()
        pinpointer = ASTPinpointer()
        ctx = pinpointer.pinpoint(SAMPLE_DICT_CODE, "app/order.py", target_line=2)
        assert ctx is not None

        can_mutate = mutator.can_mutate(ctx, "NoResultFound", "500 internal server error")
        assert can_mutate is True

        patches = mutator.generate_patches(ctx, SAMPLE_DICT_CODE)
        assert len(patches) > 0
        assert any("HTTPException(status_code=404" in p for p in patches)


class TestZeroObservedRegressionGate:
    def test_ranking_formula_weights(self):
        gate = ZeroObservedRegressionGate()
        # Test Adequate + Regression Safe + Conf=0.9, 2 lines changed
        score = gate.calculate_score(
            test_adequate=True,
            regression_safe=True,
            fault_confidence=0.90,
            lines_changed=2,
            complexity_delta=1,
        )
        # Expected: 0.35 + 0.35 + 0.15*0.9 (0.135) + 0.10*(1 - 2/50 = 0.96 -> 0.096) - 0.05*(0.1) = ~0.926
        assert 0.85 <= score <= 0.96

    def test_regression_fails_ranking(self):
        gate = ZeroObservedRegressionGate()
        score = gate.calculate_score(
            test_adequate=True,
            regression_safe=False,
            fault_confidence=0.90,
            lines_changed=2,
            complexity_delta=1,
        )
        assert score < 0.60


class TestAutonomousPRDispatcher:
    def test_branch_and_commit_formatting(self):
        dispatcher = AutonomousPRDispatcher()
        branch = dispatcher.build_branch_name("DEF-042", "7f83b165abc")
        assert branch == "astra/fix-def-042-7f83b165"

        gate = ZeroObservedRegressionGate()
        from engine.repair.regression_gate import CandidateVerificationReport
        report = CandidateVerificationReport(
            candidate_hash="7f83b165abc",
            plausible=True,
            defect_test_duration_ms=45.0,
            static_analysis_passed=True,
            regression_passed=True,
            regressions_count=0,
            regression_tests_total=24,
            regression_tests_passed=24,
            regression_tests_failed=0,
            regression_tests_error=0,
            regression_tests_timeout=0,
            complexity_delta=2,
            ranking_score=0.92,
            verified=True,
        )

        commit = dispatcher.build_commit_message("DEF-042", "Fix null dereference", "app/auth.py", 14, report)
        assert "DEF-042" in commit
        assert "24/24 Tier-1 Tests PASSED" in commit
        assert "7f83b165abc" in commit

        body = dispatcher.build_pr_body(
            "DEF-042", "Fix null dereference", "app/auth.py", 14, "Null check", report, "--- a/+\n"
        )
        assert "Zero-Observed-Regression Gate" in body
        assert "0.92" in body
