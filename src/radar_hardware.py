"""Compatibility wrapper for legacy radar_hardware imports."""

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SHARED_PY = REPO_ROOT / "shared" / "python"
if str(SHARED_PY) not in sys.path:
    sys.path.insert(0, str(SHARED_PY))

from monorepo import ensure_repo_imports

ensure_repo_imports(REPO_ROOT)

from ai_inference.radar_hardware import *  # noqa: F401,F403
