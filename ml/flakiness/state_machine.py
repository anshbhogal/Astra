"""Outcome Sequence State Machine for Flakiness Analysis."""

from typing import List, Dict, Any
from enum import Enum


class OutcomeState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    ENVIRONMENT_ERROR = "ENVIRONMENT_ERROR"
    CANCELLED = "CANCELLED"


class FlakinessStateMachine:
    """
    Tracks state transitions over an observation window W = 10 runs per test case.
    Requires minimum observations (window >= 8, transitions >= 2) before declaring high confidence flakiness.
    """

    def __init__(self, observation_window: int = 10, min_observations: int = 8, min_transitions: int = 2):
        self.observation_window = observation_window
        self.min_observations = min_observations
        self.min_transitions = min_transitions

    def analyze_sequence(self, outcome_history: List[str]) -> Dict[str, Any]:
        if not outcome_history:
            return {
                "observation_count": 0,
                "transition_count": 0,
                "pass_count": 0,
                "fail_count": 0,
                "timeout_count": 0,
                "has_sufficient_data": False,
                "transition_rate": 0.0,
            }

        window_outcomes = outcome_history[-self.observation_window:]
        obs_count = len(window_outcomes)

        pass_cnt = sum(1 for o in window_outcomes if o == OutcomeState.PASS.value)
        fail_cnt = sum(1 for o in window_outcomes if o == OutcomeState.FAIL.value)
        timeout_cnt = sum(1 for o in window_outcomes if o in (OutcomeState.TIMEOUT.value, OutcomeState.ENVIRONMENT_ERROR.value))

        transitions = 0
        for i in range(1, len(window_outcomes)):
            if window_outcomes[i] != window_outcomes[i - 1]:
                transitions += 1

        has_sufficient_data = bool(obs_count >= self.min_observations)
        transition_rate = float(transitions / max(1, obs_count - 1)) if obs_count > 1 else 0.0

        return {
            "observation_count": obs_count,
            "transition_count": transitions,
            "pass_count": pass_cnt,
            "fail_count": fail_cnt,
            "timeout_count": timeout_cnt,
            "has_sufficient_data": has_sufficient_data,
            "transition_rate": float(transition_rate),
        }
