"""
Unit & Integration Tests for Google Gemini Provider & APR Workflow.
Verifies secret redaction, structured output handling, rate limit resilience,
deterministic-first repair, and zero-fabrication verification guarantees.
"""

import json
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.core.config import settings
from engine.intelligence.providers.gemini import GeminiProvider, SUPPORTED_GEMINI_MODELS
from engine.intelligence.providers.factory import LLMProviderFactory
from engine.intelligence.providers.base import LLMResponse
from engine.repair.context import FaultLocationSnapshot, RepairContext, compute_sha256_text
from engine.repair.llm_synthesizer import LLMSynthesizer
from engine.repair.service import RepairJobService
from engine.repair.ast_pinpointer import ASTPinpointer
from engine.repair.regression_gate import ZeroObservedRegressionGate


# ─────────────────────────────────────────────────────────────────────────────
# 1. Configuration & Security Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_gemini_configuration_defaults():
    """Verify Gemini settings defaults and supported models."""
    assert hasattr(settings, "GEMINI_MODEL")
    assert hasattr(settings, "GEMINI_API_KEY")
    assert settings.GEMINI_MODEL in SUPPORTED_GEMINI_MODELS or "gemini" in settings.GEMINI_MODEL


def test_gemini_provider_secret_redaction():
    """Verify that GeminiProvider never leaks real API keys in repr or string output."""
    dummy_secret = "AIzaSySecretTestKey1234567890abcdef"
    provider = GeminiProvider(api_key=dummy_secret, model="gemini-1.5-flash")

    repr_str = repr(provider)
    str_val = str(provider)

    assert dummy_secret not in repr_str
    assert dummy_secret not in str_val
    assert "api_key=present" in repr_str
    assert provider.is_configured is True


def test_factory_returns_gemini_provider():
    """Verify that LLMProviderFactory exclusively instantiates GeminiProvider."""
    provider = LLMProviderFactory.get_provider(provider_name="gemini")
    assert isinstance(provider, GeminiProvider)
    assert provider.model == "gemini-1.5-flash"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Provider Structured Generation & Error Resilience Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gemini_missing_api_key_returns_graceful_envelope():
    """Unconfigured provider returns a structured error envelope rather than raising an unhandled exception."""
    provider = GeminiProvider(api_key="", model="gemini-1.5-flash")
    assert provider.is_configured is False

    is_healthy = await provider.health_check()
    assert is_healthy is False

    resp = await provider.generate_structured(
        system_prompt="Test sys",
        user_prompt="Test user",
        response_schema={"type": "object"},
    )
    assert resp.structured_data is None
    assert "missing or not configured" in resp.raw_text.lower()
    assert resp.provider_name == "gemini"


@pytest.mark.asyncio
async def test_gemini_strips_markdown_code_fences():
    """Provider cleanly strips ```json markdown fences from raw LLM output."""
    provider = GeminiProvider(api_key="mock_key", model="gemini-1.5-flash")

    raw_json_content = json.dumps({
        "repair_rationale": "Add null check",
        "unified_diff": "--- a/file.py\n+++ b/file.py\n@@ -1 +1,2 @@\n+if x is None: return None\n",
        "target_file": "file.py",
        "estimated_confidence": 0.88
    })

    # Wrap in markdown fences as LLMs commonly return
    fenced_content = f"```json\n{raw_json_content}\n```"

    mock_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": fenced_content}]
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 120,
            "candidatesTokenCount": 45
        }
    }

    mock_post_res = MagicMock()
    mock_post_res.status_code = 200
    mock_post_res.json.return_value = mock_gemini_response

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_post_res

        resp = await provider.generate_structured(
            system_prompt="Fix bug",
            user_prompt="Code snippet",
            response_schema={"type": "object"},
        )

        assert resp.structured_data is not None
        assert resp.structured_data["repair_rationale"] == "Add null check"
        assert resp.tokens_input == 120
        assert resp.tokens_output == 45


@pytest.mark.asyncio
async def test_gemini_rate_limit_http_429():
    """Verify HTTP 429 rate limit is reported cleanly without leaking credentials."""
    provider = GeminiProvider(api_key="mock_secret_key", model="gemini-1.5-flash")

    mock_res = MagicMock()
    mock_res.status_code = 429
    mock_res.text = "RESOURCE_EXHAUSTED"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_res

        resp = await provider.generate_structured(
            system_prompt="Fix bug",
            user_prompt="Code snippet",
            response_schema={"type": "object"},
        )

        assert resp.structured_data is None
        assert "rate limit exceeded" in resp.raw_text.lower()
        assert "mock_secret_key" not in resp.raw_text


@pytest.mark.asyncio
async def test_gemini_network_timeout():
    """Verify network timeout returns graceful error envelope."""
    provider = GeminiProvider(api_key="mock_key", model="gemini-1.5-flash")

    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Read timed out")):
        resp = await provider.generate_structured(
            system_prompt="Fix bug",
            user_prompt="Code snippet",
            response_schema={"type": "object"},
        )

        assert resp.structured_data is None
        assert "timed out" in resp.raw_text.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Deterministic-First & Genuine Repair Orchestration Tests
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_FAULTY_CODE = """import os

def process_item(item):
    val = item.value
    return val * 2
"""

