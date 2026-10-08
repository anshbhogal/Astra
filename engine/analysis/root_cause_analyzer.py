"""
ASTRA Engine - Phase 6 Master Root Cause Analyzer Orchestrator

Coordinates evidence collection, secret redaction, stack trace parsing, structural diffing,
rule classification, fault localization, root-cause candidate generation, and fingerprinting.
"""

from typing import Dict, Any, List, Optional
from engine.analysis.models import (
    FailureAnalysis,
    FailureEvidence,
    EvidenceType,
    FailureCategory,
    ParsedException,
)
from engine.analysis.redactor import EvidenceRedactor
from engine.analysis.parsers.python_parser import PythonStackTraceParser
from engine.analysis.parsers.nodejs_parser import NodejsStackTraceParser
from engine.analysis.parsers.java_parser import JavaStackTraceParser
from engine.analysis.parsers.sql_parser import SqlErrorParser
from engine.analysis.diff.json_diff_isolator import JsonDiffIsolator
from engine.analysis.classifier import FailureClassifier
from engine.analysis.localization import FaultLocalizer
from engine.analysis.candidate_engine import RootCauseCandidateEngine
from engine.analysis.fingerprint import FingerprintEngine
from engine.analyzer.knowledge_graph import ProjectKnowledgeGraph


