"""
Deterministic Gherkin Feature Parser & Step Classifier IR.
"""

import re
import hashlib
from typing import List, Optional, Dict, Any
from engine.intelligence.parsers.base import BaseRequirementParser
from engine.intelligence.models import (
    RequirementSpec, RequirementType, RequirementSource, SourceLocation, BusinessRule,
    GherkinScenario, GherkinScenarioStep
)


class GherkinRequirementParser(BaseRequirementParser):
    def parse(self, content: str, project_id: str, document_id: str) -> List[RequirementSpec]:
        requirements: List[RequirementSpec] = []
        lines = content.splitlines()

        feature_title = "Untitled Feature"
        current_scenario_title: Optional[str] = None
        current_scenario_steps: List[GherkinScenarioStep] = []
        scenario_start_line = 1

        for idx, line in enumerate(lines, start=1):
            line_str = line.strip()

            if line_str.startswith("Feature:"):
                feature_title = line_str.replace("Feature:", "").strip()

            elif line_str.startswith("Scenario:") or line_str.startswith("Scenario Outline:"):
                if current_scenario_title and current_scenario_steps:
                    req_spec = self._build_requirement_spec(
                        project_id=project_id,
                        document_id=document_id,
                        feature_title=feature_title,
                        scenario_title=current_scenario_title,
                        steps=current_scenario_steps,
                        start_line=scenario_start_line,
                        end_line=idx - 1
                    )
                    requirements.append(req_spec)

                current_scenario_title = re.sub(r"^Scenario (Outline)?:", "", line_str).strip()
                current_scenario_steps = []
                scenario_start_line = idx

            elif any(line_str.startswith(kw) for kw in ["Given ", "When ", "Then ", "And ", "But "]):
                parts = line_str.split(" ", 1)
                keyword = parts[0]
                text = parts[1] if len(parts) > 1 else ""

                # Step classification
                step_type = "PRECONDITION"
                if keyword in ["Given"]:
                    step_type = "PRECONDITION"
                elif keyword in ["When"]:
                    step_type = "ACTION"
                elif keyword in ["Then"]:
                    step_type = "EXPECTED"
                elif keyword in ["And", "But"]:
                    step_type = current_scenario_steps[-1].step_type if current_scenario_steps else "ACTION"

                current_scenario_steps.append(GherkinScenarioStep(
                    keyword=keyword,
                    text=text,
                    step_type=step_type
                ))

        if current_scenario_title and current_scenario_steps:
            req_spec = self._build_requirement_spec(
                project_id=project_id,
                document_id=document_id,
                feature_title=feature_title,
                scenario_title=current_scenario_title,
                steps=current_scenario_steps,
                start_line=scenario_start_line,
                end_line=len(lines)
            )
            requirements.append(req_spec)

        return requirements

    def _build_requirement_spec(
        self, project_id: str, document_id: str, feature_title: str, scenario_title: str,
        steps: List[GherkinScenarioStep], start_line: int, end_line: int
    ) -> RequirementSpec:
        full_text = f"{feature_title} - {scenario_title}"
        req_id = f"REQ-GHERKIN-{hashlib.sha256(full_text.encode()).hexdigest()[:8].upper()}"

        preconditions = [s.text for s in steps if s.step_type == "PRECONDITION"]
        actions = [s.text for s in steps if s.step_type == "ACTION"]
        expected = [s.text for s in steps if s.step_type == "EXPECTED"]

        location = SourceLocation(
            line_start=start_line,
            line_end=end_line,
            section=feature_title
        )

        biz_rule = BusinessRule(
            rule_id=f"BR-{req_id}",
            description=f"Scenario: {scenario_title}",
            preconditions=preconditions,
            actions=actions,
            postconditions=expected
        )

        return RequirementSpec(
            id=req_id,
            project_id=project_id,
            document_id=document_id,
            source=RequirementSource.GHERKIN_FEATURE,
            source_location=location,
            title=scenario_title,
            description="\n".join([f"{s.keyword} {s.text}" for s in steps]),
            requirement_type=RequirementType.FUNCTIONAL,
            confidence=1.0,
            business_rules=[biz_rule],
            preconditions=preconditions,
            postconditions=expected,
            extraction_method="DETERMINISTIC_GHERKIN_PARSER",
            content_hash=hashlib.sha256(full_text.encode()).hexdigest()
        )
