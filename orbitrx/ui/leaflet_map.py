from __future__ import annotations

import datetime
import json
from typing import Any

try:
    from PySide6.QtCore import QObject, QUrl, Signal, Slot
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtWebEngineCore import QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False
    QWidget = object  # type: ignore

from orbitrx.map_renderer import MapLayers, MapRenderer

_LEAFLET_HTML = """<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<style>html,body,#map{margin:0;height:100%;background:#101820}</style>
</head><body>
<div id="map"></div>
<script>
let spotBridge = null;
new QWebChannel(qt.webChannelTransport, ch => { spotBridge = ch.objects.spotBridge; });
const map = L.map('map', {worldCopyJump: true, zoomControl: true}).setView([20, 0], 2);
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; OSM &copy; CARTO', maxZoom: 18
}).addTo(map);
let userM=null, sunM=null, dxLayer=L.layerGroup().addTo(map), termLine=null, nightPane=[];
function setPayload(p) {
  dxLayer.clearLayers();
  nightPane.forEach(l => map.removeLayer(l)); nightPane=[];
  if (termLine) { map.removeLayer(termLine); termLine=null; }
  if (p.layers.night) {
    for (let lon=-180; lon<180; lon+=2) {
      if (Math.abs(((lon - p.sun_lon + 180) % 360) - 180) > 90) {
        const r = L.rectangle([[ -85, lon], [85, lon+2]], {color:'#000', fillColor:'#000', fillOpacity:0.35, weight:0});
        r.addTo(map); nightPane.push(r);
      }
    }
  }
  if (p.layers.greyline && p.terminator.length > 1) {
    termLine = L.polyline(p.terminator, {color:'#FF6420', weight:3, opacity:0.9}).addTo(map);
  }
  if (p.user) {
    if (!userM) userM = L.circleMarker(p.user, {radius:8, color:'#fff', fillColor:'#00E676', fillOpacity:1}).addTo(map).bindPopup('You');
    else userM.setLatLng(p.user);
  }
  if (p.sun) {
    if (!sunM) sunM = L.circleMarker(p.sun, {radius:10, color:'#FFA000', fillColor:'#FFEB3B', fillOpacity:1}).addTo(map).bindPopup('Sub-solar');
    else sunM.setLatLng(p.sun);
  }
  (p.spots||[]).forEach(s => {
    if (p.layers.dx_arcs && s.from_ll && s.to_ll) {
      L.polyline([s.from_ll, s.to_ll], {color:'#00E5FF', dashArray:'6 6', weight:2}).addTo(dxLayer);
    }
    if (s.from_ll) L.circleMarker(s.from_ll, {radius:5, color:'#fff', fillColor:'#FF9800', fillOpacity:1}).addTo(dxLayer);
    if (s.to_ll) {
      const col = s.demo ? '#7B1FA2' : '#AB47BC';
      const m = L.circleMarker(s.to_ll, {radius:7, color:'#fff', fillColor:col, fillOpacity:1}).addTo(dxLayer);
      m.bindPopup(s.to + ' ' + s.freq + ' MHz');
      m.on('click', () => { if (spotBridge) spotBridge.spotClicked(s.freq); });
    }
  });
}
map.on('click', e => { if (spotBridge) spotBridge.mapClicked(e.latlng.lat, e.latlng.lng); });
</script></body></html>"""


