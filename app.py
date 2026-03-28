import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
import urllib.request
import json
import threading
import socket
import time
import datetime
import csv
import os
import platform

USE_CUSTOMTK = False
try:
    import customtkinter as ctk
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    USE_CUSTOMTK = True
except Exception:
    ctk = None

try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    PLOT_AVAILABLE = True
except Exception:
    PLOT_AVAILABLE = False

try:
    from tkcalendar import DateEntry
    CALENDAR_AVAILABLE = True
except Exception:
    CALENDAR_AVAILABLE = False

try:
    import serial
    CAT_AVAILABLE = True
except Exception:
    serial = None
    CAT_AVAILABLE = False

try:
    if platform.system() == 'Windows':
        import winsound
except Exception:
    winsound = None

import math
import datetime
import csv
import os
from PIL import Image, ImageTk
from functools import lru_cache

# --- USER LOCATION ---
user_lat = None
user_lon = None
latest_dx_spots = []
latest_dx_canvas_points = []

# CAT radio control defaults
CAT_PORT = 'COM3'
CAT_BAUD = 9600
CAT_TIMEOUT = 0.5
serial_conn = None

# DX cluster
DX_CLUSTER_HOST = 've7cc.net'
DX_CLUSTER_PORT = 23
cluster_active = False
cluster_thread = None
dx_update_pending = False

# Alert rules
ALERT_KP_THRESHOLD = 2
ALERT_MUF_THRESHOLD = 28
ALERT_LAST = None

# Time travel slider state
slider_offset_hours = 0

# Global metrics to ensure safe access
kp_index = 0
flux = None
muf = None
luf = None
bands = "--"

def fetch_json(url):
    """Helper function to fetch JSON data with a standard web browser User-Agent."""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read())

def update_user_location():
    global user_lat, user_lon
    try:
        # Use a public geolocation API to estimate user coordinates based on IP
        url = "https://ipinfo.io/json"
        response = urllib.request.urlopen(url, timeout=5)
        info = json.loads(response.read())

        if "loc" in info:
            loc = info["loc"].split(",")
            user_lat = float(loc[0])
            user_lon = float(loc[1])
            lbl_location.config(text=f"You: {user_lat:.3f}°, {user_lon:.3f}°")
        else:
            lbl_location.config(text="You: location unknown")
    except Exception as e:
        user_lat = None
        user_lon = None
        lbl_location.config(text="You: location unknown")
        print("Location API failed:", e)


# --- UTILS ---
def sun_times(lat, lon, when):
    day_of_year = when.timetuple().tm_yday
    decl = 23.44 * math.sin(math.radians((360/365.25) * (day_of_year - 81)))
    lat_rad = math.radians(lat)
    decl_rad = math.radians(decl)
    cos_omega = -math.tan(lat_rad) * math.tan(decl_rad)
    if cos_omega >= 1 or cos_omega <= -1:
        return None, None
    omega = math.degrees(math.acos(cos_omega))
    noon_utc = 12 - (lon / 15.0)
    sunrise_utc = (noon_utc - omega / 15.0) % 24
    sunset_utc = (noon_utc + omega / 15.0) % 24
    return sunrise_utc, sunset_utc


def estimate_muf(flux, kp):
    if flux is None:
        return None, None
    base_muf = 4 + flux * 0.25
    disturbance = 1.0 - (kp / 20.0)
    muf = base_muf * max(0.5, min(disturbance, 1.0))
    luf = max(1.5, base_muf * 0.25)
    return round(muf, 1), round(luf, 1)


def parse_history_query(q):
    """Parse a history query string into start and end UTC datetimes."""
    q = q.strip()
    if not q:
        raise ValueError("Empty query")

    def to_dt(token):
        token = token.strip()
        if len(token) == 10 and token.count('-') == 2:
            return datetime.datetime.fromisoformat(token + 'T00:00:00+00:00')
        return datetime.datetime.fromisoformat(token)

    # range format, e.g. 2026-03-28:2026-03-30 or datetime range
    if ':' in q and q.count(':') == 1 and 'T' not in q:
        from_date, to_date = q.split(':', 1)
        start = to_dt(from_date)
        end = to_dt(to_date)
        if start.tzinfo is None:
            start = start.replace(tzinfo=datetime.timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=datetime.timezone.utc)

        # End date inclusive for date-only (increment by day)
        if len(to_date.strip()) == 10 and to_date.count('-') == 2:
            end = end + datetime.timedelta(days=1)

        return start, end

    start = to_dt(q)
    if start.tzinfo is None:
        start = start.replace(tzinfo=datetime.timezone.utc)

    if len(q) == 10 and q.count('-') == 2:
        return start, start + datetime.timedelta(days=1)

    return start, start


# --- DATA LOGGING & STORAGE ---
LOG_FILE = "propagation_log.csv"
DX_LOG_FILE = "dx_spots_log.csv"

