"""
Collections & Recursive Objects Generator (Arrays, Nested Models, Item Boundaries).
"""

from typing import List, Dict, Any, Optional
from engine.schema.models import NormalizedFieldSchema, FieldType
from engine.generator.models import ParameterMutation, MutationReason


class CollectionGenerator:
    """Generates boundary and mutation payloads for Array and Nested Object schema fields."""

    @classmethod
    def generate_array_mutations(cls, schema: NormalizedFieldSchema) -> List[ParameterMutation]:
        mutations: List[ParameterMutation] = []
        c = schema.constraint
        f_name = schema.name

        base_val = ["sample_item_1"]

        # 1. Empty Array
        mutations.append(ParameterMutation(
            field_path=f_name, original_value=base_val, mutated_value=[],
            reason=MutationReason.EMPTY_STRING, constraint_rule="empty_array", location=schema.location
        ))

        # 2. Min & Max Items BVA
        if c.min_items and c.min_items.value is not None:
            min_i = c.min_items.value
            if min_i > 0:
                mutations.append(ParameterMutation(
                    field_path=f_name, original_value=base_val, mutated_value=["item"] * (min_i - 1),
                    reason=MutationReason.MIN_MINUS_ONE, constraint_rule=f"min_items={min_i}", location=schema.location
                ))
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value=["item"] * min_i,
                reason=MutationReason.MIN_VALUE, constraint_rule=f"min_items={min_i}", location=schema.location
            ))

        if c.max_items and c.max_items.value is not None:
            max_i = c.max_items.value
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value=["item"] * max_i,
                reason=MutationReason.MAX_VALUE, constraint_rule=f"max_items={max_i}", location=schema.location
            ))
            mutations.append(ParameterMutation(
                field_path=f_name, original_value=base_val, mutated_value=["item"] * (max_i + 1),
                reason=MutationReason.LENGTH_OVERFLOW, constraint_rule=f"max_items={max_i}", location=schema.location
            ))

        # 3. Wrong Item Type in Array
        mutations.append(ParameterMutation(
            field_path=f_name, original_value=base_val, mutated_value=[{"invalid_nested_dict": True}],
            reason=MutationReason.STRICTLY_INVALID_TYPE, constraint_rule="array_item_type", location=schema.location
        ))

        return mutations

    @classmethod
    def generate_object_mutations(cls, schema: NormalizedFieldSchema, parent_prefix: str = "") -> List[ParameterMutation]:
        mutations: List[ParameterMutation] = []
        if not schema.nested_schema:
            return mutations

        # Extra unexpected field in object payload
        curr_path = f"{parent_prefix}.{schema.name}" if parent_prefix else schema.name
        mutations.append(ParameterMutation(
            field_path=f"{curr_path}.__unexpected_extra_key__",
            original_value=None,
            mutated_value="unexpected_extra_value",
            reason=MutationReason.EXTRA_FIELD,
            constraint_rule="reject_extra_fields",
            location=schema.location
        ))

        return mutations
