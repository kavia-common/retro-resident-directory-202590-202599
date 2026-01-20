"""
Repository-level `src` namespace shim.

Why this file exists:
- The backend code lives in: retro-resident-directory-202590-202599/resident_backend_api/src
- Some preview runners start Python from the workspace/repo root and attempt to
  import `src.api.main:app` (or similar).
- Without help, `import src.api.main` fails because the backend `src/` directory
  is not on sys.path.

What this does:
- Treats this `src` directory as a *namespace package* and extends its
  `__path__` to include the backend container's `resident_backend_api/src`.
- This makes `import src.api.main` resolve to the backend implementation even
  when cwd is the workspace root.

This is intentionally minimal and safe: it only affects module discovery.
"""
from __future__ import annotations

import sys
from pathlib import Path
from pkgutil import extend_path

# Allow `src` to be a namespace package spanning multiple locations.
__path__ = extend_path(__path__, __name__)  # type: ignore[name-defined]

# Compute backend src path relative to this file.
# This shim lives inside the workspace folder itself:
#   .../retro-resident-directory-202590-202599/src/__init__.py
# So the backend src should be at:
#   .../retro-resident-directory-202590-202599/resident_backend_api/src
workspace_root = Path(__file__).resolve().parents[1]
backend_src = workspace_root / "resident_backend_api" / "src"

if backend_src.is_dir():
    backend_src_str = str(backend_src)

    # Make it importable via normal sys.path resolution too.
    if backend_src_str not in sys.path:
        sys.path.insert(0, backend_src_str)

    # Also extend this namespace's search path.
    if backend_src_str not in __path__:
        __path__.append(backend_src_str)
