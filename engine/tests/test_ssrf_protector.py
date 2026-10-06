import pytest
from engine.security.ssrf_protector import SSRFProtector, SSRFValidationError
from engine.models.target_env import TargetEnvironmentConfig, EnvironmentType


def test_ssrf_protector_valid_public_url():
    config = TargetEnvironmentConfig(base_url="https://api.github.com", environment_type=EnvironmentType.EXTERNAL)
    is_valid, host = SSRFProtector.validate_url("https://api.github.com/users", config)
    assert is_valid is True
    assert host == "api.github.com"


def test_ssrf_protector_blocks_invalid_scheme():
    config = TargetEnvironmentConfig(base_url="ftp://example.com", environment_type=EnvironmentType.EXTERNAL)
    with pytest.raises(SSRFValidationError, match="Disallowed URL scheme"):
        SSRFProtector.validate_url("ftp://example.com/file", config)


def test_ssrf_protector_local_sandbox_allows_localhost():
    config = TargetEnvironmentConfig(base_url="http://localhost:8000", environment_type=EnvironmentType.LOCAL_SANDBOX)
    is_valid, host = SSRFProtector.validate_url("http://localhost:8000/health", config)
    assert is_valid is True
    assert host == "localhost"


def test_ssrf_protector_external_blocks_loopback():
    config = TargetEnvironmentConfig(base_url="http://127.0.0.1:8000", environment_type=EnvironmentType.EXTERNAL)
    with pytest.raises(SSRFValidationError, match="blocked internal/private IP address"):
        SSRFProtector.validate_url("http://127.0.0.1:8000/health", config)
