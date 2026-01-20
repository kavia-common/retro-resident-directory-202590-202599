"""
Top-level `src` package.

This file exists primarily for runtime robustness.

Some preview/orchestration environments start the backend process with a working
directory that is NOT the backend container root (e.g. the monorepo/workspace
root). In such cases, imports like `import src.api.main` will fail unless the
backend's `src/` directory is discoverable as a Python package.

By ensuring `src` is a proper package, and by keeping the backend code within
`src.api`, we make `uvicorn src.api.main:app` and `python -m src.api.main` more
reliable across different launch modes.
"""
from __future__ import annotations

# No side effects here; side-effectful startup logic belongs in src.api.__init__.