def init_dx_log_file():
    if not os.path.exists(DX_LOG_FILE):
        with open(DX_LOG_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Spotter", "To_Station", "Frequency_MHz"])

def log_dx_spot(spotter, to_station, freq):
    try:
        init_dx_log_file()
        with open(DX_LOG_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([datetime.datetime.now(datetime.timezone.utc).isoformat(), spotter, to_station, freq])
    except Exception as e:
        print("DX log error:", e)

def init_log_file():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Kp", "SolarFlux", "Sunspot", "MUF", "LUF", "BandCondition", "Lat", "Lon"])

def log_data(kp, flux, sunspot, muf, luf, band_cond, lat, lon):
    try:
        init_log_file()
        with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Remove emoji from band_cond for CSV compatibility
            sanitized_cond = band_cond.split(":")[1].strip() if ":" in band_cond else str(band_cond)[:50]
            writer.writerow([
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
                kp, flux, sunspot, muf, luf, sanitized_cond, lat or "--", lon or "--"
            ])
    except Exception as e:
        print("Log error:", e)

def export_json():
    try:
        data = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "kp_index": kp_index if 'kp_index' in globals() else None,
            "solar_flux": flux if 'flux' in globals() else None,
            "user_location": {"lat": user_lat, "lon": user_lon},
            "log_file": LOG_FILE
        }
        with open("export.json", "w") as f:
            json.dump(data, f, indent=2)
        return "export.json"
    except Exception as e:
        print("JSON export error:", e)
        return None


def view_history(query):
    """Look up historical log entries by ISO date, date-only, or exact datetime."""
    if not query:
        return

    try:
        start_dt, end_dt = parse_history_query(query)
    except ValueError as err:
        messagebox.showwarning("History Lookup", f"Invalid date/time format:\n{err}")
        return

    matches = []
    try:
        with open(LOG_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = row.get('Timestamp')
                if not ts:
                    continue
                try:
                    record_dt = datetime.datetime.fromisoformat(ts)
                except Exception:
                    continue

                if start_dt == end_dt:
                    if record_dt == start_dt:
                        matches.append(row)
                else:
                    if start_dt <= record_dt < end_dt:
                        matches.append(row)
    except FileNotFoundError:
        messagebox.showinfo("History Lookup", "No log file found yet (propagation_log.csv).")
        return

    if not matches:
        tk.messagebox.showinfo("History Lookup", f"No history entries found for {query}.")
        return

    # show match details in popup
    popup = tk.Toplevel(window)
    popup.title('History Results')

    text = tk.Text(popup, width=100, height=20, wrap='none', bg='#0E162B', fg='white', font=('Segoe UI', 10))
    text.pack(fill='both', expand=True)

    text.insert('end', f"History results for {query} (found {len(matches)} entries)\n\n")
    for row in matches:
        text.insert('end', json.dumps(row, indent=2) + '\n\n')

    text.configure(state='disabled')
    # Add scrollbars
    scroll_y = tk.Scrollbar(popup, orient='vertical', command=text.yview)
    text.configure(yscrollcommand=scroll_y.set)
    scroll_y.pack(side='right', fill='y')


def plot_history(query):
    """Plot history values from propagation_log.csv for the given date or exact timestamp."""
    if not PLOT_AVAILABLE:
        messagebox.showerror("Plot History", "Matplotlib is required for plotting. Install it with 'pip install matplotlib'.")
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

    try:
        with open(LOG_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = row.get('Timestamp')
                if not ts:
                    continue
                try:
                    record_dt = datetime.datetime.fromisoformat(ts)
                except Exception:
                    continue

                if start_dt == end_dt:
                    if record_dt != start_dt:
                        continue
                else:
                    if not (start_dt <= record_dt < end_dt):
                        continue

                times.append(record_dt)
                kp_vals.append(float(row.get('Kp', 0) or 0))
                flux_vals.append(float(row.get('SolarFlux', 0) or 0))
                muf_vals.append(float(row.get('MUF', 0) or 0))
                luf_vals.append(float(row.get('LUF', 0) or 0))
    except FileNotFoundError:
        messagebox.showinfo("Plot History", "No log file found yet (propagation_log.csv).")
        return

    if not times:
        messagebox.showinfo("Plot History", f"No log rows found for {query}.")
        return

    fig, ax1 = plt.subplots(figsize=(8, 5), dpi=100)
    ax1.set_facecolor('#0B1220')
    ax1.tick_params(colors='white')
    ax1.spines['bottom'].set_color('white')
    ax1.spines['left'].set_color('white')
    ax1.spines['top'].set_color('white')
    ax1.spines['right'].set_color('white')
    ax1.set_title(f"OrbitRx History ({query})", color='white')
    ax1.plot(times, kp_vals, label='Kp', color='cyan', marker='o')
    ax1.plot(times, flux_vals, label='Solar Flux', color='yellow', marker='o')

    ax2 = ax1.twinx()
    ax2.plot(times, muf_vals, label='MUF', color='lime', marker='x')
    ax2.plot(times, luf_vals, label='LUF', color='magenta', marker='x')
    ax2.tick_params(colors='white')

    ax1.set_xlabel('Time (UTC)', color='white')
    ax1.set_ylabel('Kp / Solar Flux', color='white')
    ax2.set_ylabel('MUF/LUF MHz', color='white')

    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc='upper left', facecolor='#122437', framealpha=0.9)

    plot_window = tk.Toplevel(window)
    plot_window.title('History Plot')

    canvas_plot = FigureCanvasTkAgg(fig, master=plot_window)
    canvas_plot.draw()
    canvas_plot.get_tk_widget().pack(fill='both', expand=True)

    toolbar_frame = tk.Frame(plot_window)
    toolbar_frame.pack(fill='x')
    try:
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        toolbar = NavigationToolbar2Tk(canvas_plot, toolbar_frame)
        toolbar.update()
    except Exception:
        pass


# --- MULTI-BAND PROPAGATION ---
HF_BANDS = {
    "160m": {"freq": 1.8, "name": "160 Meters", "color": "#FF6B6B"},
    "80m": {"freq": 3.5, "name": "80 Meters", "color": "#FF8C42"},
    "40m": {"freq": 7.0, "name": "40 Meters", "color": "#FFD93D"},
    "20m": {"freq": 14.0, "name": "20 Meters", "color": "#6BCB77"},
    "15m": {"freq": 21.0, "name": "15 Meters", "color": "#4D96FF"},
    "10m": {"freq": 28.0, "name": "10 Meters", "color": "#A78BFA"}
}

def band_condition(freq_mhz, flux, kp):
    if flux is None:
        return "UNKNOWN"
    base_score = (flux / 150.0) - (kp / 10.0)
    if base_score > 1.0:
        return "OPEN"
    elif base_score > 0.5:
        return "FAIR"
    else:
        return "CLOSED"


# --- CONTEST & EVENT SCHEDULE ---
UPCOMING_CONTESTS = [
    {"name": "ARCI Spring QSO Party", "date": "2026-04-04", "bands": ["160m", "80m", "40m", "20m", "15m", "10m"]},
    {"name": "CQ WW WPX SSB", "date": "2026-03-28", "bands": ["All HF"]},
    {"name": "RSGB IOTA Contest", "date": "2026-07-26", "bands": ["All HF", "VHF", "UHF"]},
]

def get_next_contest():
    now = datetime.datetime.now()
    for contest in UPCOMING_CONTESTS:
        contest_date = datetime.datetime.strptime(contest["date"], "%Y-%m-%d")
        if contest_date >= now:
            return contest
    return None


# --- DX SPOT FETCHER ---
DX_COORDINATES = {
    "W5XYZ": (30.2683, -97.7448),   # Austin TX
    "PY2AB": (-22.9068, -43.1729), # Rio de Janeiro BR
    "VE3ABC": (45.4215, -75.6972), # Ottawa CA
    "XU7AJ": (11.5621, 104.8885),  # Phnom Penh KH
}

PREFIX_MAP = {
    'W': (38.0, -97.0), 'K': (38.0, -97.0), 'N': (38.0, -97.0), 'A': (38.0, -97.0),
    'VE': (56.0, -106.0), 'VA': (56.0, -106.0), 'VY': (56.0, -106.0),
    'XE': (23.0, -102.0),
    'PY': (-14.0, -51.0), 'PU': (-14.0, -51.0),
    'LU': (-38.0, -63.0), 'LW': (-38.0, -63.0),
    'CE': (-35.0, -71.0),
    'G': (52.0, -1.0), 'M': (52.0, -1.0), '2': (52.0, -1.0),
    'F': (46.0, 2.0),
    'D': (51.0, 9.0),
    'I': (41.0, 12.0), 'IZ': (41.0, 12.0), 'IN': (41.0, 12.0), 'IT': (41.0, 12.0),
    'EA': (40.0, -4.0), 'EB': (40.0, -4.0),
    'CT': (39.0, -8.0),
    'HB': (46.0, 8.0),
    'OE': (47.0, 14.0),
    'SP': (52.0, 19.0), 'SQ': (52.0, 19.0),
    'OK': (49.0, 15.0),
    'OM': (48.0, 19.0),
    'UR': (48.0, 31.0), 'UT': (48.0, 31.0), 'UY': (48.0, 31.0), 'UZ': (48.0, 31.0),
    'R': (55.0, 60.0), 'U': (55.0, 60.0), 'RX': (55.0, 60.0),
    'JA': (36.0, 138.0), 'JH': (36.0, 138.0), 'JR': (36.0, 138.0), 'JE': (36.0, 138.0),
    'VK': (-25.0, 133.0),
    'ZL': (-40.0, 174.0),
    'ZS': (-30.0, 25.0), 'ZR': (-30.0, 25.0),
    'VU': (20.0, 77.0),
    'BY': (35.0, 104.0), 'BG': (35.0, 104.0),
    'YB': (-0.7, 113.0),
    'HS': (15.0, 100.0),
    '9M': (4.0, 109.0),
    '9V': (1.3, 103.0),
    'VR': (22.0, 114.0),
    'HL': (35.0, 127.0), 'DS': (35.0, 127.0),
    'DU': (12.0, 121.0),
    '4X': (31.0, 34.0), '4Z': (31.0, 34.0),
    'TA': (39.0, 35.0),
    'LA': (60.0, 10.0),
    'SM': (59.0, 15.0),
    'OH': (61.0, 25.0),
    'OZ': (56.0, 10.0),
    'PA': (52.0, 5.0), 'PB': (52.0, 5.0), 'PC': (52.0, 5.0), 'PD': (52.0, 5.0),
}

def estimate_location(callsign):
    import random
    call = callsign.upper().strip()
    # Try to match the callsign prefix to known coordinates
    for prefix in sorted(PREFIX_MAP.keys(), key=len, reverse=True):
        if call.startswith(prefix):
            lat, lon = PREFIX_MAP[prefix]
            # Add jitter to spread out spots within the same country
            return (lat + random.uniform(-3, 3), lon + random.uniform(-3, 3))
    
    # Fallback to major landmass bounding boxes if prefix is unknown
    land_boxes = [
        (30, 50, -120, -70),   # North America
        (-30, 10, -80, -50),   # South America
        (40, 60, -10, 30),     # Europe
        (-20, 30, 10, 40),     # Africa
        (30, 60, 60, 120),     # Asia
        (-30, -15, 115, 145),  # Australia
    ]
    box = random.choice(land_boxes)
    return (random.uniform(box[0], box[1]), random.uniform(box[2], box[3]))

def start_dx_cluster():
    global cluster_active, cluster_thread
    if cluster_active: return
    cluster_active = True
    cluster_thread = threading.Thread(target=dx_cluster_task, daemon=True)
    cluster_thread.start()

def dx_cluster_task():
    global latest_dx_spots, cluster_active, dx_update_pending
    import random
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((DX_CLUSTER_HOST, DX_CLUSTER_PORT))
        
        # Wait for the server login prompt and clear the buffer
        time.sleep(1.5)
        try:
            s.recv(1024)
        except socket.timeout:
            pass
        # Many nodes block 'N0CALL' and 'GUEST', use a valid format instead
        s.sendall(b"W1AW-9\r\n")
        s.settimeout(None)
        
        buffer = ""
        while cluster_active:
            data = s.recv(1024)
            if not data: break
            buffer += data.decode('ascii', errors='ignore')
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                if line.startswith("DX de"):
                    parts = line.split()
                    if len(parts) >= 5:
                        spotter = parts[2].strip(':')
                        freq = parts[3]
                        to_station = parts[4]
                        spot = {"from": spotter, "to": to_station, "freq": freq, "time": time.time()}
                        
                        log_dx_spot(spotter, to_station, freq)
                        
                        if spotter not in DX_COORDINATES:
                            DX_COORDINATES[spotter] = estimate_location(spotter)
                        if to_station not in DX_COORDINATES:
                            DX_COORDINATES[to_station] = estimate_location(to_station)
                        
                        latest_dx_spots.insert(0, spot)
                        latest_dx_spots = latest_dx_spots[:50]
                        
                        # Throttle UI updates so a flood of spots doesn't freeze the map
                        if not dx_update_pending:
                            dx_update_pending = True
                            window.after(1000, update_dx_ui)
    except Exception as e:
        print("DX Cluster disconnected:", e)
        cluster_active = False

def update_dx_ui():
    global dx_update_pending, latest_dx_spots
    dx_update_pending = False
    
    current_time = time.time()
    latest_dx_spots = [s for s in latest_dx_spots if current_time - s.get("time", current_time) < 300]
    
    if latest_dx_spots:
        dx_text = " | ".join([f"{s['from']}→{s['to']} {s['freq']} MHz" for s in latest_dx_spots[:2]])
        lbl_dx.config(text="Live DX: " + dx_text)
    else:
        lbl_dx.config(text="Live DX: --")
        draw_greyline()

def tune_radio(freq_mhz):
    try:
        freq_val = float(freq_mhz)
        messagebox.showinfo("CAT Control", f"Tuning physical radio to {freq_mhz} MHz...\n(Ensure {CAT_PORT} is connected)")
        if not CAT_AVAILABLE:
            print(f"pyserial not available. Would have tuned to {freq_val} MHz")
            return
        freq_hz = int(freq_val * 1000000)
        cmd = f"FA{freq_hz:011d};".encode('ascii')
        with serial.Serial(CAT_PORT, CAT_BAUD, timeout=CAT_TIMEOUT) as ser:
            ser.write(cmd)
        print(f"Sent CAT command: {cmd}")
    except Exception as e:
        print(f"CAT Control Error: {e}")


# --- 27-DAY SOLAR CYCLE FORECAST ---
def get_solar_cycle_forecast():
    try:
        url = "https://services.swpc.noaa.gov/products/solar-cycle-25-f10-7-predicted-range.json"
        data = fetch_json(url)
        
        now = datetime.datetime.now(datetime.timezone.utc)
        this_month = f"{now.year}-{now.month:02d}"
        
        if isinstance(data, list):
            match = next((item for item in data if isinstance(item, dict) and item.get("time-tag") == this_month), None)
            if not match and len(data) > 0:
                match = data[-1]
                
            if isinstance(match, dict):
                f_low = match.get('smoothed_f10.7_min', match.get('f10.7_min', match.get('low', '--')))
                f_high = match.get('smoothed_f10.7_max', match.get('f10.7_max', match.get('high', '--')))
                return f"F10.7 low: {f_low}, high: {f_high}"
                
        return "F10.7: --"
    except Exception as e:
        print("Solar cycle forecast error:", e)
        return "F10.7: --"


# --- NOAA SATELLITE DATA ---
def get_space_weather():
    global kp_index, flux, muf, luf, bands
    try:
        btn_refresh.config(text="Fetching Satellite Data...")
        window.update()

        url = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
        data = fetch_json(url)
        
        time_utc = "--"
        kp_index = 0
        for row in reversed(data):
            if isinstance(row, list) and len(row) > 1 and row[1] not in ("Kp", "", None):
                try:
                    kp_index = float(row[1])
                    time_utc = row[0]
                    break
                except ValueError:
                    continue
        
        if kp_index <= 3: status = "🟢 GOOD: Stable Ionosphere."
        elif kp_index <= 5: status = "🟡 FAIR: Minor Geomagnetic Activity."
        else: status = "🔴 POOR: Geomagnetic Storm. HF blackouts likely."

        lbl_kp.config(text=f"Current Kp Index: {kp_index}")
        lbl_status.config(text=status)
        lbl_time.config(text=f"Last NOAA Update: {time_utc} UTC")
        
        # Fetch Solar Flux (10cm flux)
        flux = None
        try:
            url2 = "https://services.swpc.noaa.gov/products/10cm-flux-30-day.json"
            data2 = fetch_json(url2)
            for row in reversed(data2):
                if isinstance(row, list) and len(row) > 1 and row[1] not in ("flux", "", None):
                    try:
                        flux = float(row[1])
                        break
                    except ValueError:
                        continue
            lbl_solar.config(text=f"Solar Flux: {flux}")
        except Exception as e:
            lbl_solar.config(text="Solar Flux: --")
            print("Solar flux fetch error:", e)

        # Fetch Sunspot Number (use monthly SSN prediction range if actual endpoint is not available)
        sunspot = None
        try:
            url3 = "https://services.swpc.noaa.gov/products/solar-cycle-25-ssn-predicted-range.json"
            data3 = fetch_json(url3)
            now = datetime.datetime.now(datetime.timezone.utc)
            this_month = f"{now.year}-{now.month:02d}"
            match = next((item for item in data3 if item.get("time-tag") == this_month), None)
            if match:
                sunspot = (float(match.get("smoothed_ssn_min", 0)) + float(match.get("smoothed_ssn_max", 0))) / 2
                lbl_sunspot.config(text=f"Sunspot Number (pred): {sunspot:.1f}")
            else:
                lbl_sunspot.config(text="Sunspot Number: --")
        except Exception as e:
            lbl_sunspot.config(text="Sunspot Number: --")
            print("Sunspot fetch error:", e)

        # SWPC Alerts
        try:
            url_alerts = "https://services.swpc.noaa.gov/products/alerts.json"
            data_alerts = fetch_json(url_alerts)
            alerts = []
            for row in data_alerts[:3]:
                if isinstance(row, list) and len(row) >= 2:
                    alerts.append(f"{row[0]} {row[1]}")
            lbl_alerts.config(text="Alerts: " + (" | ".join(alerts) if alerts else "none"))
        except Exception as e:
            lbl_alerts.config(text="Alerts: --")
            print("Alerts fetch error:", e)

        # Kp Forecast
        kp_forecast = "--"
        try:
            url4 = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json"
            data4 = fetch_json(url4)
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
            lbl_kp_forecast.config(text=f"Kp Forecast: {kp_forecast}")
        except Exception as e:
            lbl_kp_forecast.config(text="Kp Forecast: --")
            print("Kp forecast fetch error:", e)

        # Sunrise/sunset
        if user_lat is not None and user_lon is not None:
            sunrise, sunset = sun_times(user_lat, user_lon, datetime.datetime.now(datetime.timezone.utc))
            if sunrise is not None:
                lbl_sunrise.config(text=f"Sunrise (UTC): {sunrise:.2f}")
                lbl_sunset.config(text=f"Sunset (UTC): {sunset:.2f}")
            else:
                lbl_sunrise.config(text="Sunrise (UTC): N/A")
                lbl_sunset.config(text="Sunset (UTC): N/A")
        else:
            lbl_sunrise.config(text="Sunrise (UTC): --")
            lbl_sunset.config(text="Sunset (UTC): --")

        # MUF/LOF estimate
        muf, luf = estimate_muf(flux, kp_index)
        if muf is not None:
            lbl_muf.config(text=f"MUF est: {muf} MHz, LUF est: {luf} MHz")
        else:
            lbl_muf.config(text="MUF est: --")

        # Determine Band Conditions
        try:
            if kp_index <= 3 and flux is not None and flux > 120:
                bands = "🟢 EXCELLENT: All HF bands open for DX"
            elif kp_index <= 5 and flux is not None and flux > 100:
                bands = "🟡 GOOD: Most HF bands workable"
            else:
                bands = "🔴 POOR: Limited HF propagation"
            lbl_bands.config(text=f"Band Conditions: {bands}")
        except Exception as e:
            lbl_bands.config(text="Band Conditions: --")
            print("Band conditions calc error:", e)

        # Log data for trend analysis
        log_data(kp_index, flux, sunspot, muf if muf else "--", luf if luf else "--", bands if bands else "--", user_lat, user_lon)

        # Update advanced features
        try:
            solar_forecast = get_solar_cycle_forecast()
            lbl_solar_forecast.config(text=f"27-Day Forecast: {solar_forecast}")
        except:
            lbl_solar_forecast.config(text="27-Day Forecast: --")

        try:
            next_contest = get_next_contest()
            if next_contest:
                lbl_contest.config(text=f"Next: {next_contest['name']} ({next_contest['date']})")
            else:
                lbl_contest.config(text="Next Contest: none scheduled")
        except:
            lbl_contest.config(text="Next Contest: --")

        # Propagation Alarm Logic
        global ALERT_LAST
        if muf is not None and muf >= ALERT_MUF_THRESHOLD and kp_index <= ALERT_KP_THRESHOLD:
            now_dt = datetime.datetime.now()
            if ALERT_LAST is None or (now_dt - ALERT_LAST).total_seconds() > 3600:
                ALERT_LAST = now_dt
                if winsound:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                
                alert_win = tk.Toplevel(window)
                alert_win.title("Propagation Alarm!")
                alert_win.attributes('-topmost', True)
                tk.Label(alert_win, text=f"🚨 EXCELLENT CONDITIONS DETECTED! 🚨\n\nKp Index: {kp_index}\nMUF: {muf} MHz\n\n10m is OPEN!", font=("Segoe UI", 12, "bold"), fg="#FF0000", padx=20, pady=20).pack()
                tk.Button(alert_win, text="Tune Radio to 28.074 (FT8)", command=lambda: tune_radio("28.074"), font=("Segoe UI", 10)).pack(pady=5)
                tk.Button(alert_win, text="Dismiss", command=alert_win.destroy, font=("Segoe UI", 10)).pack(pady=5)
        
    except Exception as e:
        lbl_status.config(text=f"Error connecting: {e}")
        lbl_solar.config(text="Solar Flux: --")
        lbl_sunspot.config(text="Sunspot Number: --")
        lbl_bands.config(text="Band Conditions: --")
        print("Space weather fetch error:", e)
    finally:
        btn_refresh.config(text="Refresh Space Weather")

# --- GREYLINE MATH & DRAWING ---
def draw_greyline():
    canvas.delete("all")
    width = 700
    height = 560
    
    # 1. Check if we have the map image, otherwise draw the dark grid
    if map_image:
        # Place the image in the center of the canvas
        canvas.create_image(width/2, height/2, image=map_image)
    else:
        # Fallback if the image isn't found
        canvas.create_rectangle(0, 0, width, height, fill="#101820") 
        canvas.create_line(0, height/2, width, height/2, fill="#333", dash=(4,4))
        canvas.create_line(width/2, 0, width/2, height, fill="#333", dash=(4,4))
    
    # 2. Get Time and Math Setup
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=slider_offset_hours)
    day_of_year = now.timetuple().tm_yday
    hour_utc = now.hour + now.minute / 60.0
    
    declination_deg = -23.44 * math.cos(math.radians((360/365.25) * (day_of_year + 10)))
    declination_rad = math.radians(declination_deg)
    
    sun_lon_deg = 180 - (hour_utc * 15)
    sun_lon_rad = math.radians(sun_lon_deg)
    
    # 3. Plot the Wave
    points = []
    for x in range(width + 1):
        lon_deg = (x / width) * 360 - 180
        lon_rad = math.radians(lon_deg)
        
        tan_dec = math.tan(declination_rad)
        if abs(tan_dec) < 0.0001: tan_dec = 0.0001 
        
        tan_lat = -math.cos(lon_rad - sun_lon_rad) / tan_dec
        lat_deg = math.degrees(math.atan(tan_lat))
        
        y = height/2 - (lat_deg / 90) * (height/2)
        points.extend((x, y))
        
    # Night shading based on subsolar longitude
    for x in range(width):
        lon_deg = (x / width) * 360 - 180
        angle_diff = (lon_deg - sun_lon_deg + 180) % 360 - 180
        # Night when absolute hour angle > 90 degrees
        if abs(angle_diff) > 90:
            canvas.create_line(x, 0, x, height, fill="#000000", stipple="gray50")

    # Draw the blazing neon orange terminator line on top of the map
    canvas.create_line(points, fill="#FF4500", width=3, smooth=True)

    # Draw a little text box background so the time is readable over the map
    canvas.create_rectangle(5, 5, 300, 35, fill="#101820", outline="")
    time_text = f"Greyline Calculated @ {now.strftime('%H:%M UTC')}" + (f" (+{slider_offset_hours}h)" if slider_offset_hours > 0 else "")
    canvas.create_text(10, 10, anchor="nw", text=time_text, fill="white", font=("Arial", 11))

    def world_to_canvas(lat, lon):
        cx = ((lon + 180) / 360) * width
        cy = (height / 2) - ((lat / 90) * (height / 2))
        return cx, cy

    # Plot user location marker if available
    if user_lat is not None and user_lon is not None:
        px, py = world_to_canvas(user_lat, user_lon)
        if 0 <= px <= width and 0 <= py <= height:
            canvas.create_oval(px-7, py-7, px+7, py+7, fill="#00FF00", outline="#00FF00", width=2)
            canvas.create_text(px + 12, py - 10, text="You", fill="white", font=("Arial", 11, "bold"), anchor="w")

            # Plot DX arcs from user to each spot
            for spot in latest_dx_spots:
                from_name = spot.get('from')
                to_name = spot.get('to')
                fpos = DX_COORDINATES.get(from_name)
                tpos = DX_COORDINATES.get(to_name)
                if fpos and tpos:
                    fx, fy = world_to_canvas(fpos[0], fpos[1])
                    tx, ty = world_to_canvas(tpos[0], tpos[1])
                    # If user is one of the endpoints, connect directly
                    if from_name == "W5XYZ" or to_name == "W5XYZ" or True:
                        control_x = (px + fx + tx) / 3
                        control_y = (py + fy + ty) / 3 - 40
                        canvas.create_line(px, py, control_x, control_y, tx, ty, smooth=True, fill="#00FFFF", width=2, dash=(4,2))
                    # mark DX spots
                    canvas.create_oval(tx-5, ty-5, tx+5, ty+5, fill="#FF00FF", outline="#FFFFFF")
                    canvas.create_text(tx + 8, ty - 8, text=f"{from_name}->{to_name}", fill="#FFFF66", font=("Arial", 9), anchor="w")

# --- AUTO-REFRESH TIMER ---
def auto_refresh():
    global latest_dx_spots
    current_time = time.time()
    latest_dx_spots = [s for s in latest_dx_spots if current_time - s.get("time", current_time) < 300]
    
    update_user_location()
    get_space_weather()
    update_dx_ui()
    window.after(60000, auto_refresh)

# --- USER INTERFACE (UI) SETUP ---
if USE_CUSTOMTK:
    window = ctk.CTk()
    window.title("OrbitRx Propagation Monitor")
    window.geometry("1300x700")
    window.configure(padx=16, pady=16)
else:
    window = tk.Tk()
    window.title("OrbitRx Propagation Monitor")
    window.geometry("1300x700")
    window.configure(padx=16, pady=16, bg="#0B1220")

# Load the image into memory right as the window is created
if not os.path.exists('world_map.jpg'):
    try:
        from generate_map import generate_world_map
        generate_world_map(1600, 800)
    except Exception as e:
        print(f'[WARN] Could not generate or download map: {e}')

try:
    original_map = Image.open('world_map.jpg')
    # Scale to fit canvas with high-quality resampling (LANCZOS)
    original_map = original_map.resize((700, 560), Image.Resampling.LANCZOS)
    map_image = ImageTk.PhotoImage(original_map)
except Exception as e:
    map_image = None
    print('Could not find or load world_map.jpg. Make sure it is in the same folder as app.py!', e)

# Title section
frame_title = tk.Frame(window, bg="#0B1220")
frame_title.pack(fill="x", pady=(0, 12))

lbl_title = tk.Label(frame_title, text="OrbitRx Propagation Monitor", font=("Segoe UI", 20, "bold"), bg="#0B1220", fg="#E7EBFF")
lbl_title.pack()

sep = tk.Frame(window, height=2, bg="#1E2A40", bd=0)
sep.pack(fill="x", pady=(0, 12))

# Main content frame with side-by-side layout
frame_content = tk.Frame(window, bg="#0B1220")
frame_content.pack(fill="both", expand=True, pady=(0, 12))

# Map panel (LEFT side - larger)
panel_map = tk.Frame(frame_content, bg="#0E162B", bd=1, relief="solid")
panel_map.pack(side="left", fill="both", expand=True, padx=(0, 12))

canvas = tk.Canvas(panel_map, width=700, height=560, bg="#101820", highlightthickness=0)
canvas.pack(padx=8, pady=8)

def on_map_click(event):
    for point in latest_dx_canvas_points:
        tx, ty, freq = point
        if abs(event.x - tx) < 15 and abs(event.y - ty) < 15:
            tune_radio(freq)
            break

canvas.bind("<Button-1>", on_map_click)

lbl_note = tk.Label(panel_map, text="Red line: Greyline (day-night boundary) - optimal for HF radio propagation", font=("Segoe UI", 9), bg="#0E162B", fg="#CCCCCC", anchor="w")
lbl_note.pack(fill="x", padx=8, pady=(0, 10))

# Time Travel Slider
frame_slider = tk.Frame(panel_map, bg="#0E162B")
frame_slider.pack(fill="x", padx=8, pady=(0, 8))
lbl_slider = tk.Label(frame_slider, text="Time Travel: +0.0 hrs", bg="#0E162B", fg="#B3E5FC", font=("Segoe UI", 10, "bold"))
lbl_slider.pack(side="left")
def on_slider(val):
    global slider_offset_hours
    slider_offset_hours = float(val)
    lbl_slider.config(text=f"Time Travel: +{slider_offset_hours:.1f} hrs")
    draw_greyline()
slider = tk.Scale(frame_slider, from_=0, to=24, resolution=0.5, orient="horizontal", command=on_slider, bg="#0E162B", fg="#00A8FF", highlightthickness=0)
slider.pack(side="left", fill="x", expand=True, padx=10)

# Stats panel (RIGHT side)
panel_stats = tk.Frame(frame_content, bg="#0E162B", bd=0, width=300)
panel_stats.pack(side="right", fill="both", padx=0, pady=0)
panel_stats.pack_propagate(False)

card_weather = tk.Frame(panel_stats, bg="#131D35", bd=1, relief="solid")
card_weather.pack(fill="x", padx=10, pady=(4, 8))

card_local = tk.Frame(panel_stats, bg="#131D35", bd=1, relief="solid")
card_local.pack(fill="x", padx=10, pady=(0, 8))

card_dx = tk.Frame(panel_stats, bg="#131D35", bd=1, relief="solid")
card_dx.pack(fill="x", padx=10, pady=(0, 8))

# Space Weather Card
lbl_kp = tk.Label(card_weather, text="Current Kp Index: --", font=("Segoe UI", 15, "bold"), bg="#131D35", fg="#81D4FA", anchor="w")
lbl_kp.pack(fill="x", padx=10, pady=(8, 3))

lbl_kp_forecast = tk.Label(card_weather, text="Kp Forecast: --", font=("Segoe UI", 11), bg="#131D35", fg="#F5F5A5", anchor="w")
lbl_kp_forecast.pack(fill="x", padx=10, pady=2)

lbl_solar = tk.Label(card_weather, text="Solar Flux: --", font=("Segoe UI", 13), bg="#131D35", fg="#BBDEFB", anchor="w")
lbl_solar.pack(fill="x", padx=10, pady=2)

lbl_sunspot = tk.Label(card_weather, text="Sunspot Number: --", font=("Segoe UI", 12), bg="#131D35", fg="#CDDDFE", anchor="w")
lbl_sunspot.pack(fill="x", padx=10, pady=2)

lbl_time = tk.Label(card_weather, text="Last NOAA Update: --", font=("Segoe UI", 10, "italic"), bg="#131D35", fg="#B0BEC5", anchor="w")
lbl_time.pack(fill="x", padx=10, pady=(2, 8))

# Local Station Card
lbl_bands = tk.Label(card_local, text="Band Conditions: --", font=("Segoe UI", 12, "bold"), bg="#131D35", fg="#96CEB4", anchor="w")
lbl_bands.pack(anchor="w", padx=10, pady=(8, 6))

lbl_muf = tk.Label(card_local, text="MUF est: --", font=("Segoe UI", 11), bg="#131D35", fg="#DFE7FF", anchor="w")
lbl_muf.pack(fill="x", padx=10, pady=2)

lbl_sunrise = tk.Label(card_local, text="Sunrise (UTC): --", font=("Segoe UI", 10), bg="#131D35", fg="#CDDDFE", anchor="w")
lbl_sunrise.pack(fill="x", padx=10, pady=1)

lbl_sunset = tk.Label(card_local, text="Sunset (UTC): --", font=("Segoe UI", 10), bg="#131D35", fg="#CDDDFE", anchor="w")
lbl_sunset.pack(fill="x", padx=10, pady=1)

lbl_alerts = tk.Label(card_local, text="Alerts: --", font=("Segoe UI", 10), bg="#131D35", fg="#FFA0A0", anchor="w")
lbl_alerts.pack(fill="x", padx=10, pady=2)

lbl_location = tk.Label(card_local, text="You: locating...", font=("Segoe UI", 10), fg="#E0E8FF", bg="#131D35", anchor="w")
lbl_location.pack(fill="x", padx=10, pady=(2, 8))

lbl_status = tk.Label(card_local, text="Click refresh to load live satellite data.", font=("Segoe UI", 11, "italic"), bg="#131D35", fg="white", anchor="w")
lbl_status.pack(fill="x", padx=10, pady=5)

# DX & Events Card
lbl_solar_forecast = tk.Label(card_dx, text="27-Day Forecast: --", font=("Segoe UI", 10), bg="#131D35", fg="#B3E5FC", anchor="w")
lbl_solar_forecast.pack(fill="x", padx=10, pady=(8, 2))

lbl_contest = tk.Label(card_dx, text="Next Contest: --", font=("Segoe UI", 10), bg="#131D35", fg="#FFE082", anchor="w")
lbl_contest.pack(fill="x", padx=10, pady=2)

lbl_dx = tk.Label(card_dx, text="Recent DX: --", font=("Segoe UI", 10), bg="#131D35", fg="#C8E6C9", anchor="w")
lbl_dx.pack(fill="x", padx=10, pady=(2, 8))

# History lookup
lbl_history = tk.Label(card_dx, text="History lookup (Date):", font=("Segoe UI", 10, "bold"), bg="#131D35", fg="#FFD660", anchor="w")
lbl_history.pack(fill="x", padx=10, pady=(6, 2))

if CALENDAR_AVAILABLE:
    entry_history = DateEntry(panel_stats, font=("Segoe UI", 10), width=20, background='#006AFF', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
    entry_history.pack(fill="x", padx=10, pady=(0, 8))
else:
    entry_history = tk.Entry(panel_stats, font=("Segoe UI", 10), width=22)
    entry_history.insert(0, datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"))
    entry_history.pack(fill="x", padx=10, pady=(0, 8))

btn_history = tk.Button(panel_stats, text="View History", command=lambda: view_history(entry_history.get().strip()), bg="#FFB300", fg="black", font=("Segoe UI", 10, "bold"), relief="raised", bd=2)
btn_history.pack(padx=10, pady=(0, 4))

btn_plot = tk.Button(panel_stats, text="Plot History", command=lambda: plot_history(entry_history.get().strip()), bg="#00C853", fg="white", font=("Segoe UI", 10, "bold"), relief="raised", bd=2)
btn_plot.pack(padx=10, pady=(0, 8))

# Controls (BOTTOM - full width)
panel_buttons = tk.Frame(window, bg="#0B1220")
panel_buttons.pack(fill="x", pady=(0, 0))

btn_locate = tk.Button(panel_buttons, text="Refresh Location", command=update_user_location, bg="#006AFF", fg="white", font=("Segoe UI", 10, "bold"), relief="raised", bd=2)
btn_locate.pack(side="left", padx=4)

btn_refresh = tk.Button(panel_buttons, text="Refresh Space Weather", command=auto_refresh, bg="#00A8FF", fg="white", font=("Segoe UI", 10, "bold"), relief="raised", bd=2)
btn_refresh.pack(side="left", padx=4)

btn_export = tk.Button(panel_buttons, text="Export JSON", command=export_json, bg="#9C27B0", fg="white", font=("Segoe UI", 10, "bold"), relief="raised", bd=2)
btn_export.pack(side="left", padx=4)

def export_dx_log():
    try:
        import shutil
        dst = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="dx_spots_log.csv", 
                                           filetypes=[("CSV Files", "*.csv")], title="Save DX Log As...")
        if dst:
            if not os.path.exists(DX_LOG_FILE):
                init_dx_log_file()
            shutil.copy(DX_LOG_FILE, dst)
            messagebox.showinfo("Export Successful", f"DX Log successfully saved to:\n{dst}")
    except Exception as e:
        messagebox.showerror("Export Error", f"Could not export DX log:\n{e}")
        
btn_export_dx = tk.Button(panel_buttons, text="Export DX Log", command=export_dx_log, bg="#FF5722", fg="white", font=("Segoe UI", 10, "bold"), relief="raised", bd=2)
btn_export_dx.pack(side="left", padx=4)

def show_user_guide():
    """Display an interactive user guide window with current app status."""
    guide_window = tk.Toplevel(window)
    guide_window.title("User Guide - OrbitRx Propagation Monitor")
    guide_window.geometry("600x700")
    guide_window.configure(bg="#0B1220")
    
    # Title
    lbl_guide_title = tk.Label(guide_window, text="OrbitRx Propagation Monitor - User Guide", 
                                font=("Segoe UI", 14, "bold"), bg="#0B1220", fg="#81D4FA")
    lbl_guide_title.pack(fill="x", padx=12, pady=12)
    
    # Scrollable text area
    frame_scroll = tk.Frame(guide_window, bg="#0E162B", bd=1, relief="solid")
    frame_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))
    
    scrollbar = tk.Scrollbar(frame_scroll, bg="#1E2A40")
    scrollbar.pack(side="right", fill="y")
    
    text_guide = tk.Text(frame_scroll, bg="#0E162B", fg="#E0E8FF", font=("Segoe UI", 10),
                         yscrollcommand=scrollbar.set, wrap="word", bd=0, padx=12, pady=12)
    text_guide.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=text_guide.yview)
    text_guide.config(state="disabled")  # Read-only
    
    def update_guide_content():
        """Update guide with current app data."""
        text_guide.config(state="normal")
        text_guide.delete("1.0", "end")
        
        guide_text = """
=== OVERVIEW ===
The OrbitRx Propagation Monitor monitors real-time space weather data from NOAA and calculates optimal HF radio propagation conditions using the Kp Index and Solar Flux measurements.

=== MAP DISPLAY (LEFT PANEL) ===
The world map shows:
- Green continents & gridlines (latitude/longitude reference)
- Orange GREYLINE: The day-night boundary, where HF radio propagation is BEST
- Green marker "You": Your current location (when detected)
- Cyan lines: Equator and Prime Meridian

=== KEY METRICS (RIGHT PANEL) ===

Kp Index (0-9 scale)
  Current: """ + (str(kp_index) if 'kp_index' in globals() else "--") + """
  Controls geomagnetic activity. Lower is better for HF propagation.
  0-3: Quiet   | 4-6: Minor Storm | 7-9: Severe Storm

Solar Flux (10cm radio wave)
  Current: """ + (str(flux) if 'flux' in globals() else "--") + """
  Higher flux = better propagation (better MUF estimates).
  Typical range: 60-250 sfu

MUF (Maximum Usable Frequency)
  Current: """ + (str(muf) if 'muf' in globals() else "--") + """ MHz
  The highest frequency that will reflect off the ionosphere.
  Frequencies above MUF will NOT propagate via sky wave.

LUF (Lowest Usable Frequency)
  Current: """ + (str(luf) if 'luf' in globals() else "--") + """ MHz
  The lowest reliable frequency for a given path.

Band Conditions
  """ + (str(bands) if 'bands' in globals() else "--") + """
  Shows which HF bands are currently open:
  🟢 GREEN = EXCELLENT  | 🟡 YELLOW = FAIR  | 🔴 RED = CLOSED

=== BUTTONS ===

Refresh Location
  Detects your geographic coordinates using your IP address.
  Your location appears as green "You" marker on the map.

Refresh Space Weather
  Fetches latest NOAA satellite data (Kp Index, Solar Flux, Sunspot count).
  Auto-refreshes every 60 seconds.
  Data logged to propagation_log.csv for historical tracking.

Export JSON
  Saves current readings to export.json for external analysis.

Export DX Log
  Saves the recently mapped live DX contacts to a standalone CSV file.

View / Plot History
  Select a date from the calendar to view past propagation logs, or click Plot History to generate a graph of past Kp and Solar Flux trends.

=== TIPS FOR HAM RADIO ===

1. FOLLOW THE GREYLINE
   HF propagation is STRONGEST along the terminator (day-night line).
   Best DX contacts occur on the greyline.

2. HIGH SOLAR FLUX = GOOD CONDITIONS
   When Solar Flux > 150: Expect excellent long-distance propagation.

3. LOW Kp INDEX = BEST CONDITIONS
   When Kp < 3: Ionosphere is stable, minimal disturbances.
   When Kp > 5: Expect auroral absorption, poor propagation.

4. TIME MATTERS
   Sunrise and Sunset (UTC times shown) are great for DX.
   Early morning and evening often have the best conditions.

5. BAND SELECTION
   Plan your operating frequency based on MUF estimate.
   Use lower bands when conditions are poor.

=== ADVANCED FEATURES ===

- TIME TRAVEL: Use the slider under the map to move the greyline up to 24 hours into the future to plan distant contacts.
- LIVE DX CLUSTER: Spots automatically appear on the map. Click a purple spot to instantly send a CAT command to tune your physical radio to that frequency!
- PROPAGATION ALARM: If conditions are excellent (High MUF, Low Kp), an alert will pop up with a button to immediately tune your radio to 10m FT8.
- DX LOGGING: Map spots automatically fade out after 5 minutes to keep your screen clean, but are permanently saved to dx_spots_log.csv.

=== DATA PERSISTENCE ===
All data is automatically logged to propagation_log.csv with timestamps.
Use this file to analyze propagation trends over time.

Generated: """ + datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        
        text_guide.insert("end", guide_text)
        text_guide.config(state="disabled")
    
    update_guide_content()
    guide_window.after(5000, update_guide_content)  # Refresh every 5 seconds

btn_help = tk.Button(panel_buttons, text="Help & Guide", command=show_user_guide, 
                     bg="#FF9C27", fg="white", font=("Segoe UI", 10, "bold"), relief="raised", bd=2)
btn_help.pack(side="left", padx=4)

# Initialize logging and start app
init_log_file()
init_dx_log_file()
start_dx_cluster()
auto_refresh()

window.mainloop()