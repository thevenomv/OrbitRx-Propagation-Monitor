from orbitrx.propagation import estimate_muf, band_condition, voacap_lite_path_muf, band_grid


def test_estimate_muf():
    muf, luf = estimate_muf(150, 2)
    assert muf is not None and muf > 20
    assert luf is not None


def test_band_condition_open():
    assert band_condition(14.0, 200, 0) == "OPEN"
    assert band_condition(14.0, 160, 1) in ("OPEN", "FAIR")


def test_path_muf():
    m = voacap_lite_path_muf(150, 2, 40.0, -74.0, 35.0, 139.0)
    assert m is not None and m > 0


def test_band_grid_keys():
    g = band_grid(150, 2)
    assert "10m" in g and "20m" in g
