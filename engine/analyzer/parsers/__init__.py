from typing import Dict
from engine.analyzer.parsers.base import BaseASTParser
from engine.analyzer.parsers.python_ast import PythonASTParser
from engine.analyzer.parsers.javascript import JavaScriptParser
from engine.analyzer.parsers.typescript import TypeScriptParser


class ParserRegistry:
    """Registry mapping programming languages to their AST parser implementations."""

    def __init__(self):
        self._parsers: Dict[str, BaseASTParser] = {
            "Python": PythonASTParser(),
            "JavaScript": JavaScriptParser(),
            "TypeScript": TypeScriptParser(),
        }

    def get_parser(self, language: str) -> BaseASTParser:
        return self._parsers.get(language, PythonASTParser())


__all__ = ["BaseASTParser", "PythonASTParser", "JavaScriptParser", "TypeScriptParser", "ParserRegistry"]
