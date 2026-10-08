"""
Requirement-to-Endpoint Mapper with Multi-Signal Status Assignment.
"""

from typing import List, Dict, Any
from app.models.domain import DiscoveredEndpoint
from engine.intelligence.models import (
    RequirementSpec, RequirementEndpointMapping, MappingStatus, RequirementStatus
)
from engine.intelligence.mapping.mapping_scoring import MappingScorer


class RequirementMapper:
    @staticmethod
    def map_requirements_to_endpoints(
        requirements: List[RequirementSpec], endpoints: List[DiscoveredEndpoint]
    ) -> List[RequirementEndpointMapping]:
        all_mappings: List[RequirementEndpointMapping] = []

        for req in requirements:
            ep_mappings = MappingScorer.calculate_mapping(req, endpoints)

            if not ep_mappings:
                req.mapping_status = MappingStatus.UNMAPPED
                req.status = RequirementStatus.EXTRACTED
            elif len(ep_mappings) == 1 and ep_mappings[0].confidence >= 0.80:
                req.mapping_status = MappingStatus.MAPPED
                req.status = RequirementStatus.MAPPED
                req.target_endpoints = [ep_mappings[0].endpoint_id]
                all_mappings.append(ep_mappings[0])
            elif len(ep_mappings) > 1 and ep_mappings[0].confidence >= 0.80 and ep_mappings[0].confidence > ep_mappings[1].confidence:
                req.mapping_status = MappingStatus.MAPPED
                req.status = RequirementStatus.MAPPED
                req.target_endpoints = [ep_mappings[0].endpoint_id]
                all_mappings.append(ep_mappings[0])
            else:
                req.mapping_status = MappingStatus.AMBIGUOUS
                req.status = RequirementStatus.NEEDS_REVIEW
                all_mappings.extend(ep_mappings)

        return all_mappings
