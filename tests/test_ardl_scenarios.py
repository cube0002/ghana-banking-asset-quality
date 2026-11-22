"""Tests for conditional multi-period ARDL scenario forecasts."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest
from statsmodels.tsa.ardl import ARDL

from ghana_banking.modeling import forecast_ardl_scenarios


def _fitted_ardl():
    rng = np.random.default_rng(19)
    n = 120
    exog = np.cumsum(rng.normal(0, 0.08, n))
    endog = np.zeros(n)
    innovations = rng.normal(0, 0.15, n)
    for t in range(2, n):
        endog[t] = 0.45 * endog[t - 1] + 0.18 * exog[t] + 0.08 * exog[t - 1] + innovations[t]
    index = pd.date_range("2014-01-01", periods=n, freq="MS")
    y = pd.Series(endog, index=index, name="npl_ratio")
    x = pd.DataFrame({"inflation": exog}, index=index)
    return ARDL(y, lags=2, exog=x, order=1, trend="c").fit(), index, exog[-1]


def test_ardl_scenarios_propagate_paths_and_compare_with_baseline():
    fitted, index, last_value = _fitted_ardl()
    future = pd.date_range(index[-1] + pd.offsets.MonthBegin(1), periods=6, freq="MS")
    baseline = pd.DataFrame({"inflation": np.repeat(last_value, 6)}, index=future)
    adverse = pd.DataFrame({"inflation": np.repeat(last_value + 1.0, 6)}, index=future)

    result = forecast_ardl_scenarios(
        fitted,
        {"Baseline": baseline, "Adverse": adverse},
        significance_level=0.05,
    )
    assert len(result) == 12
    baseline_rows = result[result["scenario"] == "Baseline"]
    adverse_rows = result[result["scenario"] == "Adverse"]
    assert np.allclose(baseline_rows["change_vs_baseline"], 0.0)
    assert np.allclose(
        adverse_rows["change_vs_baseline"],
        adverse_rows["forecast"] - adverse_rows["baseline_forecast"],
    )
    assert np.all(result["interval_lower"] <= result["forecast"])
    assert np.all(result["forecast"] <= result["interval_upper"])
    assert set(result["period"]) == {str(period) for period in future}


def test_ardl_scenarios_reject_missing_baseline_columns_and_bad_dates():
    fitted, index, last_value = _fitted_ardl()
    future = pd.date_range(index[-1] + pd.offsets.MonthBegin(1), periods=4, freq="MS")
    baseline = pd.DataFrame({"inflation": np.repeat(last_value, 4)}, index=future)

    with pytest.raises(ValueError, match="baseline"):
        forecast_ardl_scenarios(fitted, {"Adverse": baseline})
    with pytest.raises(ValueError, match="columns and order"):
        forecast_ardl_scenarios(
            fitted,
            {"Baseline": pd.DataFrame({"wrong": np.ones(4)}, index=future)},
        )
    with pytest.raises(ValueError, match="continue the estimation sample"):
        wrong_dates = pd.date_range(future[0] + pd.offsets.MonthBegin(1), periods=4, freq="MS")
        wrong_path = pd.DataFrame({"inflation": np.ones(4)}, index=wrong_dates)
        forecast_ardl_scenarios(fitted, {"Baseline": wrong_path})
