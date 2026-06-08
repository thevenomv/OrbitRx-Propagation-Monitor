from __future__ import annotations

import math
from typing import Any

from orbitrx.utils import haversine_km

HF_BANDS: dict[str, dict[str, Any]] = {
    "160m": {"freq": 1.8, "dial": "1.840"},
    "80m": {"freq": 3.5, "dial": "3.790"},
    "40m": {"freq": 7.0, "dial": "7.150"},
    "20m": {"freq": 14.0, "dial": "14.200"},
    "15m": {"freq": 21.0, "dial": "21.250"},
    "10m": {"freq": 28.0, "dial": "28.400"},
}

BAND_CHIP: dict[str, str] = {
    "OPEN": "🟢",
    "FAIR": "🟡",
    "CLOSED": "🔴",
    "UNKNOWN": "⚪",
}


def estimate_muf(flux: float | None, kp: float) -> tuple[float | None, float | None]:
    if flux is None:
        return None, None
    base_muf = 4 + flux * 0.25
    disturbance = 1.0 - (kp / 20.0)
    muf = base_muf * max(0.5, min(disturbance, 1.0))
    luf = max(1.5, base_muf * 0.25)
    return round(muf, 1), round(luf, 1)


def voacap_lite_path_muf(
    flux: float | None,
    kp: float,
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float | None:
    """ITU-R style lite path MUF using distance and solar factors."""
    if flux is None:
        return None
    dist = haversine_km(lat1, lon1, lat2, lon2)
    base, _ = estimate_muf(flux, kp)
    if base is None:
        return None
    # Longer paths need lower usable max freq at oblique incidence approximation
    factor = 1.0 + min(0.35, dist / 20000.0)
    return round(base * factor, 1)


def band_condition(freq_mhz: float, flux: float | None, kp: float) -> str:
    if flux is None:
        return "UNKNOWN"
    score = (flux / 150.0) - (kp / 10.0) - (28.0 - freq_mhz) * 0.01
    if score > 1.0:
        return "OPEN"
    if score > 0.5:
        return "FAIR"
    return "CLOSED"


def band_grid(flux: float | None, kp: float) -> dict[str, str]:
    return {name: band_condition(meta["freq"], flux, kp) for name, meta in HF_BANDS.items()}


def band_chip(condition: str) -> str:
    return BAND_CHIP.get(condition, "⚪")


def suggested_dial_freq(band_name: str) -> str:
    meta = HF_BANDS.get(band_name, {})
    return str(meta.get("dial", meta.get("freq", "--")))


def bands_summary(flux: float | None, kp: float) -> str:
    if kp <= 3 and flux is not None and flux > 120:
        return "EXCELLENT: All HF bands open for DX"
    if kp <= 5 and flux is not None and flux > 100:
        return "GOOD: Most HF bands workable"
    return "POOR: Limited HF propagation"


def flux_trend_arrow(recent_flux: list[float]) -> str:
    if len(recent_flux) < 2:
        return "--"
    delta = recent_flux[-1] - recent_flux[-2]
    if delta > 2:
        return "↑"
    if delta < -2:
        return "↓"
    return "→"


def aurora_oval_lat(kp: float) -> float:
    """Approximate equatorward edge of auroral oval vs Kp."""
    return max(50.0, 70.0 - kp * 2.5)
