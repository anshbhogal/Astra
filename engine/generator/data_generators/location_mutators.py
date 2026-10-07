"""
Location-Specific Mutators (Path, Query, Header, Method, Body).
"""

from typing import List, Dict, Any, Optional
from engine.schema.models import NormalizedFieldSchema
from engine.generator.models import ParameterMutation, MutationReason


class LocationMutator:
    """Generates location-specific mutations for Path, Query, Header, Method, and Body parameters."""

    @classmethod
    def generate_path_mutations(cls, schema: NormalizedFieldSchema) -> List[ParameterMutation]:
        f_name = schema.name
        return [
            ParameterMutation(
                field_path=f_name, original_value="1", mutated_value="-1",
                reason=MutationReason.MIN_MINUS_ONE, constraint_rule="path_positive_id", location="path"
            ),
            ParameterMutation(
                field_path=f_name, original_value="1", mutated_value="0",
                reason=MutationReason.MIN_VALUE, constraint_rule="path_positive_id", location="path"
            ),
            ParameterMutation(
                field_path=f_name, original_value="1", mutated_value="invalid_path_str",
                reason=MutationReason.STRICTLY_INVALID_TYPE, constraint_rule="path_type", location="path"
            ),
        ]

    @classmethod
    def generate_query_mutations(cls, schema: NormalizedFieldSchema) -> List[ParameterMutation]:
        f_name = schema.name
        return [
            ParameterMutation(
                field_path=f_name, original_value="10", mutated_value="0",
                reason=MutationReason.MIN_VALUE, constraint_rule="query_non_zero", location="query"
            ),
            ParameterMutation(
                field_path=f_name, original_value="10", mutated_value="-1",
                reason=MutationReason.MIN_MINUS_ONE, constraint_rule="query_positive", location="query"
            ),
        ]

    @classmethod
    def generate_header_mutations(cls, schema: NormalizedFieldSchema) -> List[ParameterMutation]:
        f_name = schema.name
        return [
            ParameterMutation(
                field_path=f_name, original_value="application/json", mutated_value="text/plain",
                reason=MutationReason.INVALID_FORMAT, constraint_rule="header_content_type", location="header"
            ),
        ]

    @classmethod
    def generate_unsupported_method_mutation(cls, current_method: str) -> ParameterMutation:
        unsupported = "PATCH" if current_method.upper() != "PATCH" else "OPTIONS"
        return ParameterMutation(
            field_path="HTTP_METHOD", original_value=current_method, mutated_value=unsupported,
            reason=MutationReason.UNSUPPORTED_METHOD, constraint_rule="allowed_http_methods", location="method"
        )
