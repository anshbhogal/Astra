"""
ASTRA Engine - Boundary Condition Mutation Operator

Fixes off-by-one errors and boundary condition violations on comparison operations.
"""

import ast
from typing import List

from engine.repair.ast_pinpointer import ASTTargetContext
from engine.repair.mutators.base import BaseMutator, generate_unidiff


class BoundaryConditionMutator(BaseMutator):
    """Mutates comparison operators when failure evidence indicates off-by-one / boundary faults."""

    OP_TRANSFORMS = {
        "<": "<=",
        "<=": "<",
        ">": ">=",
        ">=": ">",
        "==": "!=",
        "!=": "==",
    }

    @property
    def name(self) -> str:
        return "BOUNDARY_CONDITION_MUTATOR"

    def can_mutate(
        self,
        context: ASTTargetContext,
        exception_type: str,
        failure_message: str,
    ) -> bool:
        # Precondition 1: Exception or failure indicates index/boundary error
        ex_lower = exception_type.lower()
        msg_lower = failure_message.lower()
        is_boundary_evidence = (
            "index" in ex_lower
            or "offbyone" in ex_lower
            or "assertion" in ex_lower
            or "range" in msg_lower
            or "boundary" in msg_lower
            or "limit" in msg_lower
            or "greater" in msg_lower
            or "less" in msg_lower
            or "==" in msg_lower
        )
        if not is_boundary_evidence:
            return False

        # Precondition 2: Target statement contains a comparison operator
        snippet = context.statement_snippet
        return any(op in snippet for op in self.OP_TRANSFORMS.keys())

    def generate_patches(
        self,
        context: ASTTargetContext,
        original_source: str,
    ) -> List[str]:
        patches: List[str] = []
        lines = original_source.splitlines(keepends=True)

        for line_idx in range(context.start_line - 1, min(context.end_line, len(lines))):
            target_line = lines[line_idx]

            # Try each applicable operator transformation
            for old_op, new_op in self.OP_TRANSFORMS.items():
                # Word-boundary or space-boundary replacement to avoid mangling identifiers
                patterns = [f" {old_op} ", f"\t{old_op} "]
                for pattern in patterns:
                    replacement = pattern.replace(old_op, new_op)
                    if pattern in target_line:
                        mutated_line = target_line.replace(pattern, replacement, 1)
                        if mutated_line != target_line:
                            mutated_lines = list(lines)
                            mutated_lines[line_idx] = mutated_line
                            patched_code = "".join(mutated_lines)

                            # Verify syntax before yielding
                            try:
                                ast.parse(patched_code)
                                unidiff = generate_unidiff(context.file_path, original_source, patched_code)
                                if unidiff and unidiff not in patches:
                                    patches.append(unidiff)
                            except SyntaxError:
                                pass

        return patches