@pytest.mark.asyncio
async def test_deterministic_first_repair_does_not_invoke_gemini(tmp_path):
    """
    When a defect matches deterministic mutator preconditions (e.g. AttributeError NoneType dereference),
    the repair pipeline must synthesize a valid patch using deterministic mutators FIRST,
    without calling the Gemini LLM.
    """
    mock_gemini = MagicMock(spec=GeminiProvider)
    mock_gemini.generate_structured = AsyncMock()

    synthesizer = LLMSynthesizer(provider=mock_gemini)
    service = RepairJobService(llm_synthesizer=synthesizer)

    defect_id = uuid4()
    context = RepairContext(
        defect_id=defect_id,
        project_id=uuid4(),
        workspace_id=None,
        build_id=None,
        commit_sha="4b825dc642cb6eb9a060e54bf8d69288fbee4904",
        base_branch="main",
        test_definition_id=uuid4(),
        test_definition_version_id=uuid4(),
        execution_attempt_id=uuid4(),
        test_result_id=uuid4(),
        file_path="services/item_processor.py",
        source_sha256=compute_sha256_text(SAMPLE_FAULTY_CODE),
        fault_location=FaultLocationSnapshot(
            file_path="services/item_processor.py",
            function_name="process_item",
            line_number=4,
            ast_node_type="Attribute",
            source_snippet="val = item.value",
            confidence=0.95,
        ),
        failure_fingerprint="fingerprint_123",
        exception_type="AttributeError",
        exception_message="'NoneType' object has no attribute 'value'",
        request_snapshot={"method": "POST", "body": {"item": None}},
        response_snapshot={"status_code": 500},
        assertion_snapshot={"expected": 200, "actual": 500},
        environment_snapshot_hash=compute_sha256_text("env"),
    )

    target_file = tmp_path / "services" / "item_processor.py"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(SAMPLE_FAULTY_CODE, encoding="utf-8")

    result = await service.execute_repair(
        repair_context=context,
        original_source=SAMPLE_FAULTY_CODE,
        repo_path=str(tmp_path),
        defect_test_cmd="python -c \"import sys; sys.exit(0)\"",
        regression_test_cmds=["python -c \"import sys; sys.exit(0)\""],
        severity="MAJOR",
    )

    # 1. Deterministic mutator MUST have succeeded
    assert result.status == "COMPLETED"
    assert result.candidates_generated >= 1
    assert result.selected_candidate is not None
    assert result.selected_candidate.generation_method == "DETERMINISTIC"
    assert "NULL_SAFETY" in result.selected_candidate.mutator_type

    # 2. Gemini must NOT have been called
    mock_gemini.generate_structured.assert_not_called()


@pytest.mark.asyncio
async def test_offline_failure_honesty_when_deterministic_fails(tmp_path):
    """
    When deterministic mutators cannot patch a fault and Gemini is unavailable (unconfigured),
    the repair pipeline must report status=FAILED with an honest failure reason,
    NEVER fabricating candidates or test pass counts.
    """
    offline_provider = GeminiProvider(api_key="", model="gemini-1.5-flash")
    synthesizer = LLMSynthesizer(provider=offline_provider)
    service = RepairJobService(llm_synthesizer=synthesizer)

    # Code with a complex logic error that deterministic mutators do not handle
    COMPLEX_CODE = """def calculate_tax(income, status):
    return income * 0.15
"""

    context = RepairContext(
        defect_id=uuid4(),
        project_id=uuid4(),
        workspace_id=None,
        build_id=None,
        commit_sha="4b825dc642cb6eb9a060e54bf8d69288fbee4904",
        base_branch="main",
        test_definition_id=uuid4(),
        test_definition_version_id=uuid4(),
        execution_attempt_id=uuid4(),
        test_result_id=uuid4(),
        file_path="services/tax.py",
        source_sha256=compute_sha256_text(COMPLEX_CODE),
        fault_location=FaultLocationSnapshot(
            file_path="services/tax.py",
            function_name="calculate_tax",
            line_number=2,
            ast_node_type="Return",
            source_snippet="return income * 0.15",
            confidence=0.85,
        ),
        failure_fingerprint="fp_tax",
        exception_type="AssertionError",
        exception_message="Tax calculation did not account for marital bracket deduction",
        request_snapshot={},
        response_snapshot={},
        assertion_snapshot={},
        environment_snapshot_hash="hash",
    )

    result = await service.execute_repair(
        repair_context=context,
        original_source=COMPLEX_CODE,
        repo_path=str(tmp_path),
        defect_test_cmd="python -c \"import sys; sys.exit(0)\"",
        regression_test_cmds=["python -c \"import sys; sys.exit(0)\""],
        severity="MAJOR",
    )

    # Must honestly report failure without fabricating candidate or 18/18 test pass reports
    assert result.status == "FAILED"
    assert result.candidates_generated == 0
    assert result.verified_candidates_count == 0
    assert result.selected_candidate is None
    assert "No plausible or syntactically valid patches could be synthesized" in (result.failure_reason or "")
