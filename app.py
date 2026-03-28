import tkinter as tk
import urllib.request
import json
import math
import datetime
import csv
import os
from PIL import Image, ImageTk
from functools import lru_cache

# --- USER LOCATION ---
user_lat = None
user_lon = None

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


# --- DATA LOGGING & STORAGE ---
LOG_FILE = "propagation_log.csv"

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
def get_dx_spots():
    try:
        # Using a simple mock DX data - real implementation would use cluster API
        # For now, return a placeholder showing example recent activity
        recent_dx = [
            "W5XYZ → PY2AB on 28.456 MHz",
            "VE3ABC → XU7AJ on 21.285 MHz"
        ]
        return recent_dx
    except Exception as e:
        print("DX spot fetch error:", e)
        return []


# --- 27-DAY SOLAR CYCLE FORECAST ---
def get_solar_cycle_forecast():
    try:
        url = "https://services.swpc.noaa.gov/products/solar-cycle-25-f10-7-predicted-range.json"
        response = urllib.request.urlopen(url, timeout=5)
        data = json.loads(response.read())
        if isinstance(data, list) and len(data) > 0:
            latest = data[-1]
            if isinstance(latest, dict):
                return f"F10.7 low: {latest.get('low', '--')}, high: {latest.get('high', '--')}"
        return "F10.7: --"
    except Exception as e:
        print("Solar cycle forecast error:", e)
        return "F10.7: --"


# --- NOAA SATELLITE DATA ---
def get_space_weather():
    try:
        btn_refresh.config(text="Fetching Satellite Data...")
        window.update()

        url = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read())
        
        latest_data = data[-1] 
        time_utc = latest_data[0]
        kp_index = float(latest_data[1])
        
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
            response2 = urllib.request.urlopen(url2)
            data2 = json.loads(response2.read())
            latest2 = data2[-1]
            flux = float(latest2[1])
            lbl_solar.config(text=f"Solar Flux: {flux}")
        except Exception as e:
            lbl_solar.config(text="Solar Flux: --")
            print("Solar flux fetch error:", e)

        # Fetch Sunspot Number (use monthly SSN prediction range if actual endpoint is not available)
        sunspot = None
        try:
            url3 = "https://services.swpc.noaa.gov/products/solar-cycle-25-ssn-predicted-range.json"
            response3 = urllib.request.urlopen(url3)
            data3 = json.loads(response3.read())
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
            response_alerts = urllib.request.urlopen(url_alerts)
            data_alerts = json.loads(response_alerts.read())
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
            response4 = urllib.request.urlopen(url4)
            data4 = json.loads(response4.read())
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

        # DX spots (non-blocking, just update display)
        try:
            spots = get_dx_spots()
            if spots:
                lbl_dx.config(text="Recent DX: " + " | ".join(spots[:2]))
            else:
                lbl_dx.config(text="Recent DX: none")
        except:
            lbl_dx.config(text="Recent DX: --")
        
    except Exception as e:
        lbl_status.config(text=f"Error connecting: {e}")
        lbl_solar.config(text="Solar Flux: --")
        lbl_sunspot.config(text="Sunspot Number: --")
        lbl_bands.config(text="Band Conditions: --")
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
    now = datetime.datetime.now(datetime.timezone.utc)
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
        
    # Draw the blazing neon orange terminator line on top of the map
    canvas.create_line(points, fill="#FF4500", width=3, smooth=True)
    
    # Draw a little text box background so the time is readable over the map
    canvas.create_rectangle(5, 5, 300, 35, fill="#101820", outline="")
    canvas.create_text(10, 10, anchor="nw", text=f"Greyline Calculated @ {now.strftime('%H:%M UTC')}", fill="white", font=("Arial", 11))

    # Plot user location marker if available
    if user_lat is not None and user_lon is not None:
        px = ((user_lon + 180) / 360) * width
        py = (height / 2) - ((user_lat / 90) * (height / 2))
        if 0 <= px <= width and 0 <= py <= height:
            canvas.create_oval(px-7, py-7, px+7, py+7, fill="#00FF00", outline="#00FF00", width=2)
            canvas.create_text(px + 12, py - 10, text="You", fill="white", font=("Arial", 11, "bold"), anchor="w")

# --- AUTO-REFRESH TIMER ---
def auto_refresh():
    update_user_location()
    get_space_weather()
    draw_greyline()
    window.after(60000, auto_refresh)

# --- USER INTERFACE (UI) SETUP ---
window = tk.Tk()
window.title("Ham Radio Space Weather App")
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

lbl_title = tk.Label(frame_title, text="Radio Propagation Tracker", font=("Segoe UI", 20, "bold"), bg="#0B1220", fg="#E7EBFF")
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

lbl_note = tk.Label(panel_map, text="Red line: Greyline (day-night boundary) - optimal for HF radio propagation", font=("Segoe UI", 9), bg="#0E162B", fg="#CCCCCC", anchor="w")
lbl_note.pack(fill="x", padx=8, pady=(0, 10))

# Stats panel (RIGHT side)
panel_stats = tk.Frame(frame_content, bg="#0E162B", bd=1, relief="solid", width=300)
panel_stats.pack(side="right", fill="both", padx=0, pady=0)
panel_stats.pack_propagate(False)

