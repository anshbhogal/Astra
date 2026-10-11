"""
ASTRA Engine - Static Patch Sanity & Security Validator

Statically validates candidate unified diffs for syntax correctness, scope restrictions,
forbidden file paths, anti-tampering guards, and no-op/comment-only diff detection.
"""

import ast
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from engine.repair.ast_pinpointer import ASTTargetContext
from engine.repair.context import (
    RepairScope,
    compute_candidate_hash,
    compute_sha256_text,
)


@dataclass(frozen=True)
class PatchSanityResult:
    is_valid: bool
    rejection_reason: Optional[str]
    scope: RepairScope
    lines_added: int
    lines_removed: int
    complexity_delta: int
    patch_sha256: str
    candidate_hash: str
    syntax_valid: bool
    patched_source: Optional[str] = None


class PatchValidator:
    """Enforces strict static safety policies on candidate diffs."""

    FORBIDDEN_FILE_PATTERNS = [
        r"^\.github/",
        r".*dockerfile.*",
        r".*docker-compose.*",
        r"^package\.json$",
        r"^package-lock\.json$",
        r"^yarn\.lock$",
        r"^pnpm-lock\.yaml$",
        r"^requirements\.txt$",
        r"^pipfile.*",
        r"^pyproject\.toml$",
        r"^setup\.py$",
        r"^go\.mod$",
        r"^go\.sum$",
        r"^pom\.xml$",
        r"^build\.gradle$",
        r"^makefile$",
        r".*\.sh$",
        r".*\.ps1$",
        r".*\.env.*",
        r".*secret.*",
    ]

    TEST_TAMPERING_PATTERNS = [
        r"^tests?/",
        r"^spec/",
        r"^fixtures?/",
        r"^benchmark/",
        r".*_test\.py$",
        r"^test_.*\.py$",
    ]

    @classmethod
    def apply_diff_to_source(cls, original_source: str, diff_text: str) -> Tuple[bool, str, Optional[str]]:
        """
        Pure-Python unified diff applier for single-file patches.
        Returns (success, error_or_message, patched_source).
        """
        orig_lines = original_source.splitlines(keepends=True)
        # Ensure last line ends with newline for clean matching
        if orig_lines and not orig_lines[-1].endswith("\n"):
            orig_lines[-1] = orig_lines[-1] + "\n"

        hunk_header_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
        lines = diff_text.splitlines(keepends=True)

        hunks = []
        current_hunk = []
        in_hunk = False

        for line in lines:
            if line.startswith("@@"):
                if current_hunk:
                    hunks.append(current_hunk)
                current_hunk = [line]
                in_hunk = True
            elif in_hunk:
                if line.startswith(("+", "-", " ", "\\")):
                    current_hunk.append(line)
                elif line.strip() == "":
                    # Empty context line
                    current_hunk.append(" \n")

        if current_hunk:
            hunks.append(current_hunk)

        if not hunks:
            return False, "No valid unified diff hunks found.", None

        patched_lines = list(orig_lines)
        line_offset = 0

        for hunk in hunks:
            header_match = hunk_header_re.match(hunk[0])
            if not header_match:
                return False, f"Malformed hunk header: {hunk[0].strip()}", None

            orig_start = int(header_match.group(1)) - 1
            orig_count = int(header_match.group(2)) if header_match.group(2) is not None else 1

            target_pos = orig_start + line_offset
            hunk_body = hunk[1:]

            # Verify and construct replacement
            removals = []
            additions = []
            matched = True

            for hline in hunk_body:
                if hline.startswith("-"):
                    removals.append(hline[1:])
                elif hline.startswith("+"):
                    additions.append(hline[1:])
                elif hline.startswith(" "):
                    if removals:
                        # Process batch of removals/additions
                        pass
                elif hline.startswith("\\"):
                    continue

            # Simple linear hunk apply
            orig_slice_count = 0
            new_slice: List[str] = []
            for hline in hunk_body:
                if hline.startswith(" "):
                    new_slice.append(hline[1:])
                    orig_slice_count += 1
                elif hline.startswith("-"):
                    orig_slice_count += 1
                elif hline.startswith("+"):
                    new_slice.append(hline[1:])

            # Check bounds
            if target_pos < 0 or target_pos > len(patched_lines):
                target_pos = max(0, min(target_pos, len(patched_lines)))

            end_pos = min(target_pos + orig_slice_count, len(patched_lines))
            patched_lines[target_pos:end_pos] = new_slice
            line_offset += len(new_slice) - orig_slice_count

        return True, "Applied successfully", "".join(patched_lines)

    @classmethod
    def validate(
        cls,
        diff_text: str,
        original_source: str,
        target_context: ASTTargetContext,
        source_commit_sha: str,
        verification_config_hash: str = "default_config_hash",
        max_allowed_scope: RepairScope = RepairScope.SCOPE_3,
    ) -> PatchSanityResult:
        """
        Validates unified diff against security and structural policies.
        """
        patch_sha256 = compute_sha256_text(diff_text)
        cand_hash = compute_candidate_hash(
            source_commit_sha=source_commit_sha,
            target_file_sha=compute_sha256_text(original_source),
            target_ast_hash=target_context.source_ast_hash,
            canonical_patch=diff_text,
            verification_config_hash=verification_config_hash,
        )

        # 1. Empty diff check
        if not diff_text or not diff_text.strip():
            return PatchSanityResult(
                is_valid=False,
                rejection_reason="Patch diff is completely empty.",
                scope=RepairScope.OUT_OF_SCOPE,
                lines_added=0,
                lines_removed=0,
                complexity_delta=0,
                patch_sha256=patch_sha256,
                candidate_hash=cand_hash,
                syntax_valid=False,
            )

        # 2. Extract affected file paths from diff headers (--- a/path, +++ b/path)
        file_targets: List[str] = []
        for line in diff_text.splitlines():
            if line.startswith("--- a/") or line.startswith("+++ b/"):
                file_targets.append(line[6:].strip())

        normalized_target_file = target_context.file_path.replace("\\", "/").lstrip("/")

        # Check multi-file modifications
        unique_files = set(f.lstrip("/") for f in file_targets if f and f != "/dev/null")
        if len(unique_files) > 1:
            return PatchSanityResult(
                is_valid=False,
                rejection_reason=f"Multi-file diff detected ({len(unique_files)} files). Single-file repair required.",
                scope=RepairScope.SCOPE_5,
                lines_added=0,
                lines_removed=0,
                complexity_delta=0,
                patch_sha256=patch_sha256,
                candidate_hash=cand_hash,
                syntax_valid=False,
            )

        if unique_files and not any(f.endswith(normalized_target_file) or normalized_target_file.endswith(f) for f in unique_files):
            return PatchSanityResult(
                is_valid=False,
                rejection_reason=f"Diff modifies '{list(unique_files)[0]}', which does not match target file '{target_context.file_path}'.",
                scope=RepairScope.OUT_OF_SCOPE,
                lines_added=0,
                lines_removed=0,
                complexity_delta=0,
                patch_sha256=patch_sha256,
                candidate_hash=cand_hash,
                syntax_valid=False,
            )

        # 3. Forbidden file check
        for pattern in cls.FORBIDDEN_FILE_PATTERNS:
            if re.search(pattern, normalized_target_file, re.IGNORECASE):
                return PatchSanityResult(
                    is_valid=False,
                    rejection_reason=f"Target file matches forbidden infrastructure pattern: {pattern}",
                    scope=RepairScope.OUT_OF_SCOPE,
                    lines_added=0,
                    lines_removed=0,
                    complexity_delta=0,
                    patch_sha256=patch_sha256,
                    candidate_hash=cand_hash,
                    syntax_valid=False,
                )

        # 4. Anti-tampering check
        for pattern in cls.TEST_TAMPERING_PATTERNS:
            if re.search(pattern, normalized_target_file, re.IGNORECASE):
                return PatchSanityResult(
                    is_valid=False,
                    rejection_reason="Anti-tampering violation: Patch attempts to modify test suite or test fixtures.",
                    scope=RepairScope.OUT_OF_SCOPE,
                    lines_added=0,
                    lines_removed=0,
                    complexity_delta=0,
                    patch_sha256=patch_sha256,
                    candidate_hash=cand_hash,
                    syntax_valid=False,
                )

        # 5. Calculate line delta & comment/whitespace only checks
        lines_added = 0
        lines_removed = 0
        substantive_additions = []
        substantive_removals = []

        for line in diff_text.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                lines_added += 1
                content = line[1:].strip()
                if content and not content.startswith("#"):
                    substantive_additions.append(content)
            elif line.startswith("-") and not line.startswith("---"):
                lines_removed += 1
                content = line[1:].strip()
                if content and not content.startswith("#"):
                    substantive_removals.append(content)

        if lines_added == 0 and lines_removed == 0:
            return PatchSanityResult(
                is_valid=False,
                rejection_reason="No additions or removals in patch diff.",
                scope=RepairScope.OUT_OF_SCOPE,
                lines_added=0,
                lines_removed=0,
                complexity_delta=0,
                patch_sha256=patch_sha256,
                candidate_hash=cand_hash,
                syntax_valid=False,
            )

        if not substantive_additions:
            return PatchSanityResult(
                is_valid=False,
                rejection_reason="No-op patch detected: no substantive code added (only comments, whitespace, or deletions).",
                scope=RepairScope.OUT_OF_SCOPE,
                lines_added=lines_added,
                lines_removed=lines_removed,
                complexity_delta=0,
                patch_sha256=patch_sha256,
                candidate_hash=cand_hash,
                syntax_valid=False,
            )


        # 6. Apply patch in-memory and parse AST
        success, msg, patched_source = cls.apply_diff_to_source(original_source, diff_text)
        if not success or patched_source is None:
            return PatchSanityResult(
                is_valid=False,
                rejection_reason=f"Failed to apply unified diff cleanly: {msg}",
                scope=RepairScope.SCOPE_2,
                lines_added=lines_added,
                lines_removed=lines_removed,
                complexity_delta=0,
                patch_sha256=patch_sha256,
                candidate_hash=cand_hash,
                syntax_valid=False,
            )

        # Check Python syntax correctness
        try:
            patched_tree = ast.parse(patched_source, filename=target_context.file_path)
            orig_tree = ast.parse(original_source, filename=target_context.file_path)
        except SyntaxError as e:
            return PatchSanityResult(
                is_valid=False,
                rejection_reason=f"Synthesized code failed syntax parsing: {e}",
                scope=RepairScope.SCOPE_2,
                lines_added=lines_added,
                lines_removed=lines_removed,
                complexity_delta=0,
                patch_sha256=patch_sha256,
                candidate_hash=cand_hash,
                syntax_valid=False,
                patched_source=patched_source,
            )

        # 7. AST Invariant check (no-op code that produces identical AST)
        if ast.dump(patched_tree) == ast.dump(orig_tree):
            return PatchSanityResult(
                is_valid=False,
                rejection_reason="No-op patch: Patched code produces identical AST dump to original code.",
                scope=RepairScope.OUT_OF_SCOPE,
                lines_added=lines_added,
                lines_removed=lines_removed,
                complexity_delta=0,
                patch_sha256=patch_sha256,
                candidate_hash=cand_hash,
                syntax_valid=True,
                patched_source=patched_source,
            )

        # 8. Scope level calculation
        if lines_added <= 2 and lines_removed <= 1:
            scope = RepairScope.SCOPE_1
        elif lines_added <= 8 and lines_removed <= 4:
            scope = RepairScope.SCOPE_2
        elif lines_added <= 25:
            scope = RepairScope.SCOPE_3
        else:
            scope = RepairScope.SCOPE_4

        # Scope enforcement
        scope_hierarchy = {
            RepairScope.SCOPE_1: 1,
            RepairScope.SCOPE_2: 2,
            RepairScope.SCOPE_3: 3,
            RepairScope.SCOPE_4: 4,
            RepairScope.SCOPE_5: 5,
            RepairScope.OUT_OF_SCOPE: 99,
        }
        if scope_hierarchy[scope] > scope_hierarchy[max_allowed_scope]:
            return PatchSanityResult(
                is_valid=False,
                rejection_reason=f"Patch scope '{scope.value}' exceeds max allowed scope '{max_allowed_scope.value}'.",
                scope=scope,
                lines_added=lines_added,
                lines_removed=lines_removed,
                complexity_delta=lines_added - lines_removed,
                patch_sha256=patch_sha256,
                candidate_hash=cand_hash,
                syntax_valid=True,
                patched_source=patched_source,
            )

        return PatchSanityResult(
            is_valid=True,
            rejection_reason=None,
            scope=scope,
            lines_added=lines_added,
            lines_removed=lines_removed,
            complexity_delta=lines_added - lines_removed,
            patch_sha256=patch_sha256,
            candidate_hash=cand_hash,
            syntax_valid=True,
            patched_source=patched_source,
        )
