"""Main service module for Project Sandbox 56205a"""

def add(a: int, b: int) -> int:
    """Calculates sum of two numbers."""
    return a + b

def authenticate(user_token: str) -> bool:
    """Authenticates API request token."""
    if not user_token:
        return False
    return len(user_token) >= 10
