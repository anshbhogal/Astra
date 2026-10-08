"""
Deterministic Markdown & PRD Requirement Parser.
"""

import re
import hashlib
from typing import List, Optional
from engine.intelligence.parsers.base import BaseRequirementParser
from engine.intelligence.models import (
    RequirementSpec, RequirementType, RequirementSource, SourceLocation, BusinessRule
)


class MarkdownRequirementParser(BaseRequirementParser):
    def parse(self, content: str, project_id: str, document_id: str) -> List[RequirementSpec]:
        requirements: List[RequirementSpec] = []
        lines = content.splitlines()

        current_section = "General Requirements"
        current_req_title: Optional[str] = None
        current_req_lines: List[str] = []
        start_line = 1

        rule_keywords = ["MUST", "SHALL", "SHOULD", "CANNOT", "REQUIRED", "ONLY", "VERIFY", "RESTRICT"]

        for idx, line in enumerate(lines, start=1):
            line_str = line.strip()

            # Section Headers
            if line_str.startswith("#"):
                header_match = re.sub(r"^#+\s*", "", line_str)
                if header_match:
                    current_section = header_match

            # Bullet points or User Stories
            if line_str.startswith("- ") or line_str.startswith("* ") or re.match(r"^\d+\.\s+", line_str):
                text = re.sub(r"^[-*\d.]+\s*", "", line_str)

                # Check if it contains business requirement keywords
                upper_text = text.upper()
                if any(kw in upper_text for kw in rule_keywords) or "AS A " in upper_text:
                    req_id = f"REQ-MD-{hashlib.sha256(text.encode()).hexdigest()[:8].upper()}"

                    # Determine type
                    req_type = RequirementType.FUNCTIONAL
                    if "SECURITY" in upper_text or "AUTH" in upper_text:
                        req_type = RequirementType.SECURITY
                    elif "LIMIT" in upper_text or "MIN" in upper_text or "MAX" in upper_text:
                        req_type = RequirementType.VALIDATION
                    elif "MUST NOT" in upper_text or "CANNOT" in upper_text:
                        req_type = RequirementType.BUSINESS_RULE

                    location = SourceLocation(
                        line_start=idx,
                        line_end=idx,
                        section=current_section
                    )

                    biz_rule = BusinessRule(
                        rule_id=f"BR-{req_id}",
                        description=text
                    )

                    req_spec = RequirementSpec(
                        id=req_id,
                        project_id=project_id,
                        document_id=document_id,
                        source=RequirementSource.PRD_MARKDOWN,
                        source_location=location,
                        title=text[:60] + "..." if len(text) > 60 else text,
                        description=text,
                        requirement_type=req_type,
                        confidence=0.95,
                        business_rules=[biz_rule],
                        acceptance_criteria=[text],
                        extraction_method="DETERMINISTIC_MARKDOWN_PARSER",
                        content_hash=hashlib.sha256(text.encode()).hexdigest()
                    )
                    requirements.append(req_spec)

        return requirements
