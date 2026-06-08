"""Tests for DX cluster line parsing."""

from orbitrx.services.dx_cluster import parse_dx_line


def test_parse_dx_line_valid():
    line = "DX de W1AW-9 28.456 PY2AB CW 1234Z"
    result = parse_dx_line(line)
    assert result is not None
    assert result["from"] == "W1AW-9"
    assert result["to"] == "PY2AB"
    assert result["freq"] == "28.456"


def test_parse_dx_line_invalid():
    assert parse_dx_line("Not a DX line") is None
    assert parse_dx_line("DX de only") is None
