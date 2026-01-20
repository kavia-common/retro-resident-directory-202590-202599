"""
resident_backend_api FastAPI entrypoint.

Provides:
- Health check
- Authentication (token-based) with admin authorization
- Residents CRUD and search/filter endpoints backed by SQLite
- Consistent error handling and OpenAPI documentation metadata

Startup robustness note:
Some preview/runtime environments may execute the backend using system Python and
may not inject environment variables from `.env`. To ensure the service still
binds to the expected port (3001) and is reachable from outside the container,
this module also supports being executed directly:

    python -m src.api.main
    python src/api/main.py

In those modes, we load `.env` if present and start Uvicorn programmatically.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routers import auth as auth_router
from src.api.routers import residents as residents_router
from src.api.storage.db import init_db
from src.api.utils.errors import APIError

openapi_tags = [
    {"name": "Health", "description": "Service health and readiness endpoints."},
    {"name": "Auth", "description": "Authentication endpoints (token issuance and current user)."},
    {"name": "Residents", "description": "Residents directory CRUD and search/filter endpoints."},
]

app = FastAPI(
    title="Resident Directory Backend",
    description=(
        "Backend API for the retro resident directory application.\n\n"
        "Auth model:\n"
        "- Obtain a token via POST /auth/login\n"
        "- Send it using: Authorization: Bearer <token>\n"
        "- Admin-only endpoints require an admin token\n"
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)


@app.on_event("startup")
async def _startup() -> None:
    """Initialize required resources (SQLite schema)."""
    init_db()


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Return consistent JSON errors for expected API errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return consistent JSON errors for unexpected server errors."""
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "Internal server error"}},
    )


def _get_allowed_origins() -> list[str]:
    """
    Compute CORS allowed origins from environment.

    Environment variables:
      - CORS_ALLOW_ORIGINS: comma-separated list of allowed origins.
        Example: "http://localhost:3000,https://myapp.example.com"
      If unset/empty, defaults to ["*"] to simplify local/dev usage.
    """
    raw = (os.getenv("CORS_ALLOW_ORIGINS") or "").strip()
    if not raw:
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"], summary="Health check", operation_id="health_check")
def health_check() -> dict:
    """Health check endpoint used by deployments and monitoring."""
    return {"message": "Healthy"}


@app.get("/docs/auth", tags=["Auth"], summary="Authentication usage help", operation_id="auth_usage_help")
def auth_usage_help() -> dict:
    """Provide instructions on how to authenticate against this API."""
    return {
        "how_to_authenticate": [
            "POST /auth/login with JSON body {username, password}",
            "Use returned token in requests as: Authorization: Bearer <token>",
            "Admin-only routes require a token from an admin account",
        ]
    }


# Keep existing routes (e.g., /auth/*, /residents/*) for backward compatibility.
app.include_router(auth_router.router)
app.include_router(residents_router.router)

# Also expose canonical API routes under /api to match the frontend implementation.
# This prevents 404s when the frontend is configured to call `/api/...`.
app.include_router(auth_router.router, prefix="/api")
app.include_router(residents_router.router, prefix="/api")


def _env_int(name: str, default: int) -> int:
    """Parse an int env var with a default fallback."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_str(name: str, default: str) -> str:
    """Parse a string env var with a default fallback."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw


if __name__ == "__main__":
    # When the platform uses "python src/api/main.py" as the entrypoint, Uvicorn
    # is never started unless we do it explicitly. Additionally, env vars may not
    # be injected; load `.env` if present.
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except Exception:
        # If python-dotenv isn't available for some reason, proceed without it.
        pass

    import uvicorn

    host = _env_str("UVICORN_HOST", _env_str("HOST", "0.0.0.0"))
    port = _env_int("PORT", 3001)

    # Use an import string so Uvicorn can resolve the ASGI app in a consistent way.
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        workers=_env_int("UVICORN_WORKERS", 1),
        proxy_headers=_env_str("TRUST_PROXY", "false").lower() in {"1", "true", "yes"},
    )
