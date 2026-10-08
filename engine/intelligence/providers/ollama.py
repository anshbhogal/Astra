"""
Local Self-Hosted Ollama LLM Provider Implementation.
"""

import os
import json
import time
import httpx
from typing import Dict, Any
from engine.intelligence.providers.base import BaseLLMProvider, LLMResponse


class OllamaProvider(BaseLLMProvider):
    def __init__(self, host_url: str = None, model: str = "llama3.1"):
        self.host_url = host_url or os.environ.get("OLLAMA_HOST_URL", "http://localhost:11434")
        self.model = model

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Dict[str, Any],
        temperature: float = 0.1
    ) -> LLMResponse:
        start_time = time.time()
        url = f"{self.host_url}/api/generate"

        full_prompt = (
            f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\n"
            f"REQUIRED OUTPUT JSON SCHEMA:\n{json.dumps(response_schema)}\n\n"
            f"USER REQUEST:\n{user_prompt}\n\n"
            f"Return ONLY raw valid JSON matching the schema."
        )

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "format": "json",
            "options": {"temperature": temperature},
            "stream": False
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                res = await client.post(url, json=payload)
                elapsed_ms = (time.time() - start_time) * 1000

                if res.status_code != 200:
                    return LLMResponse(
                        raw_text=f"Ollama Error {res.status_code}: {res.text}",
                        structured_data=None,
                        latency_ms=elapsed_ms,
                        model_name=self.model,
                        provider_name="ollama"
                    )

                data = res.json()
                raw_text = data.get("response", "")
                structured_data = json.loads(raw_text)

                return LLMResponse(
                    raw_text=raw_text,
                    structured_data=structured_data,
                    tokens_input=data.get("prompt_eval_count", 0),
                    tokens_output=data.get("eval_count", 0),
                    latency_ms=elapsed_ms,
                    model_name=self.model,
                    provider_name="ollama"
                )
        except Exception as exc:
            return LLMResponse(
                raw_text=f"Ollama Connection Failed: {str(exc)}",
                structured_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                model_name=self.model,
                provider_name="ollama"
            )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.host_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False
