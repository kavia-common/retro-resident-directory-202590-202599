"""
resident_backend_api robust preview entrypoint.

Why this file exists:
- Some preview/orchestration environments start the backend with system Python
  (e.g. /usr/bin/python) and do NOT activate the container venv.
- Some environments do not inject .env into the process environment.
- Some runners invoke a "main.py" at the project root by convention and may pass
  extra argv flags that our module-level __main__ handlers shouldn't choke on.

This script is designed to be extremely forgiving:
- It injects the local venv's site-packages onto sys.path (if present)
- It loads .env from the backend container root (if present)
- It imports the ASGI app and starts Uvicorn, binding to 0.0.0.0:3001 by default

Usage:
    python main.py

Environment variables:
    PORT: Port to bind (default 3001)
    HOST / UVICORN_HOST: Host to bind (default 0.0.0.0)
    UVICORN_WORKERS: Number of workers (default 1)
    TRUST_PROXY: true/false to enable proxy headers (default false)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_str(name: str, default: str) -> str:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw


def _maybe_inject_venv_site_packages(project_root: Path) -> None:
    """
    Prepend local venv site-packages to sys.path if available.

    This must run BEFORE importing anything that depends on venv-installed packages.
    """
    pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    candidate = project_root / "venv" / "lib" / pyver / "site-packages"
    if not candidate.exists() or not candidate.is_dir():
        return

    site_path = str(candidate)
    if site_path not in sys.path:
        sys.path.insert(0, site_path)
    # Also help any subprocesses / child imports that rely on PYTHONPATH.
    os.environ["PYTHONPATH"] = site_path + (
        os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""
    )


def _maybe_load_dotenv(project_root: Path) -> None:
    """Load .env from the backend container root if python-dotenv is available."""
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return

    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)


def main() -> None:
    """
    Start the FastAPI app under Uvicorn.

    Intentionally ignores any extra argv passed by the preview runner.
    """
    project_root = Path(__file__).resolve().parent

    _maybe_inject_venv_site_packages(project_root)
    _maybe_load_dotenv(project_root)

    # Import after venv/.env setup.
    import uvicorn  # noqa: WPS433
    from src.api.main import app  # noqa: WPS433,F401  (imported for side-effects / validation)

    host = _env_str("UVICORN_HOST", _env_str("HOST", "0.0.0.0"))
    port = _env_int("PORT", 3001)
    workers = _env_int("UVICORN_WORKERS", 1)
    trust_proxy = _env_str("TRUST_PROXY", "false").lower() in {"1", "true", "yes"}

    # Use an import string for consistency across reload/workers.
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        workers=workers,
        proxy_headers=trust_proxy,
    )


if __name__ == "__main__":
    main()
