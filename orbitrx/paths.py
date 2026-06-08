from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    """Directory containing app.py / the exe."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def bundled_root() -> Path | None:
    """PyInstaller onefile extraction folder."""
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) if meipass else None


def resolve_map_path() -> Path:
    """Find world_map.jpg from bundle, project root, or cwd."""
    names = ["world_map.jpg"]
    search: list[Path] = []
    bundle = bundled_root()
    if bundle:
        search.extend(bundle / n for n in names)
    root = project_root()
    search.extend([root / n for n in names])
    search.extend([Path.cwd() / n for n in names])
    for path in search:
        if path.is_file() and path.stat().st_size > 10_000:
            return path
    return root / "world_map.jpg"


def ensure_map_image() -> Path:
    """Return path to world map, downloading if missing."""
    path = resolve_map_path()
    if path.is_file() and path.stat().st_size > 10_000:
        return path

    target = project_root() / "world_map.jpg"
    try:
        from generate_map import generate_world_map

        generate_world_map(1800, 900)
        if target.is_file():
            return target
    except Exception:
        pass

    if path != target and target.is_file():
        return target
    return target
