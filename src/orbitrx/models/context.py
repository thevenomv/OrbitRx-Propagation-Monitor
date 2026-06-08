"""Application context combining state and UI widget references."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from orbitrx.models.state import AppState


@dataclass
class UIRefs:
    window: Any = None
    canvas: Any = None
    lbl_slider: Any = None
    lbl_kp: Any = None
    lbl_kp_forecast: Any = None
    lbl_solar: Any = None
    lbl_sunspot: Any = None
    lbl_time: Any = None
    lbl_bands: Any = None
    lbl_muf: Any = None
    lbl_sunrise: Any = None
    lbl_sunset: Any = None
    lbl_alerts: Any = None
    lbl_location: Any = None
    lbl_status: Any = None
    lbl_solar_forecast: Any = None
    lbl_contest: Any = None
    lbl_dx: Any = None
    btn_refresh: Any = None
    selected_history_date: Any = None


@dataclass
class AppContext:
    state: AppState = field(default_factory=AppState)
    ui: UIRefs = field(default_factory=UIRefs)
    dx_coordinates: dict[str, tuple[float, float]] = field(default_factory=dict)
