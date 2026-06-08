# OrbitRx Propagation Monitor

A professional-grade desktop dashboard for HAM radio operators. Monitors real-time space weather, visualises the greyline, plots live DX cluster contacts on a world map, controls your physical radio via CAT, and forecasts propagation up to 24 hours into the future.

---

## Feature Summary

### Phase 1 — Real-Time Space Weather
- **Kp Index** — geomagnetic activity (0–9)
- **Solar Flux** — 10 cm radio wave intensity from NOAA
- **Sunspot Number** — predicted from NOAA cycle-25 data
- **27-Day F10.7 Forecast** — smoothed solar flux range
- **Space Weather Alerts** — live NOAA alert feed
- **Kp Forecast** — next 3 readings from NOAA

### Phase 2 — Propagation Analysis & Map
- **MUF / LUF** — maximum and lowest usable frequency estimates
- **Band Conditions** — 160 m – 10 m real-time status (🟢/🟡/🔴)
- **Sunrise / Sunset UTC** — computed for your exact location
- **Greyline** — day/night terminator rendered on a full-colour world map
- **Night-side shading** — semi-transparent overlay marks the dark hemisphere
- **Sun position marker** — subsolar point shown as ☀️ on the map
- **Card UI** — Space Weather / Local Station / DX & Events grouped cards
- **History lookup** — search propagation_log.csv by date or date range
- **History plot** — matplotlib chart of Kp, Solar Flux, MUF, LUF over time

### Phase 3 — Professional Shack Integration

#### 1. CAT Radio Control (`pyserial`)
- Click any **purple DX spot** on the map → CAT command tunes your physical rig instantly.
- Sends Kenwood/Icom-compatible `FA...;` string over the configured COM port.
- Propagation alarm popup includes a **"Tune to 28.074 FT8"** one-click button.
- Gracefully degrades if `pyserial` is not installed.
- Configure `CAT_PORT` and `CAT_BAUD` constants at the top of `app.py`.

#### 2. Live DX Cluster (socket / Telnet)
- Connects to **dxc.ve7cc.net:23** (VE7CC DX cluster) over a persistent background thread.
- Incoming `DX de …` lines are parsed, geo-coded, and immediately arc-drawn on the map.
- **Callsign prefix table** resolves 60+ country prefixes to lat/lon with per-spot jitter.
- Spots auto-expire after **5 minutes** to keep the map clean.
- Every spot is permanently appended to `dx_spots_log.csv`.
- Launch throttle: UI updates are batched (max 1 per second) so floods don't freeze the app.

#### 3. Propagation Alarm System
- Alarm fires when `Kp ≤ 2` **AND** `MUF ≥ 28 MHz` — 10 m is open!
- Plays `winsound.MessageBeep` for an audible alert.
- Shows a topmost Tkinter popup with a one-click CAT tune button.
- Suppressed for 1 hour after each trigger to avoid spam.
- Also fires on `Kp ≥ 7` as a severe geomagnetic storm warning.

#### 4. Time-Travel Propagation Slider
- Slider beneath the map projects the greyline **+0 to +24 hours** into the future.
- Recalculates solar declination, subsolar longitude, night shading, and MUF at the selected time.
- Timestamp overlay on the map shows the projected UTC time and offset.
- Ideal for planning contest openings to Japan, Australia, or South America.

## Getting Started

### Requirements
- Python 3.11+
- Windows / macOS / Linux
- Internet connection (real-time data)

### Install dependencies
```
pip install -r requirements.txt
```

### Optional extras
```
pip install pyserial          # CAT radio control (required for physical rig tuning)
pip install customtkinter     # modern dark-mode UI shell
pip install win10toast          # Windows toast notifications on propagation alarms
```

### Run from source
```
py app.py
```
or
```
pip install -e .
orbitrx
```

### Build standalone `.exe`
```
build.bat
```
or
```
py build_exe.py
```
Output: `dist\OrbitRxMonitor.exe`

---

## Configuration

Edit `config.json` or use **Settings** in the app:

| Key | Default | Purpose |
|-----|---------|---------|
| `cat_port` | `COM3` | Serial port for CAT control |
| `cat_baud` | `9600` | Baud rate |
| `cat_rig_profile` | `kenwood` | `kenwood`, `icom`, or `yaesu` |
| `dx_cluster_host` | `dxc.ve7cc.net` | Telnet DX cluster hostname |
| `dx_cluster_callsign` | `W1AW-9` | Callsign sent on cluster connect |
| `qrz_api_key` | `""` | Optional QRZ XML lookup for spot coordinates |
| `target_dx_lat` / `target_dx_lon` | `null` | Path MUF target location |
| `alert_kp_threshold` | `2` | Max Kp for "excellent" alarm |
| `alert_muf_threshold` | `28` | Min MUF (MHz) for excellent alarm |
| `storm_kp_threshold` | `7` | Min Kp for storm alarm |
| `refresh_interval_seconds` | `60` | Auto-refresh interval |

