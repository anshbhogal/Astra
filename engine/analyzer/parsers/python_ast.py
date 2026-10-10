import ast
from pathlib import Path
from typing import List, Dict, Any, Optional
from engine.analyzer.parsers.base import BaseASTParser
from engine.analyzer.models.function import FunctionInfo


class FunctionVisitor(ast.NodeVisitor):
    """AST NodeVisitor traversing Python modules to extract function metadata and route decorators."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.functions: List[FunctionInfo] = []
        self.current_class: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef):
        prev_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._process_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._process_function(node, is_async=True)

    def _process_function(self, node: ast.AST, is_async: bool):
        func_node = node  # type: ignore
        func_name = func_node.name

        if self.current_class:
            qualified_name = f"{self.current_class}.{func_name}"
        else:
            qualified_name = func_name

        # Extract Decorators
        decorators: List[str] = []
        for dec in func_node.decorator_list:
            try:
                dec_str = ast.unparse(dec)
                if not dec_str.startswith("@"):
                    dec_str = f"@{dec_str}"
                decorators.append(dec_str)
            except Exception:
                pass

        # Extract Parameters
        parameters = self._extract_parameters(func_node.args)

        # Return Annotation
        return_type = "Any"
        if func_node.returns:
            try:
                return_type = ast.unparse(func_node.returns)
            except Exception:
                return_type = "Any"

        # Docstring
        docstring = ast.get_docstring(func_node)

        # Extracted Called Functions inside body
        called_functions = self._extract_called_functions(func_node)

        self.functions.append(
            FunctionInfo(
                name=func_name,
                qualified_name=qualified_name,
                file_path=self.file_path,
                line_number=func_node.lineno,
                parameters=parameters,
                return_type=return_type,
                decorators=decorators,
                docstring=docstring,
                called_functions=called_functions,
                is_async=is_async,
            )
        )

        self.generic_visit(node)

    def _extract_parameters(self, args: ast.arguments) -> List[Dict[str, Any]]:
        params = []
        # Calculate defaults offset
        defaults = list(args.defaults)
        num_args = len(args.args)
        num_defaults = len(defaults)
        default_offset = num_args - num_defaults

        for idx, arg in enumerate(args.args):
            if arg.arg in ["self", "cls"]:
                continue

            param_type = "Any"
            if arg.annotation:
                try:
                    param_type = ast.unparse(arg.annotation)
                except Exception:
                    param_type = "Any"

            default_val = None
            if idx >= default_offset:
                def_node = defaults[idx - default_offset]
                try:
                    default_val = ast.unparse(def_node)
                except Exception:
                    default_val = "..."

            params.append({
                "name": arg.arg,
                "type": param_type,
                "required": default_val is None,
                "default": default_val,
            })
        return params

    def _extract_called_functions(self, func_node: ast.AST) -> List[str]:
        calls = []

        class CallVisitor(ast.NodeVisitor):
            def visit_Call(self, call_node: ast.Call):
                try:
                    if isinstance(call_node.func, ast.Name):
                        calls.append(call_node.func.id)
                    elif isinstance(call_node.func, ast.Attribute):
                        calls.append(call_node.func.attr)
                except Exception:
                    pass
                self.generic_visit(call_node)

        call_visitor = CallVisitor()
        for stmt in getattr(func_node, "body", []):
            call_visitor.visit(stmt)

        return list(set(calls))


class PythonASTParser(BaseASTParser):
    """Deterministic Python AST Parser using built-in ast module."""

    def parse(self, source_file: Any) -> List[FunctionInfo]:
        """Convenience method accepting a SourceFile model."""
        try:
            content = Path(source_file.path).read_text(encoding="utf-8", errors="ignore")
            return self.parse_file(source_file.path, content)
        except Exception:
            return []

    def parse_file(self, file_path: str, file_content: str) -> List[FunctionInfo]:
        try:
            tree = ast.parse(file_content, filename=file_path)
            visitor = FunctionVisitor(file_path=file_path)
            visitor.visit(tree)
            return visitor.functions
        except SyntaxError:
            # Gracefully handle syntax errors in untrusted repos
            return []
        except Exception:
            return []
