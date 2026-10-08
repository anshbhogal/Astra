"""
LLM Provider Factory.
"""

from engine.intelligence.providers.base import BaseLLMProvider
from engine.intelligence.providers.gemini import GeminiProvider
from engine.intelligence.providers.ollama import OllamaProvider


class LLMProviderFactory:
    @staticmethod
    def get_provider(provider_name: str = "gemini", model: str = None, api_key: str = None) -> BaseLLMProvider:
        provider_name = (provider_name or "gemini").lower()
        if provider_name == "gemini":
            return GeminiProvider(api_key=api_key, model=model or "gemini-1.5-pro")
        elif provider_name == "ollama":
            return OllamaProvider(model=model or "llama3.1")
        else:
            # Fallback default to Gemini
            return GeminiProvider(api_key=api_key, model=model or "gemini-1.5-pro")
