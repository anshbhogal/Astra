"""
AI Budget & Cost Manager.
"""

from dataclasses import dataclass, field


@dataclass
class AIBudgetManager:
    max_requirements: int = 50
    max_llm_calls: int = 50
    max_tokens: int = 100000
    max_scenarios: int = 500

    current_calls: int = 0
    current_tokens: int = 0
    current_scenarios: int = 0

    def can_make_call(self) -> bool:
        return self.current_calls < self.max_llm_calls and self.current_tokens < self.max_tokens

    def record_usage(self, tokens_used: int, scenarios_count: int):
        self.current_calls += 1
        self.current_tokens += tokens_used
        self.current_scenarios += scenarios_count
