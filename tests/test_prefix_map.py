"""Tests for callsign prefix geocoding."""

from orbitrx.services.dx_cluster import estimate_location


def test_estimate_location_known_prefix():
    lat, lon = estimate_location("W5XYZ")
    assert 30 <= lat <= 45
    assert -110 <= lon <= -85


def test_estimate_location_ja_prefix():
    lat, lon = estimate_location("JA1ABC")
    assert 30 <= lat <= 42
    assert 130 <= lon <= 145


def test_estimate_location_unknown_prefix():
    lat, lon = estimate_location("ZZ9ZZZ")
    assert -90 <= lat <= 90
    assert -180 <= lon <= 180
