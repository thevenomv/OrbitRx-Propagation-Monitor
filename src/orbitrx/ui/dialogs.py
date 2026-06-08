"""Dialog windows for help and exports."""

from __future__ import annotations

import datetime
import shutil

import tkinter as tk
from tkinter import filedialog, messagebox

from orbitrx.models.context import AppContext
from orbitrx.paths import get_log_path
from orbitrx.services.logging import dx_log_file_path, init_dx_log_file


def export_dx_log() -> None:
    try:
        dst = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile="dx_spots_log.csv",
            filetypes=[("CSV Files", "*.csv")],
            title="Save DX Log As...",
        )
        if dst:
            src = get_log_path("dx_spots_log.csv")
            if not src.exists():
                init_dx_log_file()
            shutil.copy(src, dst)
            messagebox.showinfo("Export Successful", f"DX Log successfully saved to:\n{dst}")
    except Exception as exc:
        messagebox.showerror("Export Error", f"Could not export DX log:\n{exc}")


def show_user_guide(ctx: AppContext) -> None:
    guide_window = tk.Toplevel(ctx.ui.window)
    guide_window.title("User Guide - OrbitRx Propagation Monitor")
    guide_window.geometry("600x700")
    guide_window.configure(bg="#0B1220")

    tk.Label(
        guide_window,
        text="OrbitRx Propagation Monitor - User Guide",
        font=("Segoe UI", 14, "bold"),
        bg="#0B1220",
        fg="#81D4FA",
    ).pack(fill="x", padx=12, pady=12)

    frame_scroll = tk.Frame(guide_window, bg="#0E162B", bd=1, relief="solid")
    frame_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    scrollbar = tk.Scrollbar(frame_scroll, bg="#1E2A40")
    scrollbar.pack(side="right", fill="y")

    text_guide = tk.Text(
        frame_scroll, bg="#0E162B", fg="#E0E8FF", font=("Segoe UI", 10),
        yscrollcommand=scrollbar.set, wrap="word", bd=0, padx=12, pady=12,
    )
    text_guide.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=text_guide.yview)
    text_guide.config(state="disabled")

    def update_guide_content() -> None:
        state = ctx.state
        text_guide.config(state="normal")
        text_guide.delete("1.0", "end")
        log_path = get_log_path("propagation_log.csv")
        guide_text = f"""
=== OVERVIEW ===
The OrbitRx Propagation Monitor monitors real-time space weather data from NOAA and calculates optimal HF radio propagation conditions.

=== KEY METRICS ===
Kp Index: {state.kp_index}
Solar Flux: {state.flux}
MUF: {state.muf} MHz
LUF: {state.luf} MHz
Band Conditions: {state.bands}

=== DATA PERSISTENCE ===
Logs are stored in: {log_path}
DX log: {dx_log_file_path()}

Generated: {datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
"""
        text_guide.insert("end", guide_text)
        text_guide.config(state="disabled")

    update_guide_content()
    guide_window.after(5000, update_guide_content)
