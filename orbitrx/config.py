from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "cat_port": "COM3",
    "cat_baud": 9600,
    "cat_timeout": 0.5,
    "cat_rig_profile": "kenwood",
    "cat_confirm_before_tune": True,
    "dx_cluster_host": "dxc.ve7cc.net",
    "dx_cluster_port": 23,
    "dx_cluster_callsign": "W1AW-9",
    "dx_cluster_nodes": [
        {"name": "VE7CC", "host": "dxc.ve7cc.net", "port": 23},
        {"name": "NC7J", "host": "nc7j.com", "port": 7373},
    ],
    "dx_filter_bands_mhz": [],
    "dx_filter_continents": [],
    "dx_spot_sound_alert": True,
    "dx_dedup_seconds": 30,
    "qrz_api_key": "",
    "alert_kp_threshold": 2,
    "alert_muf_threshold": 28,
    "storm_kp_threshold": 7,
    "refresh_interval_seconds": 60,
    "target_dx_lat": None,
    "target_dx_lon": None,
    "theme": "dark",
    "window_geometry": "1300x700",
    "map_layers": {"greyline": True, "night": True, "dx_arcs": True, "aurora": True, "grid": False},
    "log_max_mb": 10,
    "offline_cache_enabled": True,
    "show_demo_spots": False,
    "map_backend": "static",
    "target_dx_callsign": "",
    "minimize_to_tray": True,
    "check_updates_on_launch": True,
    "rig_profiles": [],
}


@dataclass
class AppConfig:
    path: Path = field(default_factory=lambda: Path("config.json"))
    data: dict[str, Any] = field(default_factory=lambda: deepcopy(DEFAULT_CONFIG))

    def load(self) -> AppConfig:
        if self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                loaded = json.load(f)
            merged = deepcopy(DEFAULT_CONFIG)
            merged.update(loaded)
            self.data = merged
        else:
            self.save()
        return self

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()
