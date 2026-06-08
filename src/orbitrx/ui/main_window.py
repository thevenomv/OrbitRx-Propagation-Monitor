"""Main Tkinter window layout and event wiring."""

from __future__ import annotations

import calendar
import datetime
import time

import tkinter as tk
from PIL import Image, ImageTk

from orbitrx import compat
from orbitrx.config import (
    APP_TITLE,
    AUTO_REFRESH_MS,
    DEMO_SPOTS,
    DX_COORDINATES,
    MAP_CANVAS_HEIGHT,
    MAP_CANVAS_WIDTH,
    WINDOW_GEOMETRY,
)
from orbitrx.models.context import AppContext, UIRefs
from orbitrx.paths import ensure_map_file
from orbitrx.services import geolocation, logging as log_service
from orbitrx.services.cat import tune_radio
from orbitrx.services.dx_cluster import estimate_location, prune_expired_spots, start_dx_cluster, update_dx_ui
from orbitrx.services.noaa import get_space_weather
from orbitrx.ui.dialogs import export_dx_log, show_user_guide
from orbitrx.ui.history import plot_history, view_history
from orbitrx.ui.map_canvas import draw_greyline


def build_ui(ctx: AppContext) -> None:
    """Construct the full application window and start background services."""
    if compat.USE_CUSTOMTK:
        window = compat.ctk.CTk()
        window.configure(padx=16, pady=16)
    else:
        window = tk.Tk()
        window.configure(padx=16, pady=16, bg="#0B1220")

    window.title(APP_TITLE)
    window.geometry(WINDOW_GEOMETRY)

    ctx.ui.window = window
    ctx.dx_coordinates.update(DX_COORDINATES)

    _load_map(ctx)
    _build_layout(ctx)
    _seed_demo_spots(ctx)
    _wire_services(ctx)


def _load_map(ctx: AppContext) -> None:
    try:
        map_path = ensure_map_file()
        ctx.state.original_map = Image.open(map_path)
        ctx.state.original_map = ctx.state.original_map.resize(
            (MAP_CANVAS_WIDTH, MAP_CANVAS_HEIGHT), Image.Resampling.LANCZOS,
        )
        ImageTk.PhotoImage(ctx.state.original_map)
    except Exception as exc:
        ctx.state.original_map = None
        print(f"Could not load world map: {exc}")


