from __future__ import annotations

import csv
import datetime
import json
import sqlite3
from pathlib import Path
from typing import Any

from orbitrx.utils import parse_history_query

DB_PATH = Path("orbitrx.db")
CACHE_PATH = Path("weather_cache.json")


class DataStore:
    def __init__(self, db_path: Path = DB_PATH, log_max_mb: int = 10) -> None:
        self.db_path = db_path
        self.log_max_mb = log_max_mb
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS propagation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL, kp REAL, flux REAL, sunspot REAL,
                    muf REAL, luf REAL, band_cond TEXT, lat REAL, lon REAL,
                    a_index REAL, solar_wind REAL, bz REAL)"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS dx_spots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL, spotter TEXT, target TEXT, freq_mhz REAL)"""
            )
            conn.commit()
        self._rotate_if_needed()

    def _rotate_if_needed(self) -> None:
        if self.db_path.exists() and self.db_path.stat().st_size > self.log_max_mb * 1024 * 1024:
            backup = self.db_path.with_suffix(".db.bak")
            if backup.exists():
                backup.unlink()
            self.db_path.rename(backup)
            self._init_db()

    def log_propagation(self, row: dict[str, Any]) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO propagation
                   (ts, kp, flux, sunspot, muf, luf, band_cond, lat, lon, a_index, solar_wind, bz)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    row.get("ts"), row.get("kp"), row.get("flux"), row.get("sunspot"),
                    row.get("muf"), row.get("luf"), row.get("band_cond"),
                    row.get("lat"), row.get("lon"), row.get("a_index"),
                    row.get("solar_wind"), row.get("bz"),
                ),
            )
            conn.commit()
        # Legacy CSV compatibility
        csv_path = Path("propagation_log.csv")
        write_header = not csv_path.exists()
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(["Timestamp", "Kp", "SolarFlux", "Sunspot", "MUF", "LUF", "BandCondition", "Lat", "Lon"])
            w.writerow([
                row.get("ts"), row.get("kp"), row.get("flux"), row.get("sunspot"),
                row.get("muf"), row.get("luf"), row.get("band_cond"),
                row.get("lat") or "--", row.get("lon") or "--",
            ])

    def log_dx_spot(self, spotter: str, target: str, freq_mhz: float) -> None:
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO dx_spots (ts, spotter, target, freq_mhz) VALUES (?,?,?,?)",
                (ts, spotter, target, freq_mhz),
            )
            conn.commit()
        csv_path = Path("dx_spots_log.csv")
        write_header = not csv_path.exists()
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(["Timestamp", "Spotter", "To_Station", "Frequency_MHz"])
            w.writerow([ts, spotter, target, freq_mhz])

    def query_propagation(self, query: str) -> list[dict[str, Any]]:
        start, end = parse_history_query(query)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM propagation WHERE ts >= ? AND ts < ? ORDER BY ts",
                (start.isoformat(), end.isoformat()),
            ).fetchall()
        return [dict(r) for r in rows]

    def recent_flux(self, n: int = 5) -> list[float]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT flux FROM propagation WHERE flux IS NOT NULL ORDER BY id DESC LIMIT ?",
                (n,),
            ).fetchall()
        return [float(r[0]) for r in reversed(rows)]

    def export_json_snapshot(self, data: dict[str, Any]) -> Path:
        path = Path("export.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return path

    def save_weather_cache(self, data: dict[str, Any]) -> None:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "data": data}, f)

    def load_weather_cache(self) -> dict[str, Any] | None:
        if not CACHE_PATH.exists():
            return None
        try:
            with open(CACHE_PATH, encoding="utf-8") as f:
                payload = json.load(f)
            return payload.get("data")
        except (json.JSONDecodeError, OSError):
            return None

    def export_dx_csv(self, dest: Path) -> None:
        with sqlite3.connect(self.db_path) as conn, open(dest, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Timestamp", "Spotter", "To_Station", "Frequency_MHz"])
            for row in conn.execute("SELECT ts, spotter, target, freq_mhz FROM dx_spots ORDER BY id"):
                w.writerow(row)
