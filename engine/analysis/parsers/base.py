"""
ASTRA Engine - Phase 6 Base Stack Trace Parser
"""

from abc import ABC, abstractmethod
import hashlib
from typing import Optional
from engine.analysis.models import ParsedException


class BaseStackTraceParser(ABC):
    """Abstract Base Class for all language-specific stack trace parsers."""

    @abstractmethod
    def parse(self, raw_trace: str) -> Optional[ParsedException]:
        """Parses a raw stack trace or log string into a normalized ParsedException object."""
        pass

    def compute_hash(self, raw_trace: str) -> str:
        """Computes SHA256 hash of raw trace string for trace deduplication."""
        return hashlib.sha256(raw_trace.strip().encode("utf-8")).hexdigest()
