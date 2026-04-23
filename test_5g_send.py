"""Compatibility wrapper for the relocated integration script."""

from pathlib import Path
import runpy


if __name__ == "__main__":
    target = (
        Path(__file__).resolve().parent
        / "tests"
        / "integration"
        / "test_5g_send.py"
    )
    runpy.run_path(str(target), run_name="__main__")
