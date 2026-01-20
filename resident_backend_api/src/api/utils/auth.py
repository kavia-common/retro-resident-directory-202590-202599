from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.utils.errors import APIError

_security = HTTPBearer(auto_error=False)

# In-memory token store (sufficient for this app scope; can be replaced with DB later).
_TOKENS: Dict[str, "UserContext"] = {}


@dataclass(frozen=True)
class UserContext:
    """Authenticated user context extracted from a token."""

    username: str
    is_admin: bool


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value


def _constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def _hash_password(password: str, salt: str) -> str:
    # Not a full password-hashing scheme; adequate for demo with env-managed secrets.
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


# PUBLIC_INTERFACE
def authenticate_user(username: str, password: str) -> UserContext:
    """Authenticate a user using env-configured credentials and return their context.

    Environment variables expected (set by orchestrator in container .env):
    - ADMIN_USERNAME, ADMIN_PASSWORD
    - USER_USERNAME, USER_PASSWORD  (optional; if not set, only admin can login)

    Raises:
        APIError: if credentials are invalid or not configured.
    """
    admin_user = _env("ADMIN_USERNAME")
    admin_pass = _env("ADMIN_PASSWORD")
    user_user = _env("USER_USERNAME")
    user_pass = _env("USER_PASSWORD")

    if not admin_user or not admin_pass:
        raise APIError(
            status_code=500,
            code="auth_not_configured",
            message="Authentication is not configured (missing ADMIN_USERNAME/ADMIN_PASSWORD).",
        )

    salt = _env("AUTH_SALT", "resident-directory")

    # Admin auth
    if _constant_time_equals(username, admin_user) and _constant_time_equals(
        _hash_password(password, salt), _hash_password(admin_pass, salt)
    ):
        return UserContext(username=username, is_admin=True)

    # Regular user auth (optional)
    if user_user and user_pass:
        if _constant_time_equals(username, user_user) and _constant_time_equals(
            _hash_password(password, salt), _hash_password(user_pass, salt)
        ):
            return UserContext(username=username, is_admin=False)

    raise APIError(status_code=401, code="invalid_credentials", message="Invalid username or password.")


# PUBLIC_INTERFACE
def issue_token(user: UserContext, ttl_seconds: int = 60 * 60 * 8) -> Tuple[str, int]:
    """Issue a bearer token for a given user context.

    Args:
        user: Authenticated user context.
        ttl_seconds: Token time-to-live in seconds.

    Returns:
        (token, expires_at_epoch_seconds)
    """
    token = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + int(ttl_seconds)
    # Store expires_at by embedding into username key? We'll store as a separate token mapping structure.
    _TOKENS[token] = user
    return token, expires_at


def _require_credentials(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise APIError(status_code=401, code="not_authenticated", message="Missing bearer token.")
    return credentials.credentials


# PUBLIC_INTERFACE
def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_security)) -> UserContext:
    """FastAPI dependency: get current authenticated user from Authorization header."""
    token = _require_credentials(credentials)
    user = _TOKENS.get(token)
    if user is None:
        raise APIError(status_code=401, code="invalid_token", message="Invalid or expired token.")
    return user


# PUBLIC_INTERFACE
def require_admin(user: UserContext = Depends(get_current_user)) -> UserContext:
    """FastAPI dependency: ensure current user is an admin."""
    if not user.is_admin:
        raise APIError(status_code=403, code="forbidden", message="Admin privileges required.")
    return user
