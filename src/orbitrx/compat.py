"""Optional dependency detection."""

import platform

USE_CUSTOMTK = False
PLOT_AVAILABLE = False
CALENDAR_AVAILABLE = False
CAT_AVAILABLE = False
winsound = None

try:
    import customtkinter as ctk

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    USE_CUSTOMTK = True
except Exception:
    ctk = None

try:
    import matplotlib

    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    PLOT_AVAILABLE = True
except Exception:
    plt = None
    FigureCanvasTkAgg = None

try:
    from tkcalendar import DateEntry

    CALENDAR_AVAILABLE = True
except Exception:
    DateEntry = None

try:
    import serial

    CAT_AVAILABLE = True
except Exception:
    serial = None

try:
    if platform.system() == "Windows":
        import winsound
except Exception:
    winsound = None
