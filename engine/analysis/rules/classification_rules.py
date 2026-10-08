"""
ASTRA Engine - Phase 6 Priority Classification Rules (R001 - R030)

Defines deterministic rule definitions for failure categorization with semantic precedence.
"""

from dataclasses import dataclass
from typing import Callable, List, Dict, Any, Optional
from engine.analysis.models import FailureCategory, ParsedException, JsonDiffItem


@dataclass
class RuleContext:
    expected_status: Optional[int]
    actual_status: int
    test_type: str
    parsed_exception: Optional[ParsedException]
    diff_items: List[JsonDiffItem]
    raw_logs: str = ""
    execution_result: str = "FAILED"
    latency_ms: Optional[float] = None
    max_latency_ms: Optional[float] = None


@dataclass
class ClassificationRule:
    rule_id: str
    category: FailureCategory
    priority: int
    condition: Callable[[RuleContext], bool]
    description: str
    confidence: float = 0.95


def get_default_classification_rules() -> List[ClassificationRule]:
    return [
        # R001: SERVER_CRASH (Priority 100)
        ClassificationRule(
            rule_id="R001",
            category=FailureCategory.SERVER_CRASH,
            priority=100,
            condition=lambda ctx: ctx.actual_status >= 500 or (
                ctx.parsed_exception is not None and ctx.parsed_exception.language in ("python", "nodejs", "java") and ctx.actual_status in (500, 502, 503)
            ),
            description="HTTP 500 Server Error or unhandled application exception",
            confidence=0.98,
        ),

        # R002: DATABASE_ERROR (Priority 105)
        ClassificationRule(
            rule_id="R002",
            category=FailureCategory.DATABASE_ERROR,
            priority=105,
            condition=lambda ctx: (
                (ctx.parsed_exception is not None and (
                    ctx.parsed_exception.language == "sql"
                    or ctx.parsed_exception.sql_state is not None
                    or "Constraint" in ctx.parsed_exception.exception_type
                    or "IntegrityError" in ctx.parsed_exception.exception_type
                    or "OperationalError" in ctx.parsed_exception.exception_type
                    or "DatabaseError" in ctx.parsed_exception.exception_type
                )) or "duplicate key" in ctx.raw_logs.lower() or "foreign key" in ctx.raw_logs.lower()
            ),
            description="Database integrity error, constraint violation, or SQL exception",
            confidence=0.96,
        ),

        # R003: TIMEOUT_PERFORMANCE (Priority 90)
        ClassificationRule(
            rule_id="R003",
            category=FailureCategory.TIMEOUT_PERFORMANCE,
            priority=90,
            condition=lambda ctx: ctx.execution_result == "TIMEOUT" or (
                ctx.max_latency_ms is not None and ctx.latency_ms is not None and ctx.latency_ms > ctx.max_latency_ms
            ) or (ctx.parsed_exception is not None and "Timeout" in ctx.parsed_exception.exception_type),
            description="Execution timeout or SLA performance limit breach",
            confidence=0.95,
        ),

        # R004: ENVIRONMENT_FLAKE (Priority 85)
        ClassificationRule(
            rule_id="R004",
            category=FailureCategory.ENVIRONMENT_FLAKE,
            priority=85,
            condition=lambda ctx: any(
                err in ctx.raw_logs.lower()
                for err in ["connection refused", "dns failure", "target host down", "econnrefused", "name or service not known"]
            ) or (ctx.parsed_exception is not None and "ConnectionRefused" in ctx.parsed_exception.exception_type),
            description="Transient network error, DNS failure, or infrastructure connection drop",
            confidence=0.90,
        ),

        # R005: AUTHENTICATION_FAILURE (Priority 80)
        ClassificationRule(
            rule_id="R005",
            category=FailureCategory.AUTHENTICATION_FAILURE,
            priority=80,
            condition=lambda ctx: ctx.actual_status == 401 and (ctx.expected_status is None or ctx.expected_status != 401),
            description="HTTP 401 Unauthorized: missing or invalid credentials",
            confidence=0.95,
        ),

        # R006: AUTHORIZATION_FAILURE (Priority 75)
        ClassificationRule(
            rule_id="R006",
            category=FailureCategory.AUTHORIZATION_FAILURE,
            priority=75,
            condition=lambda ctx: ctx.actual_status == 403 and (ctx.expected_status is None or ctx.expected_status != 403),
            description="HTTP 403 Forbidden: insufficient scope or permission",
            confidence=0.95,
        ),

        # R007: NOT_FOUND_DEFECT (Priority 70)
        ClassificationRule(
            rule_id="R007",
            category=FailureCategory.NOT_FOUND_DEFECT,
            priority=70,
            condition=lambda ctx: ctx.actual_status == 404 and (ctx.expected_status is None or ctx.expected_status != 404),
            description="HTTP 404 Not Found: requested route or entity missing",
            confidence=0.95,
        ),

        # R008: METHOD_NOT_ALLOWED (Priority 65)
        ClassificationRule(
            rule_id="R008",
            category=FailureCategory.METHOD_NOT_ALLOWED,
            priority=65,
            condition=lambda ctx: ctx.actual_status == 405 and (ctx.expected_status is None or ctx.expected_status != 405),
            description="HTTP 405 Method Not Allowed",
            confidence=0.95,
        ),

        # R009: REQUEST_VALIDATION_DEFECT (Priority 60)
        ClassificationRule(
            rule_id="R009",
            category=FailureCategory.REQUEST_VALIDATION_DEFECT,
            priority=60,
            condition=lambda ctx: ctx.actual_status in (400, 422) and (ctx.expected_status is None or ctx.expected_status not in (400, 422)) and (
                "validation" in ctx.raw_logs.lower() or "unprocessable" in ctx.raw_logs.lower() or (ctx.parsed_exception is not None and "ValidationError" in ctx.parsed_exception.exception_type)
            ),
            description="Request body or parameters failed target schema validation",
            confidence=0.90,
        ),

        # R010: CONTRACT_VIOLATION (Priority 55)
        ClassificationRule(
            rule_id="R010",
            category=FailureCategory.CONTRACT_VIOLATION,
            priority=55,
            condition=lambda ctx: len(ctx.diff_items) > 0 and ctx.actual_status < 500,
            description="Response body or headers violate test specification contract",
            confidence=0.88,
        ),

        # R011: BUSINESS_LOGIC_DEFECT (Priority 50)
        ClassificationRule(
            rule_id="R011",
            category=FailureCategory.BUSINESS_LOGIC_DEFECT,
            priority=50,
            condition=lambda ctx: ctx.actual_status in (400, 409, 422) and (ctx.expected_status is None or ctx.expected_status != ctx.actual_status),
            description="Domain rule rejection or business logic failure",
            confidence=0.85,
        ),

        # R020: DEPENDENCY_FAILURE (Priority 45)
        ClassificationRule(
            rule_id="R020",
            category=FailureCategory.DEPENDENCY_FAILURE,
            priority=45,
            condition=lambda ctx: ctx.actual_status in (502, 504) or "upstream" in ctx.raw_logs.lower() or "bad gateway" in ctx.raw_logs.lower(),
            description="Downstream service or third-party dependency outage",
            confidence=0.85,
        ),

        # R030: UNKNOWN (Priority 10)
        ClassificationRule(
            rule_id="R030",
            category=FailureCategory.UNKNOWN,
            priority=10,
            condition=lambda ctx: True,
            description="Fallback for unclassified failures",
            confidence=0.60,
        ),
    ]
