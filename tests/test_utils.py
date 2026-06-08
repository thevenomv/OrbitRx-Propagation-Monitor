from orbitrx.utils import normalize_freq_mhz, parse_history_query
import datetime


def test_normalize_khz_to_mhz():
    assert normalize_freq_mhz(28520) == 28.52
    assert normalize_freq_mhz(14.195) == 14.195


def test_parse_history_date_range():
    start, end = parse_history_query("2026-03-28:2026-03-30")
    assert start.day == 28
    assert end.day == 31


def test_parse_history_single_day():
    start, end = parse_history_query("2026-03-28")
    assert (end - start).days == 1
