"""
src.api package initialization.

This project is deployed in an environment where the process may be started with
the system Python interpreter (e.g., /usr/bin/python) instead of the container's
virtual environment interpreter.

To make the service robust in that preview/runtime scenario, we detect the
container-local `venv/` and prepend its site-packages directory to sys.path.
This allows imports like `fastapi`/`starlette` (installed into the venv during
image build/post-process) to resolve successfully, so the API can start and bind
to port 3001.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _maybe_inject_venv_site_packages() -> None:
    """
    Prepend local venv site-packages to sys.path if available.

    This is intentionally conservative:
    - It only runs when `venv/lib/pythonX.Y/site-packages` exists alongside the
      project root (two levels up from this file: src/api/__init__.py -> project root).
    - It avoids duplicating entries.
    """
    project_root = Path(__file__).resolve().parents[2]  # .../resident_backend_api
    pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    candidate = project_root / "venv" / "lib" / pyver / "site-packages"

    if not candidate.exists() or not candidate.is_dir():
        return

    site_path = str(candidate)
    if site_path not in sys.path:
        # Prepend so venv deps take priority over any system site-packages
        sys.path.insert(0, site_path)
        # Ensure child processes also see it if they rely on PYTHONPATH
        os.environ["PYTHONPATH"] = site_path + (
            os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""
        )


_maybe_inject_venv_site_packages()
