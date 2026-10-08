"""
Deterministic OpenAPI 3.x Requirement Parser.
"""

import json
import yaml
import hashlib
from typing import List, Dict, Any
from engine.intelligence.parsers.base import BaseRequirementParser
from engine.intelligence.models import (
    RequirementSpec, RequirementType, RequirementSource, SourceLocation, BusinessRule
)


class OpenAPIRequirementParser(BaseRequirementParser):
    def parse(self, content: str, project_id: str, document_id: str) -> List[RequirementSpec]:
        requirements: List[RequirementSpec] = []
        try:
            if content.strip().startswith("{"):
                spec_dict = json.loads(content)
            else:
                spec_dict = yaml.safe_load(content)
        except Exception:
            return requirements

        paths = spec_dict.get("paths", {})
        for path_key, methods in paths.items():
            if not isinstance(methods, dict):
                continue

            for method, details in methods.items():
                if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    continue

                op_id = details.get("operationId", f"{method.upper()}_{path_key}")
                summary = details.get("summary", "")
                description = details.get("description", "")
                full_desc = f"{summary}\n{description}".strip()

                req_id = f"REQ-OAPI-{hashlib.sha256(f'{method}_{path_key}'.encode()).hexdigest()[:8].upper()}"
                
                location = SourceLocation(section=f"{method.upper()} {path_key}")
                biz_rule = BusinessRule(
                    rule_id=f"BR-{req_id}",
                    description=summary or description or f"Operation {op_id}",
                    affected_endpoints=[f"{method.upper()} {path_key}"]
                )

                req_spec = RequirementSpec(
                    id=req_id,
                    project_id=project_id,
                    document_id=document_id,
                    source=RequirementSource.OPENAPI_SPEC,
                    source_location=location,
                    title=f"Endpoint Requirement: {method.upper()} {path_key}",
                    description=full_desc or f"{method.upper()} {path_key} specification",
                    requirement_type=RequirementType.FUNCTIONAL,
                    target_endpoints=[f"{method.upper()} {path_key}"],
                    confidence=1.0,
                    business_rules=[biz_rule],
                    extraction_method="DETERMINISTIC_OPENAPI_PARSER",
                    content_hash=hashlib.sha256(f"{method}_{path_key}".encode()).hexdigest()
                )
                requirements.append(req_spec)

        return requirements
