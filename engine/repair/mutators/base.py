"""
ASTRA Engine - Base Mutation Operator Protocol & Diff Utilities
"""

import difflib
from abc import ABC, abstractmethod
from typing import List

from engine.repair.ast_pinpointer import ASTTargetContext


def generate_unidiff(file_path: str, original_source: str, patched_source: str) -> str:
    """Generates standard git-compatible unified diff."""
    norm_path = file_path.replace("\\", "/").lstrip("/")
    orig_lines = original_source.splitlines(keepends=True)
    patch_lines = patched_source.splitlines(keepends=True)

    diff = difflib.unified_diff(
        orig_lines,
        patch_lines,
        fromfile=f"a/{norm_path}",
        tofile=f"b/{norm_path}",
    )
    return "".join(diff)


class BaseMutator(ABC):
    """Abstract base class for all deterministic AST mutators."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the mutation operator."""
        pass

    @abstractmethod
    def can_mutate(
        self,
        context: ASTTargetContext,
        exception_type: str,
        failure_message: str,
    ) -> bool:
        """Determines if failure evidence and AST context satisfy strict preconditions."""
        pass

    @abstractmethod
    def generate_patches(
        self,
        context: ASTTargetContext,
        original_source: str,
    ) -> List[str]:
        """
        Synthesizes candidate unified diffs for the targeted statement.
        Returns a list of unified diff strings.
        """
        pass
