import pytest
import hmac
import hashlib
from engine.cicd.hmac_validator import HMACValidator


def test_hmac_validator_valid_and_invalid():
    secret = "my_super_secret_webhook_key_2026"
    body = b'{"action": "opened", "number": 42}'

    # Compute valid signature
    mac = hmac.new(secret.encode("utf-8"), msg=body, digestmod=hashlib.sha256)
    valid_header = f"sha256={mac.hexdigest()}"

    assert HMACValidator.verify_github_signature(body, valid_header, secret) is True

    # Invalid secret
    assert HMACValidator.verify_github_signature(body, valid_header, "wrong_secret") is False

    # Tampered body
    tampered_body = b'{"action": "opened", "number": 43}'
    assert HMACValidator.verify_github_signature(tampered_body, valid_header, secret) is False

    # Missing header
    assert HMACValidator.verify_github_signature(body, None, secret) is False
