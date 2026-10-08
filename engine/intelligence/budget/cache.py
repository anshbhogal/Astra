"""
LLM Response SHA256 Cache.
"""

import hashlib
import json
from typing import Dict, Any, Optional
from engine.intelligence.providers.base import LLMResponse


class LLMResponseCache:
    _cache: Dict[str, LLMResponse] = {}

    @classmethod
    def make_key(cls, prompt: str, provider: str, model: str) -> str:
        raw = f"{provider}:{model}:{prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @classmethod
    def get(cls, key: str) -> Optional[LLMResponse]:
        return cls._cache.get(key)

    @classmethod
    def set(cls, key: str, response: LLMResponse):
        cls._cache[key] = response
