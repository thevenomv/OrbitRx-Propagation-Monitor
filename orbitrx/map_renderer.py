from __future__ import annotations

import datetime
import math
from dataclasses import dataclass, field
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

from orbitrx.propagation import aurora_oval_lat
from orbitrx.utils import great_circle_points


@dataclass
class MapLayers:
    greyline: bool = True
    night: bool = True
    dx_arcs: bool = True
    aurora: bool = True
    grid: bool = False


@dataclass
class MapAnnotation:
    kind: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class MapScene:
    """Static raster layers + vector annotations for the UI to paint."""
    width: int
    height: int
    base_rgba: Image.Image
    overlay_rgba: Image.Image
    declination_deg: float
    sun_lon_deg: float
    hour_utc: float
    annotations: list[MapAnnotation]


class MapRenderer:
    """Builds cached map layers; DX vectors are separate for fast refresh."""

    def __init__(self, width: int = 900, height: int = 720) -> None:
        self.width = width
        self.height = height
        self._overlay_cache_key: tuple | None = None
        self._cached_overlay: Image.Image | None = None
        self._base_source: Image.Image | None = None

    def set_base_map(self, image: Image.Image | None) -> None:
        if image is None:
            self._base_source = None
            return
        self._base_source = image.resize((self.width, self.height), Image.Resampling.LANCZOS)

    def base_rgba_image(self) -> Image.Image:
        """RGBA base layer for the Qt widget (world map or placeholder)."""
        if self._base_source is not None:
            return self._base_source.copy().convert("RGBA")
        return Image.new("RGBA", (self.width, self.height), (16, 24, 32, 255))

    def world_to_map(self, lat: float, lon: float) -> tuple[float, float]:
        w, h = self.width, self.height
        x = ((lon + 180) / 360) * w
        y = (h / 2) - ((lat / 90) * (h / 2))
        return x, y

    def map_to_world(self, x: float, y: float) -> tuple[float, float]:
        w, h = self.width, self.height
        lon = (x / w) * 360 - 180
        lat = 90 - (y / (h / 2)) * 90
        return max(-90.0, min(90.0, lat)), lon

    def _terminator_lat(self, lon_deg: float, decl_rad: float, sun_lon_rad: float) -> float:
        lon_rad = math.radians(lon_deg)
        tan_dec = math.tan(decl_rad)
        if abs(tan_dec) < 0.0001:
            tan_dec = 0.0001
        tan_lat = -math.cos(lon_rad - sun_lon_rad) / tan_dec
        return math.degrees(math.atan(tan_lat))

    def _build_overlay(
        self,
        offset_hours: float,
        layers: MapLayers,
        kp: float,
    ) -> tuple[Image.Image, float, float, float]:
        w, h = self.width, self.height
        now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=offset_hours)
        day_of_year = now.timetuple().tm_yday
        # Minute resolution is enough for greyline; avoids redraw/flicker every second.
        hour_utc = now.hour + now.minute / 60.0
        declination_deg = -23.44 * math.cos(math.radians((360 / 365.25) * (day_of_year + 10)))
        decl_rad = math.radians(declination_deg)
        sun_lon_deg = 180 - (hour_utc * 15)
        sun_lon_rad = math.radians(sun_lon_deg)

        cache_key = (
            round(offset_hours, 2),
            layers.greyline,
            layers.night,
            layers.aurora,
            layers.grid,
            round(kp, 1),
            w,
            h,
        )
        if self._overlay_cache_key == cache_key and self._cached_overlay is not None:
            return self._cached_overlay, declination_deg, sun_lon_deg, hour_utc

        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)

        if layers.grid:
            grid_color = (80, 120, 160, 50)
            for lat in range(-60, 61, 30):
                y = int(h / 2 - (lat / 90) * (h / 2))
                od.line([(0, y), (w, y)], fill=grid_color, width=1)
            for lon in range(-180, 181, 30):
                x = int((lon + 180) / 360 * w)
                od.line([(x, 0), (x, h)], fill=grid_color, width=1)

        term_points: list[tuple[int, int]] = []
        step = 2
        for x in range(0, w + 1, step):
            lon_deg = (x / w) * 360 - 180
            lat_deg = self._terminator_lat(lon_deg, decl_rad, sun_lon_rad)
            y = int(h / 2 - (lat_deg / 90) * (h / 2))
            y = max(0, min(h - 1, y))
            term_points.append((x, y))

        if layers.night:
            for x in range(0, w, step):
                lon_deg = (x / w) * 360 - 180
                sun_angle = (lon_deg - sun_lon_deg + 180) % 360 - 180
                if abs(sun_angle) > 90:
                    od.line([(x, 0), (x, h - 1)], fill=(0, 0, 0, 100))

        if layers.greyline and len(term_points) > 1:
            od.line(term_points, fill=(255, 100, 30, 255), width=4)
            od.line(term_points, fill=(255, 200, 80, 180), width=2)

        if layers.aurora and kp >= 4:
            oval_lat = aurora_oval_lat(kp)
            y_top = int(h / 2 - (oval_lat / 90) * (h / 2))
            y_bot = int(h / 2 + (oval_lat / 90) * (h / 2))
            od.rectangle([(0, 0), (w, y_top)], fill=(60, 255, 140, 55))
            od.rectangle([(0, y_bot), (w, h)], fill=(60, 255, 140, 55))

        self._overlay_cache_key = cache_key
        self._cached_overlay = overlay
        return overlay, declination_deg, sun_lon_deg, hour_utc

    def build_scene(
        self,
        state: Any,
        layers: MapLayers,
        spots: list[dict[str, Any]],
        coordinates: dict[str, tuple[float, float]],
    ) -> MapScene:
        w, h = self.width, self.height
        if self._base_source is not None:
            base = self._base_source.copy().convert("RGBA")
        else:
            base = Image.new("RGBA", (w, h), (16, 24, 32, 255))

        overlay, decl_deg, sun_lon_deg, hour_utc = self._build_overlay(
            state.slider_offset_hours, layers, float(state.kp_index)
        )

        annotations: list[MapAnnotation] = []
        sun_lon_wrapped = (sun_lon_deg + 180) % 360 - 180
        sx, sy = self.world_to_map(decl_deg, sun_lon_wrapped)
        annotations.append(MapAnnotation("sun", {"x": sx, "y": sy}))

        if state.user_lat is not None and state.user_lon is not None:
            ux, uy = self.world_to_map(state.user_lat, state.user_lon)
            annotations.append(MapAnnotation("user", {"x": ux, "y": uy}))

        if layers.dx_arcs:
            for spot in spots:
                fpos = coordinates.get(spot.get("from", ""))
                tpos = coordinates.get(spot.get("to", ""))
                if not fpos or not tpos:
                    continue
                paths = self._gc_map_paths(fpos, tpos)
                fx, fy = self.world_to_map(fpos[0], fpos[1])
                tx, ty = self.world_to_map(tpos[0], tpos[1])
                annotations.append(MapAnnotation("dx_spot", {
                    "from": spot.get("from"),
                    "to": spot.get("to"),
                    "freq": spot.get("freq"),
                    "demo": spot.get("demo", False),
                    "age": max(0, int(__import__("time").time() - spot.get("time", 0))),
                    "fx": fx, "fy": fy, "tx": tx, "ty": ty,
                    "paths": paths,
                }))

        return MapScene(
            width=w,
            height=h,
            base_rgba=base,
            overlay_rgba=overlay,
            declination_deg=decl_deg,
            sun_lon_deg=sun_lon_deg,
            hour_utc=hour_utc,
            annotations=annotations,
        )

    def _gc_map_paths(
        self,
        fpos: tuple[float, float],
        tpos: tuple[float, float],
    ) -> list[list[tuple[float, float]]]:
        gc = great_circle_points(fpos[0], fpos[1], tpos[0], tpos[1], steps=32)
        segments: list[list[tuple[float, float]]] = []
        segment: list[tuple[float, float]] = []
        prev_lon: float | None = None
        for la, lo in gc:
            x, y = self.world_to_map(la, lo)
            if prev_lon is not None and abs(lo - prev_lon) > 180:
                if segment:
                    segments.append(segment)
                segment = []
            segment.append((x, y))
            prev_lon = lo
        if segment:
            segments.append(segment)
        return segments

    def pil_to_rgb_composite(self, scene: MapScene) -> Image.Image:
        return Image.alpha_composite(scene.base_rgba, scene.overlay_rgba).convert("RGB")
