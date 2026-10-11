"""
ASTRA Engine - HTTPException Wrapper Mutation Operator

Catches unhandled internal domain/ORM exceptions escaping HTTP controllers and transforms
them into clean client errors (HTTP 404 or 400).
"""

import ast
from typing import List

from engine.repair.ast_pinpointer import ASTTargetContext
from engine.repair.mutators.base import BaseMutator, generate_unidiff


class HTTPExceptionWrapperMutator(BaseMutator):
    """Wraps unhandled domain lookup exceptions with HTTPException(404/400)."""

    @property
    def name(self) -> str:
        return "HTTP_EXCEPTION_WRAPPER_MUTATOR"

    def can_mutate(
        self,
        context: ASTTargetContext,
        exception_type: str,
        failure_message: str,
    ) -> bool:
        ex_lower = exception_type.lower()
        msg_lower = failure_message.lower()

        # Evidence precondition: Internal lookup failure or unhandled exception
        is_lookup_fault = (
            "notfound" in ex_lower
            or "noresultfound" in ex_lower
            or "doesnotexist" in ex_lower
            or "keyerror" in ex_lower
            or "valueerror" in ex_lower
            or "500" in msg_lower
            or "unhandled" in msg_lower
        )
        return is_lookup_fault

    def generate_patches(
        self,
        context: ASTTargetContext,
        original_source: str,
    ) -> List[str]:
        patches: List[str] = []
        lines = original_source.splitlines(keepends=True)
        if context.start_line - 1 >= len(lines):
            return patches

        target_line = lines[context.start_line - 1]
        indent = len(target_line) - len(target_line.lstrip())
        indent_str = target_line[:indent]
        inner_indent_str = indent_str + "    "

        # Pattern: Try-Except wrapping with HTTPException(status_code=404)
        wrapped_block = (
            f"{indent_str}try:\n"
            f"{inner_indent_str}{target_line.lstrip()}"
            f"{indent_str}except Exception:\n"
            f"{inner_indent_str}raise HTTPException(status_code=404, detail=\"Resource not found\")\n"
        )

        mutated_lines = list(lines)
        mutated_lines[context.start_line - 1] = wrapped_block
        patched_code = "".join(mutated_lines)

        try:
            ast.parse(patched_code)
            diff = generate_unidiff(context.file_path, original_source, patched_code)
            if diff and diff not in patches:
                patches.append(diff)
        except SyntaxError:
            pass

        return patches
