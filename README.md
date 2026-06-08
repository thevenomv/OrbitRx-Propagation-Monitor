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
- **Band Conditions** — 160 m – 10 m real-time status
- **Sunrise / Sunset UTC** — computed for your exact location
- **Greyline** — day/night terminator rendered on a full-colour world map
- **History lookup** — search propagation logs by date or date range
- **History plot** — matplotlib chart of Kp, Solar Flux, MUF, LUF over time

### Phase 3 — Professional Shack Integration
- **CAT Radio Control** — click DX spots to tune your rig via serial
- **Live DX Cluster** — telnet feed from VE7CC, arcs on map
- **Propagation Alarm** — alerts when 10 m conditions are excellent
- **Time-Travel Slider** — project greyline +0 to +24 hours

---

## Getting Started

### Requirements
- Python 3.11+
- Windows / macOS / Linux
- Internet connection (real-time data)

### Install

```bash
pip install -e ".[full]"
```

Core only (no CAT or modern UI extras):

```bash
pip install -e .
```

### Run

```bash
python -m orbitrx
```

Or from the repository root:

```bash
python app.py
```

### Build standalone `.exe` (Windows)

```bash
pip install -e ".[full,build]"
python scripts/build_exe.py
```

Or:

```bash
scripts\build.bat
```

Output: `dist/OrbitRxMonitor.exe`

---

## Configuration

Edit constants in `src/orbitrx/config.py`:

| Constant | Default | Purpose |
|----------|---------|---------|
| `CAT_PORT` | `'COM3'` | Serial port for CAT control |
| `CAT_BAUD` | `9600` | Baud rate for your transceiver |
| `DX_CLUSTER_HOST` | `'dxc.ve7cc.net'` | Telnet DX cluster hostname |
| `ALERT_KP_THRESHOLD` | `2` | Max Kp to trigger "excellent" alarm |
| `ALERT_MUF_THRESHOLD` | `28` | Min MUF (MHz) to trigger "excellent" alarm |

Override the data directory (logs, exports, cached map):

```bash
export ORBITRX_DATA=/path/to/my/data   # Linux/macOS
set ORBITRX_DATA=C:\OrbitRx\Data       # Windows
```

Default data directory: `~/.orbitrx`

---

## File Structure

```
orbitrx/
├── pyproject.toml
├── README.md
├── .gitignore
├── app.py                          # backward-compatible entry point
│
├── src/orbitrx/
│   ├── __main__.py                 # python -m orbitrx
│   ├── app.py                      # thin bootstrap
│   ├── config.py                   # constants and band definitions
│   ├── paths.py                    # data dir and bundled asset resolution
│   ├── compat.py                   # optional dependency detection
│   │
│   ├── models/
│   │   ├── state.py                # AppState dataclass
│   │   └── context.py              # AppContext + UIRefs
│   │
│   ├── services/
│   │   ├── noaa.py                 # NOAA space weather API
│   │   ├── propagation.py          # MUF/LUF, sun times, history parsing
│   │   ├── geolocation.py          # IP-based location
│   │   ├── dx_cluster.py           # telnet DX feed + prefix geocoding
│   │   ├── cat.py                  # serial radio control
│   │   └── logging.py              # CSV logs and JSON export
│   │
│   ├── ui/
│   │   ├── main_window.py          # layout and event wiring
│   │   ├── map_canvas.py           # greyline and DX arc rendering
│   │   ├── history.py              # lookup and matplotlib plots
│   │   └── dialogs.py              # help and export dialogs
│   │
│   └── assets/
│       ├── map.py                  # map download + synthetic fallback
│       └── bundled/world_map.jpg   # shipped with PyInstaller builds
│
├── scripts/
│   ├── build.bat
│   ├── build_exe.py
│   └── inspect_noaa.py             # dev-only NOAA API probe
│
├── packaging/
│   └── orbitrx.spec                # canonical PyInstaller spec
│
└── tests/
    ├── test_propagation.py
    ├── test_dx_parser.py
    └── test_prefix_map.py
```

---

## Runtime Data Files

Stored under `~/.orbitrx` (or `$ORBITRX_DATA`):

| File | Contents |
|------|----------|
| `propagation_log.csv` | Timestamped Kp / Solar Flux / MUF readings |
| `dx_spots_log.csv` | DX cluster spots |
| `export.json` | Last JSON export snapshot |
| `world_map.jpg` | Cached world map (downloaded on first run) |

---

## Development

```bash
pip install -e ".[dev]"
pytest
python -m py_compile app.py
```

---

## Data Sources
- **NOAA SWPC** — Kp, solar flux, sunspots, alerts, forecasts
- **ipinfo.io** — IP-based geolocation
- **VE7CC DX cluster** — Live DX spot feed (Telnet)
- **Wikimedia** — High-resolution world map base image

---

**Version**: 3.0  |  **Updated**: June 2026  
**Tested On**: Windows 10/11, Linux, Python 3.11+