class RootCauseAnalyzer:
    """Master Orchestrator transforming raw test failures into structured FailureAnalysis reports."""

    def __init__(
        self,
        pkg: Optional[ProjectKnowledgeGraph] = None,
        redactor: Optional[EvidenceRedactor] = None,
        classifier: Optional[FailureClassifier] = None,
        localizer: Optional[FaultLocalizer] = None,
    ):
        self.pkg = pkg
        self.redactor = redactor or EvidenceRedactor()
        self.classifier = classifier or FailureClassifier()
        self.localizer = localizer or FaultLocalizer(pkg=pkg)
        self.diff_isolator = JsonDiffIsolator()
        self.candidate_engine = RootCauseCandidateEngine()
        self.fingerprint_engine = FingerprintEngine()

        self.parsers = [
            PythonStackTraceParser(),
            SqlErrorParser(),
            NodejsStackTraceParser(),
            JavaStackTraceParser(),
        ]

    def analyze(
        self,
        test_result_id: str,
        test_case_id: str,
        actual_status: int,
        expected_status: Optional[int] = None,
        actual_body: Any = None,
        expected_body: Any = None,
        actual_headers: Optional[Dict[str, str]] = None,
        expected_headers: Optional[Dict[str, str]] = None,
        raw_stack_trace: str = "",
        raw_logs: str = "",
        endpoint_id: Optional[str] = None,
        latency_ms: Optional[float] = None,
        max_latency_ms: Optional[float] = None,
        execution_result: str = "FAILED",
        analysis_commit_sha: Optional[str] = None,
        execution_commit_sha: Optional[str] = None,
    ) -> FailureAnalysis:
        """Executes full Phase 6 failure analysis pipeline."""
        
        # 1. Sanitize & Redact Raw Input Evidence
        clean_trace = self.redactor.sanitize_text(raw_stack_trace, self.redactor.max_stack_trace_size)
        clean_logs = self.redactor.sanitize_text(raw_logs, self.redactor.max_log_size)
        clean_actual_body = self.redactor.sanitize_payload(actual_body)

        evidence_items: List[FailureEvidence] = []

        # 2. Parse Stack Trace / Logs into Normalized ParsedException
        parsed_exception: Optional[ParsedException] = None
        if clean_trace:
            for parser in self.parsers:
                parsed_exception = parser.parse(clean_trace)
                if parsed_exception:
                    break

        if not parsed_exception and clean_logs:
            for parser in self.parsers:
                parsed_exception = parser.parse(clean_logs)
                if parsed_exception:
                    break

        if parsed_exception:
            parsed_exception.frames = self.redactor.truncate_stack_frames(parsed_exception.frames)
            evidence_items.append(
                FailureEvidence(
                    evidence_type=EvidenceType.STACK_TRACE,
                    source=f"{parsed_exception.language}_parser",
                    description=f"{parsed_exception.exception_type}: {parsed_exception.message}",
                    payload={"frames_count": len(parsed_exception.frames), "sql_state": parsed_exception.sql_state},
                )
            )

        # HTTP Status Evidence
        evidence_items.append(
            FailureEvidence(
                evidence_type=EvidenceType.HTTP_STATUS,
                source="http_client",
                description=f"Actual HTTP status {actual_status} (Expected: {expected_status})",
                payload={"actual": actual_status, "expected": expected_status},
            )
        )

        # 3. Multi-Level Response Diff Isolation
        diff_items = self.diff_isolator.compare_responses(
            expected_status=expected_status,
            actual_status=actual_status,
            expected_body=expected_body,
            actual_body=clean_actual_body,
            expected_headers=expected_headers,
            actual_headers=actual_headers,
            max_latency_ms=max_latency_ms,
            actual_latency_ms=latency_ms,
        )
        diff_items = self.redactor.truncate_diff_items(diff_items)

        if diff_items:
            evidence_items.append(
                FailureEvidence(
                    evidence_type=EvidenceType.JSON_DIFF,
                    source="json_diff_isolator",
                    description=f"{len(diff_items)} structural delta(s) detected in response",
                    payload={"deltas": [d.to_dict() for d in diff_items[:5]]},
                )
            )

        # 4. Taxonomic Priority Rule Classification
        category, class_conf, rule_id, summary = self.classifier.classify(
            expected_status=expected_status,
            actual_status=actual_status,
            parsed_exception=parsed_exception,
            diff_items=diff_items,
            raw_logs=clean_logs,
            execution_result=execution_result,
            latency_ms=latency_ms,
            max_latency_ms=max_latency_ms,
        )

        # 5. Fault Localization & PKG Correlation
        fault_locations, attr_conf, source_mismatch = self.localizer.localize(
            parsed_exception=parsed_exception,
            analysis_commit_sha=analysis_commit_sha,
            execution_commit_sha=execution_commit_sha,
        )

        # 6. Root Cause Candidate Generation & Confidence Calculation
        candidates, rc_conf = self.candidate_engine.generate_candidates(
            category=category,
            evidence_items=evidence_items,
            fault_locations=fault_locations,
            diff_items=diff_items,
            parsed_exception=parsed_exception,
        )

        # 7. Canonical Fingerprinting
        top_frame = fault_locations[0] if fault_locations else None
        fingerprint = self.fingerprint_engine.compute_fingerprint(
            category=category,
            exception_type=parsed_exception.exception_type if parsed_exception else None,
            exception_message=parsed_exception.message if parsed_exception else None,
            root_function=top_frame.function_name if top_frame else None,
            endpoint=endpoint_id,
            diff_paths=[d.path for d in diff_items],
            sql_state=parsed_exception.sql_state if parsed_exception else None,
        )

        # Construct Master Report
        error_msg = parsed_exception.message if parsed_exception else (f"HTTP {actual_status} Error" if actual_status >= 400 else "Assertion Failure")
        exc_type = parsed_exception.exception_type if parsed_exception else None

        return FailureAnalysis(
            test_result_id=test_result_id,
            test_case_id=test_case_id,
            endpoint_id=endpoint_id,
            category=category,
            summary=summary,
            error_message=error_msg,
            exception_type=exc_type,
            failing_file=top_frame.file_path if top_frame else None,
            failing_line=top_frame.line_number if top_frame else None,
            failing_function=top_frame.function_name if top_frame else None,
            commit_sha=execution_commit_sha,
            source_mismatch=source_mismatch,
            evidence=evidence_items,
            fault_locations=fault_locations,
            root_cause_candidates=candidates,
            diff_items=diff_items,
            parsed_exception=parsed_exception,
            fingerprint=fingerprint,
            classification_confidence=class_conf,
            attribution_confidence=attr_conf,
            root_cause_confidence=rc_conf,
        )
