"""Propagation math and contest helpers."""

from __future__ import annotations

import datetime
import math

from orbitrx.config import UPCOMING_CONTESTS


def sun_times(lat: float, lon: float, when: datetime.datetime) -> tuple[float | None, float | None]:
    day_of_year = when.timetuple().tm_yday
    decl = 23.44 * math.sin(math.radians((360 / 365.25) * (day_of_year - 81)))
    lat_rad = math.radians(lat)
    decl_rad = math.radians(decl)
    cos_omega = -math.tan(lat_rad) * math.tan(decl_rad)
    if cos_omega >= 1 or cos_omega <= -1:
        return None, None
    omega = math.degrees(math.acos(cos_omega))
    noon_utc = 12 - (lon / 15.0)
    sunrise_utc = (noon_utc - omega / 15.0) % 24
    sunset_utc = (noon_utc + omega / 15.0) % 24
    return sunrise_utc, sunset_utc


def estimate_muf(flux: float | None, kp: float) -> tuple[float | None, float | None]:
    if flux is None:
        return None, None
    base_muf = 4 + flux * 0.25
    disturbance = 1.0 - (kp / 20.0)
    muf = base_muf * max(0.5, min(disturbance, 1.0))
    luf = max(1.5, base_muf * 0.25)
    return round(muf, 1), round(luf, 1)


def parse_history_query(q: str) -> tuple[datetime.datetime, datetime.datetime]:
    q = q.strip()
    if not q:
        raise ValueError("Empty query")

    def to_dt(token: str) -> datetime.datetime:
        token = token.strip()
        if len(token) == 10 and token.count("-") == 2:
            return datetime.datetime.fromisoformat(token + "T00:00:00+00:00")
        return datetime.datetime.fromisoformat(token)

    if ":" in q and q.count(":") == 1 and "T" not in q:
        from_date, to_date = q.split(":", 1)
        start = to_dt(from_date)
        end = to_dt(to_date)
        if start.tzinfo is None:
            start = start.replace(tzinfo=datetime.timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=datetime.timezone.utc)
        if len(to_date.strip()) == 10 and to_date.count("-") == 2:
            end = end + datetime.timedelta(days=1)
        return start, end

    start = to_dt(q)
    if start.tzinfo is None:
        start = start.replace(tzinfo=datetime.timezone.utc)
    if len(q) == 10 and q.count("-") == 2:
        return start, start + datetime.timedelta(days=1)
    return start, start


def band_condition(freq_mhz: float, flux: float | None, kp: float) -> str:
    if flux is None:
        return "UNKNOWN"
    base_score = (flux / 150.0) - (kp / 10.0)
    if base_score > 1.0:
        return "OPEN"
    if base_score > 0.5:
        return "FAIR"
    return "CLOSED"


def get_next_contest() -> dict | None:
    now = datetime.datetime.now()
    for contest in UPCOMING_CONTESTS:
        contest_date = datetime.datetime.strptime(contest["date"], "%Y-%m-%d")
        if contest_date >= now:
            return contest
    return None
