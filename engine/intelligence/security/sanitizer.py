"""
Secret & PII Prompt Sanitizer.
"""

import re
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass
class SanitizerReport:
    redactions_count: int = 0
    secret_types: Dict[str, int] = field(default_factory=dict)
    source_hash: str = ""
    sanitized_hash: str = ""


class PromptSanitizer:
    PATTERNS = {
        "JWT": r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
        "API_KEY": r"(sk-[A-Za-z0-9]{32,}|AIzaSy[A-Za-z0-9_-]{33})",
        "POSTGRES_URL": r"postgres(ql)?://[^\s'\"]+",
        "PRIVATE_KEY": r"-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----[^\n]+\n[^\n]+",
        "BEARER_TOKEN": r"Bearer\s+[A-Za-z0-9\._-]{20,}",
        "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    }

    @classmethod
    def sanitize(cls, text: str) -> Tuple[str, SanitizerReport]:
        source_hash = hashlib.sha256(text.encode()).hexdigest()
        sanitized_text = text
        report = SanitizerReport(source_hash=source_hash)

        for name, pattern in cls.PATTERNS.items():
            matches = re.findall(pattern, sanitized_text)
            if matches:
                count = len(matches)
                report.redactions_count += count
                report.secret_types[name] = count
                sanitized_text = re.sub(pattern, f"[REDACTED_{name}]", sanitized_text)

        report.sanitized_hash = hashlib.sha256(sanitized_text.encode()).hexdigest()
        return sanitized_text, report
