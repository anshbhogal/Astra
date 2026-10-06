from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class TestType(str, Enum):
    __test__ = False
    HAPPY_PATH = "HAPPY_PATH"
    MISSING_REQUIRED = "MISSING_REQUIRED"
    INVALID_TYPE = "INVALID_TYPE"
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_FORMAT = "INVALID_FORMAT"
    EMPTY_VALUE = "EMPTY_VALUE"
    NULL_VALUE = "NULL_VALUE"
    BOUNDARY = "BOUNDARY"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    NOT_FOUND = "NOT_FOUND"


class TestOutcome(str, Enum):
    __test__ = False
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    SKIP = "SKIP"


class StatusSource(str, Enum):
    STATIC_RULE = "STATIC_RULE"
    OPENAPI = "OPENAPI"
    FRAMEWORK_CONVENTION = "FRAMEWORK_CONVENTION"
    USER_DEFINED = "USER_DEFINED"
    UNKNOWN = "UNKNOWN"


class AssertionType(str, Enum):
    STATUS_CODE = "STATUS_CODE"
    CONTENT_TYPE = "CONTENT_TYPE"
    JSON_SCHEMA = "JSON_SCHEMA"
    JSON_PATH = "JSON_PATH"
    KEY_VALUE = "KEY_VALUE"
    BODY_CONTAINS = "BODY_CONTAINS"
    BODY_NOT_CONTAINS = "BODY_NOT_CONTAINS"
    LATENCY_SLA = "LATENCY_SLA"


@dataclass
class AssertionRule:
    type: AssertionType
    expected: Any
    path: Optional[str] = None
    operator: str = "equals"  # equals, contains, less_than, greater_than, matches
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value if isinstance(self.type, Enum) else self.type,
            "expected": self.expected,
            "path": self.path,
            "operator": self.operator,
            "message": self.message
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AssertionRule":
        return cls(
            type=AssertionType(d["type"]) if isinstance(d["type"], str) else d["type"],
            expected=d.get("expected"),
            path=d.get("path"),
            operator=d.get("operator", "equals"),
            message=d.get("message")
        )


@dataclass
class TestSpecification:
    __test__ = False
    id: str
    name: str
    endpoint_id: str
    test_type: TestType
    method: str
    path: str
    path_params: Dict[str, Any] = field(default_factory=dict)
    query_params: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None
    auth_ref: Optional[Dict[str, Any]] = None
    expected_status: List[int] = field(default_factory=lambda: [200])
    expected_status_source: StatusSource = StatusSource.STATIC_RULE
    expected_schema: Optional[Dict[str, Any]] = None
    assertions: List[AssertionRule] = field(default_factory=list)
    timeout_ms: int = 10000
    execution_order: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "endpoint_id": self.endpoint_id,
            "test_type": self.test_type.value if isinstance(self.test_type, Enum) else self.test_type,
            "method": self.method,
            "path": self.path,
            "path_params": self.path_params,
            "query_params": self.query_params,
            "headers": self.headers,
            "body": self.body,
            "auth_ref": self.auth_ref,
            "expected_status": self.expected_status,
            "expected_status_source": self.expected_status_source.value if isinstance(self.expected_status_source, Enum) else self.expected_status_source,
            "expected_schema": self.expected_schema,
            "assertions": [a.to_dict() if hasattr(a, "to_dict") else a for a in self.assertions],
            "timeout_ms": self.timeout_ms,
            "execution_order": self.execution_order,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestSpecification":
        assertions_raw = data.get("assertions", [])
        assertions = [
            AssertionRule.from_dict(a) if isinstance(a, dict) else a
            for a in assertions_raw
        ]
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            endpoint_id=data.get("endpoint_id", ""),
            test_type=TestType(data["test_type"]) if isinstance(data.get("test_type"), str) else data.get("test_type", TestType.HAPPY_PATH),
            method=data.get("method", "GET"),
            path=data.get("path", "/"),
            path_params=data.get("path_params", {}),
            query_params=data.get("query_params", {}),
            headers=data.get("headers", {}),
            body=data.get("body"),
            auth_ref=data.get("auth_ref"),
            expected_status=data.get("expected_status", [200]),
            expected_status_source=StatusSource(data["expected_status_source"]) if isinstance(data.get("expected_status_source"), str) else data.get("expected_status_source", StatusSource.STATIC_RULE),
            expected_schema=data.get("expected_schema"),
            assertions=assertions,
            timeout_ms=data.get("timeout_ms", 10000),
            execution_order=data.get("execution_order", 1),
            metadata=data.get("metadata", {})
        )
