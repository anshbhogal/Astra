"""
Endpoint Existence & Method Validator.
"""

from typing import List, Optional, Tuple
from app.models.domain import DiscoveredEndpoint
from engine.intelligence.models import LLMScenarioCandidate


class EndpointValidator:
    @staticmethod
    def validate(candidate: LLMScenarioCandidate, endpoints: List[DiscoveredEndpoint]) -> Tuple[bool, Optional[str]]:
        if not candidate.endpoint_id:
            return False, "Candidate missing endpoint_id target"

        matched_ep = next((ep for ep in endpoints if str(ep.id) == str(candidate.endpoint_id)), None)
        if not matched_ep:
            return False, f"Target endpoint {candidate.endpoint_id} does not exist in AST Knowledge Graph"

        return True, None
