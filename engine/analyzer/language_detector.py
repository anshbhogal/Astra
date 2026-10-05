from collections import Counter
from typing import List, Tuple
from engine.analyzer.models.source_file import SourceFile


class LanguageDetector:
    """Detects primary programming language based on discovered source file distribution."""

    def detect_primary_language(self, source_files: List[SourceFile]) -> Tuple[str, float]:
        if not source_files:
            return "UNKNOWN", 0.0

        counts = Counter(sf.language for sf in source_files)
        total_files = len(source_files)
        primary_lang, count = counts.most_common(1)[0]
        confidence = round(count / total_files, 2)

        return primary_lang, confidence
