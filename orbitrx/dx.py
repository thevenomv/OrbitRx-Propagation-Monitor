from __future__ import annotations

import datetime
import re
import socket
import threading
import time
import urllib.request
import json
from typing import Any, Callable

from orbitrx.config import AppConfig
from orbitrx.state import AppState
from orbitrx.utils import estimate_location, normalize_freq_mhz

DX_LINE_RE = re.compile(
    r"^DX de\s+(\S+?)[:\s]+(\d+(?:\.\d+)?)\s+(\S+)",
    re.IGNORECASE,
)

CONTINENT_BOXES = {
    "NA": (15, 72, -170, -50),
    "SA": (-56, 15, -82, -34),
    "EU": (35, 72, -25, 45),
    "AF": (-35, 38, -18, 52),
    "AS": (5, 77, 25, 180),
    "OC": (-50, 10, 110, 180),
}


def parse_dx_line(line: str) -> tuple[str, float, str] | None:
    line = line.strip()
    if not line.upper().startswith("DX DE"):
        return None
    m = DX_LINE_RE.match(line)
    if m:
        spotter, freq_raw, target = m.group(1), m.group(2), m.group(3)
        return spotter.rstrip(":"), normalize_freq_mhz(freq_raw), target
    parts = line.split()
    if len(parts) >= 5 and parts[0].upper() == "DX" and parts[1].upper() == "DE":
        try:
            return parts[2].strip(":"), normalize_freq_mhz(parts[3]), parts[4]
        except ValueError:
            return None
    return None


def continent_for_latlon(lat: float, lon: float) -> str:
    for code, (la0, la1, lo0, lo1) in CONTINENT_BOXES.items():
        if la0 <= lat <= la1 and lo0 <= lon <= lo1:
            return code
    return "XX"


def spot_passes_filters(
    spot: dict[str, Any],
    state: AppState,
    cfg: AppConfig,
) -> bool:
    bands = cfg.get("dx_filter_bands_mhz") or []
    continents = cfg.get("dx_filter_continents") or []
    if bands:
        freq = spot.get("freq", 0)
        if not any(abs(freq - b) < 0.5 or abs(freq - b) < 5 for b in bands):
            # allow band bucket match
            matched = False
            for b in bands:
                if abs(freq - b) < 2.0:
                    matched = True
                    break
            if not matched:
                return False
    if continents:
        pos = state.dx_coordinates.get(spot.get("to", ""))
        if pos and continent_for_latlon(pos[0], pos[1]) not in continents:
            return False
    return True


def is_duplicate(spot: dict[str, Any], state: AppState, dedup_sec: int) -> bool:
    key = (spot.get("from"), spot.get("to"), spot.get("freq"))
    now = time.time()
    with state.dx_lock:
        for s in state.latest_dx_spots:
            if (s.get("from"), s.get("to"), s.get("freq")) == key:
                if now - s.get("time", 0) < dedup_sec:
                    return True
    return False


def qrz_lookup(callsign: str, api_key: str) -> tuple[float, float] | None:
    if not api_key:
        return None
    try:
        url = f"https://xmldata.qrz.com/xml/current/?KEY={api_key};CALLSIGN={callsign}"
        data = urllib.request.urlopen(url, timeout=8).read().decode("utf-8", errors="ignore")
        if "Session" in data and "Expired" in data:
            return None
        if re.search(r"<Error>", data, re.I):
            return None
        lat_m = re.search(r"<lat>([-\d.]+)</lat>", data)
        lon_m = re.search(r"<lon>([-\d.]+)</lon>", data)
        if lat_m and lon_m:
            return float(lat_m.group(1)), float(lon_m.group(1))
    except Exception:
        pass
    return None


def verify_qrz_api(api_key: str, callsign: str = "W1AW") -> tuple[bool, str, tuple[float, float] | None]:
    """Validate QRZ API key; returns (ok, message, coordinates)."""
    if not api_key.strip():
        return False, "QRZ API key is empty", None
    try:
        url = f"https://xmldata.qrz.com/xml/current/?KEY={api_key};CALLSIGN={callsign}"
        data = urllib.request.urlopen(url, timeout=10).read().decode("utf-8", errors="ignore")
        if "Session" in data and "Expired" in data:
            return False, "QRZ session expired — check API key", None
        err = re.search(r"<Error>([^<]+)</Error>", data, re.I)
        if err:
            return False, err.group(1).strip(), None
        pos = qrz_lookup(callsign, api_key)
        if pos:
            return True, f"QRZ OK: {callsign} @ {pos[0]:.3f}, {pos[1]:.3f}", pos
        return False, f"QRZ responded but no coords for {callsign}", None
    except Exception as e:
        return False, str(e), None


