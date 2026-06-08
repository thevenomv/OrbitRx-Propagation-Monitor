from __future__ import annotations

import datetime
import json
from pathlib import Path

from PIL import Image

from orbitrx import __version__
from orbitrx.dx import verify_qrz_api
from orbitrx.map_renderer import MapLayers, MapRenderer
from orbitrx.propagation import HF_BANDS
from orbitrx.ui.band_panel import BandPanelWidget
from orbitrx.ui.controller import OrbitRxController
from orbitrx.ui.map_widget import PropagationMapWidget, QT_AVAILABLE
from orbitrx.ui.rig_wizard import RigWizardDialog
from orbitrx.update_checker import check_github_release

try:
    from orbitrx.ui.leaflet_map import WEBENGINE_AVAILABLE, LeafletMapWidget
except ImportError:
    WEBENGINE_AVAILABLE = False
    LeafletMapWidget = None

if not QT_AVAILABLE:
    raise ImportError("PySide6 is required for the Qt UI")

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSlider, QTabWidget, QVBoxLayout, QWidget, QFileDialog,
    QSystemTrayIcon, QMenu,
)

PLOT_QT = False
try:
    import matplotlib
    matplotlib.use("QtAgg")
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    PLOT_QT = True
except ImportError:
    FigureCanvas = None

CONTINENT_OPTS = [("NA", "North America"), ("SA", "South America"), ("EU", "Europe"),
                  ("AF", "Africa"), ("AS", "Asia"), ("OC", "Oceania")]


