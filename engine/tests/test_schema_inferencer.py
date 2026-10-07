"""
Unit tests for SchemaInferencer and property-level InferredValue provenance.
"""

import pytest
from engine.schema.type_inferencer import SchemaInferencer
from engine.schema.models import FieldType


def test_infer_parameter_schema_numeric():
    param_dict = {
        "name": "age",
        "type": "int",
        "location": "body",
        "required": True,
        "ge": 18,
        "le": 60
    }
    schema = SchemaInferencer.infer_parameter_schema(param_dict)

    assert schema.name == "age"
    assert schema.field_type == FieldType.INTEGER
    assert schema.location == "body"
    assert schema.constraint.min_value.value == 18
    assert schema.constraint.min_value.source == "PYDANTIC_FIELD"
    assert schema.constraint.max_value.value == 60
    assert schema.constraint.max_value.source == "PYDANTIC_FIELD"


def test_infer_parameter_schema_format_heuristics():
    param_email = {"name": "user_email", "type": "str", "location": "body"}
    schema_email = SchemaInferencer.infer_parameter_schema(param_email)
    assert schema_email.field_type == FieldType.STRING
    assert schema_email.constraint.format.value == "email"

    param_uuid = {"name": "account_uuid", "type": "str", "location": "path"}
    schema_uuid = SchemaInferencer.infer_parameter_schema(param_uuid)
    assert schema_uuid.field_type == FieldType.STRING
    assert schema_uuid.constraint.format.value == "uuid"
