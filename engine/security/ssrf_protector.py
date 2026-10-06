import ipaddress
import socket
from urllib.parse import urlparse
from typing import List, Tuple
from engine.models.target_env import TargetEnvironmentConfig, EnvironmentType


class SSRFValidationError(ValueError):
    """Raised when a target URL fails SSRF security validation."""
    pass


class SSRFProtector:
    """Protects against Server-Side Request Forgery (SSRF) attacks."""

    BLOCKED_NETWORKS = [
        ipaddress.ip_network("127.0.0.0/8"),      # Loopback
        ipaddress.ip_network("10.0.0.0/8"),       # Private IPv4 Class A
        ipaddress.ip_network("172.16.0.0/12"),    # Private IPv4 Class B
        ipaddress.ip_network("192.168.0.0/16"),   # Private IPv4 Class C
        ipaddress.ip_network("169.254.0.0/16"),   # Link-local / Cloud Metadata (AWS IMDS)
        ipaddress.ip_network("0.0.0.0/8"),        # Broadcast / Unspecified
        ipaddress.ip_network("::1/128"),          # IPv6 Loopback
        ipaddress.ip_network("fc00::/7"),         # IPv6 Private
        ipaddress.ip_network("fe80::/10"),        # IPv6 Link-local
    ]

    @classmethod
    def validate_url(cls, url: str, config: TargetEnvironmentConfig) -> Tuple[bool, str]:
        """
        Validates target URL against scheme and IP blocklists.
        Returns (is_valid, resolved_host_or_error_message).
        """
        if not url or not isinstance(url, str):
            raise SSRFValidationError("Target URL must be a non-empty string.")

        parsed = urlparse(url.strip())
        if parsed.scheme.lower() not in ["http", "https"]:
            raise SSRFValidationError(f"Disallowed URL scheme '{parsed.scheme}'. Only http and https are permitted.")

        hostname = parsed.hostname
        if not hostname:
            raise SSRFValidationError("Invalid target URL format: missing hostname.")

        # In LOCAL_SANDBOX mode, allow hostnames explicitly configured (e.g. localhost, backend, docker service names)
        if config.environment_type == EnvironmentType.LOCAL_SANDBOX:
            allowed_hosts = [h.lower() for h in config.allowed_networks]
            if hostname.lower() in allowed_hosts or any(hostname.lower().startswith(h) for h in ["localhost", "127.0.0.1", "backend", "astra"]):
                return True, hostname

        # Resolve IP addresses for hostname
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            ip_addresses = list(set([item[4][0] for item in addr_info]))
        except socket.gaierror as err:
            raise SSRFValidationError(f"Could not resolve IP address for hostname '{hostname}': {err}")

        for ip_str in ip_addresses:
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                for blocked in cls.BLOCKED_NETWORKS:
                    if ip_obj in blocked:
                        if config.environment_type != EnvironmentType.LOCAL_SANDBOX:
                            raise SSRFValidationError(f"Access to blocked internal/private IP address '{ip_str}' is forbidden for external targets.")
            except ValueError:
                continue

        return True, hostname
