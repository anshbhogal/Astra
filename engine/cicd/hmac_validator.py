"""HMAC-SHA256 Webhook Payload Validator.
Validates HMAC-SHA256 signatures on raw HTTP body bytes before JSON decoding.
Uses constant-time comparison to protect against timing side-channel attacks.
"""

import hmac
import hashlib
from typing import Optional


class HMACValidator:
    """Validates raw request body bytes against secret signatures."""

    @staticmethod
    def verify_github_signature(raw_body: bytes, signature_header: Optional[str], secret: str) -> bool:
        """Validates X-Hub-Signature-256 header (format: sha256=<hex_digest>)."""
        if not signature_header or not secret:
            return False

        if not signature_header.startswith("sha256="):
            return False

        expected_signature = signature_header[7:].strip()
        if not expected_signature:
            return False

        try:
            mac = hmac.new(secret.encode("utf-8"), msg=raw_body, digestmod=hashlib.sha256)
            calculated_signature = mac.hexdigest()
            return hmac.compare_digest(calculated_signature.lower(), expected_signature.lower())
        except Exception:
            return False
