# Phase 5 — Requirement Intelligence & Natural Language AI Layer Implementation Guide

> **Module Focus:** SRS / Document Requirement Parsing, Requirement-to-Scenario Mapping, Provider-Agnostic LLM Orchestrator (Gemini / Ollama), Resilient Fallback Engine, and JSON-Enforced Prompt Engineering.

---

## 1. Phase Overview & Objectives

Phase 5 introduces natural language intelligence to Astra. It allows Astra to parse Software Requirement Specifications (SRS documents, Markdown, OpenAPI), convert them into structured requirements (`REQ-001`, `REQ-002`), and use Generative AI to generate complex natural-language test scenarios.

### Architectural Rule
> **Generative AI is strictly optional. The AI Layer is wrapped in an abstract provider interface with automatic fallback to deterministic rules whenever external APIs fail or are disabled.**

### Key Deliverables
1. **Requirement Parser Module:** Document reader parsing PDFs, Markdown files, and plain-text SRS documents into structured requirement schemas.
2. **Requirement-to-Scenario Engine:** Generator converting high-level business rules into discrete boundary, security, and functional scenario definitions.
3. **Provider-Agnostic LLM Orchestrator:** Pluggable interface supporting Google Gemini API (`gemini-2.5-flash`), local Ollama models (`llama3`), and custom OpenAI-compatible endpoints.
4. **Resilient AI Fallback Pipeline:** Automatic retry and downgrade cascade: `Gemini API` -> `Local Ollama` -> `Deterministic Rule Engine`.
5. **JSON-Enforced Prompt Engine:** Structured system prompts with strict schema validation preventing conversational fluff or malformed outputs.

---

## 2. Technical Stack Specifications

- **Generative AI SDK:** `google-genai` SDK for Gemini API integration.
- **Document Processing:** `pypdf` for SRS PDF text extraction, `python-markdown` for markdown AST parsing.
- **Async HTTP Client:** `httpx` for communicating with local Ollama or custom LLM endpoints.

---

## 3. Architecture & Fallback Cascade

```text
Natural Language SRS / Document
               │
               ▼
┌─────────────────────────────┐
│  Requirement Extractor      │ Extracts REQ-001, REQ-002, business constraints
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│   LLM Orchestrator Engine   │ Attempts primary LLM request
└──────────────┬──────────────┘
               │
       ┌───────┴──────────────────────────────┐
       ▼                                      ▼
[Gemini API Available?]             [Gemini API Failed / Rate-Limited?]
       │                                      │
       ├─► YES: Use Gemini Provider           ├─► Try Local Ollama Provider
       │                                      │
       └──────────────────────────────────────┴─► Failed? Fallback to Rule Engine!
```

---

## 4. LLM Provider Abstraction & Fallback Engine (`ai/orchestrator/llm_client.py`)

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import os
import json
import httpx

