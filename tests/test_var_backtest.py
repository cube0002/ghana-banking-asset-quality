"""Tests for VAR impulse-response uncertainty and chronological backtesting."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest

from ghana_banking.modeling.var_model import VARModel
from ghana_banking.modeling.var_backtest import expanding_window_var_backtest


def _stationary_var_data(n=180, seed=23):
    rng = np.random.default_rng(seed)
    innovations = rng.normal(size=(n, 2))
    values = np.zeros((n, 2))
    for t in range(1, n):
        values[t, 0] = 0.35 * values[t - 1, 0] + 0.15 * values[t - 1, 1] + innovations[t, 0]
        values[t, 1] = -0.10 * values[t - 1, 0] + 0.25 * values[t - 1, 1] + innovations[t, 1]
    return pd.DataFrame(
        values,
        columns=["npl_change", "policy_change"],
        index=pd.date_range("2010-01-01", periods=n, freq="MS"),
    )


def test_var_impulse_response_bands_are_reproducible_and_well_shaped():
    data = _stationary_var_data()
    model = VARModel(lags=2).fit(data, use_diff=False)
    first = model.impulse_response_bands(periods=5, replications=100, seed=7)
    second = model.impulse_response_bands(periods=5, replications=100, seed=7)

    lower = np.asarray(first["lower"])
    upper = np.asarray(first["upper"])
    assert lower.shape == (6, 2, 2)
    assert upper.shape == (6, 2, 2)
    assert np.all(lower <= upper)
    assert np.allclose(lower, np.asarray(second["lower"]))
    assert first["orthogonalized"] is False


def test_var_impulse_response_bands_validate_arguments():
    model = VARModel(lags=1).fit(_stationary_var_data(), use_diff=False)
    with pytest.raises(ValueError, match="replications"):
        model.impulse_response_bands(replications=10)
    with pytest.raises(ValueError, match="significance_level"):
        model.impulse_response_bands(significance_level=1.0)


def test_expanding_window_var_backtest_is_chronological_and_benchmarked():
    result = expanding_window_var_backtest(
        _stationary_var_data(),
        lag_order=2,
        initial_window=80,
        horizons=[1, 3],
        step=3,
    )
    payload = result.to_dict()
    assert payload["forecast_origins"] > 0
    assert set(row["horizon"] for row in payload["metrics"]) == {1, 3}
    assert all(row["n_forecasts"] == payload["forecast_origins"] for row in payload["metrics"])
    assert all(row["var_rmse"] >= 0 for row in payload["metrics"])
    assert all(row["mean_benchmark_rmse"] >= 0 for row in payload["metrics"])
    records = payload["forecast_records"]
    assert records[0]["target_date"] > records[0]["origin"]


def test_expanding_window_var_backtest_rejects_invalid_or_irregular_data():
    data = _stationary_var_data()
    with pytest.raises(ValueError, match="regular"):
        expanding_window_var_backtest(data.drop(index=data.index[5]), 2, 80, [1])

    with pytest.raises(ValueError, match="maximum horizon"):
        expanding_window_var_backtest(_stationary_var_data(n=90), 2, 80, [12])

    with pytest.raises(ValueError, match="complete and finite"):
        bad = _stationary_var_data()
        bad.iloc[3, 0] = np.nan
        expanding_window_var_backtest(bad, 2, 80, [1])