lbl_kp = tk.Label(panel_stats, text="Current Kp Index: --", font=("Segoe UI", 15, "bold"), bg="#0E162B", fg="#81D4FA", anchor="w")
lbl_kp.pack(fill="x", padx=10, pady=(8, 3))

lbl_kp_forecast = tk.Label(panel_stats, text="Kp Forecast: --", font=("Segoe UI", 11), bg="#0E162B", fg="#F5F5A5", anchor="w")
lbl_kp_forecast.pack(fill="x", padx=10, pady=2)

lbl_solar = tk.Label(panel_stats, text="Solar Flux: --", font=("Segoe UI", 13), bg="#0E162B", fg="#BBDEFB", anchor="w")
lbl_solar.pack(fill="x", padx=10, pady=2)

lbl_sunspot = tk.Label(panel_stats, text="Sunspot Number: --", font=("Segoe UI", 12), bg="#0E162B", fg="#CDDDFE", anchor="w")
lbl_sunspot.pack(fill="x", padx=10, pady=2)

lbl_bands = tk.Label(panel_stats, text="Band Conditions: --", font=("Segoe UI", 12, "bold"), bg="#0E162B", fg="#96CEB4", anchor="w")
lbl_bands.pack(anchor="w", padx=10, pady=6)

lbl_muf = tk.Label(panel_stats, text="MUF est: --", font=("Segoe UI", 11), bg="#0E162B", fg="#DFE7FF", anchor="w")
lbl_muf.pack(fill="x", padx=10, pady=2)

lbl_sunrise = tk.Label(panel_stats, text="Sunrise (UTC): --", font=("Segoe UI", 10), bg="#0E162B", fg="#CDDDFE", anchor="w")
lbl_sunrise.pack(fill="x", padx=10, pady=1)

lbl_sunset = tk.Label(panel_stats, text="Sunset (UTC): --", font=("Segoe UI", 10), bg="#0E162B", fg="#CDDDFE", anchor="w")
lbl_sunset.pack(fill="x", padx=10, pady=1)

lbl_alerts = tk.Label(panel_stats, text="Alerts: --", font=("Segoe UI", 10), bg="#0E162B", fg="#FFA0A0", anchor="w")
lbl_alerts.pack(fill="x", padx=10, pady=2)

lbl_status = tk.Label(panel_stats, text="Click refresh to load live satellite data.", font=("Segoe UI", 11, "italic"), bg="#0E162B", fg="white", anchor="w")
lbl_status.pack(fill="x", padx=10, pady=5)

lbl_time = tk.Label(panel_stats, text="Last NOAA Update: --", font=("Segoe UI", 9), fg="#CCCCCC", bg="#0E162B", anchor="w")
lbl_time.pack(fill="x", padx=10, pady=2)

lbl_location = tk.Label(panel_stats, text="You: locating...", font=("Segoe UI", 10), fg="#E0E8FF", bg="#0E162B", anchor="w")
lbl_location.pack(fill="x", padx=10, pady=(2, 8))

# Advanced features section
sep2 = tk.Frame(panel_stats, height=1, bg="#1E2A40", bd=0)
sep2.pack(fill="x", padx=10, pady=8)

lbl_solar_forecast = tk.Label(panel_stats, text="27-Day Forecast: --", font=("Segoe UI", 10), bg="#0E162B", fg="#B3E5FC", anchor="w")
lbl_solar_forecast.pack(fill="x", padx=10, pady=2)

lbl_contest = tk.Label(panel_stats, text="Next Contest: --", font=("Segoe UI", 10), bg="#0E162B", fg="#FFE082", anchor="w")
lbl_contest.pack(fill="x", padx=10, pady=2)

lbl_dx = tk.Label(panel_stats, text="Recent DX: --", font=("Segoe UI", 10), bg="#0E162B", fg="#C8E6C9", anchor="w")
lbl_dx.pack(fill="x", padx=10, pady=(2, 8))

# Controls (BOTTOM - full width)
panel_buttons = tk.Frame(window, bg="#0B1220")
panel_buttons.pack(fill="x", pady=(0, 0))

btn_locate = tk.Button(panel_buttons, text="Refresh Location", command=update_user_location, bg="#006AFF", fg="white", font=("Segoe UI", 10, "bold"), relief="raised", bd=2)
btn_locate.pack(side="left", padx=4)

btn_refresh = tk.Button(panel_buttons, text="Refresh Space Weather", command=auto_refresh, bg="#00A8FF", fg="white", font=("Segoe UI", 10, "bold"), relief="raised", bd=2)
btn_refresh.pack(side="left", padx=4)

btn_export = tk.Button(panel_buttons, text="Export JSON", command=export_json, bg="#9C27B0", fg="white", font=("Segoe UI", 10, "bold"), relief="raised", bd=2)
btn_export.pack(side="left", padx=4)

def show_user_guide():
    """Display an interactive user guide window with current app status."""
    guide_window = tk.Toplevel(window)
    guide_window.title("User Guide - Radio Propagation Tracker")
    guide_window.geometry("600x700")
    guide_window.configure(bg="#0B1220")
    
    # Title
    lbl_guide_title = tk.Label(guide_window, text="Radio Propagation Tracker - User Guide", 
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
The Radio Propagation Tracker monitors real-time space weather data from NOAA and calculates optimal HF radio propagation conditions using the Kp Index and Solar Flux measurements.

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
auto_refresh()

window.mainloop()