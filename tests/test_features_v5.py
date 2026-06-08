from orbitrx.propagation import band_chip, band_grid, suggested_dial_freq
from orbitrx.dx import verify_qrz_api
from orbitrx.update_checker import _parse_version


def test_band_chip_colors():
    assert band_chip("OPEN") == "🟢"
    assert band_chip("FAIR") == "🟡"
    assert band_chip("CLOSED") == "🔴"


def test_band_grid_and_dial():
    grid = band_grid(130, 2)
    assert "20m" in grid
    assert suggested_dial_freq("20m") == "14.200"


def test_qrz_empty_key():
    ok, msg, pos = verify_qrz_api("")
    assert not ok
    assert pos is None


def test_version_parse():
    assert _parse_version("v5.0.0") > _parse_version("4.0.0")
