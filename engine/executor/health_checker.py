import httpx
from typing import Tuple
from engine.models.target_env import TargetEnvironmentConfig
from engine.security.ssrf_protector import SSRFProtector, SSRFValidationError


class HealthChecker:
    """Pre-flight liveness probe checking target application availability before executing test suite."""

    @classmethod
    async def check_health(cls, config: TargetEnvironmentConfig) -> Tuple[bool, str]:
        health_url = f"{config.base_url.rstrip('/')}{config.health_check_path}"

        # SSRF Security Validation
        try:
            SSRFProtector.validate_url(health_url, config)
        except SSRFValidationError as err:
            return False, f"SSRF Security Violation: {err}"

        async with httpx.AsyncClient(verify=config.verify_ssl) as client:
            try:
                res = await client.get(
                    health_url,
                    headers=config.custom_headers,
                    timeout=config.timeout_seconds
                )
                if res.status_code in [200, 201, 204, 301, 302, 404]:
                    return True, f"Target environment healthy (HTTP {res.status_code})."
                else:
                    return False, f"Target health probe returned HTTP {res.status_code}."
            except httpx.RequestError as exc:
                return False, f"Target environment unreachable at {health_url}: {str(exc)}"
