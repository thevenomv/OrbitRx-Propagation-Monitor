from orbitrx.weather import fetch_space_weather_data
from unittest.mock import patch


MOCK_KP = [
    {"time_tag": "2026-06-08T12:00:00", "Kp": 1.33, "a_running": 5},
    {"time_tag": "2026-06-08T15:00:00", "Kp": 2.0, "a_running": 6},
]

MOCK_FLUX = [
    {"time_tag": "2026-06-07T20:00:00", "flux": 134},
]

MOCK_KP_FC = [
    {"time_tag": "2026-06-09T00:00:00", "kp": 2.0, "observed": "predicted"},
    {"time_tag": "2026-06-10T00:00:00", "kp": 3.0, "observed": "predicted"},
    {"time_tag": "2026-06-11T00:00:00", "kp": 2.5, "observed": "predicted"},
]

MOCK_MAG = [
    ["time_tag", "bx_gsm", "by_gsm", "bz_gsm", "lon_gsm", "lat_gsm", "bt"],
    ["2026-06-08 19:00:00", "-4.32", "-0.59", "-1.35", "187", "-17", "4.56"],
]

MOCK_PLASMA = [
    ["time_tag", "density", "speed", "temperature"],
    ["2026-06-08 19:00:00", "1.27", "460.7", "66446"],
]


def test_fetch_space_weather_parses_dict_rows():
    with patch("orbitrx.weather.fetch_json") as fj:
        fj.side_effect = [
            MOCK_KP,       # planetary k-index
            MOCK_FLUX,     # 10cm flux
            [],            # ssn predicted range
            MOCK_MAG,      # solar wind mag
            MOCK_PLASMA,   # solar wind plasma
            [],            # alerts
            MOCK_KP_FC,    # kp forecast
        ]
        with patch("orbitrx.weather.get_solar_cycle_forecast", return_value="F10.7 ok"):
            data = fetch_space_weather_data()

    assert data["kp_index"] == 2.0
    assert data["flux"] == 134.0
    assert data["a_index"] == 6.0
    assert data["kp_forecast"] == "2.0, 3.0, 2.5"
    assert data["bz"] == -1.35
    assert data["solar_wind_speed"] == 460.7
    assert data["time_utc"] is not None


def test_live_noaa_populates_core_fields():
    """Integration test — requires network."""
    data = fetch_space_weather_data()
    assert data["kp_index"] > 0
    assert data["flux"] is not None
    assert data["kp_forecast"] != "--"
    assert data["time_utc"] != "--"
