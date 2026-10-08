"""
Provider Capabilities Registry.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ProviderCapabilities:
    provider_name: str
    configurable_model: str
    supports_json_schema: bool = True
    supports_system_prompt: bool = True
    supports_temperature: bool = True
    max_context_tokens: int = 128000


CAPABILITIES_REGISTRY: Dict[str, ProviderCapabilities] = {
    "gemini": ProviderCapabilities(
        provider_name="gemini",
        configurable_model="gemini-1.5-pro",
        supports_json_schema=True,
        max_context_tokens=1000000
    ),
    "ollama": ProviderCapabilities(
        provider_name="ollama",
        configurable_model="llama3.1",
        supports_json_schema=True,
        max_context_tokens=32000
    ),
    "openai": ProviderCapabilities(
        provider_name="openai",
        configurable_model="gpt-4o",
        supports_json_schema=True,
        max_context_tokens=128000
    ),
    "anthropic": ProviderCapabilities(
        provider_name="anthropic",
        configurable_model="claude-3-5-sonnet-20241022",
        supports_json_schema=True,
        max_context_tokens=200000
    ),
}
