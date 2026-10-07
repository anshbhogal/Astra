"""
AdvancedTestSuiteGenerator: Orchestrates schema inferencer, IR scenario builder, data generators,
combinatorial synthesizer, deduplicator, prioritizer, and embeds provenance into TestSpecification.
"""

import uuid
from typing import List, Dict, Any, Tuple
from engine.schema.type_inferencer import SchemaInferencer
from engine.schema.models import NormalizedFieldSchema, FieldType
from engine.generator.models import (
    TestScenario,
    ParameterMutation,
    TestType,
    StatusSource,
    MutationReason,
)
from engine.generator.data_generators.numeric import NumericBoundaryGenerator
from engine.generator.data_generators.string import StringBoundaryGenerator
from engine.generator.data_generators.format import FormatBoundaryGenerator
from engine.generator.data_generators.collections import CollectionGenerator
from engine.generator.data_generators.location_mutators import LocationMutator
from engine.generator.data_generators.security import SecurityProbeGenerator
from engine.generator.combinatorial import CombinatorialSynthesizer
from engine.generator.deduplicator import PayloadDeduplicator
from engine.generator.prioritizer import TestPrioritizer
from engine.generator.strategy import TestGenerationStrategy
from engine.models.test_spec import TestSpecification, AssertionRule, AssertionType


