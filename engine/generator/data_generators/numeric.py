"""
Numeric Boundary & Equivalence Partitioning Generator (EP + BVA for Int & Float).
"""

from typing import List, Dict, Any, Optional
from engine.schema.models import NormalizedFieldSchema, FieldType
from engine.generator.models import ParameterMutation, MutationReason


class NumericBoundaryGenerator:
    """Generates equivalence partition and boundary value mutations for numeric fields."""

    @classmethod
    def generate_mutations(cls, schema: NormalizedFieldSchema) -> List[ParameterMutation]:
        mutations: List[ParameterMutation] = []
        c = schema.constraint
        f_name = schema.name
        is_float = schema.field_type == FieldType.FLOAT

        # Default valid base value
        base_val = c.default_value.value if c.default_value else (50.0 if is_float else 25)
        offset = 0.001 if is_float else 1

        # 1. MIN_VALUE & MIN_MINUS_ONE (Inclusive ge vs Exclusive gt)
        if c.min_value and c.min_value.value is not None:
            min_v = c.min_value.value
            # Valid boundary: min_v
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value=min_v,
                reason=MutationReason.MIN_VALUE, constraint_rule=f"ge={min_v}", location=schema.location
            ))
            # Invalid boundary: min_v - offset
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value=min_v - offset,
                reason=MutationReason.MIN_MINUS_ONE, constraint_rule=f"ge={min_v}", location=schema.location
            ))

        if c.exclusive_min_value and c.exclusive_min_value.value is not None:
            ex_min = c.exclusive_min_value.value
            # Invalid boundary: ex_min
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value=ex_min,
                reason=MutationReason.EXCLUSIVE_MIN, constraint_rule=f"gt={ex_min}", location=schema.location
            ))
            # Valid boundary: ex_min + offset
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value=ex_min + offset,
                reason=MutationReason.MIN_VALUE, constraint_rule=f"gt={ex_min}", location=schema.location
            ))

        # 2. MAX_VALUE & MAX_PLUS_ONE (Inclusive le vs Exclusive lt)
        if c.max_value and c.max_value.value is not None:
            max_v = c.max_value.value
            # Valid boundary: max_v
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value=max_v,
                reason=MutationReason.MAX_VALUE, constraint_rule=f"le={max_v}", location=schema.location
            ))
            # Invalid boundary: max_v + offset
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value=max_v + offset,
                reason=MutationReason.MAX_PLUS_ONE, constraint_rule=f"le={max_v}", location=schema.location
            ))

        if c.exclusive_max_value and c.exclusive_max_value.value is not None:
            ex_max = c.exclusive_max_value.value
            # Invalid boundary: ex_max
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value=ex_max,
                reason=MutationReason.EXCLUSIVE_MAX, constraint_rule=f"lt={ex_max}", location=schema.location
            ))
            # Valid boundary: ex_max - offset
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value=ex_max - offset,
                reason=MutationReason.MAX_VALUE, constraint_rule=f"lt={ex_max}", location=schema.location
            ))

        # 3. Type Coercibility & Strictly Invalid Type
        mutations.append(ParameterMutation(
            field_path=f_name, original_value=base_val, mutated_value="NOT_A_NUMBER",
            reason=MutationReason.STRICTLY_INVALID_TYPE, constraint_rule=f"type={schema.field_type.value}", location=schema.location
        ))

        mutations.append(ParameterMutation(
            field_path=f_name, original_value=base_val, mutated_value=f"{base_val}",
            reason=MutationReason.COERCIBLE_TYPE, constraint_rule=f"coercible_{schema.field_type.value}", location=schema.location
        ))

        return mutations
