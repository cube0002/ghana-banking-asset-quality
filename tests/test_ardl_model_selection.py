"""Tests for prespecified ARDL model-selection sensitivity."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest
from statsmodels.tsa.ardl import ARDL

from ghana_banking.modeling import run_ardl_model_selection_sensitivity


def _candidate(lags, order):
    rng = np.random.default_rng(31)
    n = 150
    x = np.cumsum(rng.normal(0, 0.08, n))
    y = np.zeros(n)
    noise = rng.normal(0, 0.15, n)
    for t in range(2, n):
        y[t] = 0.42 * y[t - 1] + 0.16 * x[t] + 0.07 * x[t - 1] + noise[t]
    index = pd.date_range("2012-01-01", periods=n, freq="MS")
    endog = pd.Series(y, index=index, name="npl_ratio")
    exog = pd.DataFrame({"inflation": x}, index=index)
    return ARDL(endog, lags=lags, exog=exog, order=order, trend="c").fit(), index, x[-1]


def _scenario_paths(index, last_value, horizon=6):
    future = pd.date_range(index[-1] + pd.offsets.MonthBegin(1), periods=horizon, freq="MS")
    return {
        "Baseline": pd.DataFrame({"inflation": np.repeat(last_value, horizon)}, index=future),
        "Adverse": pd.DataFrame({"inflation": np.repeat(last_value + 0.8, horizon)}, index=future),
    }


def test_model_selection_sensitivity_compares_candidates_on_common_horizon():
    fitted_a, index, last = _candidate(1, 1)
    fitted_b, _, _ = _candidate(2, 1)
    paths = _scenario_paths(index, last)
    result = run_ardl_model_selection_sensitivity(
        {"short_lag": fitted_a, "longer_lag": fitted_b},
        {"short_lag": paths, "longer_lag": paths},
    )
    assert set(result.forecasts["candidate_model"]) == {"short_lag", "longer_lag"}
    assert len(result.forecasts) == 2 * 2 * 6
    assert set(result.summary["scenario"]) == {"Baseline", "Adverse"}
    assert set(result.specifications["candidate_model"]) == {"short_lag", "longer_lag"}
    baseline = result.forecasts[result.forecasts["scenario"] == "Baseline"]
    assert np.allclose(baseline["change_vs_baseline"], 0.0)
    assert result.to_dict()["interpretation"].startswith("Specification sensitivity")


def test_model_selection_sensitivity_rejects_inconsistent_candidates():
    fitted_a, index, last = _candidate(1, 1)
    fitted_b, _, _ = _candidate(2, 1)
    paths = _scenario_paths(index, last)
    with pytest.raises(ValueError, match="exactly one scenario mapping"):
        run_ardl_model_selection_sensitivity(
            {"a": fitted_a, "b": fitted_b}, {"a": paths}
        )
    wrong_paths = _scenario_paths(index, last, horizon=5)
    with pytest.raises(ValueError, match="same future periods"):
        run_ardl_model_selection_sensitivity(
            {"a": fitted_a, "b": fitted_b},
            {"a": paths, "b": wrong_paths},
        )
    with pytest.raises(ValueError, match="same scenario names"):
        run_ardl_model_selection_sensitivity(
            {"a": fitted_a, "b": fitted_b},
            {"a": paths, "b": {"Baseline": paths["Baseline"]}},
        )


def test_model_selection_sensitivity_requires_baseline_and_valid_alpha():
    fitted, index, last = _candidate(1, 1)
    paths = _scenario_paths(index, last)
    with pytest.raises(ValueError, match="missing baseline"):
        run_ardl_model_selection_sensitivity(
            {"a": fitted}, {"a": {"Adverse": paths["Adverse"]}}
        )
    with pytest.raises(ValueError, match="significance_level"):
        run_ardl_model_selection_sensitivity(
            {"a": fitted}, {"a": paths}, significance_level=1.0
        )
