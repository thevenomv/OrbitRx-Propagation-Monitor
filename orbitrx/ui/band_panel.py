from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QWidget

from orbitrx.propagation import HF_BANDS, band_chip, suggested_dial_freq


class BandPanelWidget(QWidget):
    """Per-band OPEN/FAIR/CLOSED cards with color chips and suggested dial freq."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cards: dict[str, QLabel] = {}
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)
        for i, band in enumerate(HF_BANDS):
            card = QLabel()
            card.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card.setStyleSheet(
                "background: #1A2332; border: 1px solid #37474F; border-radius: 6px; "
                "padding: 6px; color: #E3F2FD; font-size: 11px;"
            )
            card.setMinimumWidth(72)
            self._cards[band] = card
            grid.addWidget(card, i // 3, i % 3)

    def update_grid(self, band_grid: dict[str, str]) -> None:
        for band, lbl in self._cards.items():
            cond = band_grid.get(band, "UNKNOWN")
            chip = band_chip(cond)
            dial = suggested_dial_freq(band)
            lbl.setText(f"{chip} {band}\n{cond}\n{dial} MHz")
