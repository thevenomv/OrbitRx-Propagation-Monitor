"""Mutable application state shared across services and UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AppState:
    user_lat: float | None = None
    user_lon: float | None = None
    latest_dx_spots: list[dict[str, Any]] = field(default_factory=list)
    latest_dx_canvas_points: list[tuple[float, float, str]] = field(default_factory=list)

    kp_index: float = 0
    flux: float | None = None
    muf: float | None = None
    luf: float | None = None
    bands: str = "--"

    slider_offset_hours: float = 0
    alert_last: datetime | None = None

    cluster_active: bool = False
    dx_update_pending: bool = False

    current_map_photo: Any = None
    original_map: Any = None
