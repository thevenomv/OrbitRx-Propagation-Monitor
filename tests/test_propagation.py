"""Tests for propagation math helpers."""

import datetime

from orbitrx.services.propagation import estimate_muf, parse_history_query, sun_times


def test_sun_times_returns_values_for_mid_latitudes():
    when = datetime.datetime(2026, 6, 21, 12, 0, tzinfo=datetime.timezone.utc)
    sunrise, sunset = sun_times(40.0, -74.0, when)
    assert sunrise is not None
    assert sunset is not None
    assert 0 <= sunrise < 24
    assert 0 <= sunset < 24


def test_estimate_muf_scales_with_flux():
    muf, luf = estimate_muf(150.0, 2.0)
    assert muf is not None and luf is not None
    assert muf > luf
    assert estimate_muf(None, 2.0) == (None, None)


def test_parse_history_query_single_date():
    start, end = parse_history_query("2026-03-28")
    assert start.year == 2026
    assert end > start


def test_parse_history_query_date_range():
    start, end = parse_history_query("2026-03-28:2026-03-30")
    assert (end - start).days == 3
