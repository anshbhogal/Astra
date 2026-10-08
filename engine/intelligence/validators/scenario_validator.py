"""
Master Candidate Validator & Hallucination Defense Subsystem.
"""

from typing import List, Optional, Tuple
from app.models.domain import DiscoveredEndpoint
from engine.intelligence.models import LLMScenarioCandidate
from engine.generator.models import TestScenario, TestType, StatusSource
from engine.intelligence.validators.endpoint_validator import EndpointValidator
from engine.intelligence.validators.parameter_validator import ParameterValidator
from engine.intelligence.validators.safety_validator import SafetyValidator


class CandidateValidator:
    @classmethod
    def validate_candidate(
        cls, candidate: LLMScenarioCandidate, endpoints: List[DiscoveredEndpoint]
    ) -> Tuple[bool, Optional[TestScenario], Optional[str]]:
        # 1. Endpoint Existence Check
        valid_ep, err_ep = EndpointValidator.validate(candidate, endpoints)
        if not valid_ep:
            candidate.validation_status = "REJECTED"
            candidate.rejection_reason = err_ep
            return False, None, err_ep

        matched_ep = next(ep for ep in endpoints if str(ep.id) == str(candidate.endpoint_id))

        # 2. Parameter Existence Check
        valid_param, err_param = ParameterValidator.validate(candidate, matched_ep)
        if not valid_param:
            candidate.validation_status = "REJECTED"
            candidate.rejection_reason = err_param
            return False, None, err_param

        # 3. Safety Policy Check
        valid_safety, err_safety = SafetyValidator.validate(candidate)
        if not valid_safety:
            candidate.validation_status = "REJECTED"
            candidate.rejection_reason = err_safety
            return False, None, err_safety

        # Validation Passed! Convert candidate into a TestScenario
        candidate.validation_status = "VALIDATED"
        scenario = TestScenario(
            endpoint_id=str(matched_ep.id),
            scenario_name=f"[AI: {candidate.provider}] {candidate.scenario_description}",
            test_type=candidate.test_type or TestType.BOUNDARY,
            mutations=candidate.mutations,
            expected_status_codes=None,
            expected_status_source=StatusSource.UNKNOWN,
            metadata={
                "candidate_id": candidate.candidate_id,
                "requirement_ids": candidate.requirement_ids,
                "rationale": candidate.rationale,
                "provider": candidate.provider,
                "model": candidate.model,
                "prompt_version": candidate.prompt_version,
                "confidence": candidate.confidence
            }
        )

        return True, scenario, None
