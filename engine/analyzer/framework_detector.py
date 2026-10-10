from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from engine.analyzer.models.source_file import SourceFile


@dataclass
class FrameworkDetectionResult:
    language: str
    framework: str
    confidence: float
    evidence: List[str] = field(default_factory=list)


class FrameworkDetector:
    """Polyglot framework detector inspecting manifest dependencies, source imports, and architectural patterns.
    
    Supports Python, Java, C++, and Frontend/Fullstack JavaScript/TypeScript ecosystems.
    """

    def detect(self, repository_path: Path, source_files: List[SourceFile], primary_language: str) -> FrameworkDetectionResult:
        repo_root = Path(repository_path).resolve()

        if primary_language == "Python":
            return self._detect_python(repo_root, source_files)
        elif primary_language == "Java":
            return self._detect_java(repo_root, source_files)
        elif primary_language in ["C++", "C"]:
            return self._detect_cpp(repo_root, source_files)
        elif primary_language in ["JavaScript", "TypeScript"]:
            return self._detect_frontend_and_node(repo_root, source_files, primary_language)
        else:
            return FrameworkDetectionResult(
                language=primary_language,
                framework="OTHER",
                confidence=0.50,
                evidence=["Unrecognized or custom language stack."],
            )

    # --------------------------------------------------------------------------
    # 1. PYTHON ECOSYSTEM
    # --------------------------------------------------------------------------
    def _detect_python(self, repo_root: Path, source_files: List[SourceFile]) -> FrameworkDetectionResult:
        evidence: List[str] = []

        # Read all available Python manifests
        manifest_text = ""
        for fname in ["requirements.txt", "pyproject.toml", "Pipfile", "setup.py", "setup.cfg"]:
            fpath = repo_root / fname
            if fpath.exists():
                manifest_text += fpath.read_text(encoding="utf-8", errors="ignore").lower() + "\n"

        # Scan Python source file imports and code signatures
        imports_set = set()
        for sf in source_files[:200]:  # Cap scanning for responsiveness
            if sf.language != "Python":
                continue
            try:
                content = Path(sf.path).read_text(encoding="utf-8", errors="ignore")
                for line in content.splitlines()[:50]:
                    line_clean = line.strip()
                    if line_clean.startswith("import ") or line_clean.startswith("from "):
                        imports_set.add(line_clean)
            except Exception:
                pass

        all_imports_text = " ".join(imports_set).lower()

        # Check Django
        has_manage_py = (repo_root / "manage.py").exists() or any("manage.py" in str(sf.path) for sf in source_files)
        has_django_dep = "django" in manifest_text
        has_django_import = "django" in all_imports_text or has_manage_py
        if has_django_dep or has_django_import:
            evidence.append("Detected Django framework (manifest dependencies / manage.py / imports).")
            confidence = 0.98 if (has_django_dep and has_django_import) else 0.90
            return FrameworkDetectionResult("Python", "PYTHON_DJANGO", confidence, evidence)

        # Check FastAPI
        has_fastapi_dep = "fastapi" in manifest_text
        has_fastapi_import = "fastapi" in all_imports_text
        if has_fastapi_dep or has_fastapi_import:
            evidence.append("Detected FastAPI framework (dependencies and route decorators).")
            confidence = 0.98 if (has_fastapi_dep and has_fastapi_import) else 0.88
            return FrameworkDetectionResult("Python", "PYTHON_FASTAPI", confidence, evidence)

        # Check Flask
        has_flask_dep = "flask" in manifest_text
        has_flask_import = "flask" in all_imports_text
        if has_flask_dep or has_flask_import:
            evidence.append("Detected Flask framework (dependencies and route decorators).")
            confidence = 0.98 if (has_flask_dep and has_flask_import) else 0.88
            return FrameworkDetectionResult("Python", "PYTHON_FLASK", confidence, evidence)

        # Check Tornado
        if "tornado" in manifest_text or "tornado" in all_imports_text:
            evidence.append("Detected Tornado asynchronous networking framework.")
            return FrameworkDetectionResult("Python", "PYTHON_TORNADO", 0.95, evidence)

        # Check Sanic
        if "sanic" in manifest_text or "sanic" in all_imports_text:
            evidence.append("Detected Sanic async web framework.")
            return FrameworkDetectionResult("Python", "PYTHON_SANIC", 0.95, evidence)

        # Check PySide / PyQt (Desktop GUI)
        qt_signals = ["pyside6", "pyside2", "pyqt6", "pyqt5", "qapplication", "qwidget", "qmainwindow"]
        if any(sig in manifest_text for sig in qt_signals[:4]) or any(sig in all_imports_text for sig in qt_signals):
            evidence.append("Detected PySide / PyQt Desktop GUI framework (Qt bindings).")
            return FrameworkDetectionResult("Python", "PYTHON_PYSIDE_QT", 0.98, evidence)

        # Check Tkinter / CustomTkinter (Desktop GUI)
        if "customtkinter" in manifest_text or "customtkinter" in all_imports_text or "tkinter" in all_imports_text:
            evidence.append("Detected Tkinter / CustomTkinter desktop GUI framework.")
            return FrameworkDetectionResult("Python", "PYTHON_TKINTER", 0.95, evidence)

        # Check Kivy
        if "kivy" in manifest_text or "kivy" in all_imports_text:
            evidence.append("Detected Kivy multi-platform GUI framework.")
            return FrameworkDetectionResult("Python", "PYTHON_KIVY", 0.95, evidence)

        # Check Streamlit
        if "streamlit" in manifest_text or "streamlit" in all_imports_text:
            evidence.append("Detected Streamlit data application framework.")
            return FrameworkDetectionResult("Python", "PYTHON_STREAMLIT", 0.95, evidence)

        # Check Gradio
        if "gradio" in manifest_text or "gradio" in all_imports_text:
            evidence.append("Detected Gradio interactive ML framework.")
            return FrameworkDetectionResult("Python", "PYTHON_GRADIO", 0.95, evidence)

        # Check HuggingFace / Transformers / Datasets
        if any(k in manifest_text for k in ["transformers", "accelerate", "datasets", "diffusers"]):
            evidence.append("Detected HuggingFace AI & NLP toolset.")
            return FrameworkDetectionResult("Python", "PYTHON_ML_HUGGINGFACE", 0.95, evidence)

        # Check PyTorch
        if "torch" in manifest_text or "torch" in all_imports_text:
            evidence.append("Detected PyTorch deep learning framework.")
            return FrameworkDetectionResult("Python", "PYTHON_ML_PYTORCH", 0.95, evidence)

        # Check TensorFlow / Keras
        if "tensorflow" in manifest_text or "keras" in manifest_text or "tensorflow" in all_imports_text:
            evidence.append("Detected TensorFlow / Keras machine learning framework.")
            return FrameworkDetectionResult("Python", "PYTHON_ML_TENSORFLOW", 0.95, evidence)

        # Check Celery
        if "celery" in manifest_text or "celery" in all_imports_text:
            evidence.append("Detected Celery distributed task queue.")
            return FrameworkDetectionResult("Python", "PYTHON_CELERY", 0.92, evidence)

        # Fallback Python
        return FrameworkDetectionResult(
            language="Python",
            framework="PYTHON_GENERIC",
            confidence=0.70,
            evidence=["Generic Python application without specific recognized framework."],
        )

    # --------------------------------------------------------------------------
    # 2. JAVA ECOSYSTEM
    # --------------------------------------------------------------------------
    def _detect_java(self, repo_root: Path, source_files: List[SourceFile]) -> FrameworkDetectionResult:
        evidence: List[str] = []

        manifest_text = ""
        for fname in ["pom.xml", "build.gradle", "build.gradle.kts"]:
            fpath = repo_root / fname
            if fpath.exists():
                manifest_text += fpath.read_text(encoding="utf-8", errors="ignore").lower() + "\n"

        java_sources_text = ""
        for sf in source_files[:50]:
            if sf.language == "Java":
                try:
                    content = Path(sf.path).read_text(encoding="utf-8", errors="ignore")
                    java_sources_text += content[:1500].lower() + "\n"
                except Exception:
                    pass

        # Spring Boot / Spring MVC
        if "spring-boot" in manifest_text or "org.springframework" in manifest_text or "@springbootapplication" in java_sources_text or "@restcontroller" in java_sources_text:
            evidence.append("Detected Spring Boot / Spring MVC framework via Maven/Gradle dependencies and annotations.")
            return FrameworkDetectionResult("Java", "JAVA_SPRING", 0.98, evidence)

        # Quarkus
        if "quarkus" in manifest_text or "io.quarkus" in manifest_text:
            evidence.append("Detected Quarkus supersonic cloud-native framework.")
            return FrameworkDetectionResult("Java", "JAVA_QUARKUS", 0.95, evidence)

        # Micronaut
        if "micronaut" in manifest_text or "io.micronaut" in manifest_text:
            evidence.append("Detected Micronaut modern lightweight framework.")
            return FrameworkDetectionResult("Java", "JAVA_MICRONAUT", 0.95, evidence)

        # Jakarta / JAX-RS / Jersey
        if "jakarta.ws.rs" in java_sources_text or "javax.ws.rs" in java_sources_text or "jersey" in manifest_text:
            evidence.append("Detected Jakarta EE / JAX-RS REST services.")
            return FrameworkDetectionResult("Java", "JAVA_JAKARTA", 0.92, evidence)

        # Play Framework
        if "playframework" in manifest_text or "play.mvc" in java_sources_text:
            evidence.append("Detected Play Framework.")
            return FrameworkDetectionResult("Java", "JAVA_PLAY", 0.92, evidence)

        # Vert.x
        if "vertx" in manifest_text or "io.vertx" in java_sources_text:
            evidence.append("Detected Eclipse Vert.x reactive framework.")
            return FrameworkDetectionResult("Java", "JAVA_VERTX", 0.92, evidence)

        return FrameworkDetectionResult(
            language="Java",
            framework="JAVA_GENERIC",
            confidence=0.75,
            evidence=["Generic Java application (Maven/Gradle structure)."],
        )

    # --------------------------------------------------------------------------
    # 3. C++ ECOSYSTEM
    # --------------------------------------------------------------------------
    def _detect_cpp(self, repo_root: Path, source_files: List[SourceFile]) -> FrameworkDetectionResult:
        evidence: List[str] = []

        manifest_text = ""
        for fname in ["CMakeLists.txt", "conanfile.txt", "conanfile.py", "vcpkg.json", "Makefile"]:
            fpath = repo_root / fname
            if fpath.exists():
                manifest_text += fpath.read_text(encoding="utf-8", errors="ignore").lower() + "\n"

        cpp_sources_text = ""
        for sf in source_files[:50]:
            if sf.language in ["C++", "C", "C++ Header", "C/C++ Header"]:
                try:
                    content = Path(sf.path).read_text(encoding="utf-8", errors="ignore")
                    cpp_sources_text += content[:1500].lower() + "\n"
                except Exception:
                    pass

        # Drogon Web Framework
        if "drogon" in manifest_text or "drogon/drogon.h" in cpp_sources_text or "drogon::httpappframework" in cpp_sources_text:
            evidence.append("Detected Drogon C++ asynchronous HTTP application framework.")
            return FrameworkDetectionResult("C++", "CPP_DROGON", 0.98, evidence)

        # Crow Web Framework
        if "crow" in manifest_text or "crow.h" in cpp_sources_text or "crow::simpleapp" in cpp_sources_text:
            evidence.append("Detected Crow C++ microframework.")
            return FrameworkDetectionResult("C++", "CPP_CROW", 0.98, evidence)

        # Oat++
        if "oatpp" in manifest_text or "oatpp/" in cpp_sources_text:
            evidence.append("Detected Oat++ zero-dependency web framework.")
            return FrameworkDetectionResult("C++", "CPP_OATPP", 0.98, evidence)

        # Pistache
        if "pistache" in manifest_text or "pistache/" in cpp_sources_text:
            evidence.append("Detected Pistache REST framework.")
            return FrameworkDetectionResult("C++", "CPP_PISTACHE", 0.95, evidence)

        # Boost.Beast
        if "boost/beast" in manifest_text or "boost/beast.hpp" in cpp_sources_text:
            evidence.append("Detected Boost.Beast HTTP/WebSocket framework.")
            return FrameworkDetectionResult("C++", "CPP_BOOST_BEAST", 0.95, evidence)

        # gRPC C++
        if "grpc++" in manifest_text or "grpcpp/grpcpp.h" in cpp_sources_text:
            evidence.append("Detected gRPC C++ RPC framework.")
            return FrameworkDetectionResult("C++", "CPP_GRPC", 0.95, evidence)

        # Qt C++ (Desktop GUI)
        if "find_package(qt" in manifest_text or "qapplication" in cpp_sources_text or "qmainwindow" in cpp_sources_text or "qwidget" in cpp_sources_text:
            evidence.append("Detected Qt C++ Desktop Application Framework.")
            return FrameworkDetectionResult("C++", "CPP_QT", 0.98, evidence)

        # wxWidgets
        if "wxwidgets" in manifest_text or "wx/wx.h" in cpp_sources_text:
            evidence.append("Detected wxWidgets cross-platform GUI library.")
            return FrameworkDetectionResult("C++", "CPP_WXWIDGETS", 0.95, evidence)

        # Dear ImGui
        if "imgui.h" in cpp_sources_text:
            evidence.append("Detected Dear ImGui immediate mode graphical library.")
            return FrameworkDetectionResult("C++", "CPP_IMGUI", 0.95, evidence)

        # CMake Native C++
        if (repo_root / "CMakeLists.txt").exists():
            evidence.append("Detected CMake-based native C/C++ project.")
            return FrameworkDetectionResult("C++", "CPP_CMAKE_NATIVE", 0.85, evidence)

        return FrameworkDetectionResult(
            language="C++",
            framework="CPP_GENERIC",
            confidence=0.70,
            evidence=["Generic C/C++ repository."],
        )

    # --------------------------------------------------------------------------
    # 4. FRONTEND & FULLSTACK (JAVASCRIPT / TYPESCRIPT)
    # --------------------------------------------------------------------------
    def _detect_frontend_and_node(self, repo_root: Path, source_files: List[SourceFile], primary_language: str) -> FrameworkDetectionResult:
        evidence: List[str] = []

        pkg_json = repo_root / "package.json"
        pkg_text = ""
        if pkg_json.exists():
            pkg_text = pkg_json.read_text(encoding="utf-8", errors="ignore").lower()

        # Check config files
        has_next_config = any((repo_root / f).exists() for f in ["next.config.js", "next.config.mjs", "next.config.ts"])
        has_nuxt_config = any((repo_root / f).exists() for f in ["nuxt.config.js", "nuxt.config.ts"])
        has_angular_json = (repo_root / "angular.json").exists()
        has_svelte_config = any((repo_root / f).exists() for f in ["svelte.config.js", "svelte.config.ts"])
        has_astro_config = any((repo_root / f).exists() for f in ["astro.config.mjs", "astro.config.ts"])

        # Check file extensions
        has_vue_files = any(sf.language == "Vue" or sf.path.endswith(".vue") for sf in source_files)
        has_svelte_files = any(sf.language == "Svelte" or sf.path.endswith(".svelte") for sf in source_files)
        has_astro_files = any(sf.language == "Astro" or sf.path.endswith(".astro") for sf in source_files)

        # Next.js
        if '"next"' in pkg_text or has_next_config:
            evidence.append("Detected Next.js fullstack React framework (manifest and config).")
            return FrameworkDetectionResult(primary_language, "NEXTJS", 0.98, evidence)

        # Nuxt.js
        if '"nuxt"' in pkg_text or has_nuxt_config:
            evidence.append("Detected Nuxt.js fullstack Vue framework.")
            return FrameworkDetectionResult(primary_language, "NUXT", 0.98, evidence)

        # SvelteKit
        if '"@sveltejs/kit"' in pkg_text:
            evidence.append("Detected SvelteKit fullstack framework.")
            return FrameworkDetectionResult(primary_language, "SVELTEKIT", 0.98, evidence)

        # Svelte
        if '"svelte"' in pkg_text or has_svelte_files or has_svelte_config:
            evidence.append("Detected Svelte reactive UI framework.")
            return FrameworkDetectionResult(primary_language, "SVELTE", 0.95, evidence)

        # Vue.js
        if '"vue"' in pkg_text or has_vue_files:
            evidence.append("Detected Vue.js progressive UI framework.")
            return FrameworkDetectionResult(primary_language, "VUE", 0.95, evidence)

        # Angular
        if '"@angular/core"' in pkg_text or has_angular_json:
            evidence.append("Detected Angular enterprise application framework.")
            return FrameworkDetectionResult(primary_language, "ANGULAR", 0.98, evidence)

        # Astro
        if '"astro"' in pkg_text or has_astro_files or has_astro_config:
            evidence.append("Detected Astro content-driven web framework.")
            return FrameworkDetectionResult(primary_language, "ASTRO", 0.98, evidence)

        # Solid.js
        if '"solid-js"' in pkg_text:
            evidence.append("Detected Solid.js reactive UI framework.")
            return FrameworkDetectionResult(primary_language, "SOLIDJS", 0.95, evidence)

        # React (SPA / library)
        if '"react"' in pkg_text:
            evidence.append("Detected React frontend library / SPA.")
            return FrameworkDetectionResult(primary_language, "REACT", 0.95, evidence)

        # NestJS (Backend)
        if '"@nestjs/core"' in pkg_text:
            evidence.append("Detected NestJS enterprise Node.js microservice framework.")
            return FrameworkDetectionResult(primary_language, "NODE_NESTJS", 0.98, evidence)

        # Express.js (Backend)
        if '"express"' in pkg_text:
            evidence.append("Detected Express.js web framework.")
            return FrameworkDetectionResult(primary_language, "NODE_EXPRESS", 0.95, evidence)

        # Fastify (Backend)
        if '"fastify"' in pkg_text:
            evidence.append("Detected Fastify high-performance Node.js framework.")
            return FrameworkDetectionResult(primary_language, "NODE_FASTIFY", 0.95, evidence)

        # Koa (Backend)
        if '"koa"' in pkg_text:
            evidence.append("Detected Koa middleware framework.")
            return FrameworkDetectionResult(primary_language, "NODE_KOA", 0.95, evidence)

        # Hono (Backend/Edge)
        if '"hono"' in pkg_text:
            evidence.append("Detected Hono ultrafast edge framework.")
            return FrameworkDetectionResult(primary_language, "NODE_HONO", 0.95, evidence)

        # Electron (Desktop)
        if '"electron"' in pkg_text:
            evidence.append("Detected Electron desktop application framework.")
            return FrameworkDetectionResult(primary_language, "ELECTRON", 0.95, evidence)

        # Tauri (Desktop)
        if '"@tauri-apps/api"' in pkg_text or (repo_root / "src-tauri").exists():
            evidence.append("Detected Tauri lightweight desktop framework.")
            return FrameworkDetectionResult(primary_language, "TAURI", 0.98, evidence)

        # React Native (Mobile)
        if '"react-native"' in pkg_text:
            evidence.append("Detected React Native mobile framework.")
            return FrameworkDetectionResult(primary_language, "REACT_NATIVE", 0.95, evidence)

        return FrameworkDetectionResult(
            language=primary_language,
            framework="NODE_GENERIC",
            confidence=0.60,
            evidence=["JavaScript/TypeScript application."],
        )
