from abc import ABC, abstractmethod
from typing import List, Dict, Any
from engine.analyzer.models.function import FunctionInfo


class BaseASTParser(ABC):
    """Abstract Base Class for language-specific AST parsers."""

    @abstractmethod
    def parse_file(self, file_path: str, file_content: str) -> List[FunctionInfo]:
        """Parse source file content and return discovered functions and route metadata."""
        pass
