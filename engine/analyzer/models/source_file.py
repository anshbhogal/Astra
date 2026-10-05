from dataclasses import dataclass


@dataclass
class SourceFile:
    path: str
    relative_path: str
    language: str
    size_bytes: int
    line_count: int
