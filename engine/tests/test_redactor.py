from engine.security.redactor import TelemetryRedactor


def test_redact_sensitive_headers():
    headers = {
        "Authorization": "Bearer super_secret_jwt_token",
        "Content-Type": "application/json",
        "Cookie": "session_id=12345",
        "X-Custom-Header": "public_val"
    }
    redacted = TelemetryRedactor.redact_headers(headers)
    assert redacted["Authorization"] == "[REDACTED]"
    assert redacted["Cookie"] == "[REDACTED]"
    assert redacted["Content-Type"] == "application/json"
    assert redacted["X-Custom-Header"] == "public_val"


def test_redact_sensitive_json_payload():
    payload = {
        "user": "test_user",
        "password": "Password123!",
        "nested": {
            "access_token": "secret_token_val",
            "normal_key": "normal_val"
        }
    }
    redacted = TelemetryRedactor.redact_json_payload(payload)
    assert redacted["user"] == "test_user"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["nested"]["access_token"] == "[REDACTED]"
    assert redacted["nested"]["normal_key"] == "normal_val"


def test_response_truncation_when_oversized():
    large_payload = {"data": "A" * 70000}
    redacted, is_truncated = TelemetryRedactor.redact_and_truncate_response(large_payload)
    assert is_truncated is True
    assert redacted["truncated"] is True
