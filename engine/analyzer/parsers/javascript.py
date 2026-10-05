from typing import List
from engine.analyzer.parsers.base import BaseASTParser
from engine.analyzer.models.function import FunctionInfo


class JavaScriptParser(BaseASTParser):
    """JavaScript AST Parser stub for Node.js / Express applications."""

    def parse_file(self, file_path: str, file_content: str) -> List[FunctionInfo]:
        # Basic regex / AST fallback for JavaScript files
        return []