if WEBENGINE_AVAILABLE:

    class _SpotBridge(QObject):
        spot_clicked = Signal(float)
        map_clicked = Signal(float, float)

        @Slot(float)
        def spotClicked(self, freq: float) -> None:
            self.spot_clicked.emit(float(freq))

        @Slot(float, float)
        def mapClicked(self, lat: float, lon: float) -> None:
            self.map_clicked.emit(float(lat), float(lon))

    class LeafletMapWidget(QWidget):
        spot_clicked = Signal(float)
        map_clicked = Signal(float, float)

        def __init__(self, renderer: MapRenderer, parent=None) -> None:
            super().__init__(parent)
            self.renderer = renderer
            self._layers = MapLayers()
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            self.hud = QLabel("Leaflet map — Carto dark tiles")
            self.hud.setStyleSheet("color: #B3E5FC; padding: 4px; background: #0B1220;")
            layout.addWidget(self.hud)
            self.web = QWebEngineView()
            self.web.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            layout.addWidget(self.web, stretch=1)
            self._bridge = _SpotBridge()
            self._bridge.spot_clicked.connect(self.spot_clicked)
            self._bridge.map_clicked.connect(self._emit_map_click)
            channel = QWebChannel(self.web.page())
            channel.registerObject("spotBridge", self._bridge)
            self.web.page().setWebChannel(channel)
            self.web.setHtml(_LEAFLET_HTML, QUrl("https://orbitrx.local/"))
            self._ready = False
            self.web.loadFinished.connect(self._on_ready)

        def _on_ready(self, ok: bool) -> None:
            self._ready = ok

        def _emit_map_click(self, lat: float, lon: float) -> None:
            x, y = self.renderer.world_to_map(lat, lon)
            self.map_clicked.emit(x, y)

        def set_layers(self, layers: MapLayers) -> None:
            self._layers = layers

        def set_base_map(self, _base_rgba) -> None:
            pass

        def update_scene(
            self,
            state: Any,
            spots: list[dict[str, Any]],
            coordinates: dict[str, tuple[float, float]],
            vectors_only: bool = False,
        ) -> None:
            if not self._ready:
                return
            scene = self.renderer.build_scene(state, self._layers, spots, coordinates)
            terminator = []
            import math
            w, h = self.renderer.width, self.renderer.height
            decl_rad = math.radians(scene.declination_deg)
            sun_lon_rad = math.radians(scene.sun_lon_deg)
            for x in range(0, w + 1, 4):
                lon_deg = (x / w) * 360 - 180
                lon_rad = math.radians(lon_deg)
                tan_dec = math.tan(decl_rad) or 0.0001
                tan_lat = -math.cos(lon_rad - sun_lon_rad) / tan_dec
                lat_deg = math.degrees(math.atan(tan_lat))
                terminator.append([lat_deg, lon_deg])
            spot_payload = []
            for ann in scene.annotations:
                if ann.kind != "dx_spot":
                    continue
                d = ann.data
                fcs = coordinates.get(d.get("from", ""))
                tcs = coordinates.get(d.get("to", ""))
                spot_payload.append({
                    "from": d.get("from"), "to": d.get("to"),
                    "freq": d.get("freq"), "demo": d.get("demo", False),
                    "from_ll": list(fcs) if fcs else None,
                    "to_ll": list(tcs) if tcs else None,
                })
            user = None
            sun = None
            for ann in scene.annotations:
                if ann.kind == "user" and state.user_lat is not None:
                    user = [state.user_lat, state.user_lon]
                if ann.kind == "sun":
                    lat, lon = self.renderer.map_to_world(ann.data["x"], ann.data["y"])
                    sun = [lat, lon]
            payload = {
                "layers": {
                    "greyline": self._layers.greyline,
                    "night": self._layers.night,
                    "dx_arcs": self._layers.dx_arcs,
                },
                "sun_lon": scene.sun_lon_deg,
                "terminator": terminator,
                "user": user,
                "sun": sun,
                "spots": spot_payload,
            }
            js = f"setPayload({json.dumps(payload)});"
            self.web.page().runJavaScript(js)
            offset = state.slider_offset_hours
            now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=offset)
            extra = f"  (+{offset:.1f}h)" if offset else ""
            self.hud.setText(
                f"Leaflet @ {now.strftime('%Y-%m-%d %H:%M UTC')}{extra}  |  "
                f"Scroll=zoom  Click spot=tune"
            )

else:
    LeafletMapWidget = None  # type: ignore
