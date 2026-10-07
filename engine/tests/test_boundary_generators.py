"""
Unit tests for numeric, string, format, collections, and security data generators.
"""

import pytest
from engine.schema.type_inferencer import SchemaInferencer
from engine.generator.data_generators.numeric import NumericBoundaryGenerator
from engine.generator.data_generators.string import StringBoundaryGenerator
from engine.generator.data_generators.security import SecurityProbeGenerator
from engine.generator.models import MutationReason


def test_numeric_boundary_generator():
    param_dict = {"name": "age", "type": "int", "ge": 18, "le": 60}
    schema = SchemaInferencer.infer_parameter_schema(param_dict)

    mutations = NumericBoundaryGenerator.generate_mutations(schema)
    reasons = [m.reason for m in mutations]

    assert MutationReason.MIN_VALUE in reasons
    assert MutationReason.MIN_MINUS_ONE in reasons
    assert MutationReason.MAX_VALUE in reasons
    assert MutationReason.MAX_PLUS_ONE in reasons
    assert MutationReason.STRICTLY_INVALID_TYPE in reasons

    min_mut = next(m for m in mutations if m.reason == MutationReason.MIN_VALUE)
    assert min_mut.mutated_value == 18

    min_minus_mut = next(m for m in mutations if m.reason == MutationReason.MIN_MINUS_ONE)
    assert min_minus_mut.mutated_value == 17


def test_string_boundary_generator():
    param_dict = {"name": "username", "type": "str", "min_length": 3, "max_length": 10}
    schema = SchemaInferencer.infer_parameter_schema(param_dict)

    mutations = StringBoundaryGenerator.generate_mutations(schema)
    reasons = [m.reason for m in mutations]

    assert MutationReason.EMPTY_STRING in reasons
    assert MutationReason.MIN_MINUS_ONE in reasons
    assert MutationReason.MAX_VALUE in reasons
    assert MutationReason.LENGTH_OVERFLOW in reasons

    overflow_mut = next(m for m in mutations if m.reason == MutationReason.LENGTH_OVERFLOW)
    assert len(overflow_mut.mutated_value) == 11


def test_security_probe_generator():
    param_dict = {"name": "query", "type": "str"}
    schema = SchemaInferencer.infer_parameter_schema(param_dict)

    mutations = SecurityProbeGenerator.generate_security_probes(schema)
    assert len(mutations) == 4
    for m in mutations:
        assert m.reason == MutationReason.SECURITY_PROBE
