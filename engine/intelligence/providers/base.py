"""
Base LLM Provider Interface & Response Schema.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel


class LLMResponse(BaseModel):
    raw_text: str
    structured_data: Optional[Dict[str, Any]] = None
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: float = 0.0
    model_name: str
    provider_name: str


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Dict[str, Any],
        temperature: float = 0.1
    ) -> LLMResponse:
        """Generates structured JSON adhering to response_schema."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verifies provider connectivity and API key validity."""
        pass
