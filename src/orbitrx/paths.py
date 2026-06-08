"""Runtime and bundled asset path resolution."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def get_data_dir() -> Path:
    """User-writable directory for logs, exports, and cached map."""
    override = os.environ.get("ORBITRX_DATA")
    if override:
        path = Path(override)
    else:
        path = Path.home() / ".orbitrx"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_bundled_asset(name: str) -> Path | None:
    """Return path to a bundled asset when running as a PyInstaller frozen exe."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidate = Path(sys._MEIPASS) / name
        if candidate.exists():
            return candidate
    package_asset = Path(__file__).resolve().parent / "assets" / "bundled" / name
    if package_asset.exists():
        return package_asset
    legacy = Path(__file__).resolve().parents[2] / name
    if legacy.exists():
        return legacy
    return None


def get_map_path() -> Path:
    """Path to world_map.jpg in the user data directory."""
    return get_data_dir() / "world_map.jpg"


def ensure_map_file() -> Path:
    """Ensure world_map.jpg exists in the data directory."""
    map_path = get_map_path()
    if map_path.exists():
        return map_path

    bundled = get_bundled_asset("world_map.jpg")
    if bundled is not None:
        shutil.copy2(bundled, map_path)
        return map_path

    from orbitrx.assets.map import generate_world_map

    generate_world_map(map_path, width=1600, height=800)
    return map_path


def get_log_path(name: str) -> Path:
    return get_data_dir() / name


def get_export_path() -> Path:
    return get_data_dir() / "export.json"
