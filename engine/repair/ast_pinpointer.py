"""
ASTRA Engine - AST Statement Pinpointer & Context Extractor

Maps line numbers from Phase 6 Fault Localization to exact AST statement nodes,
calculating deterministic bounding regions, scopes, local symbol tables, and AST hashes.
"""

import ast
from dataclasses import dataclass, field
from typing import Any, List, Optional, Set, Tuple

from engine.repair.context import compute_ast_node_hash


@dataclass(frozen=True)
class ASTTargetContext:
    file_path: str
    target_node_type: str
    start_line: int
    end_line: int
    statement_snippet: str
    enclosing_function_name: str
    enclosing_function_snippet: str
    allowed_start_line: int
    allowed_end_line: int
    local_variable_names: List[str]
    imported_symbols: List[str]
    source_ast_hash: str


class ASTPinpointer:
    """Extracts and bounds target statement nodes from source code."""

    STATEMENT_NODE_TYPES = (
        ast.If,
        ast.For,
        ast.While,
        ast.Return,
        ast.Assign,
        ast.AnnAssign,
        ast.AugAssign,
        ast.Raise,
        ast.Expr,
        ast.Assert,
        ast.With,
        ast.Try,
    )

    def __init__(self, default_scope_padding: int = 15):
        self.default_scope_padding = default_scope_padding

    def pinpoint(
        self,
        source_code: str,
        file_path: str,
        target_line: int,
    ) -> Optional[ASTTargetContext]:
        """
        Parses source_code and pinpoints the innermost statement node at target_line.
        Returns ASTTargetContext with bounded scope or None if parsing fails.
        """
        try:
            tree = ast.parse(source_code, filename=file_path)
        except SyntaxError:
            return None

        lines = source_code.splitlines()
        total_lines = len(lines)

        # 1. Collect all imported symbols
        imported_symbols: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_symbols.append(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_symbols.append(alias.asname or alias.name)

        # 2. Find innermost statement matching target_line and enclosing function
        best_node: Optional[ast.AST] = None
        best_span = (0, 999999)
        enclosing_func: Optional[ast.FunctionDef] = None

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_start = getattr(node, "lineno", 0)
                func_end = getattr(node, "end_lineno", func_start)
                if func_start <= target_line <= func_end:
                    enclosing_func = node

            if isinstance(node, self.STATEMENT_NODE_TYPES):
                s_line = getattr(node, "lineno", 0)
                e_line = getattr(node, "end_lineno", s_line)
                if s_line <= target_line <= e_line:
                    span_len = e_line - s_line
                    current_best_len = best_span[1] - best_span[0]
                    if span_len < current_best_len or best_node is None:
                        best_node = node
                        best_span = (s_line, e_line)

        # Fallback if no specific statement found: bound to target_line
        if best_node is None:
            start_line = max(1, target_line)
            end_line = min(total_lines, target_line)
            node_type = "Line"
            node_dump = f"Line:{target_line}"
        else:
            start_line = best_node.lineno
            end_line = getattr(best_node, "end_lineno", start_line)
            node_type = best_node.__class__.__name__
            node_dump = ast.dump(best_node)

        # 3. Extract statement snippet
        snippet_lines = lines[start_line - 1 : end_line]
        statement_snippet = "\n".join(snippet_lines)

        # 4. Extract enclosing function context
        if enclosing_func is not None:
            func_name = enclosing_func.name
            func_start = enclosing_func.lineno
            func_end = getattr(enclosing_func, "end_lineno", func_start)
            func_snippet = "\n".join(lines[func_start - 1 : func_end])
            allowed_start = func_start
            allowed_end = func_end

            # Extract local variables
            local_vars: Set[str] = set()
            for arg in enclosing_func.args.args:
                local_vars.add(arg.arg)
            for subnode in ast.walk(enclosing_func):
                if isinstance(subnode, ast.Name) and isinstance(subnode.ctx, ast.Store):
                    local_vars.add(subnode.id)
            local_variable_names = sorted(list(local_vars))
        else:
            func_name = "<module>"
            func_snippet = statement_snippet
            allowed_start = max(1, start_line - self.default_scope_padding)
            allowed_end = min(total_lines, end_line + self.default_scope_padding)
            local_variable_names = []

        ast_hash = compute_ast_node_hash(node_dump)

        return ASTTargetContext(
            file_path=file_path,
            target_node_type=node_type,
            start_line=start_line,
            end_line=end_line,
            statement_snippet=statement_snippet,
            enclosing_function_name=func_name,
            enclosing_function_snippet=func_snippet,
            allowed_start_line=allowed_start,
            allowed_end_line=allowed_end,
            local_variable_names=local_variable_names,
            imported_symbols=sorted(list(set(imported_symbols))),
            source_ast_hash=ast_hash,
        )
