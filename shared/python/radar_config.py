"""Shared config helpers for the radar launchers."""

import json
from pathlib import Path


DEFAULT_CONFIG = {
    "max_speed": 90,
    "min_speed": 30,
    "speed_factor": 0.22,
}


def get_config_path(repo_root: Path) -> Path:
    return Path(repo_root).resolve() / "config.json"


def load_config(repo_root: Path) -> dict:
    config_path = get_config_path(repo_root)
    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as config_file:
                return {**DEFAULT_CONFIG, **json.load(config_file)}
        except (OSError, ValueError, TypeError):
            pass
    return DEFAULT_CONFIG.copy()


def save_config(repo_root: Path, config: dict) -> Path:
    config_path = get_config_path(repo_root)
    with config_path.open("w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=2)
    return config_path
