from __future__ import annotations

import datetime
from typing import Any

from orbitrx.utils import fetch_json


def _is_header_row(row: Any) -> bool:
    if isinstance(row, dict):
        return False
    if not isinstance(row, list) or not row:
        return False
    head = str(row[0]).lower()
    if head in ("time_tag", "time", "date"):
        return True
    if len(row) > 1 and str(row[1]).lower() in ("kp", "flux", "dst", "bx_gsm"):
        return True
    return False


def _float_val(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _latest_numeric(
    data: list[Any],
    value_keys: tuple[str, ...],
    time_keys: tuple[str, ...] = ("time_tag", "time", "Time"),
) -> tuple[float | None, str | None]:
    """Parse newest numeric value from NOAA list rows (dict or legacy list)."""
    for row in reversed(data):
        if _is_header_row(row):
            continue
        if isinstance(row, dict):
            time_val = None
            for tk in time_keys:
                if tk in row:
                    time_val = str(row[tk])
                    break
            for vk in value_keys:
                if vk in row:
                    num = _float_val(row[vk])
                    if num is not None:
                        return num, time_val
        elif isinstance(row, list) and len(row) > 1:
            num = _float_val(row[1])
            if num is not None:
                return num, str(row[0])
    return None, None


def _latest_list_columns(
    data: list[Any],
    value_index: int,
    time_index: int = 0,
) -> tuple[float | None, str | None]:
    for row in reversed(data):
        if _is_header_row(row):
            continue
        if isinstance(row, list) and len(row) > value_index:
            num = _float_val(row[value_index])
            if num is not None:
                time_val = str(row[time_index]) if len(row) > time_index else None
                return num, time_val
    return None, None


def get_solar_cycle_forecast() -> str:
    try:
        url = "https://services.swpc.noaa.gov/products/solar-cycle-25-f10-7-predicted-range.json"
        data = fetch_json(url)
        now = datetime.datetime.now(datetime.timezone.utc)
        this_month = f"{now.year}-{now.month:02d}"
        match = next(
            (item for item in data if isinstance(item, dict) and item.get("time-tag") == this_month),
            None,
        )
        if not match and data:
            match = data[-1] if isinstance(data[-1], dict) else None
        if isinstance(match, dict):
            lo = match.get("smoothed_f10.7_min", match.get("f10.7_min", "--"))
            hi = match.get("smoothed_f10.7_max", match.get("f10.7_max", "--"))
            return f"F10.7 low: {lo}, high: {hi}"
    except Exception:
        pass
    return "F10.7: --"


def _flux_fallback_from_cycle() -> float | None:
    try:
        data = fetch_json(
            "https://services.swpc.noaa.gov/products/solar-cycle-25-f10-7-predicted-range.json"
        )
        now = datetime.datetime.now(datetime.timezone.utc)
        this_month = f"{now.year}-{now.month:02d}"
        match = next(
            (item for item in data if isinstance(item, dict) and item.get("time-tag") == this_month),
            data[-1] if data else None,
        )
        if isinstance(match, dict):
            lo = _float_val(match.get("smoothed_f10.7_min"))
            hi = _float_val(match.get("smoothed_f10.7_max"))
            if lo is not None and hi is not None:
                return round((lo + hi) / 2, 1)
    except Exception:
        pass
    return None


def fetch_space_weather_data() -> dict[str, Any]:
    result: dict[str, Any] = {
        "kp_index": 0.0,
        "time_utc": "--",
        "flux": None,
        "sunspot_observed": None,
        "sunspot_predicted": None,
        "a_index": None,
        "a_index_source": None,
        "solar_wind_speed": None,
        "bz": None,
        "alerts": [],
        "kp_forecast": "--",
        "solar_forecast": "--",
    }

    # Kp index (NOAA now returns dict rows)
    kp_data = fetch_json("https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json")
    kp, kp_time = _latest_numeric(kp_data, ("Kp", "kp", "KP"))
    if kp is not None:
        result["kp_index"] = kp
        result["time_utc"] = kp_time or "--"

    # A-index from a_running on same Kp feed when available
    for row in reversed(kp_data):
        if isinstance(row, dict) and "a_running" in row:
            a_run = _float_val(row["a_running"])
            if a_run is not None:
                result["a_index"] = a_run
                result["a_index_source"] = "NOAA a_running"
                break

    # 10cm solar flux
    try:
        flux_data = fetch_json("https://services.swpc.noaa.gov/products/10cm-flux-30-day.json")
        flux, _ = _latest_numeric(flux_data, ("flux", "Flux", "f10.7"))
        result["flux"] = flux
    except Exception:
        pass

    if result["flux"] is None:
        result["flux"] = _flux_fallback_from_cycle()

    # Sunspot predicted (monthly range)
    try:
        ssn = fetch_json(
            "https://services.swpc.noaa.gov/products/solar-cycle-25-ssn-predicted-range.json"
        )
        now = datetime.datetime.now(datetime.timezone.utc)
        this_month = f"{now.year}-{now.month:02d}"
        match = next(
            (item for item in ssn if isinstance(item, dict) and item.get("time-tag") == this_month),
            None,
        )
        if match:
            lo = _float_val(match.get("smoothed_ssn_min"))
            hi = _float_val(match.get("smoothed_ssn_max"))
            if lo is not None and hi is not None:
                result["sunspot_predicted"] = round((lo + hi) / 2, 1)
    except Exception:
        pass

    # Observed sunspot — use monthly predicted midpoint if no live obs endpoint
    result["sunspot_observed"] = result["sunspot_predicted"]

    # Kyoto Dst → A-index fallback
    if result["a_index"] is None:
        try:
            dst_data = fetch_json("https://services.swpc.noaa.gov/products/kyoto-dst.json")
            dst, _ = _latest_numeric(dst_data, ("dst", "Dst"))
            if dst is not None:
                result["a_index"] = round(abs(dst) / 10.0, 1)
                result["a_index_source"] = "Kyoto Dst est."
        except Exception:
            pass

    # Solar wind Bz (mag) + speed (plasma)
    try:
        mag = fetch_json("https://services.swpc.noaa.gov/products/solar-wind/mag-1-day.json")
        bz, _ = _latest_list_columns(mag, value_index=3)
        result["bz"] = bz
    except Exception:
        pass

    try:
        plasma = fetch_json("https://services.swpc.noaa.gov/products/solar-wind/plasma-1-day.json")
        speed, _ = _latest_list_columns(plasma, value_index=2)
        result["solar_wind_speed"] = speed
    except Exception:
        pass

    # Alerts
    try:
        alerts = fetch_json("https://services.swpc.noaa.gov/products/alerts.json")
        for row in alerts[:5]:
            if isinstance(row, list) and len(row) >= 2:
                result["alerts"].append(f"{row[0]} {row[1]}")
            elif isinstance(row, dict):
                msg = row.get("message") or row.get("text") or str(row)
                result["alerts"].append(str(msg)[:80])
    except Exception:
        pass

    # Kp forecast — predicted rows only
    try:
        fc = fetch_json(
            "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json"
        )
        kp_values: list[float] = []
        predicted_rows = [
            row for row in fc
            if isinstance(row, dict) and row.get("observed") == "predicted"
        ]
        source = predicted_rows if predicted_rows else [
            row for row in fc if isinstance(row, dict) or isinstance(row, list)
        ]
        for row in source:
            if isinstance(row, dict):
                val = _float_val(row.get("kp") or row.get("Kp"))
            elif isinstance(row, list) and len(row) > 1:
                val = _float_val(row[1])
            else:
                continue
            if val is not None:
                kp_values.append(val)
            if len(kp_values) >= 3:
                break
        if kp_values:
            result["kp_forecast"] = ", ".join(f"{x:.1f}" for x in kp_values[:3])
    except Exception:
        pass

    result["solar_forecast"] = get_solar_cycle_forecast()
    return result
