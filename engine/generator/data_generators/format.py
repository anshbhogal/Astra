"""
Format & Pattern Generator (UUID, Email, ISO8601 Date, Regex Patterns).
"""

from typing import List, Dict, Any, Optional
from engine.schema.models import NormalizedFieldSchema
from engine.generator.models import ParameterMutation, MutationReason


class FormatBoundaryGenerator:
    """Generates valid and malformed format mutations for structured format fields."""

    @classmethod
    def generate_mutations(cls, schema: NormalizedFieldSchema) -> List[ParameterMutation]:
        mutations: List[ParameterMutation] = []
        c = schema.constraint
        f_name = schema.name
        fmt = c.format.value if c.format else None

        base_val = c.default_value.value if c.default_value else "sample_format_val"

        if fmt == "uuid":
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value="123e4567-e89b-12d3-a456-426614174000",
                reason=MutationReason.HAPPY_PATH_VALID, constraint_rule="format=uuid", location=schema.location
            ))
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value="not-a-valid-uuid-12345",
                reason=MutationReason.INVALID_FORMAT, constraint_rule="format=uuid", location=schema.location
            ))

        elif fmt == "email":
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value="test.user@astra.local",
                reason=MutationReason.HAPPY_PATH_VALID, constraint_rule="format=email", location=schema.location
            ))
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value="invalid-email-missing-domain@",
                reason=MutationReason.INVALID_FORMAT, constraint_rule="format=email", location=schema.location
            ))

        elif fmt == "date-time":
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value="2026-10-07T12:00:00Z",
                reason=MutationReason.HAPPY_PATH_VALID, constraint_rule="format=date-time", location=schema.location
            ))
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value="2026-99-99T99:99:99Z",
                reason=MutationReason.INVALID_FORMAT, constraint_rule="format=date-time", location=schema.location
            ))

        elif c.enum_values:
            valid_vals = [e.value for e in c.enum_values]
            if valid_vals:
                mutations.append(ParameterMutation(
                    field_path=f_name, original_value=base_val, mutated_value=valid_vals[0],
                    reason=MutationReason.ENUM_VALID, constraint_rule="enum_valid", location=schema.location
                ))
                mutations.append(ParameterMutation(
                    field_path=f_name, original_value=base_val, mutated_value="INVALID_ENUM_OPTION_XYZ",
                    reason=MutationReason.ENUM_INVALID, constraint_rule="enum_invalid", location=schema.location
                ))

        return mutations
