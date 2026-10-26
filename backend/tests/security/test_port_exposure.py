"""
Security tests for P3-1: Verify that database (PostgreSQL 5432) and cache (Redis 6379)
ports are strictly restricted to 127.0.0.1 loopback interfaces.
"""

import os
import yaml
import pytest


def test_docker_compose_restricts_sensitive_ports():
    """Verify that docker-compose.yml binds postgres and redis ports to 127.0.0.1 only."""
    candidates = [
        "/app/docker-compose.yml",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../docker-compose.yml")),
        "docker-compose.yml",
        "/workspace/docker-compose.yml",
    ]
    compose_path = next((p for p in candidates if os.path.exists(p)), None)
    assert compose_path is not None, f"docker-compose.yml not found among {candidates}"

    with open(compose_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    services = config.get("services", {})
    assert "postgres" in services, "postgres service missing from compose"
    assert "redis" in services, "redis service missing from compose"

    postgres_ports = services["postgres"].get("ports", [])
    for p in postgres_ports:
        port_str = str(p)
        assert port_str.startswith("127.0.0.1:"), (
            f"Postgres port '{port_str}' must be bound to 127.0.0.1 to prevent public host exposure."
        )

    redis_ports = services["redis"].get("ports", [])
    for p in redis_ports:
        port_str = str(p)
        assert port_str.startswith("127.0.0.1:"), (
            f"Redis port '{port_str}' must be bound to 127.0.0.1 to prevent unauthenticated public cache access."
        )
