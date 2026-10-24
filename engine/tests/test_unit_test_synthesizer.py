"""Unit tests for Phase 2 Task P2-1: Honest Unit Test Synthesizer without Tautologies or Hardcoding."""

import ast
import pytest
from engine.analyzer.function_extractor import FunctionContract, ParameterSchema
from engine.generator.unit_test_synthesizer import UnitTestSynthesizer


def test_generator_contains_zero_tautological_assertions():
    """Synthesized tests must NEVER include tautological assertions like 'assert ... or True'."""
    contract = FunctionContract(
        function_id="fn_test_calc",
        qualified_name="calculator.add",
        file_path="calculator.py",
        source_hash="sha256_mock_1",
        line_number=10,
        parameters=[
            ParameterSchema(name="a", type_annotation="int"),
            ParameterSchema(name="b", type_annotation="int"),
        ],
        return_schema="int",
        docstring="Adds two integers.",
        side_effects=[],
        is_async=False,
    )

    code = UnitTestSynthesizer.synthesize_suite_for_contracts(
        contracts=[contract],
        module_name="calculator",
        repo_root="/workspace/repo"
    )

    # Must be valid Python AST
    parsed = ast.parse(code)
    assert parsed is not None

    # Zero occurrences of tautological or True
    assert "or True" not in code, "Tautology detected: 'or True' found in synthesized test suite!"
    assert "assert True" not in code, "Tautology detected: 'assert True' found in synthesized test suite!"

    # Zero blanket swallowed exceptions
    assert "except Exception:\n        pass" not in code, "Blanket swallowed exception detected in synthesized test suite!"


def test_generator_synthesizes_type_grounded_oracles():
    """Synthesized tests must generate typed assertion oracles based on return_schema."""
    contracts = [
        FunctionContract(
            function_id="fn_str",
            qualified_name="utils.format_name",
            file_path="utils.py",
            source_hash="sha256_mock_str",
            line_number=1,
            parameters=[ParameterSchema(name="name", type_annotation="str")],
            return_schema="str",
        ),
        FunctionContract(
            function_id="fn_bool",
            qualified_name="auth.is_valid",
            file_path="auth.py",
            source_hash="sha256_mock_bool",
            line_number=10,
            parameters=[ParameterSchema(name="token", type_annotation="str")],
            return_schema="bool",
        ),
        FunctionContract(
            function_id="fn_dict",
            qualified_name="api.get_metadata",
            file_path="api.py",
            source_hash="sha256_mock_dict",
            line_number=20,
            parameters=[],
            return_schema="dict",
        ),
    ]

    code = UnitTestSynthesizer.synthesize_suite_for_contracts(
        contracts=contracts,
        module_name="my_app",
        repo_root="/workspace/repo"
    )

    assert "isinstance(res, str)" in code
    assert "isinstance(res, bool)" in code
    assert "isinstance(res, dict)" in code


def test_generator_supports_async_functions():
    """Async functions must be generated with pytest.mark.asyncio and await."""
    async_contract = FunctionContract(
        function_id="fn_async_fetch",
        qualified_name="client.fetch_data",
        file_path="client.py",
        source_hash="sha256_mock_async",
        line_number=30,
        parameters=[ParameterSchema(name="url", type_annotation="str")],
        return_schema="dict",
        is_async=True,
    )

    code = UnitTestSynthesizer.synthesize_suite_for_contracts(
        contracts=[async_contract],
        module_name="my_app",
        repo_root="/workspace/repo"
    )

    assert "@pytest.mark.asyncio" in code
    assert "await fetch_data(" in code


def test_generator_has_no_hardcoded_lecture_rag_references():
    """Synthesizer must not contain hardcoded logic specifically naming lecture_rag."""
    import inspect
    source = inspect.getsource(UnitTestSynthesizer)
    assert "lecture_rag" not in source, "Found hardcoded 'lecture_rag' reference in UnitTestSynthesizer source!"
    assert "_format_timestamp" not in source, "Found hardcoded '_format_timestamp' in UnitTestSynthesizer source!"
    assert "dataset_stats" not in source, "Found hardcoded 'dataset_stats' in UnitTestSynthesizer source!"
