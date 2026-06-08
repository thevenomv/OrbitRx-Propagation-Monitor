from __future__ import annotations

import datetime
import json
import os
import threading
import time
import tkinter as tk
import urllib.request
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

from PIL import Image, ImageTk

from orbitrx.alerts import check_alarms
from orbitrx.cat import CatController
from orbitrx.config import AppConfig
from orbitrx.contests import get_next_contest
from orbitrx.dx import DxClusterService
from orbitrx.logger import setup_logging
from orbitrx.map_renderer import MapLayers, MapRenderer
from orbitrx.propagation import (
    band_grid,
    bands_summary,
    estimate_muf,
    flux_trend_arrow,
    voacap_lite_path_muf,
)
from orbitrx.state import AppState
from orbitrx.storage import DataStore
from orbitrx.utils import local_time_at_lon, parse_history_query, sun_times
from orbitrx.weather import fetch_space_weather_data

USE_CTK = False
try:
    import customtkinter as ctk
    ctk.set_appearance_mode("dark")
    USE_CTK = True
except ImportError:
    ctk = None

PLOT_AVAILABLE = False
try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    PLOT_AVAILABLE = True
except ImportError:
    plt = None

try:
    import platform
    if platform.system() == "Windows":
        import winsound
    else:
        winsound = None
except Exception:
    winsound = None

BG = "#0B1220"
CARD = "#131D35"
PANEL = "#0E162B"


def _widget(parent, cls, ctk_cls, **kw):
    if USE_CTK and ctk_cls:
        return ctk_cls(parent, **kw)
    return cls(parent, **{k: v for k, v in kw.items() if k != "fg_color"})


