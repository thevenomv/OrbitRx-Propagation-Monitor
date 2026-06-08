"""Propagation history lookup and plotting."""

from __future__ import annotations

import csv
import datetime
import json

import tkinter as tk
from tkinter import messagebox

from orbitrx import compat
from orbitrx.models.context import AppContext
from orbitrx.paths import get_log_path
from orbitrx.services.propagation import parse_history_query


def view_history(ctx: AppContext, query: str) -> None:
    if not query:
        return

    try:
        start_dt, end_dt = parse_history_query(query)
    except ValueError as err:
        messagebox.showwarning("History Lookup", f"Invalid date/time format:\n{err}")
        return

    matches = []
    log_path = get_log_path("propagation_log.csv")
    try:
        with log_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = row.get("Timestamp")
                if not ts:
                    continue
                try:
                    record_dt = datetime.datetime.fromisoformat(ts)
                except Exception:
                    continue
                if start_dt == end_dt:
                    if record_dt == start_dt:
                        matches.append(row)
                elif start_dt <= record_dt < end_dt:
                    matches.append(row)
    except FileNotFoundError:
        messagebox.showinfo("History Lookup", f"No log file found yet ({log_path}).")
        return

    if not matches:
        messagebox.showinfo("History Lookup", f"No history entries found for {query}.")
        return

    popup = tk.Toplevel(ctx.ui.window)
    popup.title("History Results")

    text = tk.Text(
        popup, width=100, height=20, wrap="none",
        bg="#0E162B", fg="white", font=("Segoe UI", 10),
    )
    text.pack(fill="both", expand=True)
    text.insert("end", f"History results for {query} (found {len(matches)} entries)\n\n")
    for row in matches:
        text.insert("end", json.dumps(row, indent=2) + "\n\n")
    text.configure(state="disabled")

    scroll_y = tk.Scrollbar(popup, orient="vertical", command=text.yview)
    text.configure(yscrollcommand=scroll_y.set)
    scroll_y.pack(side="right", fill="y")


def plot_history(ctx: AppContext, query: str) -> None:
    if not compat.PLOT_AVAILABLE:
        messagebox.showerror(
            "Plot History",
            "Matplotlib is required for plotting. Install it with 'pip install matplotlib'.",
        )
        return
    if not query:
        messagebox.showwarning("Plot History", "Please enter a date or timestamp first.")
        return

    try:
        start_dt, end_dt = parse_history_query(query)
    except ValueError as err:
        messagebox.showwarning("Plot History", f"Invalid date/time format:\n{err}")
        return

    times, kp_vals, flux_vals, muf_vals, luf_vals = [], [], [], [], []
    log_path = get_log_path("propagation_log.csv")
    try:
        with log_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = row.get("Timestamp")
                if not ts:
                    continue
                try:
                    record_dt = datetime.datetime.fromisoformat(ts)
                except Exception:
                    continue
                if start_dt == end_dt:
                    if record_dt != start_dt:
                        continue
                elif not (start_dt <= record_dt < end_dt):
                    continue
                times.append(record_dt)
                kp_vals.append(float(row.get("Kp", 0) or 0))
                flux_vals.append(float(row.get("SolarFlux", 0) or 0))
                muf_vals.append(float(row.get("MUF", 0) or 0))
                luf_vals.append(float(row.get("LUF", 0) or 0))
    except FileNotFoundError:
        messagebox.showinfo("Plot History", f"No log file found yet ({log_path}).")
        return

    if not times:
        messagebox.showinfo("Plot History", f"No log rows found for {query}.")
        return

    fig, ax1 = compat.plt.subplots(figsize=(8, 5), dpi=100)
    ax1.set_facecolor("#0B1220")
    ax1.tick_params(colors="white")
    for spine in ax1.spines.values():
        spine.set_color("white")
    ax1.set_title(f"OrbitRx History ({query})", color="white")
    ax1.plot(times, kp_vals, label="Kp", color="cyan", marker="o")
    ax1.plot(times, flux_vals, label="Solar Flux", color="yellow", marker="o")

    ax2 = ax1.twinx()
    ax2.plot(times, muf_vals, label="MUF", color="lime", marker="x")
    ax2.plot(times, luf_vals, label="LUF", color="magenta", marker="x")
    ax2.tick_params(colors="white")

    ax1.set_xlabel("Time (UTC)", color="white")
    ax1.set_ylabel("Kp / Solar Flux", color="white")
    ax2.set_ylabel("MUF/LUF MHz", color="white")

    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="upper left", facecolor="#122437", framealpha=0.9)

    plot_window = tk.Toplevel(ctx.ui.window)
    plot_window.title("History Plot")

    canvas_plot = compat.FigureCanvasTkAgg(fig, master=plot_window)
    canvas_plot.draw()
    canvas_plot.get_tk_widget().pack(fill="both", expand=True)

    toolbar_frame = tk.Frame(plot_window)
    toolbar_frame.pack(fill="x")
    try:
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk

        toolbar = NavigationToolbar2Tk(canvas_plot, toolbar_frame)
        toolbar.update()
    except Exception:
        pass
