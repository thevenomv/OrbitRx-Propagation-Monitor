from __future__ import annotations

import datetime
import re
import urllib.request
from typing import Any

UPCOMING_CONTESTS: list[dict[str, Any]] = [
    {"name": "ARCI Spring QSO Party", "date": "2026-04-04", "bands": ["160m", "80m", "40m", "20m", "15m", "10m"]},
    {"name": "CQ WW WPX SSB", "date": "2026-03-28", "bands": ["All HF"]},
    {"name": "RSGB IOTA Contest", "date": "2026-07-26", "bands": ["All HF", "VHF", "UHF"]},
]

_CONTEST_URL = "https://www.contestcalendar.com/contestcal/weeklycontest.php"
_CACHE: list[dict[str, Any]] | None = None
_CACHE_AT: datetime.datetime | None = None


def _parse_contest_page(html: str) -> list[dict[str, Any]]:
    contests: list[dict[str, Any]] = []
    # Lines like: "Mar 28-29 — CQ WW WPX SSB"
    for m in re.finditer(
        r"([A-Z][a-z]{2})\s+(\d{1,2})(?:-\d{1,2})?\s*[—\-]\s*([^<\n]+)",
        html,
    ):
        month, day, name = m.group(1), m.group(2), m.group(3).strip()
        try:
            dt = datetime.datetime.strptime(f"{month} {day} 2026", "%b %d %Y")
        except ValueError:
            try:
                dt = datetime.datetime.strptime(f"{month} {day} {datetime.datetime.now().year}", "%b %d %Y")
            except ValueError:
                continue
        contests.append({
            "name": name[:80],
            "date": dt.strftime("%Y-%m-%d"),
            "bands": ["HF"],
        })
    return contests


def fetch_upcoming_contests() -> list[dict[str, Any]]:
    global _CACHE, _CACHE_AT
    now = datetime.datetime.now()
    if _CACHE and _CACHE_AT and (now - _CACHE_AT).total_seconds() < 3600:
        return _CACHE
    try:
        html = urllib.request.urlopen(_CONTEST_URL, timeout=12).read().decode("utf-8", errors="ignore")
        parsed = _parse_contest_page(html)
        if parsed:
            _CACHE = parsed
            _CACHE_AT = now
            return parsed
    except Exception:
        pass
    return UPCOMING_CONTESTS


def get_next_contest() -> dict[str, Any] | None:
    now = datetime.datetime.now()
    for contest in fetch_upcoming_contests():
        contest_date = datetime.datetime.strptime(contest["date"], "%Y-%m-%d")
        if contest_date >= now:
            return contest
    return None
