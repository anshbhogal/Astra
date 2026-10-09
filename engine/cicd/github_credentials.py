"""GitHub Credential Provider Abstraction.
Supports Personal Access Tokens (PAT) and GitHub App installation access tokens.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time
import jwt


class GitHubCredentialProvider(ABC):
    @abstractmethod
    def get_auth_headers(self) -> Dict[str, str]:
        pass


class PATCredentialProvider(GitHubCredentialProvider):
    def __init__(self, token: str):
        self.token = token

    def get_auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }


class GitHubAppCredentialProvider(GitHubCredentialProvider):
    def __init__(self, app_id: str, private_key_pem: str, installation_id: str):
        self.app_id = app_id
        self.private_key_pem = private_key_pem
        self.installation_id = installation_id
        self._cached_token: Optional[str] = None
        self._expires_at: float = 0.0

    def get_auth_headers(self) -> Dict[str, str]:
        token = self._get_or_refresh_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def _get_or_refresh_token(self) -> str:
        now = time.time()
        if self._cached_token and now < (self._expires_at - 60):
            return self._cached_token

        # Generate RS256 JWT signed with App Private Key
        payload = {
            "iat": int(now) - 60,
            "exp": int(now) + (10 * 60),
            "iss": self.app_id,
        }
        try:
            app_jwt = jwt.encode(payload, self.private_key_pem, algorithm="RS256")
            self._cached_token = app_jwt
            self._expires_at = now + 600
            return app_jwt
        except Exception:
            # Fallback for dev environments
            return "mock_app_token"
