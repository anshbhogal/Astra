"""TypeScript & NestJS AST Parser for ASTRA.

Extracts typed functions, arrow functions, NestJS decorators, interfaces, and class methods.
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Optional
from engine.analyzer.parsers.base import BaseASTParser
from engine.analyzer.models.function import FunctionInfo


class TypeScriptParser(BaseASTParser):
    """TypeScript AST Parser for Node.js / NestJS / Next.js applications."""

    # Function Declaration: export async function name(a: string, b?: number): Promise<boolean> {
    TS_FN_DECL_REGEX = re.compile(
        r"(?:export\s+)?(?:default\s+)?(async\s+)?function(?:\s+([a-zA-Z0-9_$]+))?\s*\(([^)]*)\)(?:\s*:\s*([^;{]+))?",
        re.IGNORECASE
    )

    # Arrow Function: const name = async (a: string): Promise<void> =>
    TS_ARROW_FN_REGEX = re.compile(
        r"(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(async\s*)?(?:\(([^)]*)\)|([a-zA-Z0-9_$]+))(?:\s*:\s*([^=>;{]+))?\s*=>",
        re.IGNORECASE
    )

    # Class Method with optional modifiers & return type:
    # @Get('/:id')
    # async getUser(@Param('id') id: string): Promise<UserDto> {
    TS_METHOD_REGEX = re.compile(
        r"^(?:\s*(?:public|private|protected|static|readonly|override)\s+)*(async\s+)?([a-zA-Z0-9_$]+)\s*\(([^)]*)\)(?:\s*:\s*([^;{]+))?\s*\{?",
        re.IGNORECASE
    )

    CLASS_DECL_REGEX = re.compile(
        r"(?:export\s+)?class\s+([a-zA-Z0-9_$]+)",
        re.IGNORECASE
    )

    CONTROL_KEYWORDS = {"if", "for", "while", "switch", "catch", "with", "constructor"}

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

            # Track Decorators (e.g. @Get('/:id'), @Controller('users'), @Post('/create'))
            if stripped.startswith("@"):
                # Clean decorator string
                pending_decorators.append(stripped)
                continue

            # Track Classes
            class_match = self.CLASS_DECL_REGEX.search(stripped)
            if class_match:
                current_class = class_match.group(1)

            # 1. Function Declarations: export async function name(...)
            fn_match = self.TS_FN_DECL_REGEX.search(stripped)
            if fn_match and not stripped.startswith("const ") and not stripped.startswith("let "):
                is_async = bool(fn_match.group(1))
                fn_name = fn_match.group(2) or f"anonymous_fn_L{idx}"
                raw_params = fn_match.group(3) or ""
                ret_type = (fn_match.group(4) or "any").strip()

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
                                return_type=ret_type,
                                decorators=list(pending_decorators),
                                docstring=pending_docstring,
                                called_functions=[],
                                is_async=is_async or ret_type.startswith("Promise<"),
                            )
                        )
                    pending_decorators = []
                    pending_docstring = None
                    continue

            # 2. Arrow Functions: const name = async (...) : ReturnType =>
            arrow_match = self.TS_ARROW_FN_REGEX.search(stripped)
            if arrow_match:
                fn_name = arrow_match.group(1)
                is_async = bool(arrow_match.group(2))
                raw_params = arrow_match.group(3) or arrow_match.group(4) or ""
                ret_type = (arrow_match.group(5) or "any").strip()

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
                            return_type=ret_type,
                            decorators=list(pending_decorators),
                            docstring=pending_docstring,
                            called_functions=[],
                            is_async=is_async or ret_type.startswith("Promise<"),
                        )
                    )
                pending_decorators = []
                pending_docstring = None
                continue

            # 3. Class Methods (NestJS / Angular / TypeScript classes)
            if current_class and "(" in stripped and not stripped.startswith("constructor"):
                method_info = self._extract_method_signature(stripped)
                if method_info:
                    fn_name, raw_params, ret_type, is_async = method_info
                    if fn_name not in self.CONTROL_KEYWORDS and fn_name != "constructor":
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
                                    return_type=ret_type,
                                    decorators=list(pending_decorators),
                                    docstring=pending_docstring,
                                    called_functions=[],
                                    is_async=is_async or ret_type.startswith("Promise<"),
                                )
                            )
                        pending_decorators = []
                        pending_docstring = None

        return functions

    @classmethod
    def _extract_method_signature(cls, line: str) -> Optional[tuple[str, str, str, bool]]:
        open_idx = line.find("(")
        if open_idx == -1:
            return None
        prefix = line[:open_idx].strip()
        tokens = prefix.split()
        if not tokens:
            return None
        fn_name = tokens[-1]
        if not re.match(r"^[a-zA-Z0-9_$]+$", fn_name):
            return None
        is_async = "async" in tokens[:-1]

        # Match balanced closing parenthesis
        depth = 0
        close_idx = -1
        for i in range(open_idx, len(line)):
            if line[i] == "(":
                depth += 1
            elif line[i] == ")":
                depth -= 1
                if depth == 0:
                    close_idx = i
                    break
        if close_idx == -1:
            return None

        raw_params = line[open_idx + 1:close_idx].strip()
        rest = line[close_idx + 1:].strip()
        ret_type = "any"
        if rest.startswith(":"):
            rest_after_colon = rest[1:].strip()
            ret_type = re.split(r"[{;]", rest_after_colon)[0].strip() or "any"

        return fn_name, raw_params, ret_type, is_async

    def _parse_parameters(self, raw_params: str) -> List[Dict[str, Any]]:
        if not raw_params or not raw_params.strip():
            return []
        params = []
        tokens = self._split_comma_balanced(raw_params)
        for tok in tokens:
            tok = tok.strip()
            if not tok:
                continue

            # Strip parameter decorators e.g. @Param('id') id: string, @Body() dto: CreateUserDto
            tok_clean = re.sub(r"@\w+(?:\([^)]*\))?\s*", "", tok).strip()
            default_val = None
            if "=" in tok_clean:
                tok_clean, default_val = tok_clean.split("=", 1)
                tok_clean = tok_clean.strip()
                default_val = default_val.strip()

            type_ann = "any"
            is_optional = False
            if ":" in tok_clean:
                name_part, type_ann = tok_clean.split(":", 1)
                name_part = name_part.strip()
                type_ann = type_ann.strip()
            else:
                name_part = tok_clean.strip()

            if name_part.endswith("?"):
                name_part = name_part[:-1].strip()
                is_optional = True

            params.append({
                "name": name_part,
                "type": type_ann,
                "required": not is_optional and default_val is None,
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
