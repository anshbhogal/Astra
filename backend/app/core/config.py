from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    PROJECT_NAME: str = "ASTRA"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    API_V1_STR: str = "/api/v1"

    # Database (Docker container service: postgres)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://astra_user:astra_secret_password@postgres:5432/astra_db"
    )

    # Redis & Celery (Docker container service: redis)
    REDIS_URL: str = Field(default="redis://redis:6379/0")
    CELERY_BROKER_URL: str = Field(default="redis://redis:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default="redis://redis:6379/1")

    # Security & JWT
    JWT_SECRET: str = Field(
        default="super_secure_astra_jwt_secret_key_change_in_production_2026"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Strict 15-minute access token TTL
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7     # 7-day refresh token TTL
    REFRESH_TOKEN_COOKIE_NAME: str = "astra_refresh_token"

    @field_validator("JWT_SECRET")
    def validate_jwt_secret(cls, v: str) -> str:
        if not v or len(v.strip()) < 32:
            raise ValueError(
                "JWT_SECRET must be at least 32 characters in length for cryptographic security."
            )
        insecure_keys = {
            "secret",
            "password",
            "changeme",
            "12345678901234567890123456789012",
            "super_secret_jwt_key_here_please_change"
        }
        if v.strip().lower() in insecure_keys:
            raise ValueError("JWT_SECRET cannot use a known insecure default value.")
        return v

    GITHUB_WEBHOOK_SECRET: str = Field(
        default="astra_secure_webhook_key_64chars_dev_environment_2026",
        description="GitHub Webhook HMAC SHA-256 secret key."
    )

    @field_validator("GITHUB_WEBHOOK_SECRET")
    def validate_webhook_secret(cls, v: str) -> str:
        if not v or v.strip() == "astra_webhook_secret_key_2026":
            raise ValueError(
                "GITHUB_WEBHOOK_SECRET must be configured and cannot use the insecure default 'astra_webhook_secret_key_2026'."
            )
        return v

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("["):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",")]
        return v

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


settings = Settings()
