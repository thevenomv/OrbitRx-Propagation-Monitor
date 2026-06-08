"""NOAA space weather API client."""

from __future__ import annotations

import datetime
import json
import urllib.request

import tkinter as tk

from orbitrx import compat
from orbitrx.config import ALERT_KP_THRESHOLD, ALERT_MUF_THRESHOLD, ALERT_COOLDOWN_SECONDS
from orbitrx.models.context import AppContext
from orbitrx.services import logging as log_service
from orbitrx.services.propagation import estimate_muf, get_next_contest, sun_times


def fetch_json(url: str) -> list | dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read())


def get_solar_cycle_forecast() -> str:
    try:
        url = "https://services.swpc.noaa.gov/products/solar-cycle-25-f10-7-predicted-range.json"
        data = fetch_json(url)
        now = datetime.datetime.now(datetime.timezone.utc)
        this_month = f"{now.year}-{now.month:02d}"
        if isinstance(data, list):
            match = next(
                (item for item in data if isinstance(item, dict) and item.get("time-tag") == this_month),
                None,
            )
            if not match and len(data) > 0:
                match = data[-1]
            if isinstance(match, dict):
                f_low = match.get("smoothed_f10.7_min", match.get("f10.7_min", match.get("low", "--")))
                f_high = match.get("smoothed_f10.7_max", match.get("f10.7_max", match.get("high", "--")))
                return f"F10.7 low: {f_low}, high: {f_high}"
        return "F10.7: --"
    except Exception as exc:
        print("Solar cycle forecast error:", exc)
        return "F10.7: --"


def _show_propagation_alarm(ctx: AppContext) -> None:
    state = ctx.state
    if compat.winsound:
        compat.winsound.MessageBeep(compat.winsound.MB_ICONASTERISK)

    alert_win = tk.Toplevel(ctx.ui.window)
    alert_win.title("Propagation Alarm!")
    alert_win.attributes("-topmost", True)
    tk.Label(
        alert_win,
        text=(
            f"🚨 EXCELLENT CONDITIONS DETECTED! 🚨\n\n"
            f"Kp Index: {state.kp_index}\nMUF: {state.muf} MHz\n\n10m is OPEN!"
        ),
        font=("Segoe UI", 12, "bold"),
        fg="#FF0000",
        padx=20,
        pady=20,
    ).pack()
    from orbitrx.services.cat import tune_radio

    tk.Button(
        alert_win,
        text="Tune Radio to 28.074 (FT8)",
        command=lambda: tune_radio("28.074"),
        font=("Segoe UI", 10),
    ).pack(pady=5)
    tk.Button(alert_win, text="Dismiss", command=alert_win.destroy, font=("Segoe UI", 10)).pack(pady=5)


