from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple
from engine.analyzer.models.source_file import SourceFile


@dataclass
class FrameworkDetectionResult:
    language: str
    framework: str  # FASTAPI, FLASK, EXPRESS, NESTJS, SPRING_BOOT, OTHER
    confidence: float
    evidence: List[str] = field(default_factory=list)


class FrameworkDetector:
    """Detects target application framework using manifest dependencies and source import signals."""

    def detect(self, repository_path: Path, source_files: List[SourceFile], primary_language: str) -> FrameworkDetectionResult:
        repo_root = Path(repository_path).resolve()
        evidence: List[str] = []

        if primary_language == "Python":
            # 1. Check requirements.txt / pyproject.toml
            req_file = repo_root / "requirements.txt"
            pyproject_file = repo_root / "pyproject.toml"
            manifest_text = ""

            if req_file.exists():
                manifest_text += req_file.read_text(encoding="utf-8", errors="ignore").lower()
            if pyproject_file.exists():
                manifest_text += pyproject_file.read_text(encoding="utf-8", errors="ignore").lower()

            has_fastapi_dep = "fastapi" in manifest_text
            has_flask_dep = "flask" in manifest_text

            if has_fastapi_dep:
                evidence.append("Found 'fastapi' dependency in manifest.")
            if has_flask_dep:
                evidence.append("Found 'flask' dependency in manifest.")

            # 2. Check source file import signals
            fastapi_import_count = 0
            flask_import_count = 0

            for sf in source_files:
                if sf.language != "Python":
                    continue
                try:
                    content = Path(sf.path).read_text(encoding="utf-8", errors="ignore")
                    if "import fastapi" in content or "from fastapi" in content:
                        fastapi_import_count += 1
                    if "import flask" in content or "from flask" in content:
                        flask_import_count += 1
                except Exception:
                    pass

            if fastapi_import_count > 0:
                evidence.append(f"Found FastAPI import statements in {fastapi_import_count} file(s).")
            if flask_import_count > 0:
                evidence.append(f"Found Flask import statements in {flask_import_count} file(s).")

            if has_fastapi_dep or fastapi_import_count > 0:
                confidence = 0.98 if (has_fastapi_dep and fastapi_import_count > 0) else 0.85
                return FrameworkDetectionResult(
                    language="Python",
                    framework="PYTHON_FASTAPI",
                    confidence=confidence,
                    evidence=evidence,
                )

            if has_flask_dep or flask_import_count > 0:
                confidence = 0.98 if (has_flask_dep and flask_import_count > 0) else 0.85
                return FrameworkDetectionResult(
                    language="Python",
                    framework="PYTHON_FLASK",
                    confidence=confidence,
                    evidence=evidence,
                )

            return FrameworkDetectionResult(
                language="Python",
                framework="OTHER",
                confidence=0.60,
                evidence=["Generic Python application without recognized framework manifests."],
            )

        elif primary_language in ["JavaScript", "TypeScript"]:
            pkg_json = repo_root / "package.json"
            pkg_text = ""
            if pkg_json.exists():
                pkg_text = pkg_json.read_text(encoding="utf-8", errors="ignore").lower()

            if "express" in pkg_text:
                evidence.append("Found 'express' dependency in package.json.")
                return FrameworkDetectionResult(
                    language=primary_language,
                    framework="NODE_EXPRESS",
                    confidence=0.95,
                    evidence=evidence,
                )
            if "@nestjs/core" in pkg_text:
                evidence.append("Found '@nestjs/core' dependency in package.json.")
                return FrameworkDetectionResult(
                    language=primary_language,
                    framework="NODE_EXPRESS",
                    confidence=0.95,
                    evidence=evidence,
                )

            return FrameworkDetectionResult(
                language=primary_language,
                framework="OTHER",
                confidence=0.50,
                evidence=["JavaScript/TypeScript application."],
            )

        elif primary_language == "Java":
            return FrameworkDetectionResult(
                language="Java",
                framework="JAVA_SPRING",
                confidence=0.80,
                evidence=["Java repository detected."],
            )

        return FrameworkDetectionResult(
            language=primary_language,
            framework="OTHER",
            confidence=0.50,
            evidence=["Unrecognized framework."],
        )
