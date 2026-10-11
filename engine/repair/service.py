"""
ASTRA Engine - Repair Job Orchestrator Service

Implements the deterministic-first APR synthesis and verification pipeline:
Defect -> Eligibility -> Context Snapshot -> AST Pinpointing -> Mutators -> LLM Fallback ->
Sandbox -> Zero-Observed-Regression Gate -> Candidate Ranking.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from engine.repair.ast_pinpointer import ASTPinpointer, ASTTargetContext
from engine.repair.context import (
    RepairContext,
    RepairScope,
    compute_dict_hash,
)
from engine.repair.eligibility_policy import RepairEligibilityPolicy
from engine.repair.llm_synthesizer import LLMSynthesizer
from engine.repair.mutators import (
    BoundaryConditionMutator,
    HTTPExceptionWrapperMutator,
    KeyErrorGuardMutator,
    NullSafetyGuardMutator,
)
from engine.repair.patch_validator import PatchSanityResult, PatchValidator
from engine.repair.regression_gate import (
    CandidateVerificationReport,
    ZeroObservedRegressionGate,
)
from engine.repair.sandbox_executor import SandboxExecutor


@dataclass
class ProposedCandidateRecord:
    candidate_id: UUID
    candidate_rank: int
    generation_method: str               # DETERMINISTIC, LLM, HYBRID
    mutator_type: str
    target_file: str
    patch_diff: str
    candidate_hash: str
    scope: RepairScope
    sanity_result: PatchSanityResult
    verification_report: Optional[CandidateVerificationReport] = None
    repair_rationale: str = ""


@dataclass
class RepairJobExecutionResult:
    job_id: UUID
    defect_id: UUID
    status: str                         # COMPLETED, FAILED, INELIGIBLE
    is_eligible: bool
    eligibility_reason: str
    candidates_generated: int
    verified_candidates_count: int
    selected_candidate: Optional[ProposedCandidateRecord] = None
    all_candidates: List[ProposedCandidateRecord] = field(default_factory=list)
    failure_reason: Optional[str] = None


class RepairJobService:
    """End-to-end orchestrator for automated program repair jobs."""

    def __init__(
        self,
        llm_synthesizer: Optional[LLMSynthesizer] = None,
        pinpointer: Optional[ASTPinpointer] = None,
        regression_gate: Optional[ZeroObservedRegressionGate] = None,
    ):
        self.llm_synthesizer = llm_synthesizer or LLMSynthesizer()
        self.pinpointer = pinpointer or ASTPinpointer()
        self.regression_gate = regression_gate or ZeroObservedRegressionGate()

        # Deterministic mutator registry
        self.mutators = [
            BoundaryConditionMutator(),
            NullSafetyGuardMutator(),
            KeyErrorGuardMutator(),
            HTTPExceptionWrapperMutator(),
        ]

    async def execute_repair(
        self,
        repair_context: RepairContext,
        original_source: str,
        repo_path: str,
        defect_test_cmd: str,
        regression_test_cmds: List[str],
        severity: str = "MAJOR",
    ) -> RepairJobExecutionResult:
        """
        Executes complete repair lifecycle for a defect.
        """
        job_id = uuid4()
        defect_id = repair_context.defect_id
        target_file = repair_context.file_path
        target_line = repair_context.fault_location.line_number
        ex_type = repair_context.exception_type
        ex_msg = repair_context.exception_message

        # 1. Eligibility Check
        eligible, reason = RepairEligibilityPolicy.evaluate(
            severity=severity,
            file_path=target_file,
            exception_type=ex_type,
        )
        if not eligible:
            return RepairJobExecutionResult(
                job_id=job_id,
                defect_id=defect_id,
                status="FAILED",
                is_eligible=False,
                eligibility_reason=reason,
                candidates_generated=0,
                verified_candidates_count=0,
                failure_reason=f"Defect is ineligible for APR: {reason}",
            )

        # 2. AST Pinpointing
        target_context = self.pinpointer.pinpoint(
            source_code=original_source,
            file_path=target_file,
            target_line=target_line,
        )
        if target_context is None:
            return RepairJobExecutionResult(
                job_id=job_id,
                defect_id=defect_id,
                status="FAILED",
                is_eligible=True,
                eligibility_reason=reason,
                candidates_generated=0,
                verified_candidates_count=0,
                failure_reason=f"Failed to parse or pinpoint AST node at {target_file}:{target_line}",
            )

        # 3. Deterministic-First Patch Synthesis
        candidate_records: List[ProposedCandidateRecord] = []
        verified_candidates: List[ProposedCandidateRecord] = []

        # Run deterministic mutators
        for mutator in self.mutators:
            if mutator.can_mutate(target_context, ex_type, ex_msg):
                diffs = mutator.generate_patches(target_context, original_source)
                for diff in diffs:
                    sanity = PatchValidator.validate(
                        diff_text=diff,
                        original_source=original_source,
                        target_context=target_context,
                        source_commit_sha=repair_context.commit_sha,
                    )
                    if sanity.is_valid:
                        rec = ProposedCandidateRecord(
                            candidate_id=uuid4(),
                            candidate_rank=len(candidate_records) + 1,
                            generation_method="DETERMINISTIC",
                            mutator_type=mutator.name,
                            target_file=target_file,
                            patch_diff=diff,
                            candidate_hash=sanity.candidate_hash,
                            scope=sanity.scope,
                            sanity_result=sanity,
                            repair_rationale=f"Deterministic rule-based fix applied via {mutator.name}.",
                        )
                        candidate_records.append(rec)

        # 4. Fallback to Semantic LLM Synthesis if no deterministic candidates valid
        if not candidate_records and self.llm_synthesizer is not None:
            llm_cand = await self.llm_synthesizer.synthesize(
                repair_context=repair_context,
                target_context=target_context,
                original_source=original_source,
            )
            if llm_cand and llm_cand.sanity_result.is_valid:
                rec = ProposedCandidateRecord(
                    candidate_id=uuid4(),
                    candidate_rank=1,
                    generation_method="LLM",
                    mutator_type="LLM_SYNTHESIZER",
                    target_file=target_file,
                    patch_diff=llm_cand.unified_diff,
                    candidate_hash=llm_cand.sanity_result.candidate_hash,
                    scope=llm_cand.sanity_result.scope,
                    sanity_result=llm_cand.sanity_result,
                    repair_rationale=llm_cand.repair_rationale,
                )
                candidate_records.append(rec)

        if not candidate_records:
            return RepairJobExecutionResult(
                job_id=job_id,
                defect_id=defect_id,
                status="FAILED",
                is_eligible=True,
                eligibility_reason=reason,
                candidates_generated=0,
                verified_candidates_count=0,
                failure_reason="No plausible or syntactically valid patches could be synthesized.",
            )

        # 5. Isolated Sandbox Verification & Zero-Observed-Regression Gate
        for candidate in candidate_records:
            async with SandboxExecutor(repo_path=repo_path, base_commit_sha=repair_context.commit_sha) as sandbox:
                report = await self.regression_gate.verify_candidate(
                    sandbox=sandbox,
                    target_rel_path=target_file,
                    diff_text=candidate.patch_diff,
                    sanity_result=candidate.sanity_result,
                    defect_test_cmd=defect_test_cmd,
                    regression_test_cmds=regression_test_cmds,
                    fault_confidence=repair_context.fault_location.confidence,
                )
                candidate.verification_report = report
                if report.verified:
                    verified_candidates.append(candidate)

        # 6. Rank Candidates
        if verified_candidates:
            verified_candidates.sort(
                key=lambda c: c.verification_report.ranking_score if c.verification_report else 0.0,
                reverse=True,
            )
            for idx, c in enumerate(verified_candidates):
                c.candidate_rank = idx + 1
            selected = verified_candidates[0]
            status = "COMPLETED"
        else:
            selected = None
            status = "FAILED"

        return RepairJobExecutionResult(
            job_id=job_id,
            defect_id=defect_id,
            status=status,
            is_eligible=True,
            eligibility_reason=reason,
            candidates_generated=len(candidate_records),
            verified_candidates_count=len(verified_candidates),
            selected_candidate=selected,
            all_candidates=candidate_records,
            failure_reason="All candidate patches breached the Zero-Observed-Regression Gate." if not selected else None,
        )
