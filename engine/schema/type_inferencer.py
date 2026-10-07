"""
SchemaInferencer: Converts AST endpoints, Pydantic models, and type annotations
into NormalizedFieldSchema objects with property-level InferredValue provenance.
"""

from typing import List, Dict, Any, Optional
from engine.schema.models import (
    NormalizedFieldSchema,
    FieldType,
    FieldConstraint,
    InferredValue,
)


class SchemaInferencer:
    """Infers NormalizedFieldSchema from discovered endpoint parameter models."""

    @classmethod
    def infer_endpoint_schemas(cls, endpoint: Any) -> List[NormalizedFieldSchema]:
        """Infers normalized schemas for all parameters belonging to an endpoint."""
        schemas: List[NormalizedFieldSchema] = []
        raw_params = endpoint.parameters if hasattr(endpoint, "parameters") else []

        for p in raw_params:
            schema = cls.infer_parameter_schema(p)
            schemas.append(schema)

        return schemas

    @classmethod
    def infer_parameter_schema(cls, p: Any) -> NormalizedFieldSchema:
        """Infers normalized field schema for a single parameter."""
        p_name = p.get("name") if isinstance(p, dict) else getattr(p, "name", "param")
        p_type_raw = p.get("type", "str") if isinstance(p, dict) else getattr(p, "type", "str")
        p_loc = p.get("location", "query") if isinstance(p, dict) else getattr(p, "location", "query")
        is_req = p.get("required", True) if isinstance(p, dict) else getattr(p, "required", True)

        field_type, format_val = cls._map_type_and_format(p_name, str(p_type_raw))
        constraint = cls._extract_constraints(p_name, p_type_raw, p, field_type, format_val, is_req)

        # Handle nested schema if model/dict
        nested_schema = None
        if field_type == FieldType.OBJECT and isinstance(p, dict) and "fields" in p:
            nested_schema = {
                sub_k: cls.infer_parameter_schema(sub_v)
                for sub_k, sub_v in p["fields"].items()
            }

        item_schema = None
        if field_type == FieldType.ARRAY and isinstance(p, dict) and "item_type" in p:
            item_schema = cls.infer_parameter_schema({
                "name": f"{p_name}_item",
                "type": p["item_type"],
                "location": p_loc
            })

        return NormalizedFieldSchema(
            name=p_name,
            field_type=field_type,
            location=p_loc,
            constraint=constraint,
            nested_schema=nested_schema,
            item_schema=item_schema
        )

    @classmethod
    def _map_type_and_format(cls, name: str, type_str: str) -> (FieldType, Optional[str]):
        type_lower = type_str.lower()

        if "int" in type_lower:
            fmt = "int64" if "64" in type_lower else "int32"
            return FieldType.INTEGER, fmt
        elif "float" in type_lower or "double" in type_lower or "decimal" in type_lower:
            return FieldType.FLOAT, None
        elif "bool" in type_lower:
            return FieldType.BOOLEAN, None
        elif "list" in type_lower or "array" in type_lower:
            return FieldType.ARRAY, None
        elif "dict" in type_lower or "object" in type_lower or "model" in type_lower or "schema" in type_lower:
            return FieldType.OBJECT, None
        elif "literal" in type_lower or "enum" in type_lower:
            return FieldType.ENUM, None
        else:
            # Check format heuristics for strings
            if "uuid" in type_lower or "uuid" in name.lower():
                return FieldType.STRING, "uuid"
            elif "email" in type_lower or "email" in name.lower():
                return FieldType.STRING, "email"
            elif "date" in type_lower or "time" in type_lower or "created_at" in name.lower() or "updated_at" in name.lower():
                return FieldType.STRING, "date-time"
            elif "url" in type_lower or "uri" in type_lower:
                return FieldType.STRING, "uri"
            return FieldType.STRING, None

    @classmethod
    def _extract_constraints(
        cls,
        name: str,
        raw_type: Any,
        param_dict: Any,
        field_type: FieldType,
        format_val: Optional[str],
        is_req: bool
    ) -> FieldConstraint:
        c = FieldConstraint()

        # Required & Nullable
        c.required = InferredValue(is_req, "EXPLICIT_PARAM", 1.0)
        c.nullable = InferredValue(not is_req, "EXPLICIT_PARAM", 0.9)

        if format_val:
            c.format = InferredValue(format_val, "TYPE_ANNOTATION" if format_val in ["int32", "int64"] else "NAME_HEURISTIC", 0.9)

        # Extract explicit min/max constraints if provided in dictionary
        if isinstance(param_dict, dict):
            if "gt" in param_dict:
                c.exclusive_min_value = InferredValue(param_dict["gt"], "PYDANTIC_FIELD", 1.0)
            elif "ge" in param_dict or "min_value" in param_dict:
                val = param_dict.get("ge", param_dict.get("min_value"))
                c.min_value = InferredValue(val, "PYDANTIC_FIELD", 1.0)

            if "lt" in param_dict:
                c.exclusive_max_value = InferredValue(param_dict["lt"], "PYDANTIC_FIELD", 1.0)
            elif "le" in param_dict or "max_value" in param_dict:
                val = param_dict.get("le", param_dict.get("max_value"))
                c.max_value = InferredValue(val, "PYDANTIC_FIELD", 1.0)

            if "min_length" in param_dict:
                c.min_length = InferredValue(param_dict["min_length"], "PYDANTIC_FIELD", 1.0)
            if "max_length" in param_dict:
                c.max_length = InferredValue(param_dict["max_length"], "PYDANTIC_FIELD", 1.0)

            if "min_items" in param_dict:
                c.min_items = InferredValue(param_dict["min_items"], "PYDANTIC_FIELD", 1.0)
            if "max_items" in param_dict:
                c.max_items = InferredValue(param_dict["max_items"], "PYDANTIC_FIELD", 1.0)

            if "regex" in param_dict or "pattern" in param_dict:
                pat = param_dict.get("regex", param_dict.get("pattern"))
                c.regex_pattern = InferredValue(pat, "PYDANTIC_FIELD", 1.0)

            if "enum_values" in param_dict:
                c.enum_values = [InferredValue(v, "ENUM_DEFINITION", 1.0) for v in param_dict["enum_values"]]

        return c
