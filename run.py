"""Compatibility wrapper for the interactive radar launcher."""

from pathlib import Path
import runpy


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "apps" / "radar-cli" / "run.py"
    runpy.run_path(str(target), run_name="__main__")
