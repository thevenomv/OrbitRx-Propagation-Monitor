"""Application configuration constants."""

CAT_PORT = "COM3"
CAT_BAUD = 9600
CAT_TIMEOUT = 0.5

DX_CLUSTER_HOST = "dxc.ve7cc.net"
DX_CLUSTER_PORT = 23

ALERT_KP_THRESHOLD = 2
ALERT_MUF_THRESHOLD = 28

MAP_CANVAS_WIDTH = 700
MAP_CANVAS_HEIGHT = 560
AUTO_REFRESH_MS = 60_000
DX_SPOT_TTL_SECONDS = 300
DX_UI_THROTTLE_MS = 500
ALERT_COOLDOWN_SECONDS = 3600

APP_TITLE = "OrbitRx Propagation Monitor"
WINDOW_GEOMETRY = "1300x700"

HF_BANDS = {
    "160m": {"freq": 1.8, "name": "160 Meters", "color": "#FF6B6B"},
    "80m": {"freq": 3.5, "name": "80 Meters", "color": "#FF8C42"},
    "40m": {"freq": 7.0, "name": "40 Meters", "color": "#FFD93D"},
    "20m": {"freq": 14.0, "name": "20 Meters", "color": "#6BCB77"},
    "15m": {"freq": 21.0, "name": "15 Meters", "color": "#4D96FF"},
    "10m": {"freq": 28.0, "name": "10 Meters", "color": "#A78BFA"},
}

UPCOMING_CONTESTS = [
    {"name": "ARCI Spring QSO Party", "date": "2026-04-04", "bands": ["160m", "80m", "40m", "20m", "15m", "10m"]},
    {"name": "CQ WW WPX SSB", "date": "2026-03-28", "bands": ["All HF"]},
    {"name": "RSGB IOTA Contest", "date": "2026-07-26", "bands": ["All HF", "VHF", "UHF"]},
]

DX_COORDINATES = {
    "W5XYZ": (30.2683, -97.7448),
    "PY2AB": (-22.9068, -43.1729),
    "VE3ABC": (45.4215, -75.6972),
    "XU7AJ": (11.5621, 104.8885),
}

PREFIX_MAP = {
    "W": (38.0, -97.0), "K": (38.0, -97.0), "N": (38.0, -97.0), "A": (38.0, -97.0),
    "VE": (56.0, -106.0), "VA": (56.0, -106.0), "VY": (56.0, -106.0),
    "XE": (23.0, -102.0),
    "PY": (-14.0, -51.0), "PU": (-14.0, -51.0),
    "LU": (-38.0, -63.0), "LW": (-38.0, -63.0),
    "CE": (-35.0, -71.0),
    "G": (52.0, -1.0), "M": (52.0, -1.0), "2": (52.0, -1.0),
    "F": (46.0, 2.0),
    "D": (51.0, 9.0),
    "I": (41.0, 12.0), "IZ": (41.0, 12.0), "IN": (41.0, 12.0), "IT": (41.0, 12.0),
    "EA": (40.0, -4.0), "EB": (40.0, -4.0),
    "CT": (39.0, -8.0),
    "HB": (46.0, 8.0),
    "OE": (47.0, 14.0),
    "SP": (52.0, 19.0), "SQ": (52.0, 19.0),
    "OK": (49.0, 15.0),
    "OM": (48.0, 19.0),
    "UR": (48.0, 31.0), "UT": (48.0, 31.0), "UY": (48.0, 31.0), "UZ": (48.0, 31.0),
    "R": (55.0, 60.0), "U": (55.0, 60.0), "RX": (55.0, 60.0),
    "JA": (36.0, 138.0), "JH": (36.0, 138.0), "JR": (36.0, 138.0), "JE": (36.0, 138.0),
    "VK": (-25.0, 133.0),
    "ZL": (-40.0, 174.0),
    "ZS": (-30.0, 25.0), "ZR": (-30.0, 25.0),
    "VU": (20.0, 77.0),
    "BY": (35.0, 104.0), "BG": (35.0, 104.0),
    "YB": (-0.7, 113.0),
    "HS": (15.0, 100.0),
    "9M": (4.0, 109.0),
    "9V": (1.3, 103.0),
    "VR": (22.0, 114.0),
    "HL": (35.0, 127.0), "DS": (35.0, 127.0),
    "DU": (12.0, 121.0),
    "4X": (31.0, 34.0), "4Z": (31.0, 34.0),
    "TA": (39.0, 35.0),
    "LA": (60.0, 10.0),
    "SM": (59.0, 15.0),
    "OH": (61.0, 25.0),
    "OZ": (56.0, 10.0),
    "PA": (52.0, 5.0), "PB": (52.0, 5.0), "PC": (52.0, 5.0), "PD": (52.0, 5.0),
}

DEMO_SPOTS = [
    {"from": "W5XYZ", "to": "PY2AB", "freq": "28.456"},
    {"from": "VE3ABC", "to": "XU7AJ", "freq": "21.285"},
    {"from": "G3ZYZ", "to": "JA1ABC", "freq": "14.195"},
]
