"""Tests for conditional ARDL parameter-uncertainty simulation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest
from statsmodels.tsa.ardl import ARDL

from ghana_banking.modeling import forecast_ardl_parameter_uncertainty


def _fitted_ardl():
    rng = np.random.default_rng(19)
    n = 120
    exog = np.cumsum(rng.normal(0, 0.08, n))
    endog = np.zeros(n)
    innovations = rng.normal(0, 0.15, n)
    for t in range(2, n):
        endog[t] = (
            0.45 * endog[t - 1]
            + 0.18 * exog[t]
            + 0.08 * exog[t - 1]
            + innovations[t]
        )
    index = pd.date_range("2014-01-01", periods=n, freq="MS")
    y = pd.Series(endog, index=index, name="npl_ratio")
    x = pd.DataFrame({"inflation": exog}, index=index)
    return ARDL(y, lags=2, exog=x, order=1, trend="c").fit(), index, exog[-1]


def _scenarios(index, last_value):
    future = pd.date_range(index[-1] + pd.offsets.MonthBegin(1), periods=6, freq="MS")
    baseline = pd.DataFrame({"inflation": np.repeat(last_value, 6)}, index=future)
    adverse = pd.DataFrame({"inflation": np.repeat(last_value + 1.0, 6)}, index=future)
    return {"Baseline": baseline, "Adverse": adverse}


def test_parameter_uncertainty_is_reproducible_and_uses_paired_scenario_draws():
    fitted, index, last_value = _fitted_ardl()
    scenarios = _scenarios(index, last_value)
    first = forecast_ardl_parameter_uncertainty(
        fitted, scenarios, draws=500, seed=123
    )
    second = forecast_ardl_parameter_uncertainty(
        fitted, scenarios, draws=500, seed=123
    )
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 12
    assert set(first["uncertainty_type"]) == {"asymptotic parameter uncertainty only"}
    assert (first["parameter_lower"] <= first["parameter_mean"]).all()
    assert (first["parameter_mean"] <= first["parameter_upper"]).all()
    baseline = first[first["scenario"] == "Baseline"]
    assert np.allclose(baseline["change_vs_baseline_mean"], 0.0)
    assert np.allclose(baseline["change_vs_baseline_lower"], 0.0)
    assert np.allclose(baseline["change_vs_baseline_upper"], 0.0)
    adverse = first[first["scenario"] == "Adverse"]
    assert (adverse["change_vs_baseline_upper"] >= adverse["change_vs_baseline_lower"]).all()


def test_parameter_uncertainty_rejects_invalid_inputs():
    fitted, index, last_value = _fitted_ardl()
    scenarios = _scenarios(index, last_value)
    with pytest.raises(ValueError, match="at least 100"):
        forecast_ardl_parameter_uncertainty(fitted, scenarios, draws=50)
    with pytest.raises(ValueError, match="baseline"):
        forecast_ardl_parameter_uncertainty(fitted, {"Adverse": scenarios["Adverse"]})
    bad = scenarios["Adverse"].copy()
    bad.index = bad.index + pd.offsets.MonthBegin(1)
    with pytest.raises(ValueError, match="continue the estimation sample"):
        forecast_ardl_parameter_uncertainty(
            fitted, {"Baseline": scenarios["Baseline"], "Adverse": bad}
        )
