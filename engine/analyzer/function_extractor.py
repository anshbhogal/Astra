"""Function Extractor & Contract Analyzer for ASTRA Gen-2 Multi-Layer Testing (G2-03).

Extracts callable functions, methods, parameters, type hints, docstrings,
side-effect tags, and purity estimates using AST traversal.
"""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class SideEffectTag:
    FILE_IO = "FILE_IO"
    NETWORK = "NETWORK"
    ENV = "ENV"
    DB = "DB"
    LLM = "LLM"
    RANDOM = "RANDOM"
    TIME = "TIME"


@dataclass(frozen=True)
class ParameterSchema:
    name: str
    type_annotation: str = "Any"
    has_default: bool = False
    default_value: Optional[str] = None


@dataclass(frozen=True)
class FunctionContract:
    function_id: str
    qualified_name: str
    file_path: str
    source_hash: str
    line_number: int
    parameters: list[ParameterSchema]
    return_schema: str = "Any"
    docstring: Optional[str] = None
    side_effects: list[str] = field(default_factory=list)
    called_functions: list[str] = field(default_factory=list)
    purity_estimate: float = 1.0
    cyclomatic_complexity: int = 1
    is_async: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "function_id": self.function_id,
            "qualified_name": self.qualified_name,
            "file_path": self.file_path,
            "source_hash": self.source_hash,
            "line_number": self.line_number,
            "parameters": [
                {
                    "name": p.name,
                    "type_annotation": p.type_annotation,
                    "has_default": p.has_default,
                    "default_value": p.default_value,
                }
                for p in self.parameters
            ],
            "return_schema": self.return_schema,
            "docstring": self.docstring,
            "side_effects": self.side_effects,
            "called_functions": self.called_functions,
            "purity_estimate": self.purity_estimate,
            "cyclomatic_complexity": self.cyclomatic_complexity,
            "is_async": self.is_async,
        }


class FunctionASTVisitor(ast.NodeVisitor):
    """Traverses an AST module to extract callable FunctionContracts."""

    def __init__(self, file_path: str, source_code: str):
        self.file_path = file_path
        self.source_code = source_code
        self.contracts: list[FunctionContract] = []
        self.current_class: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef):
        prev = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = prev

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._process(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._process(node, is_async=True)

    def _process(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool):
        func_name = node.name

        # Skip private dunder helpers (except __init__)
        if func_name.startswith("__") and func_name.endswith("__") and func_name != "__init__":
            self.generic_visit(node)
            return

        qualified = f"{self.current_class}.{func_name}" if self.current_class else func_name

        # Function segment source hash
        try:
            node_source = ast.get_source_segment(self.source_code, node) or ast.unparse(node)
        except Exception:
            node_source = ast.unparse(node)
        src_hash = hashlib.sha256(node_source.encode("utf-8")).hexdigest()[:16]

        # Extract parameters
        parameters: list[ParameterSchema] = []
        defaults = list(node.args.defaults)
        num_args = len(node.args.args)
        num_defaults = len(defaults)
        offset = num_args - num_defaults

        for idx, arg in enumerate(node.args.args):
            if arg.arg in ("self", "cls"):
                continue
            p_type = "Any"
            if arg.annotation:
                try:
                    p_type = ast.unparse(arg.annotation)
                except Exception:
                    pass

            has_def = False
            def_val = None
            if idx >= offset:
                has_def = True
                try:
                    def_val = ast.unparse(defaults[idx - offset])
                except Exception:
                    def_val = "..."

            parameters.append(ParameterSchema(
                name=arg.arg,
                type_annotation=p_type,
                has_default=has_def,
                default_value=def_val
            ))

        # Return schema
        return_schema = "Any"
        if node.returns:
            try:
                return_schema = ast.unparse(node.returns)
            except Exception:
                pass

        docstring = ast.get_docstring(node)

        # Side effect profiling & complexity
        side_effects, called_funcs, complexity = self._profile_body(node)
        purity = max(0.0, 1.0 - (len(side_effects) * 0.25))

        contract_id = f"fn_{hashlib.sha256(f'{self.file_path}:{qualified}'.encode('utf-8')).hexdigest()[:12]}"

        self.contracts.append(FunctionContract(
            function_id=contract_id,
            qualified_name=qualified,
            file_path=self.file_path,
            source_hash=src_hash,
            line_number=node.lineno,
            parameters=parameters,
            return_schema=return_schema,
            docstring=docstring,
            side_effects=sorted(list(side_effects)),
            called_functions=called_funcs,
            purity_estimate=purity,
            cyclomatic_complexity=complexity,
            is_async=is_async,
        ))

        self.generic_visit(node)

    def _profile_body(self, node: ast.AST) -> tuple[set[str], list[str], int]:
        side_effects: set[str] = set()
        called_funcs: list[str] = []
        complexity = 1

        for child in ast.walk(node):
            # Complexity branches
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With, ast.Assert)):
                complexity += 1

            if isinstance(child, ast.Call):
                call_name = ""
                if isinstance(child.func, ast.Name):
                    call_name = child.func.id
                elif isinstance(child.func, ast.Attribute):
                    call_name = child.func.attr
                    # Detect common side effects
                    if child.func.attr in ("open", "read", "write", "listdir", "remove", "mkdir"):
                        side_effects.add(SideEffectTag.FILE_IO)
                    elif child.func.attr in ("get", "post", "put", "delete", "request"):
                        side_effects.add(SideEffectTag.NETWORK)
                    elif child.func.attr in ("getenv", "environ"):
                        side_effects.add(SideEffectTag.ENV)
                    elif child.func.attr in ("create", "encode", "predict", "generate", "chat"):
                        side_effects.add(SideEffectTag.LLM)
                    elif child.func.attr in ("query", "execute", "commit", "rollback"):
                        side_effects.add(SideEffectTag.DB)

                if call_name:
                    called_funcs.append(call_name)
                    if call_name in ("open", "print"):
                        side_effects.add(SideEffectTag.FILE_IO)

        return side_effects, called_funcs[:20], complexity


class FunctionExtractor:
    """Discovers and extracts all callable FunctionContracts in a codebase."""

    @classmethod
    def extract_from_file(cls, file_path: str, repo_root: str) -> list[FunctionContract]:
        p = Path(file_path)
        if not p.exists() or not p.is_file() or p.suffix != ".py":
            return []

        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=str(p))
            rel_path = str(p.relative_to(Path(repo_root))).replace("\\", "/")
            visitor = FunctionASTVisitor(file_path=rel_path, source_code=content)
            visitor.visit(tree)
            return visitor.contracts
        except Exception:
            return []

    @classmethod
    def extract_from_directory(cls, repo_root: str) -> list[FunctionContract]:
        root = Path(repo_root)
        all_contracts: list[FunctionContract] = []

        ignore_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build", "tests", "test", ".pytest_cache"}

        for p in root.rglob("*.py"):
            if any(part in ignore_dirs for part in p.parts):
                continue
            all_contracts.extend(cls.extract_from_file(str(p), repo_root))

        # Sort: public pure functions first, then by complexity descending
        all_contracts.sort(
            key=lambda c: (
                0 if not c.qualified_name.startswith("_") else 1,
                -c.purity_estimate,
                -c.cyclomatic_complexity,
            )
        )
        return all_contracts
