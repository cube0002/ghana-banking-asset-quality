"""Tests for expanding-window conditional ARDL backtesting."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest

from ghana_banking.modeling import expanding_window_ardl_backtest


def _data(n=100):
    rng = np.random.default_rng(821)
    index = pd.date_range("2015-01-01", periods=n, freq="MS")
    x = np.cumsum(rng.normal(0, 0.05, n))
    y = np.zeros(n)
    eps = rng.normal(0, 0.1, n)
    for t in range(1, n):
        y[t] = 0.55 * y[t - 1] + 0.25 * x[t] + eps[t]
    return pd.DataFrame({"npl": y, "inflation": x}, index=index)


def test_conditional_ardl_backtest_is_chronological_and_reports_benchmarks():
    result = expanding_window_ardl_backtest(
        _data(),
        dependent_variable="npl",
        regressors=["inflation"],
        ar_lags=1,
        distributed_lags=1,
        initial_window=60,
        horizons=[1, 3],
        step=2,
        trend="c",
        hold_back=1,
        benchmark_ar_lags=1,
    )
    assert result.forecast_origins > 0
    assert set(row["horizon"] for row in result.metrics) == {1, 3}
    assert result.information_set == "realised_future_exogenous_regressors"
    assert all(
        record["information_set"] == "realised_future_exogenous_regressors"
        for record in result.forecast_records
    )
    assert all("ardl_conditional_mae" in row and "no_change_rmse" in row for row in result.metrics)
    assert all(
        row["ardl_interval_lower"] <= row["ardl_interval_upper"]
        for row in result.forecast_records
    )


def test_conditional_ardl_backtest_rejects_invalid_specifications():
    data = _data()
    with pytest.raises(ValueError, match="regressors"):
        expanding_window_ardl_backtest(
            data, "npl", [], 1, 1, 60
        )
    with pytest.raises(ValueError, match="finite"):
        broken = data.copy()
        broken.iloc[5, 0] = np.inf
        expanding_window_ardl_backtest(
            broken, "npl", ["inflation"], 1, 1, 60
        )
    with pytest.raises(ValueError, match="hold_back"):
        expanding_window_ardl_backtest(
            data, "npl", ["inflation"], 2, 1, 60, hold_back=1
        )
