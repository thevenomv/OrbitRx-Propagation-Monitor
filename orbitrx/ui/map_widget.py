from __future__ import annotations

import datetime
from typing import Any

from PIL import Image

from orbitrx.map_renderer import MapLayers, MapRenderer, MapScene

try:
    from PySide6.QtCore import Qt, QRectF, Signal
    from PySide6.QtGui import (
        QBrush, QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap,
    )
    from PySide6.QtWidgets import (
        QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsPixmapItem,
        QGraphicsScene, QGraphicsTextItem, QGraphicsView, QLabel, QVBoxLayout, QWidget,
    )
    QT_AVAILABLE = True

    class SmoothGraphicsView(QGraphicsView):
        def wheelEvent(self, event) -> None:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)

except ImportError:
    QT_AVAILABLE = False
    SmoothGraphicsView = None  # type: ignore


def _pil_to_qpixmap(img: Image.Image) -> QPixmap:
    """PIL → Qt with an explicit buffer copy so Qt never holds dangling memory."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    stride = img.width * 4
    qimg = QImage(data, img.width, img.height, stride, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg.copy())


class PropagationMapWidget(QWidget):
    """GPU-friendly map: persistent base raster + overlay + vector DX layer."""

    spot_clicked = Signal(float)
    map_clicked = Signal(float, float)

    def __init__(self, renderer: MapRenderer, parent=None) -> None:
        super().__init__(parent)
        self.renderer = renderer
        self._layers = MapLayers()
        self._scene_data: MapScene | None = None
        self._click_targets: list[tuple[float, float, float, float]] = []
        self._view_fitted = False
        self._overlay_key: tuple | None = None
        self._base_pixmap: QPixmap | None = None
        self._overlay_pixmap: QPixmap | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.hud = QLabel("")
        self.hud.setStyleSheet("color: #B3E5FC; padding: 4px; background: #0B1220;")
        layout.addWidget(self.hud)

        self.view = SmoothGraphicsView()
        self.view.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
        self._pan_anchor = None
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setBackgroundBrush(QBrush(QColor("#101820")))
        layout.addWidget(self.view, stretch=1)

        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)

        self._base_item = QGraphicsPixmapItem()
        self._base_item.setZValue(0)
        self.scene.addItem(self._base_item)

        self._overlay_item = QGraphicsPixmapItem()
        self._overlay_item.setZValue(5)
        self.scene.addItem(self._overlay_item)

        self._vector_root = self.scene.createItemGroup([])
        self._vector_root.setZValue(10)

    def set_layers(self, layers: MapLayers) -> None:
        if (
            self._layers.greyline != layers.greyline
            or self._layers.night != layers.night
            or self._layers.aurora != layers.aurora
            or self._layers.grid != layers.grid
        ):
            self._overlay_key = None
        self._layers = layers

    def set_base_map(self, base_rgba: Image.Image) -> None:
        """Load world map once; kept until widget is destroyed or map is reloaded."""
        pixmap = _pil_to_qpixmap(base_rgba)
        if pixmap.isNull():
            raise RuntimeError("Base map pixmap conversion failed")
        self._base_pixmap = pixmap
        self._base_item.setPixmap(pixmap)
        self._base_item.setPos(0, 0)
        w, h = base_rgba.width, base_rgba.height
        self.scene.setSceneRect(0, 0, w, h)
        if not self._view_fitted:
            self.view.fitInView(
                QRectF(0, 0, w, h),
                Qt.AspectRatioMode.KeepAspectRatio,
            )
            self._view_fitted = True

    def _overlay_refresh_key(self, scene: MapScene, state: Any) -> tuple:
        return (
            round(scene.sun_lon_deg, 1),
            round(scene.declination_deg, 1),
            round(state.slider_offset_hours, 1),
            self._layers.greyline,
            self._layers.night,
            self._layers.aurora,
            self._layers.grid,
            round(float(state.kp_index), 1),
        )

    def _update_overlay(self, scene: MapScene, state: Any) -> None:
        key = self._overlay_refresh_key(scene, state)
        if key == self._overlay_key and self._overlay_pixmap is not None:
            return
        pixmap = _pil_to_qpixmap(scene.overlay_rgba)
        if pixmap.isNull():
            raise RuntimeError("Overlay pixmap conversion failed")
        self._overlay_pixmap = pixmap
        self._overlay_item.setPixmap(pixmap)
        self._overlay_item.setPos(0, 0)
        self._overlay_key = key

    def update_scene(
        self,
        state: Any,
        spots: list[dict[str, Any]],
        coordinates: dict[str, tuple[float, float]],
        vectors_only: bool = False,
    ) -> None:
        scene = self.renderer.build_scene(state, self._layers, spots, coordinates)
        self._scene_data = scene

        if self._base_pixmap is None or self._base_item.pixmap().isNull():
            self.set_base_map(scene.base_rgba)

        if not vectors_only:
            self._update_overlay(scene, state)

        self._draw_vectors(scene)
        offset = state.slider_offset_hours
        now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=offset)
        extra = f"  (+{offset:.1f}h)" if offset else ""
        self.hud.setText(
            f"Greyline @ {now.strftime('%Y-%m-%d %H:%M UTC')}{extra}  |  "
            f"Scroll=zoom  Right-drag=pan  Double-click=reset  Click purple=tune"
        )

    def _clear_vectors(self) -> None:
        for item in self._vector_root.childItems()[:]:
            self._vector_root.removeFromGroup(item)
            del item

    def _add_to_vectors(self, item) -> None:
        self._vector_root.addToGroup(item)

    def _draw_vectors(self, scene: MapScene) -> None:
        self._clear_vectors()
        self._click_targets.clear()

        sun_font = QFont("Segoe UI", 9)
        for ann in scene.annotations:
            if ann.kind == "sun":
                x, y = ann.data["x"], ann.data["y"]
                glow = QGraphicsEllipseItem(x - 16, y - 16, 32, 32)
                glow.setBrush(QBrush(QColor(255, 235, 80, 80)))
                glow.setPen(QPen(Qt.PenStyle.NoPen))
                self._add_to_vectors(glow)
                core = QGraphicsEllipseItem(x - 9, y - 9, 18, 18)
                core.setBrush(QBrush(QColor("#FFEB3B")))
                core.setPen(QPen(QColor("#FFA000"), 2))
                self._add_to_vectors(core)

            elif ann.kind == "user":
                x, y = ann.data["x"], ann.data["y"]
                dot = QGraphicsEllipseItem(x - 7, y - 7, 14, 14)
                dot.setBrush(QBrush(QColor("#00E676")))
                dot.setPen(QPen(QColor("white"), 2))
                self._add_to_vectors(dot)
                lbl = QGraphicsTextItem("You")
                lbl.setDefaultTextColor(QColor("white"))
                lbl.setFont(sun_font)
                lbl.setPos(x + 10, y - 14)
                self._add_to_vectors(lbl)

            elif ann.kind == "dx_spot":
                d = ann.data
                pen_arc = QPen(QColor("#00E5FF"), 2, Qt.PenStyle.DashLine)
                for seg in d.get("paths", []):
                    if len(seg) < 2:
                        continue
                    path = QPainterPath()
                    path.moveTo(seg[0][0], seg[0][1])
                    for px, py in seg[1:]:
                        path.lineTo(px, py)
                    arc_item = QGraphicsPathItem(path)
                    arc_item.setPen(pen_arc)
                    self._add_to_vectors(arc_item)

                fx, fy, tx, ty = d["fx"], d["fy"], d["tx"], d["ty"]
                spotter = QGraphicsEllipseItem(fx - 5, fy - 5, 10, 10)
                spotter.setBrush(QBrush(QColor("#FF9800")))
                spotter.setPen(QPen(QColor("white")))
                self._add_to_vectors(spotter)

                color = QColor("#7B1FA2") if d.get("demo") else QColor("#AB47BC")
                target = QGraphicsEllipseItem(tx - 7, ty - 7, 14, 14)
                target.setBrush(QBrush(color))
                target.setPen(QPen(QColor("white"), 2))
                self._add_to_vectors(target)

                freq = d.get("freq", "?")
                age = d.get("age", 0)
                label = QGraphicsTextItem(f"{d.get('to')} {freq} MHz ({age}s)")
                label.setDefaultTextColor(QColor("#FFF59D"))
                label.setFont(QFont("Segoe UI", 8))
                label.setPos(tx + 8, ty - 16)
                self._add_to_vectors(label)

                self._click_targets.append((tx, ty, float(freq), 18.0))

    def mouseDoubleClickEvent(self, event) -> None:
        self.view.resetTransform()
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self._pan_anchor = event.pos()
        elif event.button() == Qt.MouseButton.LeftButton:
            sp = self.view.mapToScene(event.pos())
            for tx, ty, freq, radius in self._click_targets:
                if (sp.x() - tx) ** 2 + (sp.y() - ty) ** 2 <= radius ** 2:
                    self.spot_clicked.emit(freq)
                    return
            self.map_clicked.emit(sp.x(), sp.y())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._pan_anchor is not None and event.buttons() & Qt.MouseButton.RightButton:
            delta = event.pos() - self._pan_anchor
            self._pan_anchor = event.pos()
            self.view.horizontalScrollBar().setValue(
                self.view.horizontalScrollBar().value() - delta.x()
            )
            self.view.verticalScrollBar().setValue(
                self.view.verticalScrollBar().value() - delta.y()
            )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self._pan_anchor = None
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit_map_view()

    def _fit_map_view(self) -> None:
        if self._base_item.pixmap() and not self._base_item.pixmap().isNull():
            r = self._base_item.boundingRect()
            if r.width() > 0 and r.height() > 0:
                self.view.fitInView(r, Qt.AspectRatioMode.KeepAspectRatio)
