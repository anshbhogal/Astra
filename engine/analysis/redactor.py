"""
ASTRA Engine - Phase 6 Secret Redactor & Resource Truncator

Sanitizes secrets (tokens, credentials, passwords, JWTs, cookies) from raw evidence strings
and enforces strict resource size/count truncation limits before persistence.
"""

import re
from typing import Dict, Any, List, Union, Optional


SENSITIVE_PATTERNS = [
    (re.compile(r'(?i)(bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*'), r'\1[REDACTED_TOKEN]'),
    (re.compile(r'(?i)(api[_-]?key["\']?\s*[:=]\s*["\']?)[A-Za-z0-9\-\._~]+'), r'\1[REDACTED_API_KEY]'),
    (re.compile(r'(?i)(password["\']?\s*[:=]\s*["\']?)[^\s,\'"\}]+'), r'\1[REDACTED_PASSWORD]'),
    (re.compile(r'(?i)(secret["\']?\s*[:=]\s*["\']?)[^\s,\'"\}]+'), r'\1[REDACTED_SECRET]'),
    (re.compile(r'(?i)(cookie["\']?\s*[:=]\s*["\']?)[^\r\n;]+'), r'\1[REDACTED_COOKIE]'),
    (re.compile(r'(?i)(postgres(?:ql)?|mysql|mongodb|redis):\/\/[^\s@]+@'), r'\1://[REDACTED_CREDS]@'),
    (re.compile(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'), r'[REDACTED_JWT]'),
]


class EvidenceRedactor:
    """Sanitizes text and dictionary payloads, and applies resource truncation limits."""

    def __init__(
        self,
        max_stack_trace_size: int = 50_000,
        max_log_size: int = 100_000,
        max_response_body_size: int = 50_000,
        max_diff_items: int = 50,
        max_stack_frames: int = 100,
    ):
        self.max_stack_trace_size = max_stack_trace_size
        self.max_log_size = max_log_size
        self.max_response_body_size = max_response_body_size
        self.max_diff_items = max_diff_items
        self.max_stack_frames = max_stack_frames

    def sanitize_text(self, text: str, max_length: Optional[int] = None) -> str:
        """Applies regex redaction rules to text and truncates if exceeding max_length."""
        if not text:
            return ""

        result = text
        for pattern, replacement in SENSITIVE_PATTERNS:
            result = pattern.sub(replacement, result)

        if max_length and len(result) > max_length:
            truncated_len = max_length - 30
            result = result[:truncated_len] + f"\n... [TRUNCATED at {max_length} chars]"

        return result

    def sanitize_payload(self, data: Any) -> Any:
        """Recursively sanitizes dictionary or list data structures."""
        if isinstance(data, str):
            return self.sanitize_text(data)
        elif isinstance(data, dict):
            sanitized = {}
            for k, v in data.items():
                if any(sec in k.lower() for sec in ["password", "secret", "token", "auth", "cookie", "key", "credential"]):
                    sanitized[k] = "[REDACTED]"
                else:
                    sanitized[k] = self.sanitize_payload(v)
            return sanitized
        elif isinstance(data, list):
            return [self.sanitize_payload(item) for item in data]
        return data

    def truncate_stack_frames(self, frames: List[Any]) -> List[Any]:
        """Limits stack frame count to max_stack_frames."""
        if len(frames) > self.max_stack_frames:
            return frames[:self.max_stack_frames]
        return frames

    def truncate_diff_items(self, diff_items: List[Any]) -> List[Any]:
        """Limits diff items count to max_diff_items."""
        if len(diff_items) > self.max_diff_items:
            return diff_items[:self.max_diff_items]
        return diff_items
