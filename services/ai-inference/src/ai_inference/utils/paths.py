"""Path helpers for monorepo-local inference runtime files."""

from __future__ import annotations

from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path | None:
    """Best-effort discovery of the monorepo root from scripts or containers."""
    search_starts = [start, Path.cwd(), Path(__file__).resolve()]
    seen: set[Path] = set()

    for raw_start in search_starts:
        if raw_start is None:
            continue

        current = raw_start if raw_start.is_dir() else raw_start.parent
        for candidate in (current, *current.parents):
            if candidate in seen:
                continue
            seen.add(candidate)
            if _looks_like_repo_root(candidate):
                return candidate
    return None


def resolve_repo_path(path_like: str | Path, *, must_exist: bool = False) -> Path:
    """Resolve relative paths from the repo root when possible."""
    path = Path(path_like).expanduser()
    if path.is_absolute():
        return path.resolve()

    candidates = []
    repo_root = find_repo_root()
    if repo_root is not None:
        candidates.append(repo_root / path)
    candidates.append(Path.cwd() / path)

    if must_exist:
        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()

    return candidates[0].resolve()


def to_repo_relative_path(path_like: str | Path) -> str:
    """Return a portable repo-relative path when the file is inside the repo."""
    path = Path(path_like).resolve()
    repo_root = find_repo_root(path)
    if repo_root is None:
        return str(path)

    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return str(path)


def _looks_like_repo_root(candidate: Path) -> bool:
    has_services = (candidate / "services").exists()
    has_root_marker = (
        (candidate / "requirements.txt").exists()
        or (candidate / "shared").exists()
        or (candidate / "datasets").exists()
    )
    return has_services and has_root_marker