class TkOrbitRxApplication:
    def __init__(self) -> None:
        self.log = setup_logging()
        self.cfg = AppConfig().load()
        self.state = AppState()
        self.store = DataStore(log_max_mb=int(self.cfg.get("log_max_mb", 10)))
        self.map_renderer = MapRenderer(width=700, height=560)
        self.cat = CatController(self.cfg)
        self.original_map: Image.Image | None = None
        self.current_map_photo = None
        self._pan_start: tuple[float, float] | None = None
        self._build_window()
        self._build_ui()
        self._load_map()
        self._seed_demo()
        self._dx = DxClusterService(
            self.state, self.cfg,
            on_spot=lambda: self.root.after(500, self._update_dx_ui),
            on_status=self._set_cluster_status,
            on_band_alert=self._spot_sound_alert,
            store=self.store,
        )
        self._dx.start()
        self._schedule_refresh()

    def _build_window(self) -> None:
        geom = self.cfg.get("window_geometry", "1300x700")
        theme = self.cfg.get("theme", "dark")
        if USE_CTK:
            if theme == "light":
                ctk.set_appearance_mode("light")
            self.root = ctk.CTk()
        else:
            self.root = tk.Tk()
            self.root.configure(bg=BG)
        self.root.title("OrbitRx Propagation Monitor v4")
        self.root.geometry(geom)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        try:
            self.root.bind("<Unmap>", self._on_minimize_tray)
        except Exception:
            pass

    def _build_ui(self) -> None:
        container = _widget(self.root, tk.Frame, ctk.CTkFrame if USE_CTK else None, fg_color=BG)
        if USE_CTK:
            container.pack(fill="both", expand=True, padx=12, pady=12)
        else:
            container.configure(bg=BG)
            container.pack(fill="both", expand=True, padx=12, pady=12)

        title = _widget(container, tk.Label, ctk.CTkLabel, text="OrbitRx Propagation Monitor",
                        font=("Segoe UI", 20, "bold"), text_color="#E7EBFF", fg_color=BG)
        if not USE_CTK:
            title.configure(bg=BG, fg="#E7EBFF")
        title.pack(fill="x", pady=(0, 8))

        content = _widget(container, tk.Frame, ctk.CTkFrame, fg_color=BG)
        if not USE_CTK:
            content.configure(bg=BG)
        content.pack(fill="both", expand=True)

        # Map panel
        self.panel_map = _widget(content, tk.Frame, ctk.CTkFrame, fg_color=PANEL)
        if not USE_CTK:
            self.panel_map.configure(bg=PANEL)
        self.panel_map.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.canvas = tk.Canvas(self.panel_map, width=700, height=560, bg="#101820", highlightthickness=0)
        self.canvas.pack(padx=8, pady=8)
        self.canvas.bind("<Button-1>", self._on_map_click)
        self.canvas.bind("<ButtonPress-3>", self._on_pan_start)
        self.canvas.bind("<B3-Motion>", self._on_pan_move)
        self.canvas.bind("<MouseWheel>", self._on_zoom)

        layer_frame = tk.Frame(self.panel_map, bg=PANEL)
        layer_frame.pack(fill="x", padx=8)
        self.layer_vars = {}
        for key, label in [("greyline", "Greyline"), ("night", "Night"), ("dx_arcs", "DX"), ("aurora", "Aurora")]:
            v = tk.BooleanVar(value=self.cfg.get("map_layers", {}).get(key, True))
            self.layer_vars[key] = v
            tk.Checkbutton(layer_frame, text=label, variable=v, command=self._draw_map,
                           bg=PANEL, fg="white", selectcolor=CARD).pack(side="left", padx=4)

        self.lbl_cluster = tk.Label(self.panel_map, text="Cluster: connecting", bg=PANEL, fg="#90CAF9", anchor="w")
        self.lbl_cluster.pack(fill="x", padx=8)
        self.lbl_click_time = tk.Label(self.panel_map, text="", bg=PANEL, fg="#B0BEC5", anchor="w")
        self.lbl_click_time.pack(fill="x", padx=8)

        slider_frame = tk.Frame(self.panel_map, bg=PANEL)
        slider_frame.pack(fill="x", padx=8, pady=6)
        self.lbl_slider = tk.Label(slider_frame, text="Time Travel: +0.0 hrs", bg=PANEL, fg="#B3E5FC")
        self.lbl_slider.pack(side="left")
        self.slider = tk.Scale(slider_frame, from_=0, to=24, resolution=0.5, orient="horizontal",
                               command=self._on_slider, bg=PANEL, fg="#00A8FF", highlightthickness=0)
        self.slider.pack(side="left", fill="x", expand=True, padx=8)

        # Stats panel
        self.panel_stats = tk.Frame(content, bg=PANEL, width=320)
        self.panel_stats.pack(side="right", fill="y")
        self.panel_stats.pack_propagate(False)

        self._labels: dict[str, tk.Label] = {}
        cards = [
            ("weather", ["kp", "kp_forecast", "solar", "sunspot", "a_index", "solar_wind", "time"]),
            ("local", ["bands", "band_grid", "muf", "path_muf", "sunrise", "sunset", "alerts", "location", "status"]),
            ("dx", ["solar_forecast", "contest", "dx"]),
        ]
        for card_name, keys in cards:
            card = tk.Frame(self.panel_stats, bg=CARD, bd=1, relief="solid")
            card.pack(fill="x", padx=8, pady=6)
            for key in keys:
                lbl = tk.Label(card, text=f"{key}: --", bg=CARD, fg="#CDDDFE", anchor="w", wraplength=280)
                lbl.pack(fill="x", padx=8, pady=2)
                self._labels[key] = lbl

        hist_frame = tk.Frame(self.panel_stats, bg=PANEL)
        hist_frame.pack(fill="x", padx=8)
        self.history_date = tk.StringVar(value=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"))
        tk.Entry(hist_frame, textvariable=self.history_date, width=12).pack(side="left")
        tk.Button(hist_frame, text="View", command=self._view_history).pack(side="left", padx=2)
        tk.Button(hist_frame, text="Plot", command=self._plot_history).pack(side="left", padx=2)

        btn_row = tk.Frame(container, bg=BG)
        if not USE_CTK:
            btn_row.configure(bg=BG)
        btn_row.pack(fill="x", pady=8)
        for text, cmd, color in [
            ("Refresh Location", self._refresh_location, "#006AFF"),
            ("Refresh Weather", self._fetch_weather, "#00A8FF"),
            ("Settings", self._open_settings, "#607D8B"),
            ("Export JSON", self._export_json, "#9C27B0"),
            ("Export DX CSV", self._export_dx, "#FF5722"),
            ("Help", self._show_help, "#FF9C27"),
        ]:
            tk.Button(btn_row, text=text, command=cmd, bg=color, fg="white").pack(side="left", padx=3)

    def _load_map(self) -> None:
        if not Path("world_map.jpg").exists():
            try:
                from generate_map import generate_world_map
                generate_world_map(1600, 800)
            except Exception as e:
                self.log.warning("Map download failed: %s", e)
        try:
            img = Image.open("world_map.jpg")
            self.map_renderer.set_base_map(img)
            self.original_map = img
        except Exception as e:
            self.log.warning("Map load failed: %s", e)
            self.original_map = None

    def _seed_demo(self) -> None:
        if not self.cfg.get("show_demo_spots", True):
            return
        demos = [
            {"from": "W5XYZ", "to": "PY2AB", "freq": 28.456, "time": time.time(), "demo": True},
            {"from": "VE3ABC", "to": "XU7AJ", "freq": 21.285, "time": time.time(), "demo": True},
        ]
        from orbitrx.utils import estimate_location
        with self.state.dx_lock:
            for s in demos:
                self.state.dx_coordinates.setdefault(s["from"], estimate_location(s["from"]))
                self.state.dx_coordinates.setdefault(s["to"], estimate_location(s["to"]))
            self.state.latest_dx_spots.extend(demos)
        self._draw_map()

    def _layers(self) -> MapLayers:
        ml = self.cfg.get("map_layers", {})
        return MapLayers(
            greyline=self.layer_vars["greyline"].get(),
            night=self.layer_vars["night"].get(),
            dx_arcs=self.layer_vars["dx_arcs"].get(),
            aurora=self.layer_vars["aurora"].get(),
        )

    def _draw_map(self) -> None:
        self.canvas.delete("all")
        with self.state.dx_lock:
            spots = list(self.state.latest_dx_spots)
            coords = dict(self.state.dx_coordinates)
        scene = self.map_renderer.build_scene(self.state, self._layers(), spots, coords)
        composite = self.map_renderer.pil_to_rgb_composite(scene)
        self.current_map_photo = ImageTk.PhotoImage(composite)
        self.state.latest_dx_canvas_points = []
        self.canvas.create_image(350, 280, image=self.current_map_photo)

        now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=self.state.slider_offset_hours)
        self.canvas.create_rectangle(5, 5, 340, 28, fill=BG, outline="")
        self.canvas.create_text(10, 8, anchor="nw",
                                text=f"Greyline @ {now.strftime('%H:%M UTC')} (+{self.state.slider_offset_hours:.1f}h)",
                                fill="white", font=("Arial", 10))

        for ann in scene.annotations:
            if ann.kind == "sun":
                sx, sy = ann.data["x"], ann.data["y"]
                self.canvas.create_oval(sx - 10, sy - 10, sx + 10, sy + 10, fill="#FFEB3B", outline="#FFA000")
            elif ann.kind == "user":
                ux, uy = ann.data["x"], ann.data["y"]
                self.canvas.create_oval(ux - 6, uy - 6, ux + 6, uy + 6, fill="#00FF00", outline="white")
                self.canvas.create_text(ux + 10, uy - 8, text="You", fill="white", anchor="w")
            elif ann.kind == "dx_spot":
                d = ann.data
                for seg in d.get("paths", []):
                    for i in range(len(seg) - 1):
                        self.canvas.create_line(seg[i][0], seg[i][1], seg[i + 1][0], seg[i + 1][1],
                                                fill="#00FFFF", width=2)
                tx, ty = d["tx"], d["ty"]
                self.state.latest_dx_canvas_points.append((tx, ty, float(d.get("freq", 14))))
                color = "#7B1FA2" if d.get("demo") else "#9C27B0"
                self.canvas.create_oval(tx - 6, ty - 6, tx + 6, ty + 6, fill=color, outline="white")
                self.canvas.create_text(tx + 8, ty - 12, text=f"{d.get('to')} ({d.get('age', 0)}s)",
                                        fill="#FFFF66", font=("Arial", 8), anchor="w")
                fx, fy = d["fx"], d["fy"]
                self.canvas.create_polygon(fx, fy - 5, fx + 5, fy, fx, fy + 5, fx - 5, fy,
                                           fill="#FF9800", outline="white")

    def _on_slider(self, val: str) -> None:
        self.state.slider_offset_hours = float(val)
        self.lbl_slider.config(text=f"Time Travel: +{self.state.slider_offset_hours:.1f} hrs")
        self._draw_map()

    def _on_map_click(self, event: tk.Event) -> None:
        for tx, ty, freq in self.state.latest_dx_canvas_points:
            if abs(event.x - tx) < 15 and abs(event.y - ty) < 15:
                self._tune_radio(freq)
                return
        lat, lon = self.map_renderer.map_to_world(event.x, event.y)
        lt = local_time_at_lon(lon)
        self.state.click_local_time = f"{lat:.1f}°, {lon:.1f}° → local ~{lt}"
        self.lbl_click_time.config(text=self.state.click_local_time)

    def _on_pan_start(self, event: tk.Event) -> None:
        self._pan_start = (event.x, event.y)

    def _on_pan_move(self, event: tk.Event) -> None:
        if self._pan_start:
            dx = event.x - self._pan_start[0]
            dy = event.y - self._pan_start[1]
            self.state.map_pan_x += dx
            self.state.map_pan_y += dy
            self._pan_start = (event.x, event.y)
            self._draw_map()

    def _on_zoom(self, event: tk.Event) -> None:
        delta = 1.1 if event.delta > 0 else 0.9
        self.state.map_zoom = max(0.5, min(3.0, self.state.map_zoom * delta))
        self._draw_map()

    def _tune_radio(self, freq: float) -> None:
        def confirm(msg: str) -> bool:
            return messagebox.askyesno("CAT Tune", msg)

        result = self.cat.tune(freq, confirm=confirm if self.cfg.get("cat_confirm_before_tune") else None)
        messagebox.showinfo("CAT", result)

    def _set_cluster_status(self, status: str) -> None:
        self.state.cluster_status = status
        colors = {"connected": "#4CAF50", "connecting": "#FFC107", "reconnecting": "#FF9800"}
        self.root.after(0, lambda: self.lbl_cluster.config(
            text=f"Cluster: {status}", fg=colors.get(status, "#90CAF9")
        ))

    def _spot_sound_alert(self, spot: dict[str, Any]) -> None:
        if self.cfg.get("dx_spot_sound_alert") and winsound:
            winsound.MessageBeep(winsound.MB_OK)

    def _refresh_location(self) -> None:
        def worker():
            try:
                r = urllib.request.urlopen("https://ipinfo.io/json", timeout=5)
                info = json.loads(r.read())
                self.root.after(0, lambda: self._apply_location(info))
            except Exception as e:
                self.root.after(0, lambda: self._labels["location"].config(text=f"You: unknown ({e})"))
        threading.Thread(target=worker, daemon=True).start()

    def _apply_location(self, info: dict[str, Any]) -> None:
        if "loc" in info:
            la, lo = info["loc"].split(",")
            self.state.user_lat = float(la)
            self.state.user_lon = float(lo)
            self._labels["location"].config(text=f"You: {self.state.user_lat:.3f}, {self.state.user_lon:.3f}")
            self._draw_map()

    def _fetch_weather(self) -> None:
        if self.state.weather_fetch_in_progress:
            return
        self.state.weather_fetch_in_progress = True

        def worker():
            try:
                data = fetch_space_weather_data()
                if self.cfg.get("offline_cache_enabled"):
                    self.store.save_weather_cache(data)
                self.root.after(0, lambda d=data: self._apply_weather(d))
            except Exception as e:
                cached = self.store.load_weather_cache() if self.cfg.get("offline_cache_enabled") else None
                if cached:
                    self.root.after(0, lambda d=cached: self._apply_weather(d, offline=True))
                else:
                    self.root.after(0, lambda: self._labels["status"].config(text=f"Error: {e}"))
            finally:
                self.root.after(0, self._weather_done)

        threading.Thread(target=worker, daemon=True).start()

    def _weather_done(self) -> None:
        self.state.weather_fetch_in_progress = False

    def _apply_weather(self, data: dict[str, Any], offline: bool = False) -> None:
        self.state.last_weather_cache = data
        self.state.kp_index = float(data.get("kp_index", 0))
        self.state.flux = data.get("flux")
        self.state.a_index = data.get("a_index")
        self.state.solar_wind_speed = data.get("solar_wind_speed")
        self.state.bz = data.get("bz")
        self.state.sunspot_observed = data.get("sunspot_observed")
        self.state.sunspot_predicted = data.get("sunspot_predicted")
        self.state.time_utc = data.get("time_utc", "--")
        self.state.kp_forecast = data.get("kp_forecast", "--")
        self.state.alerts = data.get("alerts", [])
        self.state.solar_forecast = data.get("solar_forecast", "--")

        trend = flux_trend_arrow(self.store.recent_flux(5))
        self.state.flux_trend = trend
        muf, luf = estimate_muf(self.state.flux, self.state.kp_index)
        self.state.muf, self.state.luf = muf, luf
        self.state.band_grid = band_grid(self.state.flux, self.state.kp_index)
        self.state.bands_summary = bands_summary(self.state.flux, self.state.kp_index)

        if self.state.user_lat and self.state.user_lon:
            tlat = self.cfg.get("target_dx_lat")
            tlon = self.cfg.get("target_dx_lon")
            if tlat is not None and tlon is not None:
                self.state.path_muf = voacap_lite_path_muf(
                    self.state.flux, self.state.kp_index,
                    self.state.user_lat, self.state.user_lon, float(tlat), float(tlon),
                )

        prefix = "[OFFLINE] " if offline else ""
        self._labels["kp"].config(text=f"{prefix}Kp: {self.state.kp_index}")
        self._labels["kp_forecast"].config(text=f"Kp Forecast: {self.state.kp_forecast}")
        flux_txt = f"{self.state.flux} {trend}" if self.state.flux else "--"
        self._labels["solar"].config(text=f"Solar Flux: {flux_txt}")
        ss = self.state.sunspot_observed or self.state.sunspot_predicted
        self._labels["sunspot"].config(text=f"Sunspot: {ss:.1f}" if ss else "Sunspot: --")
        self._labels["a_index"].config(text=f"A-index est: {self.state.a_index or '--'}")
        sw = self.state.solar_wind_speed
        bz = self.state.bz
        self._labels["solar_wind"].config(text=f"Solar wind: {sw or '--'} km/s  Bz: {bz or '--'} nT")
        self._labels["time"].config(text=f"NOAA: {self.state.time_utc} UTC")
        self._labels["bands"].config(text=f"Bands: {self.state.bands_summary}")
        grid = " | ".join(f"{k}:{v}" for k, v in self.state.band_grid.items())
        self._labels["band_grid"].config(text=f"Per-band: {grid}")
        self._labels["muf"].config(text=f"MUF: {muf or '--'} / LUF: {luf or '--'} MHz")
        self._labels["path_muf"].config(text=f"Path MUF: {self.state.path_muf or '--'} MHz")

        if self.state.user_lat and self.state.user_lon:
            sr, ss2 = sun_times(self.state.user_lat, self.state.user_lon, datetime.datetime.now(datetime.timezone.utc))
            if sr:
                self._labels["sunrise"].config(text=f"Sunrise UTC: {sr:.2f}")
                self._labels["sunset"].config(text=f"Sunset UTC: {ss2:.2f}")

        self._labels["alerts"].config(text="Alerts: " + (" | ".join(self.state.alerts) or "none"))
        self._labels["status"].config(text="Conditions updated" if not offline else "Offline cache")
        self._labels["solar_forecast"].config(text=f"27-Day: {self.state.solar_forecast}")
        nc = get_next_contest()
        self._labels["contest"].config(text=f"Next: {nc['name']}" if nc else "Next: none")

        self.store.log_propagation({
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "kp": self.state.kp_index, "flux": self.state.flux,
            "sunspot": ss, "muf": muf, "luf": luf,
            "band_cond": self.state.bands_summary,
            "lat": self.state.user_lat, "lon": self.state.user_lon,
            "a_index": self.state.a_index,
            "solar_wind": self.state.solar_wind_speed, "bz": self.state.bz,
        })
        self._draw_map()
        self._check_alarms()

    def _check_alarms(self) -> None:
        def excellent_popup():
            w = tk.Toplevel(self.root)
            w.title("Propagation Alarm")
            w.attributes("-topmost", True)
            tk.Label(w, text=f"EXCELLENT! Kp {self.state.kp_index} MUF {self.state.muf} MHz", padx=16, pady=16).pack()
            tk.Button(w, text="Tune 28.074 FT8", command=lambda: self._tune_radio(28.074)).pack(pady=4)
            tk.Button(w, text="Dismiss", command=w.destroy).pack()

        def storm_popup():
            w = tk.Toplevel(self.root)
            w.title("Storm Warning")
            w.attributes("-topmost", True)
            tk.Label(w, text=f"STORM Kp {self.state.kp_index}", fg="#FF6600", padx=16, pady=16).pack()
            tk.Button(w, text="Dismiss", command=w.destroy).pack()

        el, sl = check_alarms(
            self.state.kp_index, self.state.muf,
            float(self.cfg.get("alert_kp_threshold", 2)),
            float(self.cfg.get("alert_muf_threshold", 28)),
            float(self.cfg.get("storm_kp_threshold", 7)),
            self.state.alert_excellent_last, self.state.alert_storm_last,
            excellent_popup, storm_popup,
        )
        self.state.alert_excellent_last = el
        self.state.alert_storm_last = sl

    def _update_dx_ui(self) -> None:
        self.state.dx_update_pending = False
        self.state.prune_dx_spots()
        with self.state.dx_lock:
            visible = list(self.state.latest_dx_spots[:2])
        if visible:
            parts = []
            for s in visible:
                p = "[DEMO] " if s.get("demo") else ""
                parts.append(f"{p}{s['from']}→{s['to']} {s['freq']} MHz")
            self._labels["dx"].config(text="DX: " + " | ".join(parts))
        self._draw_map()

    def _schedule_refresh(self) -> None:
        interval = int(self.cfg.get("refresh_interval_seconds", 60)) * 1000
        self.root.after(interval, self._auto_refresh)

    def _auto_refresh(self) -> None:
        self.state.prune_dx_spots()
        self._refresh_location()
        self._fetch_weather()
        self._update_dx_ui()
        self._schedule_refresh()

    def _export_json(self) -> None:
        path = self.store.export_json_snapshot({
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "kp_index": self.state.kp_index,
            "solar_flux": self.state.flux,
            "muf_mhz": self.state.muf,
            "luf_mhz": self.state.luf,
            "path_muf_mhz": self.state.path_muf,
            "band_conditions": self.state.bands_summary,
            "band_grid": self.state.band_grid,
            "user_location": {"lat": self.state.user_lat, "lon": self.state.user_lon},
        })
        messagebox.showinfo("Export", f"Saved {path}")

    def _export_dx(self) -> None:
        dst = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if dst:
            self.store.export_dx_csv(Path(dst))
            messagebox.showinfo("Export", f"Saved {dst}")

    def _view_history(self) -> None:
        q = self.history_date.get().strip()
        try:
            rows = self.store.query_propagation(q)
        except ValueError as e:
            messagebox.showwarning("History", str(e))
            return
        if not rows:
            messagebox.showinfo("History", "No rows found")
            return
        w = tk.Toplevel(self.root)
        w.geometry("700x400")
        t = tk.Text(w, wrap="none")
        t.pack(fill="both", expand=True)
        for row in rows:
            t.insert("end", json.dumps(row, indent=2) + "\n\n")

    def _plot_history(self) -> None:
        if not PLOT_AVAILABLE:
            messagebox.showerror("Plot", "Install matplotlib")
            return
        q = self.history_date.get().strip()
        try:
            rows = self.store.query_propagation(q)
        except ValueError as e:
            messagebox.showwarning("Plot", str(e))
            return
        if not rows:
            messagebox.showinfo("Plot", "No data")
            return
        times, kp, flux, muf, luf = [], [], [], [], []
        for r in rows:
            times.append(datetime.datetime.fromisoformat(r["ts"]))
            kp.append(float(r.get("kp") or 0))
            flux.append(float(r.get("flux") or 0))
            muf.append(float(r.get("muf") or 0))
            luf.append(float(r.get("luf") or 0))
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(times, kp, label="Kp", marker="o")
        ax.plot(times, flux, label="Flux", marker="o")
        ax2 = ax.twinx()
        ax2.plot(times, muf, label="MUF", color="green", marker="x")
        ax2.plot(times, luf, label="LUF", color="magenta", marker="x")
        ax.legend(loc="upper left")
        pw = tk.Toplevel(self.root)
        canvas = FigureCanvasTkAgg(fig, master=pw)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        tb = tk.Frame(pw)
        tb.pack(fill="x")
        NavigationToolbar2Tk(canvas, tb)
        tk.Button(pw, text="Save PNG", command=lambda: self._save_plot(fig)).pack()

    def _save_plot(self, fig) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if path:
            fig.savefig(path, dpi=150, facecolor="#0B1220")
            messagebox.showinfo("Saved", path)

    def _open_settings(self) -> None:
        w = tk.Toplevel(self.root)
        w.title("Settings")
        w.geometry("420x520")
        fields: list[tuple[str, str]] = [
            ("cat_port", "CAT Port"), ("cat_baud", "CAT Baud"),
            ("cat_rig_profile", "Rig (kenwood/icom/yaesu)"),
            ("dx_cluster_host", "Cluster Host"), ("dx_cluster_callsign", "Cluster Call"),
            ("qrz_api_key", "QRZ API Key"),
            ("target_dx_lat", "Target DX Lat"), ("target_dx_lon", "Target DX Lon"),
            ("refresh_interval_seconds", "Refresh (sec)"),
            ("theme", "Theme (dark/light)"),
        ]
        entries: dict[str, tk.Entry] = {}
        for i, (key, label) in enumerate(fields):
            tk.Label(w, text=label).grid(row=i, column=0, sticky="w", padx=8, pady=4)
            e = tk.Entry(w, width=30)
            e.insert(0, str(self.cfg.get(key, "") or ""))
            e.grid(row=i, column=1, padx=8, pady=4)
            entries[key] = e

        def save():
            for key, entry in entries.items():
                val = entry.get().strip()
                if key in ("cat_baud", "refresh_interval_seconds"):
                    self.cfg.set(key, int(val) if val else self.cfg.get(key))
                elif key in ("target_dx_lat", "target_dx_lon"):
                    self.cfg.set(key, float(val) if val else None)
                else:
                    self.cfg.set(key, val)
            ml = {k: v.get() for k, v in self.layer_vars.items()}
            self.cfg.data["map_layers"] = ml
            self.cfg.save()
            if USE_CTK and self.cfg.get("theme") == "light":
                ctk.set_appearance_mode("light")
            elif USE_CTK:
                ctk.set_appearance_mode("dark")
            ports = self.cat.list_ports()
            if ports:
                messagebox.showinfo("COM Ports", "\n".join(ports))
            w.destroy()

        tk.Button(w, text="Save", command=save).grid(row=len(fields), column=0, columnspan=2, pady=12)
        nodes = self.cfg.get("dx_cluster_nodes", [])
        if nodes:
            tk.Label(w, text="Cluster nodes:").grid(row=len(fields) + 1, column=0, sticky="w", padx=8)
            node_var = tk.StringVar(value=nodes[0]["name"])
            om = tk.OptionMenu(w, node_var, *[n["name"] for n in nodes])
            om.grid(row=len(fields) + 1, column=1, padx=8)

            def apply_node(*_):
                n = next(x for x in nodes if x["name"] == node_var.get())
                self.cfg.set("dx_cluster_host", n["host"])
                self.cfg.set("dx_cluster_port", n["port"])

            node_var.trace_add("write", apply_node)

    def _show_help(self) -> None:
        messagebox.showinfo(
            "OrbitRx v4",
            "Greyline map • NOAA weather • DX cluster • CAT tune\n"
            "Right-drag pan • scroll zoom • layer toggles\n"
            "Settings: cluster, CAT, QRZ, path MUF target\n"
            "Data: SQLite orbitrx.db + CSV export",
        )

    def _on_minimize_tray(self, _event=None) -> None:
        try:
            import pystray
            from PIL import Image as PILImage
            img = PILImage.new("RGB", (64, 64), color=(0, 100, 200))
            icon = pystray.Icon("orbitrx", img, "OrbitRx", menu=pystray.Menu(
                pystray.MenuItem("Show", lambda: self.root.after(0, self.root.deiconify)),
                pystray.MenuItem("Quit", lambda: self.root.after(0, self._quit)),
            ))
            threading.Thread(target=icon.run, daemon=True).start()
        except ImportError:
            pass

    def _on_close(self) -> None:
        self.cfg.set("window_geometry", self.root.geometry())
        self.cat.disconnect()
        self._dx.stop()
        self.root.destroy()

    def _quit(self) -> None:
        self._on_close()

    def run(self) -> None:
        self._refresh_location()
        self._fetch_weather()
        self.root.mainloop()
