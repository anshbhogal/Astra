"""Base benchmark environment management and shared infrastructure."""

import logging
from typing import Dict, Optional, Set
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class BenchmarkEnvironment:
    """Manages active defect toggles and clean reset contracts across all benchmark services."""

    _active_bugs: Set[str] = set()
    _seed_value: int = 42

    @classmethod
    def enable_all_bugs(cls) -> None:
        from benchmark_apps.catalog import BenchmarkBugCatalog
        cls._active_bugs = set(BenchmarkBugCatalog.BUGS.keys())

    @classmethod
    def disable_all_bugs(cls) -> None:
        cls._active_bugs = set()

    @classmethod
    def set_active_bugs(cls, bug_ids: Set[str]) -> None:
        cls._active_bugs = set(bug_ids)

    @classmethod
    def is_bug_active(cls, bug_id: str) -> bool:
        # Default is active if not explicitly cleared
        if not cls._active_bugs and bug_id.startswith("BUG-"):
            return True
        return bug_id in cls._active_bugs

    @classmethod
    def get_seed(cls) -> int:
        return cls._seed_value

    @classmethod
    def seed(cls, seed: int = 42) -> None:
        cls._seed_value = seed

    @classmethod
    def reset(cls) -> None:
        cls.enable_all_bugs()
        cls._seed_value = 42


# Auto-initialize all bugs as active by default
BenchmarkEnvironment.enable_all_bugs()


def create_benchmark_app(title: str, version: str = "1.0.0") -> FastAPI:
    """Creates a standard FastAPI application configured for benchmark testing."""
    app = FastAPI(title=title, version=version)

    @app.get("/health")
    async def base_health():
        return {"status": "HEALTHY", "service": title, "version": version}

    return app
