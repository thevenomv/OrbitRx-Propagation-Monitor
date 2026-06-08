from __future__ import annotations

import time
from typing import Callable

try:
    from win10toast import ToastNotifier
    TOAST_AVAILABLE = True
except ImportError:
    ToastNotifier = None
    TOAST_AVAILABLE = False

try:
    import platform
    if platform.system() == "Windows":
        import winsound
    else:
        winsound = None
except Exception:
    winsound = None


def show_toast(title: str, message: str) -> None:
    if not TOAST_AVAILABLE:
        return
    try:
        ToastNotifier().show_toast(title, message, duration=5, threaded=True)
    except Exception:
        pass


def check_alarms(
    kp: float,
    muf: float | None,
    excellent_kp: float,
    excellent_muf: float,
    storm_kp: float,
    excellent_last: float | None,
    storm_last: float | None,
    on_excellent: Callable[[], None],
    on_storm: Callable[[], None],
    cooldown: float = 3600.0,
) -> tuple[float | None, float | None]:
    now = time.time()
    if muf is not None and muf >= excellent_muf and kp <= excellent_kp:
        if excellent_last is None or now - excellent_last > cooldown:
            excellent_last = now
            if winsound:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            show_toast("OrbitRx", f"Excellent conditions! Kp {kp}, MUF {muf} MHz")
            on_excellent()
    if kp >= storm_kp:
        if storm_last is None or now - storm_last > cooldown:
            storm_last = now
            if winsound:
                winsound.MessageBeep(winsound.MB_ICONHAND)
            show_toast("OrbitRx", f"Storm warning! Kp {kp}")
            on_storm()
    return excellent_last, storm_last
