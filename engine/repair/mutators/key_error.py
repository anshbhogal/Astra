"""
ASTRA Engine - KeyError Guard Mutation Operator

Transforms dangerous dictionary bracket lookups (d[key]) into safe .get(key, default) accessors.
"""

import ast
import re
from typing import List

from engine.repair.ast_pinpointer import ASTTargetContext
from engine.repair.mutators.base import BaseMutator, generate_unidiff


class KeyErrorGuardMutator(BaseMutator):
    """Guards against KeyError exceptions in dictionary access."""

    @property
    def name(self) -> str:
        return "KEY_ERROR_GUARD_MUTATOR"

    def can_mutate(
        self,
        context: ASTTargetContext,
        exception_type: str,
        failure_message: str,
    ) -> bool:
        ex_lower = exception_type.lower()
        msg_lower = failure_message.lower()
        return "keyerror" in ex_lower or "keyerror" in msg_lower

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

        # Match dict[key] patterns: identifier[expr]
        subscript_re = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\[([^\]]+)\]")
        matches = list(subscript_re.finditer(target_line))

        for match in matches:
            dict_var = match.group(1)
            key_expr = match.group(2)
            orig_expr = match.group(0)

            # Option 1: d.get(key, None)
            safe_expr_none = f"{dict_var}.get({key_expr}, None)"
            mutated_line_none = target_line.replace(orig_expr, safe_expr_none, 1)

            mutated_lines = list(lines)
            mutated_lines[context.start_line - 1] = mutated_line_none
            patched_code = "".join(mutated_lines)

            try:
                ast.parse(patched_code)
                diff = generate_unidiff(context.file_path, original_source, patched_code)
                if diff and diff not in patches:
                    patches.append(diff)
            except SyntaxError:
                pass

            # Option 2: d.get(key, {}) for nested dict structures
            safe_expr_dict = f"{dict_var}.get({key_expr}, {{}})"
            mutated_line_dict = target_line.replace(orig_expr, safe_expr_dict, 1)

            mutated_lines = list(lines)
            mutated_lines[context.start_line - 1] = mutated_line_dict
            patched_code = "".join(mutated_lines)

            try:
                ast.parse(patched_code)
                diff = generate_unidiff(context.file_path, original_source, patched_code)
                if diff and diff not in patches:
                    patches.append(diff)
            except SyntaxError:
                pass

        return patches
