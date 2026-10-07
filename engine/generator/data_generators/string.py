"""
String Boundary & Length Generator (EP + BVA for String, Length, Unicode, Control Chars).
"""

from typing import List, Dict, Any, Optional
from engine.schema.models import NormalizedFieldSchema, FieldType
from engine.generator.models import ParameterMutation, MutationReason


class StringBoundaryGenerator:
    """Generates boundary and mutation payloads for string fields."""

    @classmethod
    def generate_mutations(cls, schema: NormalizedFieldSchema) -> List[ParameterMutation]:
        mutations: List[ParameterMutation] = []
        c = schema.constraint
        f_name = schema.name

        base_val = c.default_value.value if c.default_value else "sample_text"

        # 1. Empty & Null Mutations
        mutations.append(ParameterMutation(
            field_path=f_name, original_value=base_val, mutated_value="",
            reason=MutationReason.EMPTY_STRING, constraint_rule="empty_string", location=schema.location
        ))

        # 2. Length Constraints BVA (min_length & max_length)
        if c.min_length and c.min_length.value is not None:
            min_l = c.min_length.value
            if min_l > 0:
                # Invalid: min_l - 1
                mutations.append(ParameterMutation(
                    field_path=f_name, original_value=base_val, mutated_value="A" * (min_l - 1),
                    reason=MutationReason.MIN_MINUS_ONE, constraint_rule=f"min_length={min_l}", location=schema.location
                ))
            # Valid: min_l
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value="A" * min_l,
                reason=MutationReason.MIN_VALUE, constraint_rule=f"min_length={min_l}", location=schema.location
            ))

        if c.max_length and c.max_length.value is not None:
            max_l = c.max_length.value
            # Valid: max_l
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value="B" * max_l,
                reason=MutationReason.MAX_VALUE, constraint_rule=f"max_length={max_l}", location=schema.location
            ))
            # Invalid overflow: max_l + 1
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value="B" * (max_l + 1),
                reason=MutationReason.LENGTH_OVERFLOW, constraint_rule=f"max_length={max_l}", location=schema.location
            ))

        # 3. Unicode & Special Character Mutations
        mutations.append(ParameterMutation(
            field_path=f_name, original_value=base_val, mutated_value="こんにちはASTRA🚀",
            reason=MutationReason.HAPPY_PATH_VALID, constraint_rule="utf8_unicode", location=schema.location
        ))

        return mutations
