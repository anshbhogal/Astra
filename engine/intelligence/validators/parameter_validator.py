"""
Parameter Existence Validator.
"""

from typing import List, Optional, Tuple
from app.models.domain import DiscoveredEndpoint
from engine.intelligence.models import LLMScenarioCandidate


class ParameterValidator:
    @staticmethod
    def validate(candidate: LLMScenarioCandidate, endpoint: DiscoveredEndpoint) -> Tuple[bool, Optional[str]]:
        ep_param_names = [
            (p.get("name") if isinstance(p, dict) else getattr(p, "name", "")).lower()
            for p in (getattr(endpoint, "parameters", []) or [])
        ]
        
        # If endpoint parameters are empty (e.g. body payload), allow top-level fields
        if not ep_param_names:
            return True, None

        for mut in candidate.mutations:
            field_name = mut.field_path.lower()
            if field_name not in ep_param_names and field_name != "body":
                return False, f"Hallucinated parameter '{mut.field_path}' does not exist on endpoint {endpoint.method} {endpoint.path}"

        return True, None
