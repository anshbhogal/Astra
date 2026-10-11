"""
ASTRA Engine - Null Safety Guard Mutation Operator

Synthesizes null/None guards for NoneType dereferences (AttributeError & TypeError).
"""

import ast
import re
from typing import List, Optional

from engine.repair.ast_pinpointer import ASTTargetContext
from engine.repair.mutators.base import BaseMutator, generate_unidiff


class NullSafetyGuardMutator(BaseMutator):
    """Guards against AttributeError / TypeError NoneType dereferences."""

    @property
    def name(self) -> str:
        return "NULL_SAFETY_GUARD_MUTATOR"

    def can_mutate(
        self,
        context: ASTTargetContext,
        exception_type: str,
        failure_message: str,
    ) -> bool:
        ex_lower = exception_type.lower()
        msg_lower = failure_message.lower()

        # Evidence precondition: Explicit NoneType dereference
        is_none_error = (
            "nonetype" in msg_lower
            or "attributeerror" in ex_lower
            or ("typeerror" in ex_lower and "subscriptable" in msg_lower)
            or "null" in msg_lower
        )
        return is_none_error

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

        # Extract identifiers from statement snippet
        try:
            tree = ast.parse(context.statement_snippet.strip())
        except SyntaxError:
            return patches

        candidate_names: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                candidate_names.append(node.value.id)
            elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
                candidate_names.append(node.value.id)

        # Remove duplicates while preserving order
        candidate_names = list(dict.fromkeys(candidate_names))

        for var_name in candidate_names:
            # Pattern A: Preceding Null Check with Early Return / Default
            # if <var> is None: return None
            guard_stmt = f"{indent_str}if {var_name} is None:\n{indent_str}    return None\n"
            mutated_lines = list(lines)
            mutated_lines.insert(context.start_line - 1, guard_stmt)
            patched_code = "".join(mutated_lines)

            try:
                ast.parse(patched_code)
                diff = generate_unidiff(context.file_path, original_source, patched_code)
                if diff and diff not in patches:
                    patches.append(diff)
            except SyntaxError:
                pass

            # Pattern B: Inline Safe Navigation (getattr or ternary)
            # obj.attr -> (obj.attr if obj is not None else None)
            attr_pattern = rf"\b{var_name}\.([a-zA-Z_][a-zA-Z0-9_]*)\b"
            matches = list(re.finditer(attr_pattern, target_line))
            for match in matches:
                full_expr = match.group(0)
                safe_expr = f"({full_expr} if {var_name} is not None else None)"
                mutated_line = target_line.replace(full_expr, safe_expr, 1)

                mutated_lines = list(lines)
                mutated_lines[context.start_line - 1] = mutated_line
                patched_code = "".join(mutated_lines)

                try:
                    ast.parse(patched_code)
                    diff = generate_unidiff(context.file_path, original_source, patched_code)
                    if diff and diff not in patches:
                        patches.append(diff)
                except SyntaxError:
                    pass

        return patches
