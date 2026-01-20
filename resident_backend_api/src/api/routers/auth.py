from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.models import CurrentUserResponse, LoginRequest, LoginResponse
from src.api.utils.auth import authenticate_user, get_current_user, issue_token, UserContext

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login and receive a bearer token",
    operation_id="auth_login",
)
def login(payload: LoginRequest) -> LoginResponse:
    """Authenticate using username/password and return a bearer token."""
    user = authenticate_user(payload.username, payload.password)
    token, expires_at = issue_token(user)
    return LoginResponse(token=token, expires_at=expires_at, username=user.username, is_admin=user.is_admin)


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Get current authenticated user",
    operation_id="auth_me",
)
def me(user: UserContext = Depends(get_current_user)) -> CurrentUserResponse:
    """Return the currently authenticated user context."""
    return CurrentUserResponse(username=user.username, is_admin=user.is_admin)
