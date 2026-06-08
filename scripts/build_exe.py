"""Build standalone Windows executable via PyInstaller."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "packaging" / "orbitrx.spec"


def main() -> int:
    bundled = ROOT / "src" / "orbitrx" / "assets" / "bundled" / "world_map.jpg"
    if not bundled.exists():
        root_map = ROOT / "world_map.jpg"
        if root_map.exists():
            bundled.parent.mkdir(parents=True, exist_ok=True)
            bundled.write_bytes(root_map.read_bytes())
            print(f"Copied bundled map to {bundled}")

    cmd = [sys.executable, "-m", "PyInstaller", str(SPEC), "--distpath", "dist", "--workpath", "build"]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
