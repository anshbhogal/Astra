"""
Google Gemini LLM Provider Implementation.
"""

import os
import json
import time
import httpx
from typing import Dict, Any
from engine.intelligence.providers.base import BaseLLMProvider, LLMResponse


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str = None, model: str = "gemini-1.5-pro"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Dict[str, Any],
        temperature: float = 0.1
    ) -> LLMResponse:
        start_time = time.time()
        
        if not self.api_key:
            return LLMResponse(
                raw_text="Gemini API Key missing",
                structured_data=None,
                model_name=self.model,
                provider_name="gemini"
            )

        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        full_prompt = (
            f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\n"
            f"REQUIRED OUTPUT JSON SCHEMA:\n{json.dumps(response_schema)}\n\n"
            f"USER REQUEST:\n{user_prompt}\n\n"
            f"Return ONLY valid raw JSON matching the required schema. Do not include markdown codeblocks or explanation."
        )

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json"
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(url, json=payload, headers=headers)
            elapsed_ms = (time.time() - start_time) * 1000

            if res.status_code != 200:
                return LLMResponse(
                    raw_text=f"API Error {res.status_code}: {res.text}",
                    structured_data=None,
                    latency_ms=elapsed_ms,
                    model_name=self.model,
                    provider_name="gemini"
                )

            data = res.json()
            raw_text = ""
            try:
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        raw_text = parts[0].get("text", "")
                
                # Parse JSON
                clean_text = raw_text.strip()
                if clean_text.startswith("```json"):
                    clean_text = clean_text.replace("```json", "").replace("```", "").strip()
                elif clean_text.startswith("```"):
                    clean_text = clean_text.replace("```", "").strip()

                structured_data = json.loads(clean_text)
                usage = data.get("usageMetadata", {})

                return LLMResponse(
                    raw_text=raw_text,
                    structured_data=structured_data,
                    tokens_input=usage.get("promptTokenCount", 0),
                    tokens_output=usage.get("candidatesTokenCount", 0),
                    latency_ms=elapsed_ms,
                    model_name=self.model,
                    provider_name="gemini"
                )
            except Exception as e:
                return LLMResponse(
                    raw_text=raw_text,
                    structured_data=None,
                    latency_ms=elapsed_ms,
                    model_name=self.model,
                    provider_name="gemini"
                )

    async def health_check(self) -> bool:
        return bool(self.api_key)