class LLMProvider(ABC):
    @abstractmethod
    async def generate_json(self, prompt: str, system_instruction: str) -> Optional[Dict[str, Any]]:
        pass

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

    async def generate_json(self, prompt: str, system_instruction: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {"responseMimeType": "application/json"}
        }

        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(url, json=payload, timeout=20.0)
                if res.status_code == 200:
                    data = res.json()
                    text_content = data["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(text_content)
            except Exception as e:
                print(f"[AI Layer] Gemini API call failed: {e}")
        return None

class LocalOllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url
        self.model = model

    async def generate_json(self, prompt: str, system_instruction: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": f"{system_instruction}\n\nTask:\n{prompt}",
            "format": "json",
            "stream": False
        }

        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(url, json=payload, timeout=30.0)
                if res.status_code == 200:
                    return json.loads(res.json()["response"])
            except Exception as e:
                print(f"[AI Layer] Local Ollama call failed: {e}")
        return None

class ResilientAIOrchestrator:
    def __init__(self):
        self.providers = [
            GeminiProvider(),
            LocalOllamaProvider()
        ]

    async def execute_prompt(self, prompt: str, system_instruction: str) -> Optional[Dict[str, Any]]:
        for provider in self.providers:
            result = await provider.generate_json(prompt, system_instruction)
            if result:
                return result
        print("[AI Layer] All AI providers failed. Returning None to trigger Rule Engine fallback.")
        return None
```

---

## 5. Requirement Parser & Model (`backend/app/models/requirement.py`)

```python
from datetime import datetime
import uuid
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.domain import Base

class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    req_code: Mapped[str] = mapped_column(String(50), nullable=False)  # REQ-001
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="MANUAL") # MANUAL, SRS_PDF, OPENAPI
    extracted_constraints: Mapped[dict] = mapped_column(JSON, default={}, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    scenarios: Mapped[list["TestScenario"]] = relationship("TestScenario", back_populates="requirement", cascade="all, delete-orphan")

class TestScenario(Base):
    __tablename__ = "test_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requirement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("requirements.id"), nullable=False)
    scenario_code: Mapped[str] = mapped_column(String(50), nullable=False) # SCEN-001
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False) # BOUNDARY, NEGATIVE, SECURITY
    generated_by: Mapped[str] = mapped_column(String(50), nullable=False) # GEMINI, OLLAMA, RULE_ENGINE

    requirement: Mapped["Requirement"] = relationship("Requirement", back_populates="scenarios")
```

---

## 6. Prompt Engineering Specification (`ai/prompts/requirement_prompts.py`)

```python
SYSTEM_INSTRUCTION_REQ_EXTRACTOR = """
You are an expert Software Quality Assurance Engineer.
Your task is to analyze natural language requirements or software specifications and output a structured JSON array of discrete requirements.

OUTPUT JSON SCHEMA EQUIVALENT:
{
  "requirements": [
    {
      "req_code": "REQ-001",
      "title": "Short title",
      "description": "Detailed business rule description",
      "constraints": {
        "min_length": 8,
        "required_fields": ["email", "password"]
      }
    }
  ]
}
Return ONLY pure JSON. Do not include markdown codeblocks or conversational preamble.
"""

SYSTEM_INSTRUCTION_SCENARIO_GENERATOR = """
You are an AI Test Scenario Synthesizer. Given a business requirement, generate test scenarios including happy path, boundary conditions, negative cases, and security input validations.

OUTPUT JSON SCHEMA EQUIVALENT:
{
  "scenarios": [
    {
      "scenario_code": "SCEN-001",
      "title": "Valid registration with 8-character password",
      "category": "HAPPY_PATH",
      "expected_status": 200
    }
  ]
}
Return ONLY valid JSON matching the schema.
"""
```

---

## 7. API Controllers (`backend/app/api/v1/requirements.py`)

- `POST /requirements/parse-document` — Accepts PDF or Markdown SRS files; parses text and calls `ResilientAIOrchestrator` to extract structured requirements.
- `POST /requirements/{id}/generate-scenarios` — Generates edge-case test scenarios for a given requirement ID using AI or Rule Engine fallback.
- `GET /projects/{id}/requirements` — Lists all requirements and their linked scenarios.

---

## 8. Verification & Test Plan

1. **AI Fallback Resilience Test:**
   - Set invalid `GEMINI_API_KEY=invalid_key` and ensure Local Ollama is stopped. Trigger `generate-scenarios`. Verify system logs `All AI providers failed` and seamlessly delegates to `RuleBasedTestGenerator` without throwing an unhandled exception.
2. **JSON Schema Strictness Test:**
   - Execute test harness for `GeminiProvider`. Verify that `responseMimeType="application/json"` prevents extra natural language prose and returns valid JSON parseable by `json.loads()`.
3. **SRS PDF Reader Test:**
   - Upload a sample 5-page SRS PDF (`upload_srs.pdf`). Verify that text extraction accurately populates `requirements` records in PostgreSQL.
