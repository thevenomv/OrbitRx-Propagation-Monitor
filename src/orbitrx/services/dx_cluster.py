"""Live DX cluster telnet client and callsign geocoding."""

from __future__ import annotations

import random
import socket
import threading
import time
from typing import Callable

from orbitrx.config import (
    DX_CLUSTER_HOST,
    DX_CLUSTER_PORT,
    DX_SPOT_TTL_SECONDS,
    DX_UI_THROTTLE_MS,
    PREFIX_MAP,
)
from orbitrx.models.context import AppContext
from orbitrx.services import logging as log_service


def parse_dx_line(line: str) -> dict | None:
    """Parse a DX cluster line into spotter, frequency, and target station."""
    line = line.strip()
    if not line.startswith("DX de"):
        return None
    parts = line.split()
    if len(parts) < 5:
        return None
    return {
        "from": parts[2].strip(":"),
        "freq": parts[3],
        "to": parts[4],
    }


def estimate_location(callsign: str) -> tuple[float, float]:
    call = callsign.upper().strip()
    for prefix in sorted(PREFIX_MAP.keys(), key=len, reverse=True):
        if call.startswith(prefix):
            lat, lon = PREFIX_MAP[prefix]
            return (lat + random.uniform(-3, 3), lon + random.uniform(-3, 3))

    land_boxes = [
        (30, 50, -120, -70),
        (-30, 10, -80, -50),
        (40, 60, -10, 30),
        (-20, 30, 10, 40),
        (30, 60, 60, 120),
        (-30, -15, 115, 145),
    ]
    box = random.choice(land_boxes)
    return (random.uniform(box[0], box[1]), random.uniform(box[2], box[3]))


def prune_expired_spots(ctx: AppContext) -> None:
    current_time = time.time()
    ctx.state.latest_dx_spots = [
        s for s in ctx.state.latest_dx_spots
        if current_time - s.get("time", current_time) < DX_SPOT_TTL_SECONDS
    ]


def update_dx_ui(ctx: AppContext, draw_greyline: Callable[[], None]) -> None:
    ctx.state.dx_update_pending = False
    prune_expired_spots(ctx)

    if ctx.state.latest_dx_spots:
        dx_text = " | ".join(
            f"{s['from']}→{s['to']} {s['freq']} MHz" for s in ctx.state.latest_dx_spots[:2]
        )
        ctx.ui.lbl_dx.config(text="Live DX: " + dx_text)
    else:
        ctx.ui.lbl_dx.config(text="Live DX: --")
    draw_greyline()


def dx_cluster_task(ctx: AppContext, draw_greyline: Callable[[], None]) -> None:
    while ctx.state.cluster_active:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((DX_CLUSTER_HOST, DX_CLUSTER_PORT))

            time.sleep(1.5)
            try:
                sock.recv(2048)
            except socket.timeout:
                pass
            sock.sendall(b"W1AW-9\r\n")
            sock.settimeout(None)

            buffer = ""
            while ctx.state.cluster_active:
                data = sock.recv(1024)
                if not data:
                    break
                buffer += data.decode("ascii", errors="ignore")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    parsed = parse_dx_line(line)
                    if not parsed:
                        continue

                    spotter = parsed["from"]
                    freq = parsed["freq"]
                    to_station = parsed["to"]
                    spot = {"from": spotter, "to": to_station, "freq": freq, "time": time.time()}

                    log_service.log_dx_spot(spotter, to_station, freq)

                    if spotter not in ctx.dx_coordinates:
                        ctx.dx_coordinates[spotter] = estimate_location(spotter)
                    if to_station not in ctx.dx_coordinates:
                        ctx.dx_coordinates[to_station] = estimate_location(to_station)

                    ctx.state.latest_dx_spots.insert(0, spot)
                    ctx.state.latest_dx_spots = ctx.state.latest_dx_spots[:50]

                    if not ctx.state.dx_update_pending:
                        ctx.state.dx_update_pending = True
                        ctx.ui.window.after(
                            DX_UI_THROTTLE_MS,
                            lambda: update_dx_ui(ctx, draw_greyline),
                        )
        except Exception as exc:
            print(f"DX Cluster disconnected ({DX_CLUSTER_HOST}:{DX_CLUSTER_PORT}): {exc}")
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
        if not ctx.state.cluster_active:
            break
        time.sleep(30)


def start_dx_cluster(ctx: AppContext, draw_greyline: Callable[[], None]) -> None:
    if ctx.state.cluster_active:
        return
    ctx.state.cluster_active = True
    thread = threading.Thread(
        target=dx_cluster_task,
        args=(ctx, draw_greyline),
        daemon=True,
    )
    thread.start()
