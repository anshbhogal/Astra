from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any
from engine.analyzer.models.function import FunctionInfo


class BaseASTParser(ABC):
    """Abstract Base Class for language-specific AST parsers."""

    def parse(self, source_file: Any) -> List[FunctionInfo]:
        """Convenience method accepting a SourceFile model."""
        try:
            file_path = getattr(source_file, "path", str(source_file))
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            return self.parse_file(file_path, content)
        except Exception:
            return []

    @abstractmethod
    def parse_file(self, file_path: str, file_content: str) -> List[FunctionInfo]:
        """Parse source file content and return discovered functions and route metadata."""
        pass
