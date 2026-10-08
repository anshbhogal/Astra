"""
LLM Boundary Explorer Engine.
"""

import uuid
from typing import List, Dict, Any
from app.models.domain import DiscoveredEndpoint
from engine.intelligence.models import RequirementSpec, LLMScenarioCandidate
from engine.intelligence.providers.factory import LLMProviderFactory
from engine.intelligence.security.prompt_guard import PromptGuard
from engine.generator.models import TestType, ParameterMutation, MutationReason


class LLMBoundaryExplorer:
    def __init__(self, provider_name: str = "gemini", model: str = None, api_key: str = None):
        self.provider_name = provider_name
        self.model = model
        self.provider = LLMProviderFactory.get_provider(provider_name, model=model, api_key=api_key)
        self.prompt_version = "5.0.2"

    async def explore_scenarios(
        self,
        endpoint: DiscoveredEndpoint,
        requirements: List[RequirementSpec]
    ) -> List[LLMScenarioCandidate]:
        candidates: List[LLMScenarioCandidate] = []
        if not requirements:
            return candidates

        ep_summary = f"Endpoint: {endpoint.method} {endpoint.path} (Function: {endpoint.function_name})"
        req_texts = "\n".join([f"- [{r.id}] {r.title}: {r.description}" for r in requirements])
        
        guarded_req_doc = PromptGuard.prepare_guarded_prompt(req_texts)

        system_prompt = (
            "You are an expert AI software test engineer.\n"
            "Analyze the target REST API endpoint and the untrusted business requirement specifications.\n"
            "Propose edge-case scenarios testing business logic invariants, state transitions, and multi-parameter dependencies.\n"
            "DO NOT create simple structural type errors (Phase 4 handles those).\n"
            "Focus on realistic domain business rule edge cases (e.g. balance limits, payment states, authorization)."
        )

        user_prompt = (
            f"TARGET ENDPOINT:\n{ep_summary}\n\n"
            f"REQUIREMENT SPECIFICATIONS:\n{guarded_req_doc}\n\n"
            f"Generate candidate edge-case test scenarios."
        )

        response_schema = {
            "type": "object",
            "properties": {
                "scenarios": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "scenario_description": {"type": "string"},
                            "requirement_ids": {"type": "array", "items": {"type": "string"}},
                            "target_field": {"type": "string"},
                            "original_value": {"type": "string"},
                            "mutated_value": {"type": "string"},
                            "mutation_reason": {"type": "string"},
                            "rationale": {"type": "string"},
                            "confidence": {"type": "number"}
                        },
                        "required": ["scenario_description", "target_field", "mutated_value", "rationale"]
                    }
                }
            }
        }

        res = await self.provider.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=response_schema,
            temperature=0.1
        )

        if not res.structured_data or "scenarios" not in res.structured_data:
            return candidates

        raw_scenarios = res.structured_data.get("scenarios", [])
        for sc in raw_scenarios:
            field_name = sc.get("target_field", "body")
            mutated_val = sc.get("mutated_value", "")
            orig_val = sc.get("original_value", None)
            reason_str = sc.get("mutation_reason", "SECURITY_PROBE")

            mutation = ParameterMutation(
                field_path=field_name,
                original_value=orig_val,
                mutated_value=mutated_val,
                reason=MutationReason.SECURITY_PROBE,
                constraint_rule=sc.get("rationale", "")
            )

            cand = LLMScenarioCandidate(
                candidate_id=f"LLM-CAND-{uuid.uuid4().hex[:8].upper()}",
                requirement_ids=sc.get("requirement_ids", [r.id for r in requirements]),
                endpoint_id=str(endpoint.id),
                scenario_description=sc.get("scenario_description", "AI Boundary Edge Case"),
                test_type=TestType.BOUNDARY,
                mutations=[mutation],
                rationale=sc.get("rationale", "Derived from business logic requirements"),
                assumptions=[],
                confidence=float(sc.get("confidence", 0.85)),
                provider=self.provider_name,
                model=res.model_name,
                prompt_version=self.prompt_version,
                validation_status="PENDING"
            )
            candidates.append(cand)

        return candidates
