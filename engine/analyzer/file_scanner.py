import os
from pathlib import Path
from typing import List
from engine.analyzer.models.source_file import SourceFile

DEFAULT_IGNORE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    "coverage",
    ".idea",
    ".vscode",
}

EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
}


class FileScanner:
    """Safe source file crawler filtering out build artifacts and large files."""

    def __init__(
        self,
        max_files: int = 10000,
        max_file_size_mb: int = 5,
        ignore_dirs: set = None
    ):
        self.max_files = max_files
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.ignore_dirs = ignore_dirs or DEFAULT_IGNORE_DIRS

    def scan(self, repository_path: Path) -> List[SourceFile]:
        root_path = Path(repository_path).resolve()
        discovered_files: List[SourceFile] = []

        for current_root, dirs, files in os.walk(root_path):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs and not d.startswith(".")]

            for filename in files:
                if len(discovered_files) >= self.max_files:
                    break

                file_path = Path(current_root) / filename
                ext = file_path.suffix.lower()

                if ext not in EXTENSION_LANGUAGE_MAP:
                    continue

                try:
                    stat = file_path.stat()
                except OSError:
                    continue

                if stat.st_size > self.max_file_size_bytes:
                    continue

                line_count = 0
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        line_count = sum(1 for _ in f)
                except Exception:
                    line_count = 0

                relative_path = str(file_path.relative_to(root_path)).replace("\\", "/")
                language = EXTENSION_LANGUAGE_MAP[ext]

                discovered_files.append(
                    SourceFile(
                        path=str(file_path),
                        relative_path=relative_path,
                        language=language,
                        size_bytes=stat.st_size,
                        line_count=line_count,
                    )
                )

        return discovered_files
