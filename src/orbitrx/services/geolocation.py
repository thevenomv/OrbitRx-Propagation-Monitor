"""IP-based geolocation."""

from __future__ import annotations

import json
import urllib.request

from orbitrx.models.context import AppContext


def update_user_location(ctx: AppContext) -> None:
    try:
        url = "https://ipinfo.io/json"
        with urllib.request.urlopen(url, timeout=5) as response:
            info = json.loads(response.read())
        if "loc" in info:
            loc = info["loc"].split(",")
            ctx.state.user_lat = float(loc[0])
            ctx.state.user_lon = float(loc[1])
            if ctx.ui.lbl_location:
                ctx.ui.lbl_location.config(
                    text=f"You: {ctx.state.user_lat:.3f}°, {ctx.state.user_lon:.3f}°",
                )
        elif ctx.ui.lbl_location:
            ctx.ui.lbl_location.config(text="You: location unknown")
    except Exception as exc:
        ctx.state.user_lat = None
        ctx.state.user_lon = None
        if ctx.ui.lbl_location:
            ctx.ui.lbl_location.config(text="You: location unknown")
        print("Location API failed:", exc)
