"""Dynamic Value Text Normalizer for Stack Traces & Error Messages."""

import re


class FailureTextNormalizer:
    """
    Normalizes error strings by replacing dynamic values (UUIDs, timestamps, IP addresses, ports, file line numbers)
    with generic placeholder tokens before TF-IDF vectorization.
    """

    UUID_REGEX = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
    HEX_REGEX = re.compile(r"0x[0-9a-fA-F]+")
    TIMESTAMP_REGEX = re.compile(r"\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?")
    IPV4_REGEX = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?\b")
    PORT_REGEX = re.compile(r"port\s+\d+", re.IGNORECASE)
    DIGIT_ID_REGEX = re.compile(r"\b\d{4,}\b")

    @classmethod
    def normalize_text(cls, text: str) -> str:
        if not text:
            return ""

        cleaned = str(text)
        cleaned = cls.UUID_REGEX.sub("<UUID>", cleaned)
        cleaned = cls.HEX_REGEX.sub("<HEX>", cleaned)
        cleaned = cls.TIMESTAMP_REGEX.sub("<TIMESTAMP>", cleaned)
        cleaned = cls.IPV4_REGEX.sub("<IP>", cleaned)
        cleaned = cls.PORT_REGEX.sub("port <PORT>", cleaned)
        cleaned = cls.DIGIT_ID_REGEX.sub("<ID>", cleaned)

        # Normalize multiple whitespaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