---

## UI Layout

| Area | Content |
|------|---------|
| Title bar | App name |
| Map (left) | World map, greyline, night shade, ☀️ sun, DX arcs, "You" marker |
| Time-travel slider | +0–24 h offset, live greyline redraw |
| Space Weather card | Kp, Kp forecast, Solar Flux, Sunspot, timestamp |
| Local Station card | Band conditions, MUF/LUF, sunrise/sunset, alerts, location |
| DX & Events card | 27-day forecast, next contest, live DX feed, history controls |
| Button bar | Refresh Location · Refresh Space Weather · Export JSON · Export DX Log · Help |

---

## Propagation Reference

### Kp Index
- **0–3**: Quiet conditions, excellent propagation
- **4–6**: Unsettled, minor degradation
- **7–9**: Major storm, severe propagation loss possible

### Solar Flux
- **60–100**: Low activity, poor long-distance propagation
- **100–150**: Normal conditions
- **150+**: Excellent propagation expected

### Band Conditions
- 🟢 **GREEN (EXCELLENT)**: All bands open, excellent DX conditions
- 🟡 **YELLOW (FAIR)**: Some bands open, limited range
- 🔴 **RED (CLOSED)**: Poor propagation, local-only contacts

### The Greyline
The **orange line** on the map shows where sunrise and sunset occur. This terminator line is where HF propagation is **strongest** because signals can skip off the ionosphere at shallow angles. Best DX contacts occur along the greyline.

## Using the Map

| Symbol | Meaning |
|--------|---------|
| Orange curve | Greyline — day/night terminator |
| Dark stipple | Night side of Earth |
| ☀️ yellow dot | Subsolar point |
| Green dot | Your location |
| Cyan arc + cyan dot | DX path from spotter |
| Purple dot | DX target — **click to tune radio** |
| Yellow label | Callsign pair |

---

## Data Files

| File | Contents |
|------|---------|
| `propagation_log.csv` | Timestamped Kp / Solar Flux / MUF readings (auto-appended) |
| `dx_spots_log.csv` | DX cluster spots — spotter, target, frequency, timestamp |
| `export.json` | One-shot JSON snapshot of current readings |
| `world_map.jpg` | Downloaded from Wikimedia on first run |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Location unknown" | Check internet; click Refresh Location |
| Map not showing | Ensure `world_map.jpg` is in the same folder; delete & restart to re-download |
| No data | Click Refresh Space Weather; check https://www.swpc.noaa.gov/ |
| DX arcs not appearing | Cluster connection in progress (may take 10–30 s); check console |
| CAT not working | Verify `CAT_PORT` in app.py matches Device Manager COM port |

---

## Data Sources
- **NOAA SWPC** — Kp, solar flux, sunspots, alerts, forecasts
- **ipinfo.io** — IP-based geolocation
- **VE7CC DX cluster** — Live DX spot feed (Telnet)
- **Wikimedia** — High-resolution world map base image

---

## File Structure

```
OrbitRx-Propagation-Monitor/
├── app.py                      # Entry point
├── config.json                 # User settings (editable in-app)
├── orbitrx/                    # Application package (v4)
│   ├── main.py                 # CLI entry
│   ├── config.py               # Config loader
│   ├── state.py                # AppState dataclass
│   ├── weather.py              # NOAA fetch + offline cache
│   ├── propagation.py          # MUF, bands, VOACAP-lite path MUF
│   ├── dx.py                   # DX cluster parser + filters
│   ├── cat.py                  # Multi-rig CAT control
│   ├── map_renderer.py         # Cached greyline / aurora / great-circle
│   ├── storage.py              # SQLite + CSV + log rotation
│   └── ui/qt_app.py            # Main window (PySide6 — default)
│   └── ui/tk_app.py            # Tkinter fallback
│   └── ui/map_widget.py        # QGraphicsView propagation map
├── tests/                      # pytest unit tests
├── installer/OrbitRxMonitor.iss# Inno Setup installer script
├── generate_map.py             # Map downloader
├── requirements.txt
├── pyproject.toml
└── build.bat
```

### v5 highlights (recommended UI)
- **PySide6 (Qt)** desktop UI — native feel, smooth rendering, better threading
- **Layered map engine**: cached greyline/night raster + **vector DX overlay** (fast spot updates)
- **900×720** map, antialiased great-circle arcs, optional lat/lon grid
- Scroll zoom, right-drag pan, double-click reset view
- Tkinter UI remains as fallback if PySide6 is missing

### v4 highlights
- Modular `orbitrx` package, SQLite + CSV, propagation science, DX cluster, CAT

---

**Version**: 5.0  |  **Updated**: June 2026
**Tested On**: Windows 10/11, Python 3.11+
