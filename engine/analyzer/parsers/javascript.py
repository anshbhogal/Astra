"""JavaScript & Express AST Parser for ASTRA.

Extracts functions, arrow functions, class methods, parameters, and Express route handlers.
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Optional
from engine.analyzer.parsers.base import BaseASTParser
from engine.analyzer.models.function import FunctionInfo


class JavaScriptParser(BaseASTParser):
    """JavaScript AST Parser for Node.js / Express applications."""

    EXPRESS_ROUTE_REGEX = re.compile(
        r"(?:(app|router)\.(get|post|put|delete|patch|options|head))\(\s*['\"]([^'\"]+)['\"]\s*,\s*(async\s*)?(?:\(([^)]*)\)|([a-zA-Z0-9_$]+))",
        re.IGNORECASE
    )

    FN_DECL_REGEX = re.compile(
        r"(?:export\s+)?(?:default\s+)?(async\s+)?function(?:\s+([a-zA-Z0-9_$]+))?\s*\(([^)]*)\)",
        re.IGNORECASE
    )

    ARROW_FN_REGEX = re.compile(
        r"(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(async\s*)?(?:\(([^)]*)\)|([a-zA-Z0-9_$]+))\s*=>",
        re.IGNORECASE
    )

    FN_EXPR_REGEX = re.compile(
        r"(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(async\s*)?function\s*\(([^)]*)\)",
        re.IGNORECASE
    )

    CLASS_DECL_REGEX = re.compile(
        r"class\s+([a-zA-Z0-9_$]+)",
        re.IGNORECASE
    )

    METHOD_DECL_REGEX = re.compile(
        r"^(?:\s*(?:static|async|get|set)\s+)*([a-zA-Z0-9_$]+)\s*\(([^)]*)\)\s*\{",
        re.MULTILINE
    )

    CONTROL_KEYWORDS = {"if", "for", "while", "switch", "catch", "with"}

    def parse_file(self, file_path: str, file_content: str) -> List[FunctionInfo]:
        functions: List[FunctionInfo] = []
        lines = file_content.splitlines()

        current_class: Optional[str] = None
        pending_decorators: List[str] = []
        pending_docstring: Optional[str] = None
        in_jsdoc = False
        jsdoc_lines: List[str] = []

        seen_keys = set()

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Track JSDoc
            if "/**" in stripped:
                in_jsdoc = True
                jsdoc_lines = [stripped.replace("/**", "").strip()]
                if "*/" in stripped:
                    in_jsdoc = False
                    pending_docstring = " ".join(jsdoc_lines).replace("*/", "").strip()
                continue
            elif in_jsdoc:
                if "*/" in stripped:
                    in_jsdoc = False
                    jsdoc_lines.append(stripped.replace("*/", "").strip())
                    pending_docstring = " ".join(jsdoc_lines).strip()
                else:
                    jsdoc_lines.append(stripped.lstrip("* ").strip())
                continue

            # Track Decorators
            if stripped.startswith("@"):
                pending_decorators.append(stripped)
                continue

            # Track Classes
            class_match = self.CLASS_DECL_REGEX.search(stripped)
            if class_match:
                current_class = class_match.group(1)

            # 1. Express Routes: router.get('/path', (req, res) => ...)
            route_match = self.EXPRESS_ROUTE_REGEX.search(stripped)
            if route_match:
                router_var = route_match.group(1)
                method = route_match.group(2).lower()
                path = route_match.group(3)
                is_async = bool(route_match.group(4))
                raw_params = route_match.group(5) or route_match.group(6) or "req, res"

                path_slug = re.sub(r'[^a-zA-Z0-9_]', '_', path.strip("/")) or "root"
                fn_name = f"route_{method}_{path_slug}"
                route_dec = f"@{router_var}.{method}('{path}')"

                key = (fn_name, idx)
                if key not in seen_keys:
                    seen_keys.add(key)
                    functions.append(
                        FunctionInfo(
                            name=fn_name,
                            qualified_name=fn_name,
                            file_path=file_path,
                            line_number=idx,
                            parameters=self._parse_parameters(raw_params),
                            return_type="void",
                            decorators=[route_dec],
                            docstring=pending_docstring,
                            called_functions=[],
                            is_async=is_async,
                        )
                    )
                pending_decorators = []
                pending_docstring = None
                continue

            # 2. Function Declarations: function name(a, b) { ... }
            fn_match = self.FN_DECL_REGEX.search(stripped)
            if fn_match:
                is_async = bool(fn_match.group(1))
                fn_name = fn_match.group(2) or f"anonymous_fn_L{idx}"
                raw_params = fn_match.group(3) or ""

                if fn_name not in self.CONTROL_KEYWORDS:
                    q_name = f"{current_class}.{fn_name}" if current_class else fn_name
                    key = (fn_name, idx)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        functions.append(
                            FunctionInfo(
                                name=fn_name,
                                qualified_name=q_name,
                                file_path=file_path,
                                line_number=idx,
                                parameters=self._parse_parameters(raw_params),
                                return_type="any",
                                decorators=list(pending_decorators),
                                docstring=pending_docstring,
                                called_functions=[],
                                is_async=is_async,
                            )
                        )
                    pending_decorators = []
                    pending_docstring = None
                    continue

            # 3. Arrow Functions: const name = async (a, b) => ...
            arrow_match = self.ARROW_FN_REGEX.search(stripped)
            if arrow_match:
                fn_name = arrow_match.group(1)
                is_async = bool(arrow_match.group(2))
                raw_params = arrow_match.group(3) or arrow_match.group(4) or ""

                q_name = f"{current_class}.{fn_name}" if current_class else fn_name
                key = (fn_name, idx)
                if key not in seen_keys:
                    seen_keys.add(key)
                    functions.append(
                        FunctionInfo(
                            name=fn_name,
                            qualified_name=q_name,
                            file_path=file_path,
                            line_number=idx,
                            parameters=self._parse_parameters(raw_params),
                            return_type="any",
                            decorators=list(pending_decorators),
                            docstring=pending_docstring,
                            called_functions=[],
                            is_async=is_async,
                        )
                    )
                pending_decorators = []
                pending_docstring = None
                continue

            # 4. Function Expressions: const name = function(a, b) ...
            expr_match = self.FN_EXPR_REGEX.search(stripped)
            if expr_match:
                fn_name = expr_match.group(1)
                is_async = bool(expr_match.group(2))
                raw_params = expr_match.group(3) or ""

                q_name = f"{current_class}.{fn_name}" if current_class else fn_name
                key = (fn_name, idx)
                if key not in seen_keys:
                    seen_keys.add(key)
                    functions.append(
                        FunctionInfo(
                            name=fn_name,
                            qualified_name=q_name,
                            file_path=file_path,
                            line_number=idx,
                            parameters=self._parse_parameters(raw_params),
                            return_type="any",
                            decorators=list(pending_decorators),
                            docstring=pending_docstring,
                            called_functions=[],
                            is_async=is_async,
                        )
                    )
                pending_decorators = []
                pending_docstring = None
                continue

            # 5. Class Methods
            if current_class and "{" in stripped and "(" in stripped:
                method_match = self.METHOD_DECL_REGEX.search(stripped)
                if method_match:
                    fn_name = method_match.group(1)
                    raw_params = method_match.group(2)
                    if fn_name not in self.CONTROL_KEYWORDS and fn_name != "constructor":
                        is_async = "async " in stripped
                        q_name = f"{current_class}.{fn_name}"
                        key = (fn_name, idx)
                        if key not in seen_keys:
                            seen_keys.add(key)
                            functions.append(
                                FunctionInfo(
                                    name=fn_name,
                                    qualified_name=q_name,
                                    file_path=file_path,
                                    line_number=idx,
                                    parameters=self._parse_parameters(raw_params),
                                    return_type="any",
                                    decorators=list(pending_decorators),
                                    docstring=pending_docstring,
                                    called_functions=[],
                                    is_async=is_async,
                                )
                            )
                        pending_decorators = []
                        pending_docstring = None

        return functions

    def _parse_parameters(self, raw_params: str) -> List[Dict[str, Any]]:
        if not raw_params or not raw_params.strip():
            return []
        params = []
        tokens = self._split_comma_balanced(raw_params)
        for tok in tokens:
            tok = tok.strip()
            if not tok:
                continue
            default_val = None
            if "=" in tok:
                tok, default_val = tok.split("=", 1)
                tok = tok.strip()
                default_val = default_val.strip()

            params.append({
                "name": tok,
                "type": "any",
                "required": default_val is None,
                "default": default_val
            })
        return params

    @staticmethod
    def _split_comma_balanced(text: str) -> List[str]:
        tokens = []
        cur = []
        depth = 0
        for ch in text:
            if ch in "([{<":
                depth += 1
            elif ch in ")]}>":
                depth -= 1
            elif ch == "," and depth == 0:
                tokens.append("".join(cur).strip())
                cur = []
                continue
            cur.append(ch)
        if cur:
            tokens.append("".join(cur).strip())
        return tokens