def get_space_weather(ctx: AppContext) -> None:
    state = ctx.state
    ui = ctx.ui
    try:
        if ui.btn_refresh:
            ui.btn_refresh.config(text="Fetching Satellite Data...")
            ui.window.update()

        data = fetch_json("https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json")
        time_utc = "--"
        state.kp_index = 0
        for row in reversed(data):
            if isinstance(row, list) and len(row) > 1 and row[1] not in ("Kp", "", None):
                try:
                    state.kp_index = float(row[1])
                    time_utc = row[0]
                    break
                except ValueError:
                    continue

        if state.kp_index <= 3:
            status = "🟢 GOOD: Stable Ionosphere."
        elif state.kp_index <= 5:
            status = "🟡 FAIR: Minor Geomagnetic Activity."
        else:
            status = "🔴 POOR: Geomagnetic Storm. HF blackouts likely."

        ui.lbl_kp.config(text=f"Current Kp Index: {state.kp_index}")
        ui.lbl_status.config(text=status)
        ui.lbl_time.config(text=f"Last NOAA Update: {time_utc} UTC")

        state.flux = None
        try:
            data2 = fetch_json("https://services.swpc.noaa.gov/products/10cm-flux-30-day.json")
            for row in reversed(data2):
                if isinstance(row, list) and len(row) > 1 and row[1] not in ("flux", "", None):
                    try:
                        state.flux = float(row[1])
                        break
                    except ValueError:
                        continue
            ui.lbl_solar.config(text=f"Solar Flux: {state.flux}")
        except Exception as exc:
            ui.lbl_solar.config(text="Solar Flux: --")
            print("Solar flux fetch error:", exc)

        sunspot = None
        try:
            data3 = fetch_json("https://services.swpc.noaa.gov/products/solar-cycle-25-ssn-predicted-range.json")
            now = datetime.datetime.now(datetime.timezone.utc)
            this_month = f"{now.year}-{now.month:02d}"
            match = next((item for item in data3 if item.get("time-tag") == this_month), None)
            if match:
                sunspot = (
                    float(match.get("smoothed_ssn_min", 0)) + float(match.get("smoothed_ssn_max", 0))
                ) / 2
                ui.lbl_sunspot.config(text=f"Sunspot Number (pred): {sunspot:.1f}")
            else:
                ui.lbl_sunspot.config(text="Sunspot Number: --")
        except Exception as exc:
            ui.lbl_sunspot.config(text="Sunspot Number: --")
            print("Sunspot fetch error:", exc)

        try:
            data_alerts = fetch_json("https://services.swpc.noaa.gov/products/alerts.json")
            alerts = []
            for row in data_alerts[:3]:
                if isinstance(row, list) and len(row) >= 2:
                    alerts.append(f"{row[0]} {row[1]}")
            ui.lbl_alerts.config(text="Alerts: " + (" | ".join(alerts) if alerts else "none"))
        except Exception as exc:
            ui.lbl_alerts.config(text="Alerts: --")
            print("Alerts fetch error:", exc)

        try:
            data4 = fetch_json("https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json")
            kp_values = []
            for row in data4:
                if isinstance(row, list) and len(row) > 1:
                    try:
                        kp_values.append(float(row[1]))
                    except ValueError:
                        continue
                if len(kp_values) >= 3:
                    break
            kp_forecast = ", ".join(f"{x:.1f}" for x in kp_values[:3]) if kp_values else "--"
            ui.lbl_kp_forecast.config(text=f"Kp Forecast: {kp_forecast}")
        except Exception as exc:
            ui.lbl_kp_forecast.config(text="Kp Forecast: --")
            print("Kp forecast fetch error:", exc)

        if state.user_lat is not None and state.user_lon is not None:
            sunrise, sunset = sun_times(
                state.user_lat, state.user_lon, datetime.datetime.now(datetime.timezone.utc),
            )
            if sunrise is not None:
                ui.lbl_sunrise.config(text=f"Sunrise (UTC): {sunrise:.2f}")
                ui.lbl_sunset.config(text=f"Sunset (UTC): {sunset:.2f}")
            else:
                ui.lbl_sunrise.config(text="Sunrise (UTC): N/A")
                ui.lbl_sunset.config(text="Sunset (UTC): N/A")
        else:
            ui.lbl_sunrise.config(text="Sunrise (UTC): --")
            ui.lbl_sunset.config(text="Sunset (UTC): --")

        state.muf, state.luf = estimate_muf(state.flux, state.kp_index)
        if state.muf is not None:
            ui.lbl_muf.config(text=f"MUF est: {state.muf} MHz, LUF est: {state.luf} MHz")
        else:
            ui.lbl_muf.config(text="MUF est: --")

        try:
            if state.kp_index <= 3 and state.flux is not None and state.flux > 120:
                state.bands = "🟢 EXCELLENT: All HF bands open for DX"
            elif state.kp_index <= 5 and state.flux is not None and state.flux > 100:
                state.bands = "🟡 GOOD: Most HF bands workable"
            else:
                state.bands = "🔴 POOR: Limited HF propagation"
            ui.lbl_bands.config(text=f"Band Conditions: {state.bands}")
        except Exception as exc:
            ui.lbl_bands.config(text="Band Conditions: --")
            print("Band conditions calc error:", exc)

        log_service.log_data(
            state.kp_index,
            state.flux,
            sunspot,
            state.muf if state.muf else "--",
            state.luf if state.luf else "--",
            state.bands if state.bands else "--",
            state.user_lat,
            state.user_lon,
        )

        try:
            ui.lbl_solar_forecast.config(text=f"27-Day Forecast: {get_solar_cycle_forecast()}")
        except Exception:
            ui.lbl_solar_forecast.config(text="27-Day Forecast: --")

        try:
            next_contest = get_next_contest()
            if next_contest:
                ui.lbl_contest.config(text=f"Next: {next_contest['name']} ({next_contest['date']})")
            else:
                ui.lbl_contest.config(text="Next Contest: none scheduled")
        except Exception:
            ui.lbl_contest.config(text="Next Contest: --")

        if (
            state.muf is not None
            and state.muf >= ALERT_MUF_THRESHOLD
            and state.kp_index <= ALERT_KP_THRESHOLD
        ):
            now_dt = datetime.datetime.now()
            if state.alert_last is None or (now_dt - state.alert_last).total_seconds() > ALERT_COOLDOWN_SECONDS:
                state.alert_last = now_dt
                _show_propagation_alarm(ctx)

    except Exception as exc:
        ui.lbl_status.config(text=f"Error connecting: {exc}")
        ui.lbl_solar.config(text="Solar Flux: --")
        ui.lbl_sunspot.config(text="Sunspot Number: --")
        ui.lbl_bands.config(text="Band Conditions: --")
        print("Space weather fetch error:", exc)
    finally:
        if ui.btn_refresh:
            ui.btn_refresh.config(text="Refresh Space Weather")
