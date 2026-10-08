"""
Multi-Signal Endpoint Mapping Scoring Engine.
"""

from typing import List, Dict, Any, Tuple
from app.models.domain import DiscoveredEndpoint
from engine.intelligence.models import RequirementSpec, RequirementEndpointMapping, MappingStatus


class MappingScorer:
    @staticmethod
    def calculate_mapping(
        req: RequirementSpec, endpoints: List[DiscoveredEndpoint]
    ) -> List[RequirementEndpointMapping]:
        mappings: List[RequirementEndpointMapping] = []
        req_text = (req.title + " " + req.description + " " + " ".join(req.target_endpoints)).lower()

        for ep in endpoints:
            score = 0.0
            signals = []

            ep_path = ep.path.lower()
            ep_method = ep.method.lower()
            ep_func = ep.function_name.lower()
            ep_full = f"{ep_method} {ep_path}"

            # 1. Exact Endpoint Mention (HTTP Method + Path)
            if ep_full in req_text:
                score = max(score, 0.95)
                signals.append("EXACT_METHOD_PATH_MATCH")
            elif ep_path in req_text:
                score = max(score, 0.85)
                signals.append("EXACT_PATH_MATCH")

            # 2. Function Name Heuristic
            if ep_func in req_text or ep_func.replace("_", "") in req_text:
                score = max(score, 0.70)
                signals.append("FUNCTION_NAME_MATCH")

            # 3. Parameter Overlap
            ep_params = [
                (p.get("name") if isinstance(p, dict) else getattr(p, "name", "")).lower()
                for p in (getattr(ep, "parameters", []) or [])
            ]
            matched_params = [p for p in ep_params if p in req_text]
            if matched_params:
                param_score = 0.50 + min(len(matched_params) * 0.1, 0.25)
                score = max(score, param_score)
                signals.append(f"PARAM_MATCH_{len(matched_params)}")

            # 4. Entity / Domain Overlap
            path_segments = [seg for seg in ep_path.split("/") if seg and not seg.startswith("{")]
            matched_segments = [seg for seg in path_segments if seg in req_text]
            if matched_segments:
                score = max(score, 0.60)
                signals.append(f"ENTITY_MATCH_{matched_segments[0]}")

            if score > 0.40:
                mapping_status = MappingStatus.MAPPED if score >= 0.80 else MappingStatus.AMBIGUOUS
                mappings.append(RequirementEndpointMapping(
                    requirement_id=req.id,
                    endpoint_id=str(ep.id),
                    confidence=round(score, 2),
                    evidence=signals,
                    mapping_method=signals[0] if signals else "HEURISTIC",
                    status=mapping_status
                ))

        # Sort mappings by confidence descending
        mappings.sort(key=lambda m: m.confidence, reverse=True)

        if len(mappings) > 1 and mappings[0].confidence == mappings[1].confidence:
            for m in mappings:
                m.status = MappingStatus.MULTIPLE_MATCHES

        return mappings
