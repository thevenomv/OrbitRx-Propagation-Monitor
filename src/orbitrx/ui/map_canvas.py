"""Greyline map rendering on Tkinter canvas."""

from __future__ import annotations

import datetime
import math

from PIL import Image, ImageDraw, ImageTk

from orbitrx.config import MAP_CANVAS_HEIGHT, MAP_CANVAS_WIDTH
from orbitrx.models.context import AppContext


def draw_greyline(ctx: AppContext) -> None:
    state = ctx.state
    canvas = ctx.ui.canvas
    width = MAP_CANVAS_WIDTH
    height = MAP_CANVAS_HEIGHT

    canvas.delete("all")

    if state.original_map is not None:
        base = state.original_map.copy().convert("RGBA")
    else:
        base = Image.new("RGBA", (width, height), (16, 24, 32, 255))

    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=state.slider_offset_hours)
    day_of_year = now.timetuple().tm_yday
    hour_utc = now.hour + now.minute / 60.0

    declination_deg = -23.44 * math.cos(math.radians((360 / 365.25) * (day_of_year + 10)))
    declination_rad = math.radians(declination_deg)
    sun_lon_deg = 180 - (hour_utc * 15)
    sun_lon_rad = math.radians(sun_lon_deg)

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    for x in range(width):
        lon_deg = (x / width) * 360 - 180
        angle_diff = (lon_deg - sun_lon_deg + 180) % 360 - 180
        if abs(angle_diff) > 90:
            od.line([(x, 0), (x, height - 1)], fill=(0, 0, 0, 120))

    term_points = []
    for x in range(width + 1):
        lon_deg = (x / width) * 360 - 180
        lon_rad = math.radians(lon_deg)
        tan_dec = math.tan(declination_rad)
        if abs(tan_dec) < 0.0001:
            tan_dec = 0.0001
        tan_lat = -math.cos(lon_rad - sun_lon_rad) / tan_dec
        lat_deg = math.degrees(math.atan(tan_lat))
        y = int(height / 2 - (lat_deg / 90) * (height / 2))
        y = max(0, min(height - 1, y))
        term_points.append((x, y))

    if len(term_points) > 1:
        od.line(term_points, fill=(255, 80, 0, 240), width=3)

    combined = Image.alpha_composite(base, overlay).convert("RGB")
    state.current_map_photo = ImageTk.PhotoImage(combined)
    canvas.create_image(width / 2, height / 2, image=state.current_map_photo)

    time_text = f"Greyline @ {now.strftime('%H:%M UTC')}"
    if state.slider_offset_hours:
        time_text += f"  (+{state.slider_offset_hours:.1f}h)"
    canvas.create_rectangle(5, 5, 310, 30, fill="#0B1220", outline="")
    canvas.create_text(10, 8, anchor="nw", text=time_text, fill="white", font=("Arial", 11))

    def world_to_canvas(lat: float, lon: float) -> tuple[float, float]:
        cx = ((lon + 180) / 360) * width
        cy = (height / 2) - ((lat / 90) * (height / 2))
        return cx, cy

    state.latest_dx_canvas_points = []

    sun_lon_wrapped = (sun_lon_deg + 180) % 360 - 180
    sun_x, sun_y = world_to_canvas(declination_deg, sun_lon_wrapped)
    canvas.create_oval(sun_x - 12, sun_y - 12, sun_x + 12, sun_y + 12, fill="#FFEB3B", outline="#FFA000", width=2)
    canvas.create_oval(sun_x - 20, sun_y - 20, sun_x + 20, sun_y + 20, outline="#FFE082", dash=(2, 2))
    canvas.create_text(sun_x, sun_y, text="\u2600", font=("Arial", 10), fill="#FFA000")

    if state.user_lat is not None and state.user_lon is not None:
        px, py = world_to_canvas(state.user_lat, state.user_lon)
        if 0 <= px <= width and 0 <= py <= height:
            canvas.create_oval(px - 7, py - 7, px + 7, py + 7, fill="#00FF00", outline="white", width=2)
            canvas.create_rectangle(px + 10, py - 18, px + 44, py - 4, fill="#0B1220", outline="")
            canvas.create_text(px + 12, py - 10, text="You", fill="white", font=("Arial", 11, "bold"), anchor="w")

    for spot in state.latest_dx_spots:
        from_name = spot.get("from")
        to_name = spot.get("to")
        fpos = ctx.dx_coordinates.get(from_name)
        tpos = ctx.dx_coordinates.get(to_name)
        if not fpos or not tpos:
            continue
        fx, fy = world_to_canvas(fpos[0], fpos[1])
        tx, ty = world_to_canvas(tpos[0], tpos[1])

        if abs(fx - tx) < width * 0.6:
            mx, my = (fx + tx) / 2, (fy + ty) / 2
            curve_y = my - math.hypot(tx - fx, ty - fy) * 0.15
            canvas.create_line(fx, fy, mx, curve_y, tx, ty, smooth=True, fill="#00FFFF", width=2, dash=(5, 3))

        canvas.create_polygon(
            fx, fy - 7, fx + 7, fy, fx, fy + 7, fx - 7, fy,
            fill="#FF9800", outline="#FFFFFF", width=1,
        )
        canvas.create_text(fx, fy - 13, text=from_name, fill="#FFC44D", font=("Arial", 8, "bold"), anchor="s")

        canvas.create_oval(tx - 6, ty - 6, tx + 6, ty + 6, fill="#FF00FF", outline="#FFFFFF", width=1)
        canvas.create_text(tx + 9, ty - 10, text=to_name, fill="#FFFF66", font=("Arial", 8, "bold"), anchor="w")

        canvas.create_text(
            (fx + tx) / 2, (fy + ty) / 2 - 14,
            text=f"{spot.get('freq', '?')} MHz",
            fill="#00FFCC", font=("Arial", 8), anchor="center",
        )

        state.latest_dx_canvas_points.append((tx, ty, spot.get("freq", "14.000")))
