"""Gateway API package bootstrap."""

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SHARED_PYTHON = REPO_ROOT / "shared" / "python"

shared_python_str = str(SHARED_PYTHON)
if SHARED_PYTHON.exists() and shared_python_str not in sys.path:
    sys.path.insert(0, shared_python_str)

from monorepo import ensure_repo_imports


ensure_repo_imports(REPO_ROOT)
