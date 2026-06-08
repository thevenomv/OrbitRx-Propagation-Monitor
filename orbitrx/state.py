from __future__ import annotations

import datetime
import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppState:
    user_lat: float | None = None
    user_lon: float | None = None
    kp_index: float = 0.0
    a_index: float | None = None
    a_index_source: str | None = None
    flux: float | None = None
    flux_trend: str = "--"
    sunspot_observed: float | None = None
    sunspot_predicted: float | None = None
    solar_wind_speed: float | None = None
    bz: float | None = None
    muf: float | None = None
    luf: float | None = None
    path_muf: float | None = None
    path_muf_label: str | None = None
    bands_summary: str = "--"
    band_grid: dict[str, str] = field(default_factory=dict)
    time_utc: str = "--"
    kp_forecast: str = "--"
    alerts: list[str] = field(default_factory=list)
    solar_forecast: str = "--"
    slider_offset_hours: float = 0.0
    map_zoom: float = 1.0
    map_pan_x: float = 0.0
    map_pan_y: float = 0.0
    cluster_status: str = "disconnected"
    latest_dx_spots: list[dict[str, Any]] = field(default_factory=list)
    latest_dx_canvas_points: list[tuple[float, float, float]] = field(default_factory=list)
    dx_coordinates: dict[str, tuple[float, float]] = field(default_factory=dict)
    dx_lock: threading.Lock = field(default_factory=threading.Lock)
    weather_fetch_in_progress: bool = False
    cluster_active: bool = False
    dx_update_pending: bool = False
    alert_excellent_last: float | None = None
    alert_storm_last: float | None = None
    last_weather_cache: dict[str, Any] | None = None
    click_local_time: str = ""
    last_weather_update: datetime.datetime | None = None
    last_dx_update: datetime.datetime | None = None
    dx_coord_source: dict[str, str] = field(default_factory=dict)
    hamqsl_band_hint: str = ""

    def prune_dx_spots(self, max_age: float = 300) -> None:
        now = time.time()
        with self.dx_lock:
            self.latest_dx_spots[:] = [
                s for s in self.latest_dx_spots if now - s.get("time", now) < max_age
            ]
