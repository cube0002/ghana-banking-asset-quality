"""Tests for ARDL scenario sensitivity analysis."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest
from statsmodels.tsa.ardl import ARDL

from ghana_banking.modeling import run_ardl_scenario_sensitivity


def _inputs(n=150, seed=22):
    rng = np.random.default_rng(seed)
    index = pd.date_range("2011-01-01", periods=n, freq="MS")
    x = np.zeros(n)
    y = np.zeros(n)
    e = rng.normal(size=n)
    u = rng.normal(size=n)
    for t in range(1, n):
        x[t] = 0.4 * x[t - 1] + e[t]
        y[t] = 0.5 * y[t - 1] + 0.2 * x[t] + u[t]
    exog = pd.DataFrame({"inflation": x}, index=index)
    endog = pd.Series(y, index=index, name="npl_change")
    return ARDL(endog, lags=1, exog=exog, order=1, trend="c").fit(), exog


def test_scenario_sensitivity_returns_summary_and_forecasts_for_each_setting():
    fitted, history = _inputs()
    result = run_ardl_scenario_sensitivity(
        fitted_results=fitted,
        historical_exog=history,
        horizon=4,
        adverse_directions={"inflation": 1},
        quantile_pairs=[(0.90, 0.975)],
        persistence_values=[0.3, 0.8],
    ).to_dict()
    assert len(result["summary"]) == 4
    assert len(result["forecasts"]) == 24
    assert {row["shock_persistence"] for row in result["summary"]} == {0.3, 0.8}
    assert {row["scenario"] for row in result["summary"]} == {"Adverse", "Severe"}
    assert all(row["n_periods"] == 4 for row in result["summary"])


def test_scenario_sensitivity_rejects_invalid_grids():
    fitted, history = _inputs()
    common = {
        "fitted_results": fitted,
        "historical_exog": history,
        "horizon": 3,
        "adverse_directions": {"inflation": 1},
    }
    with pytest.raises(ValueError, match="quantile pairs"):
        run_ardl_scenario_sensitivity(**common, quantile_pairs=[])
    with pytest.raises(ValueError, match="persistence values"):
        run_ardl_scenario_sensitivity(**common, persistence_values=[])
    with pytest.raises(ValueError, match="satisfy"):
        run_ardl_scenario_sensitivity(**common, quantile_pairs=[(0.98, 0.95)])
