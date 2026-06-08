from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from orbitrx.propagation import estimate_muf, voacap_lite_path_muf

HAMQSL_SOLAR_URL = "https://www.hamqsl.com/solarxml.php"


def fetch_solar_xml() -> dict[str, Any] | None:
    """HamQSL solar XML — supplementary propagation data."""
    try:
        raw = urllib.request.urlopen(HAMQSL_SOLAR_URL, timeout=12).read()
        root = ET.fromstring(raw)
        out: dict[str, Any] = {}
        for tag in ("solarflux", "kindex", "ap_index", "sunspot", "updated"):
            el = root.find(f".//{tag}")
            if el is not None and el.text:
                out[tag] = el.text.strip()
        bands: list[str] = []
        for band in root.findall(".//band"):
            name = band.get("name") or band.findtext("name") or "?"
            status = band.text or band.get("status") or ""
            if name and status:
                bands.append(f"{name}:{status.strip()}")
        if bands:
            out["bands"] = bands
        return out or None
    except Exception:
        return None


def hamqsl_path_muf(
    flux: float | None,
    kp: float,
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    hamqsl_data: dict[str, Any] | None = None,
) -> tuple[float | None, str]:
    """
    Path MUF: VOACAP-lite base with optional HamQSL solar flux blend.
    Returns (muf_mhz, source_label).
    """
    base_flux = flux
    source = "VOACAP-lite"
    if hamqsl_data:
        try:
            hq_flux = float(hamqsl_data.get("solarflux", 0))
            if hq_flux > 0 and base_flux is not None:
                base_flux = round((base_flux + hq_flux) / 2, 1)
                source = "VOACAP-lite+HamQSL"
            elif hq_flux > 0:
                base_flux = hq_flux
                source = "HamQSL"
        except (TypeError, ValueError):
            pass
    muf = voacap_lite_path_muf(base_flux, kp, lat1, lon1, lat2, lon2)
    return muf, source
