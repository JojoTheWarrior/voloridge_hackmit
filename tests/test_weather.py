from warsignal.indicators import REGISTRY
from warsignal.indicators.weather import _parse_isd_line


def test_parse_isd_fixed_width_line():
    line = [" "] * 120

    def put(start, value):
        line[start:start + len(value)] = value

    put(15, "20250301")
    put(23, "1230")
    put(60, "270")
    put(65, "0015")
    put(78, "010000")
    put(87, "+0123")
    put(93, "-0045")
    put(99, "10132")
    parsed = _parse_isd_line("".join(line))
    assert parsed["date"].strftime("%Y-%m-%d") == "2025-03-01"
    assert parsed["wind_dir"] == 270
    assert parsed["wind"] == 1.5
    assert parsed["visibility"] == 10000
    assert parsed["temp"] == 12.3
    assert parsed["dew"] == -4.5
    assert parsed["slp"] == 1013.2


def test_cams_indicators_registered():
    names = set(REGISTRY)
    assert "airquality.tehran.cams_pm25" in names
    assert "airquality.dubai.cams_pm10" in names
