"""AST Change Analyzer with Qualified Symbol Identity.
Parses Python source files using AST to extract full symbol identity (module.Class.method)
and detect signature, body, decorator, or structural AST changes.
"""

import ast
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any
from engine.regression.git_diff_parser import FileDiff, ChangedSymbol


@dataclass
class SymbolIdentity:
    symbol_id: str  # e.g., python:app.services.user_service.UserService.get_user
    language: str
    module_path: str
    class_name: Optional[str]
    symbol_name: str
    start_line: int
    end_line: int
    signature_hash: str
    body_hash: str
    decorators: List[str] = field(default_factory=list)


class ASTChangeAnalyzer:
    """Extracts qualified symbols from Python source code and maps git line diffs to changed symbols."""

    def __init__(self):
        pass

    def extract_symbols(self, source_code: str, module_path: str, language: str = "python") -> List[SymbolIdentity]:
        """Parses source code into a list of SymbolIdentity objects."""
        if not source_code or not source_code.strip():
            return []

        try:
            tree = ast.parse(source_code)
        except Exception:
            return []

        symbols: List[SymbolIdentity] = []
        module_name = self._filepath_to_module(module_path)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                class_name = self._get_parent_class_name(node, tree)
                sym_id = self._format_symbol_id(language, module_name, class_name, node.name)
                sig_hash = self._compute_signature_hash(node)
                body_hash = self._compute_body_hash(node)
                decorators = [ast.unparse(d) if hasattr(ast, "unparse") else str(d) for d in node.decorator_list]

                start_line = getattr(node, "lineno", 1)
                end_line = getattr(node, "end_lineno", start_line)

                symbols.append(SymbolIdentity(
                    symbol_id=sym_id,
                    language=language,
                    module_path=module_path,
                    class_name=class_name,
                    symbol_name=node.name,
                    start_line=start_line,
                    end_line=end_line,
                    signature_hash=sig_hash,
                    body_hash=body_hash,
                    decorators=decorators,
                ))

        return symbols

    def analyze_file_diff(
        self,
        file_diff: FileDiff,
        old_source: Optional[str] = None,
        new_source: Optional[str] = None,
    ) -> List[ChangedSymbol]:
        """Maps a FileDiff to affected symbol identities in the AST."""
        changed_symbols: List[ChangedSymbol] = []

        old_symbols = self.extract_symbols(old_source, file_diff.old_path or file_diff.new_path) if old_source else []
        new_symbols = self.extract_symbols(new_source, file_diff.new_path) if new_source else []

        old_sym_map = {s.symbol_id: s for s in old_symbols}
        new_sym_map = {s.symbol_id: s for s in new_symbols}

        all_sym_ids: Set[str] = set(old_sym_map.keys()).union(set(new_sym_map.keys()))

        # If source code is missing, fallback to matching line ranges against new_symbols or heuristic
        if not old_source and not new_source:
            return changed_symbols

        for sym_id in all_sym_ids:
            old_sym = old_sym_map.get(sym_id)
            new_sym = new_sym_map.get(sym_id)

            if not old_sym and new_sym:
                # Symbol added
                changed_symbols.append(ChangedSymbol(
                    symbol_id=sym_id,
                    change_type="ADDED",
                    start_line=new_sym.start_line,
                    end_line=new_sym.end_line,
                    signature_hash=new_sym.signature_hash,
                    body_hash=new_sym.body_hash,
                ))
            elif old_sym and not new_sym:
                # Symbol deleted
                changed_symbols.append(ChangedSymbol(
                    symbol_id=sym_id,
                    change_type="DELETED",
                    start_line=old_sym.start_line,
                    end_line=old_sym.end_line,
                    signature_hash=old_sym.signature_hash,
                    body_hash=old_sym.body_hash,
                ))
            elif old_sym and new_sym:
                # Compare hashes & decorators
                sig_changed = (old_sym.signature_hash != new_sym.signature_hash)
                body_changed = (old_sym.body_hash != new_sym.body_hash)
                dec_changed = (old_sym.decorators != new_sym.decorators)

                # Check if line diff overlaps symbol line range
                line_overlap = any(
                    new_sym.start_line <= line <= new_sym.end_line
                    for line in file_diff.added_lines
                ) or any(
                    old_sym.start_line <= line <= old_sym.end_line
                    for line in file_diff.deleted_lines
                )

                if sig_changed:
                    chg_type = "SIGNATURE_CHANGED"
                elif dec_changed:
                    chg_type = "DECORATOR_CHANGED"
                elif body_changed or line_overlap:
                    chg_type = "MODIFIED"
                else:
                    continue

                changed_symbols.append(ChangedSymbol(
                    symbol_id=sym_id,
                    change_type=chg_type,
                    start_line=new_sym.start_line,
                    end_line=new_sym.end_line,
                    signature_hash=new_sym.signature_hash,
                    body_hash=new_sym.body_hash,
                ))

        return changed_symbols

    def _filepath_to_module(self, filepath: str) -> str:
        clean_path = filepath.replace("\\", "/").strip("/")
        if clean_path.endswith(".py"):
            clean_path = clean_path[:-3]
        return clean_path.replace("/", ".")

    def _format_symbol_id(self, language: str, module_name: str, class_name: Optional[str], func_name: str) -> str:
        if class_name:
            return f"{language}:{module_name}.{class_name}.{func_name}"
        return f"{language}:{module_name}.{func_name}"

    def _get_parent_class_name(self, func_node: ast.AST, tree: ast.AST) -> Optional[str]:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for child in ast.walk(node):
                    if child is func_node:
                        return node.name
        return None

    def _compute_signature_hash(self, node: ast.AST) -> str:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args_str = ast.unparse(node.args) if hasattr(ast, "unparse") else str(node.args)
            returns_str = ast.unparse(node.returns) if hasattr(ast, "unparse") and node.returns else ""
            sig_raw = f"{node.name}({args_str}) -> {returns_str}"
            return hashlib.sha256(sig_raw.encode("utf-8")).hexdigest()[:16]
        return ""

    def _compute_body_hash(self, node: ast.AST) -> str:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body_raw = ast.unparse(node) if hasattr(ast, "unparse") else str(node.body)
            return hashlib.sha256(body_raw.encode("utf-8")).hexdigest()[:16]
        return ""
