"""
ASTRA Engine - APR Immutable Repair Context & Cryptographic Hashes

Provides frozen context snapshots and deterministic hashing functions to guarantee
perfect experiment provenance and reproducibility across defect repairs.
"""

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID


class RepairScope(str, Enum):
    SCOPE_1 = "SCOPE_1"          # Single AST node
    SCOPE_2 = "SCOPE_2"          # Enclosing statement/block
    SCOPE_3 = "SCOPE_3"          # Enclosing function body (default max)
    SCOPE_4 = "SCOPE_4"          # Required import + target function body
    SCOPE_5 = "SCOPE_5"          # Multiple files (requires human approval)
    OUT_OF_SCOPE = "OUT_OF_SCOPE"  # Forbidden files / dependency changes


@dataclass(frozen=True)
class FaultLocationSnapshot:
    file_path: str
    function_name: str
    line_number: int
    column_number: Optional[int] = None
    ast_node_type: str = "Unknown"
    source_snippet: str = ""
    confidence: float = 1.0


@dataclass(frozen=True)
class RepairContext:
    # 1. Defect & Project Identity
    defect_id: UUID
    project_id: UUID
    workspace_id: Optional[UUID]

    # 2. Canonical Gen 2 Lineage
    build_id: Optional[UUID]
    commit_sha: str
    base_branch: str
    test_definition_id: UUID
    test_definition_version_id: UUID
    execution_attempt_id: UUID
    test_result_id: UUID

    # 3. Source Code Fingerprint
    file_path: str
    source_sha256: str
    fault_location: FaultLocationSnapshot

    # 4. Deterministic Failure Snapshots (Secret-Redacted)
    failure_fingerprint: str
    exception_type: str
    exception_message: str
    request_snapshot: Dict[str, Any]       # Redacted headers, method, path, query, body
    response_snapshot: Dict[str, Any]      # Status code, headers, redacted body
    assertion_snapshot: Dict[str, Any]     # Expected vs Actual invariants

    # 5. Environment & Engine Provenance
    environment_snapshot_hash: str
    analyzer_version: str = "2.0.0"
    repair_engine_version: str = "2.0.0"


def compute_sha256_text(text: str) -> str:
    """Computes standard hex SHA-256 for string content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_dict_hash(data: Dict[str, Any]) -> str:
    """Computes deterministic canonical SHA-256 for a JSON dictionary."""
    canonical_json = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_candidate_hash(
    source_commit_sha: str,
    target_file_sha: str,
    target_ast_hash: str,
    canonical_patch: str,
    verification_config_hash: str,
) -> str:
    """
    Computes cryptographic candidate patch hash:
    SHA256(source_commit_sha + target_file_sha + target_ast_hash + canonical_patch + verification_config_hash)
    """
    # Normalize patch whitespace and CRLF before hashing
    normalized_patch = "\n".join(line.rstrip() for line in canonical_patch.strip().splitlines())
    raw_key = (
        f"{source_commit_sha}:"
        f"{target_file_sha}:"
        f"{target_ast_hash}:"
        f"{normalized_patch}:"
        f"{verification_config_hash}"
    )
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def compute_ast_node_hash(node_repr: str) -> str:
    """Generates a deterministic hash for an AST statement dump."""
    return hashlib.sha256(node_repr.strip().encode("utf-8")).hexdigest()
