"""
Property-Level Provenance & Normalized Schema Data Models for Phase 4 Engine.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Union, Generic, TypeVar

T = TypeVar("T")


@dataclass
class InferredValue(Generic[T]):
    """Wraps an inferred schema property value with explicit source and confidence score."""
    value: T
    source: str = "UNKNOWN"  # e.g., "PYDANTIC_FIELD", "TYPE_ANNOTATION", "FASTAPI_PARAM", "NAME_HEURISTIC"
    confidence: float = 1.0  # 1.0 for explicit type hints, 0.55 for name heuristics

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "source": self.source,
            "confidence": self.confidence
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "InferredValue":
        return cls(
            value=d.get("value"),
            source=d.get("source", "UNKNOWN"),
            confidence=float(d.get("confidence", 1.0))
        )


class FieldType(str, Enum):
    STRING = "STRING"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    ENUM = "ENUM"
    ARRAY = "ARRAY"
    OBJECT = "OBJECT"
    UNKNOWN = "UNKNOWN"


@dataclass
class FieldConstraint:
    """Contains property-level inferred constraints for a schema field."""
    min_value: Optional[InferredValue[Union[int, float]]] = None
    max_value: Optional[InferredValue[Union[int, float]]] = None
    exclusive_min_value: Optional[InferredValue[Union[int, float]]] = None
    exclusive_max_value: Optional[InferredValue[Union[int, float]]] = None
    multiple_of: Optional[InferredValue[Union[int, float]]] = None
    min_length: Optional[InferredValue[int]] = None
    max_length: Optional[InferredValue[int]] = None
    min_items: Optional[InferredValue[int]] = None
    max_items: Optional[InferredValue[int]] = None
    unique_items: InferredValue[bool] = field(default_factory=lambda: InferredValue(False, "DEFAULT", 1.0))
    regex_pattern: Optional[InferredValue[str]] = None
    format: Optional[InferredValue[str]] = None  # "uuid", "email", "date-time", "uri", "int32", "int64"
    enum_values: List[InferredValue[Any]] = field(default_factory=list)
    nullable: InferredValue[bool] = field(default_factory=lambda: InferredValue(False, "DEFAULT", 1.0))
    required: InferredValue[bool] = field(default_factory=lambda: InferredValue(True, "DEFAULT", 1.0))
    default_value: Optional[InferredValue[Any]] = None
    examples: List[InferredValue[Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_value": self.min_value.to_dict() if self.min_value else None,
            "max_value": self.max_value.to_dict() if self.max_value else None,
            "exclusive_min_value": self.exclusive_min_value.to_dict() if self.exclusive_min_value else None,
            "exclusive_max_value": self.exclusive_max_value.to_dict() if self.exclusive_max_value else None,
            "multiple_of": self.multiple_of.to_dict() if self.multiple_of else None,
            "min_length": self.min_length.to_dict() if self.min_length else None,
            "max_length": self.max_length.to_dict() if self.max_length else None,
            "min_items": self.min_items.to_dict() if self.min_items else None,
            "max_items": self.max_items.to_dict() if self.max_items else None,
            "unique_items": self.unique_items.to_dict(),
            "regex_pattern": self.regex_pattern.to_dict() if self.regex_pattern else None,
            "format": self.format.to_dict() if self.format else None,
            "enum_values": [v.to_dict() for v in self.enum_values],
            "nullable": self.nullable.to_dict(),
            "required": self.required.to_dict(),
            "default_value": self.default_value.to_dict() if self.default_value else None,
            "examples": [e.to_dict() for e in self.examples]
        }


@dataclass
class NormalizedFieldSchema:
    """Normalized schema representation of an API parameter or payload property."""
    name: str
    field_type: FieldType
    location: str = "body"  # "path", "query", "header", "body"
    constraint: FieldConstraint = field(default_factory=FieldConstraint)
    nested_schema: Optional[Dict[str, "NormalizedFieldSchema"]] = None  # For OBJECT
    item_schema: Optional["NormalizedFieldSchema"] = None                # For ARRAY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "field_type": self.field_type.value,
            "location": self.location,
            "constraint": self.constraint.to_dict(),
            "nested_schema": {k: v.to_dict() for k, v in self.nested_schema.items()} if self.nested_schema else None,
            "item_schema": self.item_schema.to_dict() if self.item_schema else None
        }
