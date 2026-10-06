from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List


class EnvironmentType(str, Enum):
    LOCAL_SANDBOX = "LOCAL_SANDBOX"
    EXTERNAL = "EXTERNAL"


@dataclass
class TargetEnvironmentConfig:
    base_url: str
    environment_type: EnvironmentType = EnvironmentType.LOCAL_SANDBOX
    health_check_path: str = "/health"
    timeout_seconds: float = 10.0
    allowed_networks: List[str] = field(default_factory=lambda: ["127.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "localhost", "backend", "astra_backend", "postgres", "redis"])
    verify_ssl: bool = False
    custom_headers: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_url": self.base_url,
            "environment_type": self.environment_type.value if isinstance(self.environment_type, Enum) else self.environment_type,
            "health_check_path": self.health_check_path,
            "timeout_seconds": self.timeout_seconds,
            "allowed_networks": self.allowed_networks,
            "verify_ssl": self.verify_ssl,
            "custom_headers": self.custom_headers,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TargetEnvironmentConfig":
        env_type = data.get("environment_type", EnvironmentType.LOCAL_SANDBOX)
        if isinstance(env_type, str):
            env_type = EnvironmentType(env_type)
        return cls(
            base_url=data.get("base_url", "http://localhost:8000"),
            environment_type=env_type,
            health_check_path=data.get("health_check_path", "/health"),
            timeout_seconds=float(data.get("timeout_seconds", 10.0)),
            allowed_networks=data.get("allowed_networks", ["127.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "localhost", "backend", "astra_backend", "postgres", "redis"]),
            verify_ssl=bool(data.get("verify_ssl", False)),
            custom_headers=data.get("custom_headers", {}),
            metadata=data.get("metadata", {})
        )
