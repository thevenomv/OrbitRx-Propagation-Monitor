"""CAT radio serial control."""

from __future__ import annotations

from tkinter import messagebox

from orbitrx import compat
from orbitrx.config import CAT_BAUD, CAT_PORT, CAT_TIMEOUT


def tune_radio(freq_mhz: str) -> None:
    try:
        freq_val = float(freq_mhz)
        messagebox.showinfo(
            "CAT Control",
            f"Tuning physical radio to {freq_mhz} MHz...\n(Ensure {CAT_PORT} is connected)",
        )
        if not compat.CAT_AVAILABLE:
            print(f"pyserial not available. Would have tuned to {freq_val} MHz")
            return
        freq_hz = int(freq_val * 1_000_000)
        cmd = f"FA{freq_hz:011d};".encode("ascii")
        with compat.serial.Serial(CAT_PORT, CAT_BAUD, timeout=CAT_TIMEOUT) as ser:
            ser.write(cmd)
        print(f"Sent CAT command: {cmd}")
    except Exception as exc:
        print(f"CAT Control Error: {exc}")
