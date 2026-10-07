"""
Core Domain Enums & Intermediate Scenario Data Models for Phase 4 Test Generator.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class TestType(str, Enum):
    __test__ = False
    HAPPY_PATH = "HAPPY_PATH"
    BOUNDARY = "BOUNDARY"
    EQUIVALENCE_PARTITION = "EQUIVALENCE_PARTITION"
    MISSING_REQUIRED = "MISSING_REQUIRED"
    INVALID_TYPE = "INVALID_TYPE"
    INVALID_FORMAT = "INVALID_FORMAT"
    NULL_VALUE = "NULL_VALUE"
    SECURITY_PROBE = "SECURITY_PROBE"
    COMBINATORIAL = "COMBINATORIAL"
    UNAUTHORIZED = "UNAUTHORIZED"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"


class StatusSource(str, Enum):
    OPENAPI = "OPENAPI"
    FRAMEWORK_CONVENTION = "FRAMEWORK_CONVENTION"
    STATIC_RULE = "STATIC_RULE"
    USER_DEFINED = "USER_DEFINED"
    UNKNOWN = "UNKNOWN"


class SecurityOutcome(str, Enum):
    SECURITY_SAFE = "SECURITY_SAFE"
    SECURITY_SUSPECT = "SECURITY_SUSPECT"
    INCONCLUSIVE = "INCONCLUSIVE"


class MutationReason(str, Enum):
    HAPPY_PATH_VALID = "HAPPY_PATH_VALID"
    MIN_VALUE = "MIN_VALUE"
    MAX_VALUE = "MAX_VALUE"
    MIN_MINUS_ONE = "MIN_MINUS_ONE"
    MAX_PLUS_ONE = "MAX_PLUS_ONE"
    EXCLUSIVE_MIN = "EXCLUSIVE_MIN"
    EXCLUSIVE_MAX = "EXCLUSIVE_MAX"
    EMPTY_STRING = "EMPTY_STRING"
    LENGTH_OVERFLOW = "LENGTH_OVERFLOW"
    INVALID_FORMAT = "INVALID_FORMAT"
    STRICTLY_INVALID_TYPE = "STRICTLY_INVALID_TYPE"
    COERCIBLE_TYPE = "COERCIBLE_TYPE"
    MISSING_REQUIRED = "MISSING_REQUIRED"
    NULL_ALLOWED = "NULL_ALLOWED"
    NULL_DISALLOWED = "NULL_DISALLOWED"
    BOOLEAN_MUTATION = "BOOLEAN_MUTATION"
    ENUM_VALID = "ENUM_VALID"
    ENUM_INVALID = "ENUM_INVALID"
    EXTRA_FIELD = "EXTRA_FIELD"
    SECURITY_PROBE = "SECURITY_PROBE"
    COMBINATORIAL_PAIR = "COMBINATORIAL_PAIR"
    UNSUPPORTED_METHOD = "UNSUPPORTED_METHOD"


@dataclass
class ParameterMutation:
    """Represents a targeted mutation performed on a parameter or field."""
    field_path: str                 # e.g., "address.pincode" or "age"
    original_value: Any
    mutated_value: Any
    reason: MutationReason
    constraint_rule: Optional[str] = None
    location: str = "body"          # "path", "query", "header", "body", "method"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_path": self.field_path,
            "original_value": self.original_value,
            "mutated_value": self.mutated_value,
            "reason": self.reason.value,
            "constraint_rule": self.constraint_rule,
            "location": self.location
        }


@dataclass
class TestScenario:
    """
    Intermediate Representation (IR) encapsulating test intent, parameter mutations,
    and expected behavior before compilation into TestSpecification.
    """
    __test__ = False
    endpoint_id: str
    scenario_name: str
    test_type: TestType
    mutations: List[ParameterMutation]
    expected_status_codes: Optional[List[int]] = None  # None/UNKNOWN when expectations cannot be inferred
    expected_status_source: StatusSource = StatusSource.UNKNOWN
    auth_omitted: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "endpoint_id": self.endpoint_id,
            "scenario_name": self.scenario_name,
            "test_type": self.test_type.value,
            "mutations": [m.to_dict() for m in self.mutations],
            "expected_status_codes": self.expected_status_codes,
            "expected_status_source": self.expected_status_source.value,
            "auth_omitted": self.auth_omitted,
            "metadata": self.metadata
        }
