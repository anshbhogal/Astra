from typing import List
from engine.analyzer.parsers.base import BaseASTParser
from engine.analyzer.models.function import FunctionInfo


class TypeScriptParser(BaseASTParser):
    """TypeScript AST Parser stub for TS / NestJS applications."""

    def parse_file(self, file_path: str, file_content: str) -> List[FunctionInfo]:
        return []
