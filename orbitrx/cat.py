from __future__ import annotations

import datetime
from pathlib import Path
from typing import Callable

from orbitrx.config import AppConfig
from orbitrx.utils import normalize_freq_mhz

try:
    import serial
    CAT_AVAILABLE = True
except ImportError:
    serial = None
    CAT_AVAILABLE = False

CAT_LOG = Path("cat_log.txt")


def _kenwood_cmd(freq_hz: int) -> bytes:
    return f"FA{freq_hz:011d};".encode("ascii")


def _icom_cmd(freq_hz: int) -> bytes:
    # CI-V set freq VFO A — simplified; many Icom rigs accept Kenwood-style via emulation
    return _kenwood_cmd(freq_hz)


def _yaesu_cmd(freq_hz: int) -> bytes:
    return f"FA{freq_hz:08d};".encode("ascii")


RIG_PROFILES = {
    "kenwood": _kenwood_cmd,
    "icom": _icom_cmd,
    "yaesu": _yaesu_cmd,
}


class CatController:
    def __init__(self, cfg: AppConfig) -> None:
        self.cfg = cfg
        self._ser = None

    def list_ports(self) -> list[str]:
        if not CAT_AVAILABLE:
            return []
        try:
            from serial.tools import list_ports
            return [p.device for p in list_ports.comports()]
        except Exception:
            return []

    def _log(self, msg: str) -> None:
        with open(CAT_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now(datetime.timezone.utc).isoformat()} {msg}\n")

    def connect(self) -> bool:
        if not CAT_AVAILABLE:
            return False
        try:
            if self._ser and self._ser.is_open:
                return True
            self._ser = serial.Serial(
                self.cfg.get("cat_port", "COM3"),
                int(self.cfg.get("cat_baud", 9600)),
                timeout=float(self.cfg.get("cat_timeout", 0.5)),
            )
            self._log(f"CONNECTED {self.cfg.get('cat_port')}")
            return True
        except Exception as e:
            self._log(f"CONNECT_FAIL {e}")
            return False

    def disconnect(self) -> None:
        if self._ser and self._ser.is_open:
            self._ser.close()
            self._log("DISCONNECTED")

    def tune(
        self,
        freq_mhz: float | str,
        confirm: Callable[[str], bool] | None = None,
    ) -> str:
        freq_val = normalize_freq_mhz(freq_mhz)
        msg = f"Tuning to {freq_val} MHz"
        if self.cfg.get("cat_confirm_before_tune") and confirm and not confirm(msg):
            return "cancelled"
        if not CAT_AVAILABLE:
            self._log(f"WOULD_TUNE {freq_val}")
            return "pyserial not installed"
        freq_hz = int(freq_val * 1_000_000)
        profile = self.cfg.get("cat_rig_profile", "kenwood")
        builder = RIG_PROFILES.get(profile, _kenwood_cmd)
        cmd = builder(freq_hz)
        try:
            if not self.connect():
                raise RuntimeError("Could not open serial port")
            self._ser.write(cmd)
            self._log(f"TUNE {freq_val} profile={profile} cmd={cmd!r}")
            return f"Sent CAT: {freq_val} MHz"
        except Exception as e:
            self._log(f"TUNE_FAIL {e}")
            return str(e)
