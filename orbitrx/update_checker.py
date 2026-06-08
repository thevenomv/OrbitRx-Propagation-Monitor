from __future__ import annotations

import json
import re
import urllib.request
from typing import Any

GITHUB_REPO = "thevenomv/OrbitRx-Propagation-Monitor"


def _parse_version(tag: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", tag.lstrip("vV"))
    return tuple(int(n) for n in nums) if nums else (0,)


def check_github_release(current_version: str) -> dict[str, Any]:
    """
    Compare current version to latest GitHub release.
    Returns {update_available, latest, url, message}.
    """
    result: dict[str, Any] = {
        "update_available": False,
        "latest": current_version,
        "url": f"https://github.com/{GITHUB_REPO}/releases",
        "message": "",
    }
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
            headers={"Accept": "application/vnd.github+json", "User-Agent": "OrbitRx"},
        )
        data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
        latest = (data.get("tag_name") or data.get("name") or "").strip()
        if not latest:
            return result
        result["latest"] = latest
        result["url"] = data.get("html_url") or result["url"]
        if _parse_version(latest) > _parse_version(current_version):
            result["update_available"] = True
            result["message"] = f"OrbitRx {latest} is available (you have v{current_version})"
        else:
            result["message"] = f"Up to date (v{current_version})"
    except Exception as e:
        result["message"] = f"Update check skipped: {e}"
    return result