class AdvancedTestSuiteGenerator:
    """Advanced rule-based synthetic test suite generator for Phase 4."""

    GENERATOR_VERSION = "4.0.0"

    def generate_suite_for_endpoints(
        self,
        endpoints: List[Any],
        strategy: TestGenerationStrategy,
        suite_name: str = "Advanced Synthetic Suite"
    ) -> Tuple[List[TestSpecification], Dict[str, Any]]:
        """
        Main pipeline:
        AST Endpoints -> Schema Inferencer -> Scenarios (IR) -> Prioritizer -> TestSpecification -> Deduplicator.
        Returns (test_specifications, generation_report_dict).
        """
        config_hash = strategy.compute_configuration_hash()
        all_scenarios: List[TestScenario] = []

        total_candidates = 0
        breakdown_by_type: Dict[str, int] = {}

        for ep in endpoints:
            ep_id = str(ep.id) if hasattr(ep, "id") else str(uuid.uuid4())
            method = ep.method.upper() if hasattr(ep, "method") else "GET"
            path = ep.path if hasattr(ep, "path") else "/"

            schemas = SchemaInferencer.infer_endpoint_schemas(ep)

            # 1. Happy Path Scenario
            if strategy.include_happy_path:
                hp_scenario = self._create_happy_path_scenario(ep_id, method, path, schemas)
                all_scenarios.append(hp_scenario)

            # 2. Field Boundary & Mutation Scenarios
            for s in schemas:
                mutations: List[ParameterMutation] = []

                if s.field_type in [FieldType.INTEGER, FieldType.FLOAT] and strategy.include_boundary_tests:
                    mutations.extend(NumericBoundaryGenerator.generate_mutations(s))

                elif s.field_type == FieldType.STRING and strategy.include_boundary_tests:
                    mutations.extend(StringBoundaryGenerator.generate_mutations(s))

                if s.constraint.format or s.constraint.enum_values:
                    if strategy.include_format_violations:
                        mutations.extend(FormatBoundaryGenerator.generate_mutations(s))

                if s.field_type == FieldType.ARRAY and strategy.include_boundary_tests:
                    mutations.extend(CollectionGenerator.generate_array_mutations(s))

                if s.field_type == FieldType.OBJECT and strategy.include_boundary_tests:
                    mutations.extend(CollectionGenerator.generate_object_mutations(s))

                if s.location == "path" and strategy.include_boundary_tests:
                    mutations.extend(LocationMutator.generate_path_mutations(s))

                if s.location == "query" and strategy.include_boundary_tests:
                    mutations.extend(LocationMutator.generate_query_mutations(s))

                if s.location == "header" and strategy.include_boundary_tests:
                    mutations.extend(LocationMutator.generate_header_mutations(s))

                # Opt-in Security Probes
                if strategy.include_security_probes:
                    mutations.extend(SecurityProbeGenerator.generate_security_probes(s))

                # Convert mutations to TestScenario objects
                for mut in mutations:
                    sc = self._mutation_to_scenario(ep_id, method, path, s, mut)
                    all_scenarios.append(sc)

            # 3. Method Not Allowed Scenario
            if strategy.include_boundary_tests:
                method_mut = LocationMutator.generate_unsupported_method_mutation(method)
                all_scenarios.append(TestScenario(
                    endpoint_id=ep_id,
                    scenario_name=f"Unsupported Method {method_mut.mutated_value} on {path}",
                    test_type=TestType.METHOD_NOT_ALLOWED,
                    mutations=[method_mut],
                    expected_status_codes=[405],
                    expected_status_source=StatusSource.FRAMEWORK_CONVENTION
                ))

            # 4. Combinatorial N-wise Scenarios
            if strategy.pairwise_strength >= 1:
                comb_scenarios = CombinatorialSynthesizer.generate_combinatorial_scenarios(
                    endpoint_id=ep_id,
                    schemas=schemas,
                    strength=strategy.pairwise_strength,
                    max_combinations=strategy.max_cases_per_endpoint
                )
                all_scenarios.extend(comb_scenarios)

        total_candidates = len(all_scenarios)

        # 5. Prioritization & Budget Truncation
        prioritized_scenarios, truncated_count = TestPrioritizer.prioritize_and_cap(
            all_scenarios, max_total_cases=strategy.max_total_cases
        )

        # 6. Compile Scenarios into TestSpecification instances
        raw_specs: List[TestSpecification] = []
        execution_order = 1
        for sc in prioritized_scenarios:
            spec = self._compile_scenario_to_spec(sc, execution_order, config_hash, strategy.seed)
            raw_specs.append(spec)
            execution_order += 1

            # Count breakdown
            t_name = sc.test_type.value if hasattr(sc.test_type, "value") else str(sc.test_type)
            breakdown_by_type[t_name] = breakdown_by_type.get(t_name, 0) + 1

        # 7. Deduplicate Specifications
        deduped_specs, deduped_count = PayloadDeduplicator.deduplicate_specifications(raw_specs)

        report = {
            "generator_version": self.GENERATOR_VERSION,
            "configuration_hash": config_hash,
            "seed": strategy.seed,
            "total_candidates": total_candidates,
            "total_generated": len(deduped_specs),
            "total_deduplicated": deduped_count,
            "total_truncated": truncated_count,
            "breakdown_by_type": breakdown_by_type
        }

        return deduped_specs, report

    def _create_happy_path_scenario(
        self, ep_id: str, method: str, path: str, schemas: List[NormalizedFieldSchema]
    ) -> TestScenario:
        mutations: List[ParameterMutation] = []
        for s in schemas:
            val = s.constraint.default_value.value if s.constraint.default_value else "valid_sample"
            if s.field_type == FieldType.INTEGER:
                val = s.constraint.min_value.value if s.constraint.min_value else 1
            elif s.field_type == FieldType.BOOLEAN:
                val = True
            elif s.constraint.format and s.constraint.format.value == "uuid":
                val = "123e4567-e89b-12d3-a456-426614174000"
            elif s.constraint.format and s.constraint.format.value == "email":
                val = "test@astra.local"

            mutations.append(ParameterMutation(
                field_path=s.name, original_value=val, mutated_value=val,
                reason=MutationReason.HAPPY_PATH_VALID, location=s.location
            ))

        expected_status = [200, 201, 204] if method in ["POST", "PUT"] else [200]
        return TestScenario(
            endpoint_id=ep_id,
            scenario_name=f"Happy Path — {method} {path}",
            test_type=TestType.HAPPY_PATH,
            mutations=mutations,
            expected_status_codes=expected_status,
            expected_status_source=StatusSource.STATIC_RULE
        )

    def _mutation_to_scenario(
        self, ep_id: str, method: str, path: str, schema: NormalizedFieldSchema, mut: ParameterMutation
    ) -> TestScenario:
        t_type = TestType.BOUNDARY
        exp_status = [400, 422]

        if mut.reason in [MutationReason.MIN_VALUE, MutationReason.MAX_VALUE, MutationReason.HAPPY_PATH_VALID, MutationReason.ENUM_VALID]:
            exp_status = [200, 201, 204] if method in ["POST", "PUT"] else [200]
            t_type = TestType.HAPPY_PATH if mut.reason == MutationReason.HAPPY_PATH_VALID else TestType.BOUNDARY
        elif mut.reason == MutationReason.SECURITY_PROBE:
            t_type = TestType.SECURITY_PROBE
            exp_status = [200, 400, 422]  # Non-crashing security resilience
        elif mut.reason == MutationReason.STRICTLY_INVALID_TYPE:
            t_type = TestType.INVALID_TYPE
        elif mut.reason == MutationReason.INVALID_FORMAT:
            t_type = TestType.INVALID_FORMAT

        return TestScenario(
            endpoint_id=ep_id,
            scenario_name=f"Mutation '{mut.field_path}' [{mut.reason.value}] — {method} {path}",
            test_type=t_type,
            mutations=[mut],
            expected_status_codes=exp_status,
            expected_status_source=StatusSource.FRAMEWORK_CONVENTION
        )

    def _compile_scenario_to_spec(
        self, scenario: TestScenario, order: int, config_hash: str, seed: int
    ) -> TestSpecification:
        path_params = {}
        query_params = {}
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        body = {}
        method = "GET"

        for mut in scenario.mutations:
            if mut.location == "method":
                method = str(mut.mutated_value)
            elif mut.location == "path":
                path_params[mut.field_path] = mut.mutated_value
            elif mut.location == "query":
                query_params[mut.field_path] = mut.mutated_value
            elif mut.location == "header":
                headers[mut.field_path] = str(mut.mutated_value)
            else:
                body[mut.field_path] = mut.mutated_value

        expected_status = scenario.expected_status_codes if scenario.expected_status_codes else [200]

        assertions = [
            AssertionRule(type=AssertionType.STATUS_CODE, expected=expected_status),
            AssertionRule(type=AssertionType.LATENCY_SLA, expected=5000)
        ]

        # Embed Provenance
        provenance = {
            "generator_version": self.GENERATOR_VERSION,
            "configuration_hash": config_hash,
            "seed": seed,
            "scenario_name": scenario.scenario_name,
            "mutations": [m.to_dict() for m in scenario.mutations]
        }

        return TestSpecification(
            id=str(uuid.uuid4()),
            name=scenario.scenario_name,
            endpoint_id=scenario.endpoint_id,
            test_type=scenario.test_type,
            method=method,
            path=scenario.scenario_name.split(" — ")[-1] if " — " in scenario.scenario_name else "/",
            path_params=path_params,
            query_params=query_params,
            headers=headers,
            body=body if body else None,
            auth_ref=None if scenario.auth_omitted else {"type": "bearer", "credential_ref": "default-test-token"},
            expected_status=expected_status,
            expected_status_source=scenario.expected_status_source,
            assertions=assertions,
            timeout_ms=10000,
            execution_order=order,
            metadata=provenance
        )
