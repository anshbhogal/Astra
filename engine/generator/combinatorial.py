"""
CombinatorialSynthesizer: N-Wise (Single-value, Pairwise, 3-wise) Combinatorial Synthesizer.
"""

from typing import List, Dict, Any
from itertools import combinations, product
from engine.schema.models import NormalizedFieldSchema
from engine.generator.models import ParameterMutation, MutationReason, TestScenario, TestType, StatusSource


class CombinatorialSynthesizer:
    """Synthesizes N-wise combinatorial parameter test scenarios."""

    @classmethod
    def generate_combinatorial_scenarios(
        cls,
        endpoint_id: str,
        schemas: List[NormalizedFieldSchema],
        strength: int = 2,
        max_combinations: int = 25
    ) -> List[TestScenario]:
        scenarios: List[TestScenario] = []

        # Filter parameters that have valid choices
        param_domains: Dict[str, List[Any]] = {}
        for s in schemas:
            if s.location in ["body", "query"]:
                choices = [f"sample_{s.name}_1", f"sample_{s.name}_2"]
                if s.constraint.enum_values:
                    choices = [e.value for e in s.constraint.enum_values]
                param_domains[s.name] = choices

        param_names = list(param_domains.keys())
        if len(param_names) < strength or strength < 1:
            return scenarios

        if strength == 1:
            # Single parameter value coverage
            for p_name in param_names:
                for val in param_domains[p_name]:
                    mutation = ParameterMutation(
                        field_path=p_name, original_value=None, mutated_value=val,
                        reason=MutationReason.COMBINATORIAL_PAIR, constraint_rule="nwise_strength=1"
                    )
                    scenarios.append(TestScenario(
                        endpoint_id=endpoint_id,
                        scenario_name=f"Combinatorial 1-wise choice '{p_name}={val}'",
                        test_type=TestType.COMBINATORIAL,
                        mutations=[mutation],
                        expected_status_codes=[200, 201],
                        expected_status_source=StatusSource.STATIC_RULE
                    ))
        else:
            # Pairwise (strength=2) or N-wise (strength > 2)
            combo_count = 0
            for param_subset in combinations(param_names, strength):
                value_tuples = product(*(param_domains[p] for p in param_subset))
                for val_tuple in value_tuples:
                    if combo_count >= max_combinations:
                        break

                    mutations = [
                        ParameterMutation(
                            field_path=param_subset[i],
                            original_value=None,
                            mutated_value=val_tuple[i],
                            reason=MutationReason.COMBINATORIAL_PAIR,
                            constraint_rule=f"nwise_strength={strength}"
                        )
                        for i in range(len(param_subset))
                    ]

                    scenarios.append(TestScenario(
                        endpoint_id=endpoint_id,
                        scenario_name=f"Combinatorial {strength}-wise pair ({', '.join(param_subset)})",
                        test_type=TestType.COMBINATORIAL,
                        mutations=mutations,
                        expected_status_codes=[200, 201],
                        expected_status_source=StatusSource.STATIC_RULE
                    ))
                    combo_count += 1

        return scenarios
