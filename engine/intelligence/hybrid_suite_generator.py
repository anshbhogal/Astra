"""
Hybrid Test Suite Generator Pipeline (Deterministic BVA Rules + AI LLM Candidates).
"""

from typing import List, Dict, Any, Tuple
from app.models.domain import DiscoveredEndpoint
from engine.generator.strategy import TestGenerationStrategy
from engine.generator.advanced_suite_generator import AdvancedTestSuiteGenerator
from engine.generator.models import TestScenario
from engine.models.test_spec import TestSpecification
from engine.generator.deduplicator import PayloadDeduplicator
from engine.generator.prioritizer import TestPrioritizer
from engine.compiler.test_compiler import TestCompiler

from engine.intelligence.models import RequirementSpec, LLMScenarioCandidate
from engine.intelligence.exploration.boundary_explorer import LLMBoundaryExplorer
from engine.intelligence.validators.scenario_validator import CandidateValidator
from engine.intelligence.budget.budget_manager import AIBudgetManager


class HybridSuiteGenerator:
    def __init__(
        self,
        enable_ai: bool = True,
        provider_name: str = "gemini",
        model: str = None,
        api_key: str = None
    ):
        self.enable_ai = enable_ai
        self.provider_name = provider_name
        self.model = model
        self.api_key = api_key
        self.phase4_generator = AdvancedTestSuiteGenerator()
        self.budget_manager = AIBudgetManager()

    async def generate_hybrid_suite(
        self,
        endpoints: List[DiscoveredEndpoint],
        requirements: List[RequirementSpec],
        strategy: TestGenerationStrategy,
        suite_name: str = "Hybrid Synthetic Test Suite"
    ) -> Tuple[List[TestSpecification], Dict[str, Any]]:
        report = {
            "total_candidates": 0,
            "deterministic_count": 0,
            "ai_candidates_generated": 0,
            "ai_candidates_validated": 0,
            "ai_candidates_rejected": 0,
            "rejection_reasons": [],
            "total_deduplicated": 0,
            "total_generated": 0,
            "requirement_coverage_pct": 0.0
        }

        # 1. Deterministic Phase 4 Rule Generation
        rule_specs, rule_report = self.phase4_generator.generate_suite_for_endpoints(
            endpoints, strategy, suite_name=f"{suite_name} (Rule-Based)"
        )
        report["deterministic_count"] = len(rule_specs)
        all_scenarios: List[TestScenario] = []

        # 2. AI Boundary Candidate Exploration
        if self.enable_ai and requirements and self.budget_manager.can_make_call():
            explorer = LLMBoundaryExplorer(
                provider_name=self.provider_name,
                model=self.model,
                api_key=self.api_key
            )

            for ep in endpoints:
                # Find mapped requirements for this endpoint
                ep_reqs = [
                    r for r in requirements
                    if str(ep.id) in r.target_endpoints or any(str(ep.id) in br.affected_endpoints for br in r.business_rules)
                ]
                if not ep_reqs:
                    ep_reqs = requirements[:2]  # Fallback to top requirements if unmapped

                if self.budget_manager.can_make_call():
                    candidates = await explorer.explore_scenarios(ep, ep_reqs)
                    report["ai_candidates_generated"] += len(candidates)

                    for cand in candidates:
                        valid, scenario, err_msg = CandidateValidator.validate_candidate(cand, endpoints)
                        if valid and scenario:
                            all_scenarios.append(scenario)
                            report["ai_candidates_validated"] += 1
                        else:
                            report["ai_candidates_rejected"] += 1
                            if err_msg and err_msg not in report["rejection_reasons"]:
                                report["rejection_reasons"].append(err_msg)

        report["total_candidates"] = report["deterministic_count"] + report["ai_candidates_generated"]

        # 3. Deduplication & Prioritization
        # Compile rule_specs back to scenarios or merge with AI scenarios
        final_scenarios = self._merge_and_deduplicate(rule_specs, all_scenarios, endpoints)
        report["total_deduplicated"] = (report["total_candidates"]) - len(final_scenarios)

        # 4. Prioritize & Limit
        prioritized = TestPrioritizer.prioritize_scenarios(final_scenarios)
        limited = prioritized[:strategy.max_total_cases]

        # 5. Compile into final TestSpecifications
        final_specs = []
        for sc in limited:
            matched_ep = next((e for e in endpoints if str(e.id) == str(sc.endpoint_id)), endpoints[0] if endpoints else None)
            if matched_ep:
                spec = self.phase4_generator._compile_scenario_to_spec(sc, matched_ep)
                final_specs.append(spec)

        report["total_generated"] = len(final_specs)
        
        # Calculate requirement coverage
        if requirements:
            mapped_reqs = sum(1 for r in requirements if r.status in ["MAPPED", "APPROVED"])
            report["requirement_coverage_pct"] = round((mapped_reqs / len(requirements)) * 100, 2)

        return final_specs, report

    def _merge_and_deduplicate(
        self, rule_specs: List[TestSpecification], ai_scenarios: List[TestScenario], endpoints: List[DiscoveredEndpoint]
    ) -> List[TestScenario]:
        dedup = PayloadDeduplicator()
        unique_scenarios: List[TestScenario] = []

        # Process rule specs
        for spec in rule_specs:
            fp = dedup.create_fingerprint(
                method=spec.method,
                path=spec.path,
                query_params=spec.query_params,
                headers=spec.headers,
                body=spec.body_payload,
                test_type=spec.test_type.value
            )
            if dedup.is_unique(fp):
                sc = TestScenario(
                    endpoint_id=spec.endpoint_id,
                    scenario_name=spec.name,
                    test_type=spec.test_type,
                    mutations=[],
                    expected_status_codes=spec.expected_status_codes
                )
                unique_scenarios.append(sc)

        # Process AI scenarios
        for sc in ai_scenarios:
            matched_ep = next((e for e in endpoints if str(e.id) == str(sc.endpoint_id)), None)
            if matched_ep:
                body_payload = {}
                for m in sc.mutations:
                    body_payload[m.field_path] = m.mutated_value

                fp = dedup.create_fingerprint(
                    method=matched_ep.method,
                    path=matched_ep.path,
                    query_params={},
                    headers={},
                    body=body_payload,
                    test_type=sc.test_type.value
                )
                if dedup.is_unique(fp):
                    unique_scenarios.append(sc)

        return unique_scenarios
