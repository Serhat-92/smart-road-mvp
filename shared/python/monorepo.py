"""Helpers for bootstrapping local imports inside the monorepo."""

from pathlib import Path
import sys


def ensure_repo_imports(repo_root: Path) -> Path:
    """Add shared Python directories to sys.path for script-based entrypoints."""
    repo_root = Path(repo_root).resolve()
    python_paths = (
        repo_root / "shared" / "python",
        repo_root / "shared" / "event-contracts" / "python",
        repo_root / "services" / "ai-inference" / "src",
    )

    for python_path in python_paths:
        python_path_str = str(python_path)
        if python_path.exists() and python_path_str not in sys.path:
            sys.path.insert(0, python_path_str)

    return repo_root