def _build_layout(ctx: AppContext) -> None:
    window = ctx.ui.window
    ui = ctx.ui

    frame_title = tk.Frame(window, bg="#0B1220")
    frame_title.pack(fill="x", pady=(0, 12))
    tk.Label(
        frame_title, text=APP_TITLE, font=("Segoe UI", 20, "bold"), bg="#0B1220", fg="#E7EBFF",
    ).pack()

    tk.Frame(window, height=2, bg="#1E2A40", bd=0).pack(fill="x", pady=(0, 12))

    frame_content = tk.Frame(window, bg="#0B1220")
    frame_content.pack(fill="both", expand=True, pady=(0, 12))

    panel_map = tk.Frame(frame_content, bg="#0E162B", bd=1, relief="solid")
    panel_map.pack(side="left", fill="both", expand=True, padx=(0, 12))

    ui.canvas = tk.Canvas(panel_map, width=MAP_CANVAS_WIDTH, height=MAP_CANVAS_HEIGHT, bg="#101820", highlightthickness=0)
    ui.canvas.pack(padx=8, pady=8)

    def on_map_click(event: tk.Event) -> None:
        for tx, ty, freq in ctx.state.latest_dx_canvas_points:
            if abs(event.x - tx) < 15 and abs(event.y - ty) < 15:
                tune_radio(freq)
                break

    ui.canvas.bind("<Button-1>", on_map_click)

    tk.Label(
        panel_map,
        text="Orange line: Greyline (day-night boundary) - optimal for HF radio propagation",
        font=("Segoe UI", 9), bg="#0E162B", fg="#CCCCCC", anchor="w",
    ).pack(fill="x", padx=8, pady=(0, 10))

    frame_slider = tk.Frame(panel_map, bg="#0E162B")
    frame_slider.pack(fill="x", padx=8, pady=(0, 8))
    ui.lbl_slider = tk.Label(
        frame_slider, text="Time Travel: +0.0 hrs", bg="#0E162B", fg="#B3E5FC", font=("Segoe UI", 10, "bold"),
    )
    ui.lbl_slider.pack(side="left")

    def on_slider(val: str) -> None:
        ctx.state.slider_offset_hours = float(val)
        ui.lbl_slider.config(text=f"Time Travel: +{ctx.state.slider_offset_hours:.1f} hrs")
        draw_greyline(ctx)

    tk.Scale(
        frame_slider, from_=0, to=24, resolution=0.5, orient="horizontal", command=on_slider,
        bg="#0E162B", fg="#00A8FF", highlightthickness=0,
    ).pack(side="left", fill="x", expand=True, padx=10)

    panel_stats = tk.Frame(frame_content, bg="#0E162B", bd=0, width=300)
    panel_stats.pack(side="right", fill="both", padx=0, pady=0)
    panel_stats.pack_propagate(False)

    card_weather = tk.Frame(panel_stats, bg="#131D35", bd=1, relief="solid")
    card_weather.pack(fill="x", padx=10, pady=(4, 8))
    card_local = tk.Frame(panel_stats, bg="#131D35", bd=1, relief="solid")
    card_local.pack(fill="x", padx=10, pady=(0, 8))
    card_dx = tk.Frame(panel_stats, bg="#131D35", bd=1, relief="solid")
    card_dx.pack(fill="x", padx=10, pady=(0, 8))

    ui.lbl_kp = tk.Label(card_weather, text="Current Kp Index: --", font=("Segoe UI", 15, "bold"), bg="#131D35", fg="#81D4FA", anchor="w")
    ui.lbl_kp.pack(fill="x", padx=10, pady=(8, 3))
    ui.lbl_kp_forecast = tk.Label(card_weather, text="Kp Forecast: --", font=("Segoe UI", 11), bg="#131D35", fg="#F5F5A5", anchor="w")
    ui.lbl_kp_forecast.pack(fill="x", padx=10, pady=2)
    ui.lbl_solar = tk.Label(card_weather, text="Solar Flux: --", font=("Segoe UI", 13), bg="#131D35", fg="#BBDEFB", anchor="w")
    ui.lbl_solar.pack(fill="x", padx=10, pady=2)
    ui.lbl_sunspot = tk.Label(card_weather, text="Sunspot Number: --", font=("Segoe UI", 12), bg="#131D35", fg="#CDDDFE", anchor="w")
    ui.lbl_sunspot.pack(fill="x", padx=10, pady=2)
    ui.lbl_time = tk.Label(card_weather, text="Last NOAA Update: --", font=("Segoe UI", 10, "italic"), bg="#131D35", fg="#B0BEC5", anchor="w")
    ui.lbl_time.pack(fill="x", padx=10, pady=(2, 8))

    ui.lbl_bands = tk.Label(card_local, text="Band Conditions: --", font=("Segoe UI", 12, "bold"), bg="#131D35", fg="#96CEB4", anchor="w")
    ui.lbl_bands.pack(anchor="w", padx=10, pady=(8, 6))
    ui.lbl_muf = tk.Label(card_local, text="MUF est: --", font=("Segoe UI", 11), bg="#131D35", fg="#DFE7FF", anchor="w")
    ui.lbl_muf.pack(fill="x", padx=10, pady=2)
    ui.lbl_sunrise = tk.Label(card_local, text="Sunrise (UTC): --", font=("Segoe UI", 10), bg="#131D35", fg="#CDDDFE", anchor="w")
    ui.lbl_sunrise.pack(fill="x", padx=10, pady=1)
    ui.lbl_sunset = tk.Label(card_local, text="Sunset (UTC): --", font=("Segoe UI", 10), bg="#131D35", fg="#CDDDFE", anchor="w")
    ui.lbl_sunset.pack(fill="x", padx=10, pady=1)
    ui.lbl_alerts = tk.Label(card_local, text="Alerts: --", font=("Segoe UI", 10), bg="#131D35", fg="#FFA0A0", anchor="w")
    ui.lbl_alerts.pack(fill="x", padx=10, pady=2)
    ui.lbl_location = tk.Label(card_local, text="You: locating...", font=("Segoe UI", 10), fg="#E0E8FF", bg="#131D35", anchor="w")
    ui.lbl_location.pack(fill="x", padx=10, pady=(2, 8))
    ui.lbl_status = tk.Label(
        card_local, text="Click refresh to load live satellite data.",
        font=("Segoe UI", 11, "italic"), bg="#131D35", fg="white", anchor="w",
    )
    ui.lbl_status.pack(fill="x", padx=10, pady=5)

    ui.lbl_solar_forecast = tk.Label(card_dx, text="27-Day Forecast: --", font=("Segoe UI", 10), bg="#131D35", fg="#B3E5FC", anchor="w")
    ui.lbl_solar_forecast.pack(fill="x", padx=10, pady=(8, 2))
    ui.lbl_contest = tk.Label(card_dx, text="Next Contest: --", font=("Segoe UI", 10), bg="#131D35", fg="#FFE082", anchor="w")
    ui.lbl_contest.pack(fill="x", padx=10, pady=2)
    ui.lbl_dx = tk.Label(card_dx, text="Recent DX: --", font=("Segoe UI", 10), bg="#131D35", fg="#C8E6C9", anchor="w")
    ui.lbl_dx.pack(fill="x", padx=10, pady=(2, 8))

    tk.Label(card_dx, text="History lookup (Date):", font=("Segoe UI", 10, "bold"), bg="#131D35", fg="#FFD660", anchor="w").pack(fill="x", padx=10, pady=(6, 2))

    ui.selected_history_date = tk.StringVar(
        value=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
    )
    frame_cal_entry = tk.Frame(card_dx, bg="#131D35")
    frame_cal_entry.pack(fill="x", padx=10, pady=(0, 4))
    tk.Label(
        frame_cal_entry, textvariable=ui.selected_history_date, font=("Segoe UI", 10, "bold"),
        bg="#131D35", fg="#00E5FF", anchor="w", width=12,
    ).pack(side="left", padx=(0, 6))

    def open_calendar_picker() -> None:
        cal_win = tk.Toplevel(window)
        cal_win.title("Pick a date")
        cal_win.configure(bg="#0B1220")
        cal_win.resizable(False, False)
        cal_win.attributes("-topmost", True)

        try:
            current = datetime.datetime.strptime(ui.selected_history_date.get(), "%Y-%m-%d")
        except Exception:
            current = datetime.datetime.now(datetime.timezone.utc)

        nav = {"year": current.year, "month": current.month}

        def rebuild() -> None:
            for w in frame_body.winfo_children():
                w.destroy()
            cal_matrix = calendar.monthcalendar(nav["year"], nav["month"])
            month_name = datetime.date(nav["year"], nav["month"], 1).strftime("%B %Y")
            lbl_month.config(text=month_name)
            for day_name in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]:
                tk.Label(frame_body, text=day_name, width=4, bg="#0E162B", fg="#90A4AE", font=("Segoe UI", 9, "bold")).pack(side="top")
            for row in cal_matrix:
                row_frame = tk.Frame(frame_body, bg="#0B1220")
                row_frame.pack()
                for day in row:
                    txt = str(day) if day != 0 else ""
                    is_today = (
                        day == datetime.datetime.now().day
                        and nav["month"] == datetime.datetime.now().month
                        and nav["year"] == datetime.datetime.now().year
                    )
                    is_sel = (
                        day != 0 and day == current.day
                        and nav["month"] == current.month and nav["year"] == current.year
                    )
                    bg_col = "#006AFF" if is_sel else ("#1E3A5F" if is_today else "#131D35")
                    fg_col = "white" if is_sel or is_today else "#CFD8DC"

                    def pick_day(d: int = day) -> None:
                        ui.selected_history_date.set(f"{nav['year']:04d}-{nav['month']:02d}-{d:02d}")
                        cal_win.destroy()

                    tk.Button(
                        row_frame, text=txt, width=3, bg=bg_col, fg=fg_col, relief="flat",
                        font=("Segoe UI", 9), activebackground="#0040CC",
                        command=pick_day if day != 0 else None,
                    ).pack(side="left", padx=1, pady=1)

        def prev_month() -> None:
            if nav["month"] == 1:
                nav["month"] = 12
                nav["year"] -= 1
            else:
                nav["month"] -= 1
            rebuild()

        def next_month() -> None:
            if nav["month"] == 12:
                nav["month"] = 1
                nav["year"] += 1
            else:
                nav["month"] += 1
            rebuild()

        frame_nav = tk.Frame(cal_win, bg="#0B1220")
        frame_nav.pack(fill="x", padx=8, pady=(8, 4))
        tk.Button(frame_nav, text="◀", command=prev_month, bg="#0E162B", fg="white", font=("Segoe UI", 11), relief="flat", width=3).pack(side="left")
        lbl_month = tk.Label(frame_nav, text="", bg="#0B1220", fg="#81D4FA", font=("Segoe UI", 11, "bold"), width=16)
        lbl_month.pack(side="left", expand=True)
        tk.Button(frame_nav, text="▶", command=next_month, bg="#0E162B", fg="white", font=("Segoe UI", 11), relief="flat", width=3).pack(side="right")

        frame_body = tk.Frame(cal_win, bg="#0B1220")
        frame_body.pack(padx=8, pady=(0, 8))
        rebuild()

    tk.Button(
        frame_cal_entry, text="📅 Pick", command=open_calendar_picker,
        bg="#006AFF", fg="white", font=("Segoe UI", 9, "bold"), relief="raised", bd=1,
    ).pack(side="left")

    class _DateVar:
        def get(self) -> str:
            return ui.selected_history_date.get()

    entry_history = _DateVar()

    tk.Button(
        card_dx, text="View History",
        command=lambda: view_history(ctx, entry_history.get().strip()),
        bg="#FFB300", fg="black", font=("Segoe UI", 10, "bold"), relief="raised", bd=2,
    ).pack(padx=10, pady=(0, 4))
    tk.Button(
        card_dx, text="Plot History",
        command=lambda: plot_history(ctx, entry_history.get().strip()),
        bg="#00C853", fg="white", font=("Segoe UI", 10, "bold"), relief="raised", bd=2,
    ).pack(padx=10, pady=(0, 8))

    panel_buttons = tk.Frame(window, bg="#0B1220")
    panel_buttons.pack(fill="x")

    tk.Button(
        panel_buttons, text="Refresh Location", command=lambda: geolocation.update_user_location(ctx),
        bg="#006AFF", fg="white", font=("Segoe UI", 10, "bold"), relief="raised", bd=2,
    ).pack(side="left", padx=4)

    ui.btn_refresh = tk.Button(
        panel_buttons, text="Refresh Space Weather",
        command=lambda: _auto_refresh(ctx),
        bg="#00A8FF", fg="white", font=("Segoe UI", 10, "bold"), relief="raised", bd=2,
    )
    ui.btn_refresh.pack(side="left", padx=4)

    tk.Button(
        panel_buttons, text="Export JSON", command=lambda: log_service.export_json(ctx),
        bg="#9C27B0", fg="white", font=("Segoe UI", 10, "bold"), relief="raised", bd=2,
    ).pack(side="left", padx=4)
    tk.Button(
        panel_buttons, text="Export DX Log", command=export_dx_log,
        bg="#FF5722", fg="white", font=("Segoe UI", 10, "bold"), relief="raised", bd=2,
    ).pack(side="left", padx=4)
    tk.Button(
        panel_buttons, text="Help & Guide", command=lambda: show_user_guide(ctx),
        bg="#FF9C27", fg="white", font=("Segoe UI", 10, "bold"), relief="raised", bd=2,
    ).pack(side="left", padx=4)


def _seed_demo_spots(ctx: AppContext) -> None:
    now = time.time()
    for spot in DEMO_SPOTS:
        entry = {**spot, "time": now}
        if entry["from"] not in ctx.dx_coordinates:
            ctx.dx_coordinates[entry["from"]] = estimate_location(entry["from"])
        if entry["to"] not in ctx.dx_coordinates:
            ctx.dx_coordinates[entry["to"]] = estimate_location(entry["to"])
        ctx.state.latest_dx_spots.append(entry)


def _auto_refresh(ctx: AppContext) -> None:
    prune_expired_spots(ctx)
    geolocation.update_user_location(ctx)
    get_space_weather(ctx)
    update_dx_ui(ctx, lambda: draw_greyline(ctx))
    ctx.ui.window.after(AUTO_REFRESH_MS, lambda: _auto_refresh(ctx))


def _wire_services(ctx: AppContext) -> None:
    log_service.init_log_file()
    log_service.init_dx_log_file()
    draw_fn = lambda: draw_greyline(ctx)
    start_dx_cluster(ctx, draw_fn)
    _auto_refresh(ctx)
