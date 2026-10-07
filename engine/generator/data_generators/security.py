"""
Opt-In Passive Security Safety Probe Engine.
Generates non-destructive resilience probe tokens for SQLi, XSS, Path Traversal, and Command Injection.
"""

from typing import List, Dict, Any
from engine.schema.models import NormalizedFieldSchema
from engine.generator.models import ParameterMutation, MutationReason


class SecurityProbeGenerator:
    """Generates opt-in non-destructive security safety probe tokens."""

    PROBES = [
        {"name": "SQL_INJECTION_RESILIENCE", "token": "' OR '1'='1", "rule": "sqli_probe"},
        {"name": "XSS_RESILIENCE", "token": "<script>alert('ASTRA_PROBE')</script>", "rule": "xss_probe"},
        {"name": "PATH_TRAVERSAL_RESILIENCE", "token": "../../../../etc/passwd", "rule": "traversal_probe"},
        {"name": "COMMAND_INJECTION_RESILIENCE", "token": "; id;", "rule": "cmdi_probe"},
    ]

    @classmethod
    def generate_security_probes(cls, schema: NormalizedFieldSchema) -> List[ParameterMutation]:
        mutations: List[ParameterMutation] = []
        f_name = schema.name

        for p in cls.PROBES:
            mutations.append(ParameterMutation(
                field_path=f_name,
                original_value="sample_value",
                mutated_value=p["token"],
                reason=MutationReason.SECURITY_PROBE,
                constraint_rule=f"security_{p['name'].lower()}",
                location=schema.location
            ))

        return mutations
