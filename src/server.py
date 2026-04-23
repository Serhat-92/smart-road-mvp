"""Compatibility wrapper for the legacy src/server.py entrypoint."""

from pathlib import Path
import runpy


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "apps" / "command-center" / "server.py"
    runpy.run_path(str(target), run_name="__main__")
