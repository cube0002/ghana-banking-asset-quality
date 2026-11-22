"""Tests for expanding-window AR forecasts and prediction intervals."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest

from ghana_banking.modeling import expanding_window_ar_backtest


def _ar_data(n=150, seed=42):
    rng = np.random.default_rng(seed)
    values = np.zeros(n)
    errors = rng.normal(size=n)
    for t in range(1, n):
        values[t] = 0.55 * values[t - 1] + errors[t]
    return pd.DataFrame(
        {"npl_change": values},
        index=pd.date_range("2012-01-01", periods=n, freq="MS"),
    )


def test_ar_backtest_is_chronological_and_reports_intervals_and_benchmarks():
    result = expanding_window_ar_backtest(
        _ar_data(), lag_order=2, initial_window=75, horizons=[1, 3], step=3
    )
    payload = result.to_dict()
    assert payload["forecast_origins"] > 0
    assert payload["trend"] == "c"
    assert payload["significance_level"] == 0.05
    assert {item["horizon"] for item in payload["metrics"]} == {1, 3}
    assert all(item["n_forecasts"] == payload["forecast_origins"] for item in payload["metrics"])
    for item in payload["metrics"]:
        assert item["ar_rmse"] >= 0
        assert item["no_change_rmse"] >= 0
        assert item["expanding_mean_rmse"] >= 0
        assert 0 <= item["ar_interval_coverage"] <= 1
        assert item["ar_mean_interval_width"] >= 0
    record = payload["forecast_records"][0]
    assert record["target_date"] > record["origin"]
    assert record["prediction_lower"] <= record["ar_forecast"] <= record["prediction_upper"]


def test_ar_backtest_rejects_invalid_data_and_settings():
    data = _ar_data()
    with pytest.raises(ValueError, match="regular"):
        expanding_window_ar_backtest(data.drop(index=data.index[4]), 2, 75, [1])
    with pytest.raises(ValueError, match="complete and finite"):
        bad = data.copy()
        bad.iloc[2, 0] = np.nan
        expanding_window_ar_backtest(bad, 2, 75, [1])
    with pytest.raises(ValueError, match="initial_window"):
        expanding_window_ar_backtest(data, 2, 4, [1])
    with pytest.raises(ValueError, match="maximum horizon"):
        expanding_window_ar_backtest(_ar_data(90), 2, 80, [12])
