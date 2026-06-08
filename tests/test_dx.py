from orbitrx.dx import parse_dx_line


def test_parse_dx_standard():
    line = "DX de W1AW: 14095 N4BP 2014Z"
    r = parse_dx_line(line)
    assert r is not None
    spotter, freq, target = r
    assert spotter == "W1AW"
    assert freq == 14.095
    assert target == "N4BP"


def test_parse_dx_spaced():
    line = "DX de VE3XYZ 14200 AB1CD 1234Z"
    r = parse_dx_line(line)
    assert r is not None
    assert r[1] == 14.2
