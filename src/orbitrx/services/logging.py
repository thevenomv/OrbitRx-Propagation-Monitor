"""CSV logging and JSON export."""

from __future__ import annotations

import csv
import datetime
import json

from orbitrx.models.context import AppContext
from orbitrx.paths import get_export_path, get_log_path

LOG_FILE_NAME = "propagation_log.csv"
DX_LOG_FILE_NAME = "dx_spots_log.csv"


def log_file_path() -> str:
    return str(get_log_path(LOG_FILE_NAME))


def dx_log_file_path() -> str:
    return str(get_log_path(DX_LOG_FILE_NAME))


def init_dx_log_file() -> None:
    path = get_log_path(DX_LOG_FILE_NAME)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["Timestamp", "Spotter", "To_Station", "Frequency_MHz"])


def log_dx_spot(spotter: str, to_station: str, freq: str) -> None:
    try:
        init_dx_log_file()
        with get_log_path(DX_LOG_FILE_NAME).open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
                spotter,
                to_station,
                freq,
            ])
    except Exception as exc:
        print("DX log error:", exc)


def init_log_file() -> None:
    path = get_log_path(LOG_FILE_NAME)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                "Timestamp", "Kp", "SolarFlux", "Sunspot", "MUF", "LUF",
                "BandCondition", "Lat", "Lon",
            ])


def log_data(
    kp: float,
    flux: float | None,
    sunspot: float | None,
    muf: float | str,
    luf: float | str,
    band_cond: str,
    lat: float | None,
    lon: float | None,
) -> None:
    try:
        init_log_file()
        sanitized_cond = band_cond.split(":")[1].strip() if ":" in band_cond else str(band_cond)[:50]
        with get_log_path(LOG_FILE_NAME).open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
                kp, flux, sunspot, muf, luf, sanitized_cond, lat or "--", lon or "--",
            ])
    except Exception as exc:
        print("Log error:", exc)


def export_json(ctx: AppContext) -> str | None:
    try:
        data = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "kp_index": ctx.state.kp_index,
            "solar_flux": ctx.state.flux,
            "user_location": {"lat": ctx.state.user_lat, "lon": ctx.state.user_lon},
            "log_file": log_file_path(),
        }
        export_path = get_export_path()
        export_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return str(export_path)
    except Exception as exc:
        print("JSON export error:", exc)
        return None
