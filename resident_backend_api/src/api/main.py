"""
resident_backend_api FastAPI entrypoint.

Provides:
- Health check
- Authentication (token-based) with admin authorization
- Residents CRUD and search/filter endpoints backed by SQLite
- Consistent error handling and OpenAPI documentation metadata
"""

from __future__ import annotations

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


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Frontend URL may vary in hosted environments.
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


app.include_router(auth_router.router)
app.include_router(residents_router.router)