class QtOrbitRxApplication(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"OrbitRx v{__version__} — Qt Map [SOURCE BUILD]")
        self.renderer = MapRenderer(width=900, height=720)
        self._labels: dict[str, QLabel] = {}
        self._layer_checks: dict[str, QCheckBox] = {}
        self._map_container: QWidget | None = None
        self._tray: QSystemTrayIcon | None = None

        self.ctrl = OrbitRxController(
            on_status=self._set_status,
            on_weather=self._refresh_labels_and_map,
            on_dx=self._refresh_labels_and_map,
            on_cluster=self._set_cluster,
            on_alarm_excellent=self._alarm_excellent,
            on_alarm_storm=self._alarm_storm,
        )
        self.ctrl._on_band_beep = self._spot_beep

        cfg_backend = self.ctrl.cfg.get("map_backend", "static")
        if cfg_backend == "leaflet" and not self._leaflet_available():
            cfg_backend = "static"
        self._map_backend = cfg_backend

        geom = self.ctrl.cfg.get("window_geometry", "1400x820")
        self.resize(*self._parse_geom(geom))
        self._build_ui()
        self._load_map()
        self._refresh_map()
        self.ctrl.seed_demo_spots()
        self.ctrl.start()
        self._setup_tray()
        QTimer.singleShot(200, self._startup)
        if self.ctrl.cfg.get("check_updates_on_launch", True):
            QTimer.singleShot(3000, self._check_updates)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._auto_refresh)
        self._timer.start(int(self.ctrl.cfg.get("refresh_interval_seconds", 60)) * 1000)

    def _leaflet_available(self) -> bool:
        return bool(WEBENGINE_AVAILABLE and LeafletMapWidget)

    def _parse_geom(self, g: str) -> tuple[int, int]:
        try:
            w, h = g.split("x")
            return int(w), int(h)
        except Exception:
            return 1400, 820

    def _create_map_widget(self):
        if self._map_backend == "leaflet" and self._leaflet_available():
            return LeafletMapWidget(self.renderer)
        return PropagationMapWidget(self.renderer)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        left = QVBoxLayout()
        self.banner = QLabel("v5 Qt UI — loading map...")
        self.banner.setStyleSheet(
            "background: #37474F; color: #ECEFF1; padding: 8px; font-weight: bold; border-radius: 4px;"
        )
        self.banner.setWordWrap(True)
        left.addWidget(self.banner)

        cluster_row = QHBoxLayout()
        cluster_row.addWidget(QLabel("Cluster:"))
        self.cluster_combo = QComboBox()
        self._populate_cluster_combo()
        self.cluster_combo.currentIndexChanged.connect(self._cluster_node_changed)
        cluster_row.addWidget(self.cluster_combo, stretch=1)
        left.addLayout(cluster_row)

        self.map_widget = self._create_map_widget()
        self.map_widget.spot_clicked.connect(self._tune_from_map)
        self.map_widget.map_clicked.connect(self._on_map_click)
        left.addWidget(self.map_widget, stretch=1)

        layer_row = QHBoxLayout()
        for key, label in [("greyline", "Greyline"), ("night", "Night"), ("dx_arcs", "DX"),
                           ("aurora", "Aurora"), ("grid", "Grid")]:
            cb = QCheckBox(label)
            cb.setChecked(self.ctrl.cfg.get("map_layers", {}).get(key, key != "grid"))
            cb.stateChanged.connect(self._layers_changed)
            self._layer_checks[key] = cb
            layer_row.addWidget(cb)
        left.addLayout(layer_row)

        slider_row = QHBoxLayout()
        slider_row.addWidget(QLabel("Time travel (+hrs):"))
        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setRange(0, 48)
        self.time_slider.setValue(0)
        self.time_slider.valueChanged.connect(self._slider_moved)
        slider_row.addWidget(self.time_slider)
        self.lbl_slider = QLabel("+0.0h")
        slider_row.addWidget(self.lbl_slider)
        left.addLayout(slider_row)
        root.addLayout(left, stretch=3)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setMaximumWidth(380)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.last_updated_lbl = QLabel("Last updated: never")
        self.last_updated_lbl.setStyleSheet("color: #90CAF9; font-size: 11px; padding: 2px;")
        right_layout.addWidget(self.last_updated_lbl)

        self.band_panel = BandPanelWidget()
        right_layout.addWidget(self.band_panel)

        self.tabs = QTabWidget()
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        for key in [
            "kp", "kp_forecast", "solar", "sunspot", "a_index", "solar_wind", "time",
            "bands", "band_grid", "muf", "path_muf", "hamqsl", "sunrise", "sunset", "alerts",
            "location", "cluster", "solar_forecast", "contest", "dx",
        ]:
            lbl = QLabel(f"{key}: --")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #CDDDFE; padding: 2px;")
            self._labels[key] = lbl
            stats_layout.addWidget(lbl)
        stats_layout.addStretch()
        self.tabs.addTab(stats_tab, "Stats")

        plot_tab = QWidget()
        plot_layout = QVBoxLayout(plot_tab)
        hist_row = QHBoxLayout()
        self.hist_date = QLineEdit(datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"))
        hist_row.addWidget(self.hist_date)
        hist_row.addWidget(QPushButton("Refresh", clicked=self._refresh_plot_tab))
        plot_layout.addLayout(hist_row)
        self.plot_container = QVBoxLayout()
        plot_layout.addLayout(self.plot_container)
        self.plot_placeholder = QLabel("Click Refresh to load history chart")
        self.plot_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.plot_container.addWidget(self.plot_placeholder)
        self.tabs.addTab(plot_tab, "Plot")

        right_layout.addWidget(self.tabs)

        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet("color: #81D4FA; font-style: italic;")
        right_layout.addWidget(self.status_lbl)

        self.click_lbl = QLabel("")
        self.click_lbl.setWordWrap(True)
        self.click_lbl.setStyleSheet("color: #90A4AE;")
        right_layout.addWidget(self.click_lbl)

        btn_row = QHBoxLayout()
        for text, slot in [
            ("Location", self.ctrl.refresh_location),
            ("Weather", self.ctrl.fetch_weather),
            ("Settings", self._settings),
            ("Rig", self._rig_wizard),
            ("Export", self._export_json),
            ("DX CSV", self._export_dx),
        ]:
            btn_row.addWidget(QPushButton(text, clicked=slot))
        right_layout.addLayout(btn_row)
        right_layout.addStretch()
        right_scroll.setWidget(right_panel)
        root.addWidget(right_scroll, stretch=1)

    def _populate_cluster_combo(self) -> None:
        self.cluster_combo.blockSignals(True)
        self.cluster_combo.clear()
        nodes = self.ctrl.cfg.get("dx_cluster_nodes") or []
        current_host = self.ctrl.cfg.get("dx_cluster_host", "")
        select_idx = 0
        for i, node in enumerate(nodes):
            label = f"{node.get('name', '?')} ({node.get('host')}:{node.get('port', 23)})"
            self.cluster_combo.addItem(label, node)
            if node.get("host") == current_host:
                select_idx = i
        if not nodes:
            self.cluster_combo.addItem(
                f"Custom ({current_host})", {"host": current_host, "port": self.ctrl.cfg.get("dx_cluster_port", 23)}
            )
        else:
            self.cluster_combo.setCurrentIndex(select_idx)
        self.cluster_combo.blockSignals(False)

    def _cluster_node_changed(self, index: int) -> None:
        if index < 0:
            return
        node = self.cluster_combo.itemData(index)
        if not node:
            return
        self.ctrl.cfg.set("dx_cluster_host", node.get("host"))
        self.ctrl.cfg.set("dx_cluster_port", int(node.get("port", 23)))
        self.ctrl.stop()
        self.ctrl.start()
        self._set_status(f"Cluster → {node.get('name', node.get('host'))}")

    def _load_map(self) -> None:
        from orbitrx.paths import ensure_map_image

        self._map_label = "Map: loading..."
        try:
            if self._map_backend == "leaflet":
                self._map_label = "Leaflet map (Carto dark tiles)"
                self.banner.setText(
                    f"v5 Qt UI — {self._map_label} | online tiles | click spot=tune"
                )
                self.banner.setStyleSheet(
                    "background: #1B5E20; color: #C8E6C9; padding: 8px; font-weight: bold;"
                )
                return
            map_path = ensure_map_image()
            if not map_path.is_file():
                raise FileNotFoundError(f"world_map.jpg not found at {map_path}")
            img = Image.open(map_path)
            img.load()
            self.renderer.set_base_map(img)
            self.map_widget.set_base_map(self.renderer.base_rgba_image())
            self._map_label = f"Map loaded: {map_path.name} ({img.width}×{img.height})"
            self.banner.setText(
                f"v5 Qt UI — {self._map_label} | scroll=zoom | right-drag=pan | click spot=tune"
            )
            self.banner.setStyleSheet(
                "background: #1B5E20; color: #C8E6C9; padding: 8px; font-weight: bold;"
            )
        except Exception as e:
            self.renderer.set_base_map(None)
            if hasattr(self.map_widget, "set_base_map"):
                self.map_widget.set_base_map(self.renderer.base_rgba_image())
            self._map_label = f"Map FAILED: {e}"
            self.banner.setText(self._map_label)
            self.banner.setStyleSheet(
                "background: #B71C1C; color: white; padding: 8px; font-weight: bold;"
            )

    def _current_layers(self) -> MapLayers:
        return MapLayers(
            greyline=self._layer_checks["greyline"].isChecked(),
            night=self._layer_checks["night"].isChecked(),
            dx_arcs=self._layer_checks["dx_arcs"].isChecked(),
            aurora=self._layer_checks["aurora"].isChecked(),
            grid=self._layer_checks["grid"].isChecked(),
        )

    def _refresh_map(self, vectors_only: bool = False) -> None:
        spots, coords = self.ctrl.get_spots_snapshot()
        self.map_widget.set_layers(self._current_layers())
        self.map_widget.update_scene(
            self.ctrl.state, spots, coords, vectors_only=vectors_only
        )

    def _refresh_labels_and_map(self) -> None:
        labels = self.ctrl.weather_labels()
        for k, v in labels.items():
            if k in self._labels:
                self._labels[k].setText(v)
        self.band_panel.update_grid(self.ctrl.state.band_grid)
        self.last_updated_lbl.setText(self.ctrl.last_updated_text())
        self._refresh_map()

    def _layers_changed(self) -> None:
        ml = {k: cb.isChecked() for k, cb in self._layer_checks.items()}
        self.ctrl.cfg.data["map_layers"] = ml
        self.ctrl.cfg.save()
        self._refresh_map()

    def _slider_moved(self, val: int) -> None:
        self.ctrl.state.slider_offset_hours = val / 2.0
        self.lbl_slider.setText(f"+{self.ctrl.state.slider_offset_hours:.1f}h")
        self._refresh_map()

    def _on_map_click(self, x: float, y: float) -> None:
        self.click_lbl.setText(self.ctrl.map_click_latlon(x, y, self.renderer))

    def _tune_from_map(self, freq: float) -> None:
        def confirm(msg: str) -> bool:
            return QMessageBox.question(self, "CAT", msg) == QMessageBox.StandardButton.Yes
        result = self.ctrl.tune_radio(freq, confirm if self.ctrl.cfg.get("cat_confirm_before_tune") else None)
        QMessageBox.information(self, "CAT", result)

    def _set_status(self, text: str) -> None:
        self.status_lbl.setText(text)

    def _set_cluster(self, status: str) -> None:
        self.ctrl.state.cluster_status = status
        self._labels["cluster"].setText(f"Cluster: {status}")

    def _spot_beep(self, spot: dict) -> None:
        self.ctrl.spot_beep(spot)
        self._refresh_map(vectors_only=True)

    def _alarm_excellent(self) -> None:
        QMessageBox.information(
            self, "Propagation Alarm",
            f"Excellent conditions! Kp {self.ctrl.state.kp_index}  MUF {self.ctrl.state.muf} MHz",
        )

    def _alarm_storm(self) -> None:
        QMessageBox.warning(self, "Storm Warning", f"Geomagnetic storm — Kp {self.ctrl.state.kp_index}")

    def _startup(self) -> None:
        self.ctrl.refresh_location()
        self.ctrl.fetch_weather()
        self._refresh_labels_and_map()

    def _auto_refresh(self) -> None:
        self.ctrl.state.prune_dx_spots()
        self.ctrl.refresh_location()
        self.ctrl.fetch_weather()

    def _check_updates(self) -> None:
        info = check_github_release(__version__)
        if info.get("update_available"):
            QMessageBox.information(
                self, "Update Available",
                f"{info['message']}\n\nDownload: {info['url']}",
            )

    def _export_json(self) -> None:
        p = self.ctrl.export_json()
        QMessageBox.information(self, "Export", f"Saved {p}")

    def _export_dx(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export DX", "dx_spots.csv", "CSV (*.csv)")
        if path:
            self.ctrl.store.export_dx_csv(Path(path))
            QMessageBox.information(self, "Export", f"Saved {path}")

    def _rig_wizard(self) -> None:
        dlg = RigWizardDialog(self.ctrl.cfg, self.ctrl.cat, self)
        dlg.exec()

    def _refresh_plot_tab(self) -> None:
        if not PLOT_QT:
            self.plot_placeholder.setText("matplotlib Qt backend required")
            return
        q = self.hist_date.text().strip()
        try:
            rows = self.ctrl.store.query_propagation(q)
        except ValueError as e:
            self.plot_placeholder.setText(str(e))
            return
        if not rows:
            self.plot_placeholder.setText("No data for this date range")
            return
        while self.plot_container.count():
            item = self.plot_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        times, kp, flux, muf, luf = [], [], [], [], []
        for r in rows:
            times.append(datetime.datetime.fromisoformat(r["ts"]))
            kp.append(float(r.get("kp") or 0))
            flux.append(float(r.get("flux") or 0))
            muf.append(float(r.get("muf") or 0))
            luf.append(float(r.get("luf") or 0))
        fig = Figure(figsize=(5, 3.5), facecolor="#0B1220")
        ax = fig.add_subplot(111)
        ax.set_facecolor("#0B1220")
        ax.tick_params(colors="#CDDDFE")
        for spine in ax.spines.values():
            spine.set_color("#37474F")
        ax.plot(times, kp, label="Kp", marker="o", color="#64B5F6")
        ax.plot(times, flux, label="Flux", marker="o", color="#FFD54F")
        ax2 = ax.twinx()
        ax2.plot(times, muf, label="MUF", color="#81C784", marker="x")
        ax2.plot(times, luf, label="LUF", color="#F48FB1", marker="x")
        ax.legend(loc="upper left", fontsize=8)
        ax2.legend(loc="upper right", fontsize=8)
        fig.tight_layout()
        canvas = FigureCanvas(fig)
        self.plot_container.addWidget(canvas)
        save_btn = QPushButton("Save PNG", clicked=lambda: self._save_fig(fig))
        self.plot_container.addWidget(save_btn)

    def _save_fig(self, fig) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save PNG", "history.png", "PNG (*.png)")
        if path:
            fig.savefig(path, dpi=150, facecolor="#0B1220")
            QMessageBox.information(self, "Saved", path)

    def _settings(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Settings")
        dlg.resize(480, 520)
        outer = QVBoxLayout(dlg)
        form = QFormLayout()
        fields: dict[str, QLineEdit] = {}
        for key, label in [
            ("cat_port", "CAT port"), ("cat_baud", "CAT baud"),
            ("cat_rig_profile", "Rig profile"), ("dx_cluster_callsign", "Cluster callsign"),
            ("qrz_api_key", "QRZ API key"), ("target_dx_callsign", "Target DX callsign"),
            ("target_dx_lat", "Target lat"), ("target_dx_lon", "Target lon"),
            ("refresh_interval_seconds", "Refresh sec"),
        ]:
            e = QLineEdit(str(self.ctrl.cfg.get(key, "") or ""))
            form.addRow(label, e)
            fields[key] = e

        map_backend = QComboBox()
        map_backend.addItem("Static JPG map", "static")
        if self._leaflet_available():
            map_backend.addItem("Leaflet slippy map", "leaflet")
        idx = map_backend.findData(self.ctrl.cfg.get("map_backend", "static"))
        if idx >= 0:
            map_backend.setCurrentIndex(idx)
        form.addRow("Map backend", map_backend)

        band_box = QGroupBox("DX band filters (empty = all)")
        band_layout = QVBoxLayout(band_box)
        band_checks: dict[float, QCheckBox] = {}
        current_bands = set(self.ctrl.cfg.get("dx_filter_bands_mhz") or [])
        for name, meta in HF_BANDS.items():
            cb = QCheckBox(f"{name} ({meta['freq']} MHz)")
            cb.setChecked(meta["freq"] in current_bands)
            band_checks[meta["freq"]] = cb
            band_layout.addWidget(cb)
        outer.addLayout(form)
        outer.addWidget(band_box)

        cont_box = QGroupBox("DX continent filters (empty = all)")
        cont_layout = QHBoxLayout(cont_box)
        cont_checks: dict[str, QCheckBox] = {}
        current_cont = set(self.ctrl.cfg.get("dx_filter_continents") or [])
        for code, label in CONTINENT_OPTS:
            cb = QCheckBox(code)
            cb.setToolTip(label)
            cb.setChecked(code in current_cont)
            cont_checks[code] = cb
            cont_layout.addWidget(cb)
        outer.addWidget(cont_box)

        qrz_row = QHBoxLayout()
        qrz_btn = QPushButton("Test QRZ")
        qrz_result = QLabel("")
        qrz_result.setWordWrap(True)

        def do_qrz_test() -> None:
            ok, msg, _ = verify_qrz_api(fields["qrz_api_key"].text().strip())
            qrz_result.setText(msg)
            qrz_result.setStyleSheet(f"color: {'#81C784' if ok else '#EF9A9A'};")

        qrz_btn.clicked.connect(do_qrz_test)
        qrz_row.addWidget(qrz_btn)
        qrz_row.addWidget(qrz_result, stretch=1)
        outer.addLayout(qrz_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        outer.addWidget(buttons)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            for key, e in fields.items():
                val = e.text().strip()
                if key in ("cat_baud", "refresh_interval_seconds"):
                    self.ctrl.cfg.set(key, int(val) if val else self.ctrl.cfg.get(key))
                elif key in ("target_dx_lat", "target_dx_lon"):
                    self.ctrl.cfg.set(key, float(val) if val else None)
                else:
                    self.ctrl.cfg.set(key, val)
            bands = [f for f, cb in band_checks.items() if cb.isChecked()]
            conts = [c for c, cb in cont_checks.items() if cb.isChecked()]
            self.ctrl.cfg.set("dx_filter_bands_mhz", bands)
            self.ctrl.cfg.set("dx_filter_continents", conts)
            new_backend = map_backend.currentData()
            if new_backend != self._map_backend:
                self.ctrl.cfg.set("map_backend", new_backend)
                QMessageBox.information(
                    self, "Map backend",
                    "Map backend changed — restart OrbitRx to apply.",
                )
            ports = self.ctrl.cat.list_ports()
            if ports:
                QMessageBox.information(self, "COM ports", "\n".join(ports))
            self._timer.setInterval(int(self.ctrl.cfg.get("refresh_interval_seconds", 60)) * 1000)
            self._populate_cluster_combo()

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        if not self.ctrl.cfg.get("minimize_to_tray", True):
            return
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        from PySide6.QtGui import QPainter, QColor
        p = QPainter(pix)
        p.setBrush(QColor(0, 120, 215))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(2, 2, 28, 28)
        p.end()
        self._tray = QSystemTrayIcon(QIcon(pix), self)
        menu = QMenu()
        show_act = QAction("Show OrbitRx", self)
        show_act.triggered.connect(self._show_from_tray)
        quit_act = QAction("Quit", self)
        quit_act.triggered.connect(self._quit_app)
        menu.addAction(show_act)
        menu.addAction(quit_act)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._tray_activated)
        self._tray.setToolTip("OrbitRx Propagation Monitor")
        self._tray.show()

    def _tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.activateWindow()

    def _quit_app(self) -> None:
        self.ctrl.stop()
        QApplication.quit()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if (
            self._tray
            and self.ctrl.cfg.get("minimize_to_tray", True)
            and event.type() == QEvent.Type.WindowStateChange
            and self.isMinimized()
        ):
            QTimer.singleShot(0, self.hide)
            self._tray.showMessage(
                "OrbitRx",
                "Running in system tray — background refresh active.",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )

    def closeEvent(self, event) -> None:
        if self._tray and self._tray.isVisible() and self.ctrl.cfg.get("minimize_to_tray", True):
            event.ignore()
            self.hide()
            self._tray.showMessage(
                "OrbitRx",
                "Minimized to tray. Right-click tray icon to quit.",
                QSystemTrayIcon.MessageIcon.Information,
                2500,
            )
            return
        self.ctrl.cfg.set("window_geometry", f"{self.width()}x{self.height()}")
        self.ctrl.stop()
        super().closeEvent(event)

    def run(self) -> None:
        self.show()


def run_qt_app() -> None:
    import sys
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
    win = QtOrbitRxApplication()
    win.run()
    sys.exit(app.exec())