def resolve_coordinate(
    callsign: str,
    state: AppState,
    cfg: AppConfig,
) -> tuple[float, float]:
    if callsign in state.dx_coordinates:
        return state.dx_coordinates[callsign]
    pos = qrz_lookup(callsign, cfg.get("qrz_api_key", ""))
    if pos is not None:
        state.dx_coord_source[callsign] = "qrz"
    else:
        pos = estimate_location(callsign)
        state.dx_coord_source[callsign] = "prefix"
    state.dx_coordinates[callsign] = pos
    return pos


def resolve_target_position(
    callsign: str,
    cfg: AppConfig,
    state: AppState,
) -> tuple[float, float, str]:
    """Resolve path target by callsign (QRZ → prefix guess)."""
    cs = callsign.strip().upper()
    if not cs:
        raise ValueError("empty callsign")
    pos = qrz_lookup(cs, cfg.get("qrz_api_key", ""))
    if pos is not None:
        state.dx_coordinates[cs] = pos
        state.dx_coord_source[cs] = "qrz"
        return pos[0], pos[1], "qrz"
    pos = estimate_location(cs)
    state.dx_coordinates[cs] = pos
    state.dx_coord_source[cs] = "prefix"
    return pos[0], pos[1], "prefix"


class DxClusterService:
    def __init__(
        self,
        state: AppState,
        cfg: AppConfig,
        on_spot: Callable[[], None],
        on_status: Callable[[str], None],
        on_band_alert: Callable[[dict[str, Any]], None] | None = None,
        store: Any = None,
    ) -> None:
        self.state = state
        self.cfg = cfg
        self.on_spot = on_spot
        self.on_status = on_status
        self.on_band_alert = on_band_alert
        self.store = store
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self.state.cluster_active:
            return
        self.state.cluster_active = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.state.cluster_active = False

    def _run(self) -> None:
        while self.state.cluster_active:
            s = None
            host = self.cfg.get("dx_cluster_host")
            port = int(self.cfg.get("dx_cluster_port", 23))
            callsign = self.cfg.get("dx_cluster_callsign", "W1AW-9")
            try:
                self.on_status("connecting")
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(10)
                s.connect((host, port))
                time.sleep(1.5)
                try:
                    s.recv(4096)
                except socket.timeout:
                    pass
                s.sendall(f"{callsign}\r\n".encode("ascii"))
                s.settimeout(None)
                self.on_status("connected")
                buffer = ""
                while self.state.cluster_active:
                    data = s.recv(2048)
                    if not data:
                        break
                    buffer += data.decode("ascii", errors="ignore")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        self._handle_line(line)
            except Exception:
                self.on_status("reconnecting")
            finally:
                if s is not None:
                    try:
                        s.close()
                    except OSError:
                        pass
            if self.state.cluster_active:
                time.sleep(30)

    def _handle_line(self, line: str) -> None:
        parsed = parse_dx_line(line)
        if not parsed:
            return
        spotter, freq_mhz, target = parsed
        spot = {
            "from": spotter,
            "to": target,
            "freq": freq_mhz,
            "time": time.time(),
            "demo": False,
        }
        if is_duplicate(spot, self.state, int(self.cfg.get("dx_dedup_seconds", 30))):
            return
        resolve_coordinate(spotter, self.state, self.cfg)
        resolve_coordinate(target, self.state, self.cfg)
        if not spot_passes_filters(spot, self.state, self.cfg):
            return
        if self.store:
            self.store.log_dx_spot(spotter, target, freq_mhz)
        with self.state.dx_lock:
            self.state.latest_dx_spots.insert(0, spot)
            self.state.latest_dx_spots = self.state.latest_dx_spots[:50]
        self.state.last_dx_update = datetime.datetime.now(datetime.timezone.utc)
        if self.on_band_alert and freq_mhz >= 28.0:
            self.on_band_alert(spot)
        if not self.state.dx_update_pending:
            self.state.dx_update_pending = True
            self.on_spot()
