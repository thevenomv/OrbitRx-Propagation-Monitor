from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QMessageBox, QVBoxLayout,
)

from orbitrx.cat import CatController, RIG_PROFILES
from orbitrx.config import AppConfig


class RigWizardDialog(QDialog):
    """Detect COM port, test CAT, save rig profile."""

    def __init__(self, cfg: AppConfig, cat: CatController, parent=None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.cat = cat
        self.setWindowTitle("Rig Profile Wizard")
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.port_combo = QComboBox()
        ports = cat.list_ports() or [cfg.get("cat_port", "COM3")]
        self.port_combo.addItems(ports)
        idx = self.port_combo.findText(str(cfg.get("cat_port", "")))
        if idx >= 0:
            self.port_combo.setCurrentIndex(idx)
        form.addRow("COM port", self.port_combo)

        self.profile_combo = QComboBox()
        self.profile_combo.addItems(sorted(RIG_PROFILES.keys()))
        pidx = self.profile_combo.findText(str(cfg.get("cat_rig_profile", "kenwood")))
        if pidx >= 0:
            self.profile_combo.setCurrentIndex(pidx)
        form.addRow("Rig profile", self.profile_combo)

        self.baud_combo = QComboBox()
        for b in ("4800", "9600", "19200", "38400", "115200"):
            self.baud_combo.addItem(b)
        bidx = self.baud_combo.findText(str(cfg.get("cat_baud", 9600)))
        if bidx >= 0:
            self.baud_combo.setCurrentIndex(bidx)
        form.addRow("Baud", self.baud_combo)

        lay.addLayout(form)
        self.status = QLabel("Select port and click Test CAT.")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

        from PySide6.QtWidgets import QPushButton, QHBoxLayout
        test_row = QHBoxLayout()
        test_row.addWidget(QPushButton("Refresh ports", clicked=self._refresh_ports))
        test_row.addWidget(QPushButton("Test CAT", clicked=self._test_cat))
        lay.addLayout(test_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _refresh_ports(self) -> None:
        ports = self.cat.list_ports()
        self.port_combo.clear()
        if ports:
            self.port_combo.addItems(ports)
            self.status.setText(f"Found {len(ports)} port(s).")
        else:
            self.port_combo.addItem(self.cfg.get("cat_port", "COM3"))
            self.status.setText("No COM ports detected (pyserial missing or no USB rigs).")

    def _test_cat(self) -> None:
        self.cfg.data["cat_port"] = self.port_combo.currentText()
        self.cfg.data["cat_baud"] = int(self.baud_combo.currentText())
        self.cfg.data["cat_rig_profile"] = self.profile_combo.currentText()
        result = self.cat.tune(14.200, confirm=None)
        self.status.setText(result)
        if "Sent CAT" in result:
            QMessageBox.information(self, "CAT", "Rig responded — profile looks good.")

    def _save(self) -> None:
        profile = {
            "name": f"{self.profile_combo.currentText()} @ {self.port_combo.currentText()}",
            "port": self.port_combo.currentText(),
            "baud": int(self.baud_combo.currentText()),
            "rig_profile": self.profile_combo.currentText(),
        }
        profiles = list(self.cfg.get("rig_profiles") or [])
        profiles = [p for p in profiles if p.get("port") != profile["port"]]
        profiles.insert(0, profile)
        self.cfg.set("rig_profiles", profiles[:5])
        self.cfg.set("cat_port", profile["port"])
        self.cfg.set("cat_baud", profile["baud"])
        self.cfg.set("cat_rig_profile", profile["rig_profile"])
        self.accept()
