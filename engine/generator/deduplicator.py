"""
PayloadDeduplicator: Multi-part SHA256 Request Payload Fingerprinting & Deduplication.
"""

import hashlib
import json
from typing import Dict, Any, Tuple
from engine.models.test_spec import TestSpecification


class PayloadDeduplicator:
    """Computes deterministic SHA256 fingerprints to eliminate duplicate generated test cases."""

    @classmethod
    def compute_fingerprint(
        cls,
        method: str,
        path: str,
        query_params: Dict[str, Any],
        headers: Dict[str, str],
        body: Any,
        auth_omitted: bool,
        test_type: str
    ) -> str:
        """
        Computes SHA256 fingerprint over HTTP Method, Normalized Path, Query, Headers, Body, Auth, TestType.
        """
        raw_components = {
            "method": method.upper().strip(),
            "path": path.strip().rstrip("/"),
            "query_params": json.dumps(query_params, sort_keys=True) if query_params else "",
            "headers": json.dumps({k.lower(): v for k, v in headers.items()}, sort_keys=True) if headers else "",
            "body": json.dumps(body, sort_keys=True) if body else "",
            "auth_omitted": auth_omitted,
            "test_type": test_type
        }
        serialized = json.dumps(raw_components, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def deduplicate_specifications(
        cls, specs: list[TestSpecification]
    ) -> Tuple[list[TestSpecification], int]:
        """
        Deduplicates a list of TestSpecifications.
        Returns (deduplicated_specs, deduplicated_count).
        """
        seen_fingerprints = set()
        deduped: list[TestSpecification] = []
        deduped_count = 0

        for spec in specs:
            fp = cls.compute_fingerprint(
                method=spec.method,
                path=spec.path,
                query_params=spec.query_params,
                headers=spec.headers,
                body=spec.body,
                auth_omitted=spec.auth_ref is None,
                test_type=spec.test_type.value if hasattr(spec.test_type, "value") else str(spec.test_type)
            )

            if fp in seen_fingerprints:
                deduped_count += 1
                continue

            seen_fingerprints.add(fp)
            spec.metadata["fingerprint"] = fp
            deduped.append(spec)

        return deduped, deduped_count
