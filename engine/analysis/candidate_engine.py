"""
ASTRA Engine - Phase 6 Root Cause Candidate & Multi-Metric Confidence Generator

Aggregates failure evidence, categorization, and fault locations into prioritized RootCauseCandidate hypotheses
with strict false-positive restraint when evidence is insufficient.
"""

from typing import List, Tuple, Optional
from engine.analysis.models import (
    FailureCategory,
    FailureEvidence,
    FaultLocation,
    JsonDiffItem,
    ParsedException,
    RootCauseCandidate,
    ReasoningType,
)


class RootCauseCandidateEngine:
    """Generates root-cause candidate hypotheses and computes overall root_cause_confidence."""

    def generate_candidates(
        self,
        category: FailureCategory,
        evidence_items: List[FailureEvidence],
        fault_locations: List[FaultLocation],
        diff_items: List[JsonDiffItem],
        parsed_exception: Optional[ParsedException] = None,
    ) -> Tuple[List[RootCauseCandidate], float]:
        """
        Returns (candidates, root_cause_confidence).
        """
        # 1. False-Positive Restraint Check:
        # If no stack trace, no diff items, and category is UNKNOWN or SERVER_CRASH with zero frames
        has_stack_frames = parsed_exception is not None and len(parsed_exception.frames) > 0
        body_diff_items = [d for d in diff_items if d.path.startswith("$.body")]
        has_body_diffs = len(body_diff_items) > 0

        if not has_stack_frames and not has_body_diffs and category in (FailureCategory.UNKNOWN, FailureCategory.SERVER_CRASH):
            candidate = RootCauseCandidate(
                description="Insufficient empirical evidence available to determine definitive root cause.",
                reasoning_type=ReasoningType.INSUFFICIENT_EVIDENCE,
                evidence_ids=[e.evidence_id for e in evidence_items],
                fault_locations=[],
                confidence=0.0,
                suggested_remediation="Enable detailed logging, inspect server logs, or run with stack trace collection.",
            )
            return [candidate], 0.0

        candidates: List[RootCauseCandidate] = []

        # 2. Database Constraint Candidate
        if category == FailureCategory.DATABASE_ERROR and parsed_exception:
            cand = RootCauseCandidate(
                description=f"Database constraint violation ({parsed_exception.exception_type}): {parsed_exception.message}",
                reasoning_type=ReasoningType.DATABASE_CONSTRAINT,
                evidence_ids=[e.evidence_id for e in evidence_items],
                fault_locations=fault_locations[:2],
                confidence=0.92 if fault_locations else 0.80,
                suggested_remediation="Inspect entity constraints, duplicate key indices, or foreign key dependencies.",
            )
            candidates.append(cand)

        # 3. Exception Origin Candidate
        elif has_stack_frames and parsed_exception:
            top_loc = fault_locations[0] if fault_locations else None
            loc_str = f" in {top_loc.file_path}:{top_loc.line_number}" if top_loc else ""
            cand = RootCauseCandidate(
                description=f"Unhandled exception ({parsed_exception.exception_type}) raised{loc_str}: {parsed_exception.message}",
                reasoning_type=ReasoningType.EXCEPTION_ORIGIN,
                evidence_ids=[e.evidence_id for e in evidence_items],
                fault_locations=fault_locations,
                confidence=top_loc.confidence if top_loc else 0.85,
                suggested_remediation="Review target function logic and add explicit exception handling or parameter validation.",
            )
            candidates.append(cand)

        # 4. JSON Contract Mismatch Candidate
        if has_body_diffs:
            diff_paths = [d.path for d in body_diff_items[:3]]
            diff_summary = ", ".join(diff_paths)
            cand = RootCauseCandidate(
                description=f"Response schema contract mismatch at JSON paths: {diff_summary}",
                reasoning_type=ReasoningType.JSON_CONTRACT_MISMATCH,
                evidence_ids=[e.evidence_id for e in evidence_items],
                fault_locations=fault_locations,
                confidence=0.88,
                suggested_remediation="Align API handler response payload schema with expected specification contract.",
            )
            candidates.append(cand)

        # 5. Performance SLA Timeout Candidate
        if category == FailureCategory.TIMEOUT_PERFORMANCE:
            cand = RootCauseCandidate(
                description="Execution time breached SLA threshold or timed out waiting for downstream response.",
                reasoning_type=ReasoningType.TIMEOUT,
                evidence_ids=[e.evidence_id for e in evidence_items],
                fault_locations=fault_locations,
                confidence=0.90,
                suggested_remediation="Optimize database queries, introduce caching, or increase timeout thresholds.",
            )
            candidates.append(cand)

        # 6. Fallback / General Candidate
        if not candidates:
            cand = RootCauseCandidate(
                description=f"Failure classified as {category.value} based on response status or log evidence.",
                reasoning_type=ReasoningType.STATUS_MISMATCH,
                evidence_ids=[e.evidence_id for e in evidence_items],
                fault_locations=fault_locations,
                confidence=0.70,
                suggested_remediation="Investigate API handler status codes and request payload constraints.",
            )
            candidates.append(cand)

        top_confidence = candidates[0].confidence if candidates else 0.0
        return candidates, top_confidence
