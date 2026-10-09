"""Git Diff Parser with Rename Detection & Multi-Commit Support.
Parses git diff outputs into structured file diff records with exact line range tracking.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ChangedSymbol:
    symbol_id: str
    change_type: str  # MODIFIED, ADDED, DELETED, SIGNATURE_CHANGED, DECORATOR_CHANGED
    start_line: int
    end_line: int
    signature_hash: Optional[str] = None
    body_hash: Optional[str] = None


@dataclass
class FileDiff:
    old_path: Optional[str]
    new_path: str
    change_type: str  # ADDED, DELETED, MODIFIED, RENAMED, COPIED
    rename_similarity: float = 1.0
    added_lines: List[int] = field(default_factory=list)
    deleted_lines: List[int] = field(default_factory=list)
    modified_line_ranges: List[Dict[str, int]] = field(default_factory=list)
    changed_symbols: List[ChangedSymbol] = field(default_factory=list)
    change_category: str = "CODE_MODIFIED"  # SCHEMA_CHANGE, ROUTE_CHANGE, UTIL_CHANGE, TEST_ONLY, DOCUMENTATION_ONLY


class GitDiffParser:
    """Parses unified diff strings or git commit comparisons into structured FileDiff records."""

    def __init__(self):
        pass

    def parse_diff(self, diff_text: str) -> List[FileDiff]:
        """Parses a unified git diff string into a list of FileDiff objects."""
        if not diff_text or not diff_text.strip():
            return []

        file_diffs: List[FileDiff] = []
        raw_chunks = self._split_file_diffs(diff_text)

        for chunk in raw_chunks:
            parsed = self._parse_single_file_diff(chunk)
            if parsed:
                file_diffs.append(parsed)

        return file_diffs

    def _split_file_diffs(self, diff_text: str) -> List[str]:
        """Splits unified diff by 'diff --git' markers."""
        lines = diff_text.splitlines()
        chunks = []
        current_chunk = []

        for line in lines:
            if line.startswith("diff --git ") and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
            else:
                current_chunk.append(line)

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks

    def _parse_single_file_diff(self, chunk: str) -> Optional[FileDiff]:
        lines = chunk.splitlines()
        if not lines:
            return None

        header_line = lines[0]
        # Match diff --git a/path b/path
        git_header = re.match(r"diff --git a/(.+) b/(.+)", header_line)
        if not git_header:
            old_path_guess = None
            new_path_guess = "unknown"
        else:
            old_path_guess = git_header.group(1)
            new_path_guess = git_header.group(2)

        old_path = old_path_guess
        new_path = new_path_guess
        change_type = "MODIFIED"
        rename_similarity = 1.0

        added_lines: List[int] = []
        deleted_lines: List[int] = []
        modified_line_ranges: List[Dict[str, int]] = []

        # Parse header metadata (rename from/to, similarity, new file, deleted file)
        i = 0
        new_line_offset = 0
        old_line_offset = 0

        while i < len(lines):
            line = lines[i]

            if line.startswith("similarity index "):
                match = re.search(r"(\d+)%", line)
                if match:
                    rename_similarity = float(match.group(1)) / 100.0

            elif line.startswith("rename from "):
                old_path = line[12:].strip()
                change_type = "RENAMED"

            elif line.startswith("rename to "):
                new_path = line[10:].strip()
                change_type = "RENAMED"

            elif line.startswith("new file mode "):
                change_type = "ADDED"
                old_path = None

            elif line.startswith("deleted file mode "):
                change_type = "DELETED"
                new_path = old_path or new_path

            elif line.startswith("@@"):
                # Hunk header @@ -old_start,old_count +new_start,new_count @@
                hunk_match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
                if hunk_match:
                    old_start = int(hunk_match.group(1))
                    old_count = int(hunk_match.group(2) or 1)
                    new_start = int(hunk_match.group(3))
                    new_count = int(hunk_match.group(4) or 1)

                    old_line_offset = old_start
                    new_line_offset = new_start

                    modified_line_ranges.append({
                        "old_start": old_start,
                        "old_count": old_count,
                        "new_start": new_start,
                        "new_count": new_count,
                    })

            elif line.startswith("+") and not line.startswith("+++"):
                added_lines.append(new_line_offset)
                new_line_offset += 1

            elif line.startswith("-") and not line.startswith("---"):
                deleted_lines.append(old_line_offset)
                old_line_offset += 1

            elif not line.startswith("\\") and not line.startswith("diff"):
                new_line_offset += 1
                old_line_offset += 1

            i += 1

        # Determine overall change category
        change_category = self._determine_change_category(new_path, added_lines, deleted_lines)

        return FileDiff(
            old_path=old_path,
            new_path=new_path,
            change_type=change_type,
            rename_similarity=rename_similarity,
            added_lines=added_lines,
            deleted_lines=deleted_lines,
            modified_line_ranges=modified_line_ranges,
            changed_symbols=[],
            change_category=change_category,
        )

    def _determine_change_category(self, filepath: str, added_lines: List[int], deleted_lines: List[int]) -> str:
        fp_lower = filepath.lower()
        if "test" in fp_lower or fp_lower.endswith("_test.py") or fp_lower.startswith("tests/"):
            return "TEST_ONLY"
        if fp_lower.endswith(".md") or fp_lower.endswith(".rst") or fp_lower.endswith(".txt"):
            return "DOCUMENTATION_ONLY"
        if "schema" in fp_lower or "models" in fp_lower or "migration" in fp_lower:
            return "SCHEMA_CHANGE"
        if "router" in fp_lower or "api" in fp_lower or "endpoint" in fp_lower or "views" in fp_lower:
            return "ROUTE_CHANGE"
        return "CODE_MODIFIED"
