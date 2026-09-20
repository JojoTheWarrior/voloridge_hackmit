from warsignal.indicators import catalogue_text, get_series, list_indicators
from warsignal.analysis.stats import transform


def test_catalogue_and_transforms():
    assert catalogue_text()
    assert list_indicators()
    for kind in ("level", "diff", "pct_change", "log_return", "zscore", "anomaly"):
        transform([1, 2, 3], kind)
