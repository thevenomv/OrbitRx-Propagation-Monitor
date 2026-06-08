from __future__ import annotations

import datetime
import json
import math
import random
import urllib.request
from typing import Any


def fetch_json(url: str, timeout: int = 10) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 OrbitRx/4.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read())


def normalize_freq_mhz(freq: float | str) -> float:
    val = float(freq)
    if val >= 1000:
        val /= 1000.0
    return round(val, 3)


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
    return start, start + datetime.timedelta(minutes=1)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def great_circle_points(
    lat1: float, lon1: float, lat2: float, lon2: float, steps: int = 24
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    la1, lo1, la2, lo2 = map(math.radians, (lat1, lon1, lat2, lon2))
    d = 2 * math.asin(
        math.sqrt(
            math.sin((la2 - la1) / 2) ** 2
            + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
        )
    )
    if d == 0:
        return [(math.degrees(la1), math.degrees(lo1))]
    for i in range(steps + 1):
        f = i / steps
        a = math.sin((1 - f) * d) / math.sin(d)
        b = math.sin(f * d) / math.sin(d)
        x = a * math.cos(la1) * math.cos(lo1) + b * math.cos(la2) * math.cos(lo2)
        y = a * math.cos(la1) * math.sin(lo1) + b * math.cos(la2) * math.sin(lo2)
        z = a * math.sin(la1) + b * math.sin(la2)
        la = math.atan2(z, math.sqrt(x * x + y * y))
        lo = math.atan2(y, x)
        points.append((math.degrees(la), math.degrees(lo)))
    return points


def local_time_at_lon(lon: float, when: datetime.datetime | None = None) -> str:
    when = when or datetime.datetime.now(datetime.timezone.utc)
    offset_h = lon / 15.0
    local = when + datetime.timedelta(hours=offset_h)
    return local.strftime("%H:%M")


PREFIX_MAP: dict[str, tuple[float, float]] = {
    "W": (38.0, -97.0), "K": (38.0, -97.0), "N": (38.0, -97.0), "A": (38.0, -97.0),
    "VE": (56.0, -106.0), "VA": (56.0, -106.0), "VY": (56.0, -106.0),
    "XE": (23.0, -102.0), "PY": (-14.0, -51.0), "PU": (-14.0, -51.0),
    "LU": (-38.0, -63.0), "CE": (-35.0, -71.0), "G": (52.0, -1.0), "M": (52.0, -1.0),
    "F": (46.0, 2.0), "D": (51.0, 9.0), "I": (41.0, 12.0), "EA": (40.0, -4.0),
    "JA": (36.0, 138.0), "JH": (36.0, 138.0), "VK": (-25.0, 133.0), "ZL": (-40.0, 174.0),
    "ZS": (-30.0, 25.0), "VU": (20.0, 77.0), "BY": (35.0, 104.0), "HL": (35.0, 127.0),
}


def estimate_location(callsign: str) -> tuple[float, float]:
    call = callsign.upper().strip()
    for prefix in sorted(PREFIX_MAP.keys(), key=len, reverse=True):
        if call.startswith(prefix):
            lat, lon = PREFIX_MAP[prefix]
            return (lat + random.uniform(-3, 3), lon + random.uniform(-3, 3))
    land_boxes = [
        (30, 50, -120, -70), (-30, 10, -80, -50), (40, 60, -10, 30),
        (-20, 30, 10, 40), (30, 60, 60, 120), (-30, -15, 115, 145),
    ]
    box = random.choice(land_boxes)
    return (random.uniform(box[0], box[1]), random.uniform(box[2], box[3]))
