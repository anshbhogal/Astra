import json
from typing import Dict, Any, Tuple, Optional


class TelemetryRedactor:
    """Redacts sensitive credentials, secrets, tokens, and PII before DB telemetry persistence."""

    SENSITIVE_HEADERS = {
        "authorization", "cookie", "set-cookie", "x-api-key", "api-key",
        "proxy-authorization", "secret", "x-secret-key"
    }

    SENSITIVE_FIELD_KEYWORDS = {
        "password", "pass", "hashed_password", "secret", "access_token",
        "refresh_token", "auth_token", "token", "api_key", "private_key",
        "client_secret", "ssn"
    }

    MAX_RESPONSE_BYTES = 65536  # 64 KB limit

    @classmethod
    def redact_headers(cls, headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        if not headers or not isinstance(headers, dict):
            return {}

        redacted = {}
        for key, val in headers.items():
            if key.lower() in cls.SENSITIVE_HEADERS or any(k in key.lower() for k in ["auth", "token", "key"]):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = str(val)
        return redacted

    @classmethod
    def redact_json_payload(cls, data: Any) -> Any:
        if isinstance(data, dict):
            redacted_dict = {}
            for k, v in data.items():
                if k.lower() in cls.SENSITIVE_FIELD_KEYWORDS or any(kw in k.lower() for kw in ["password", "secret", "access_token", "refresh_token", "auth_token"]):
                    redacted_dict[k] = "[REDACTED]"
                else:
                    redacted_dict[k] = cls.redact_json_payload(v)
            return redacted_dict
        elif isinstance(data, list):
            return [cls.redact_json_payload(item) for item in data]
        else:
            return data

    @classmethod
    def redact_and_truncate_response(cls, response_data: Any) -> Tuple[Any, bool]:
        """
        Redacts response body payload and truncates if payload exceeds MAX_RESPONSE_BYTES.
        Returns (sanitized_response_data, is_truncated).
        """
        if response_data is None:
            return None, False

        redacted_data = cls.redact_json_payload(response_data)

        try:
            raw_str = json.dumps(redacted_data)
            if len(raw_str.encode("utf-8")) > cls.MAX_RESPONSE_BYTES:
                truncated_dict = {
                    "truncated": True,
                    "message": f"Response payload size exceeded max limit of {cls.MAX_RESPONSE_BYTES} bytes.",
                    "sample": str(redacted_data)[:1000] + "..."
                }
                return truncated_dict, True
        except Exception:
            pass

        return redacted_data, False
