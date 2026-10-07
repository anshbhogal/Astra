"""
Unit tests for CombinatorialSynthesizer (N-wise algorithm).
"""

import pytest
from engine.schema.type_inferencer import SchemaInferencer
from engine.generator.combinatorial import CombinatorialSynthesizer


def test_combinatorial_pairwise_generation():
    p1 = {"name": "role", "type": "str", "enum_values": ["user", "admin"], "location": "body"}
    p2 = {"name": "status", "type": "str", "enum_values": ["active", "inactive"], "location": "body"}

    s1 = SchemaInferencer.infer_parameter_schema(p1)
    s2 = SchemaInferencer.infer_parameter_schema(p2)

    scenarios = CombinatorialSynthesizer.generate_combinatorial_scenarios(
        endpoint_id="ep-1",
        schemas=[s1, s2],
        strength=2,
        max_combinations=10
    )

    assert len(scenarios) > 0
    assert scenarios[0].test_type.value == "COMBINATORIAL"
