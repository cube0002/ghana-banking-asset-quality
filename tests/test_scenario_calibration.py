"""Tests for historical AR(1)-based scenario calibration."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest

from ghana_banking.modeling import calibrate_historical_scenario_paths


def _history(n=180, seed=31):
    rng = np.random.default_rng(seed)
    index = pd.date_range("2010-01-01", periods=n, freq="MS")
    inflation = np.zeros(n)
    depreciation = np.zeros(n)
    for t in range(1, n):
        inflation[t] = 0.35 * inflation[t - 1] + rng.normal(0, 0.4)
        depreciation[t] = 0.25 * depreciation[t - 1] + rng.normal(0, 0.7)
    fx_level = 5 + np.cumsum(depreciation)
    return pd.DataFrame({"inflation": inflation, "fx_change": depreciation, "fx_level": fx_level}, index=index)


def test_historical_calibrator_returns_aligned_baseline_adverse_and_severe_paths():
    history = _history()
    paths = calibrate_historical_scenario_paths(
        history,
        horizon=12,
        adverse_directions={"inflation": 1, "fx_change": 1, "fx_level": 1},
        integrated_variables=["fx_level"],
        persistence=0.6,
    )
    assert set(paths) == {"Baseline", "Adverse", "Severe"}
    assert all(frame.shape == (12, 3) for frame in paths.values())
    assert all(frame.index.equals(paths["Baseline"].index) for frame in paths.values())
    assert paths["Adverse"].attrs["cross_variable_dependence"] == "not preserved"
    assert paths["Severe"].attrs["calibration"][0]["innovation_observations"] > 0
    assert np.all(paths["Severe"]["inflation"] >= paths["Baseline"]["inflation"])
    assert np.all(paths["Adverse"]["fx_change"] >= paths["Baseline"]["fx_change"])
    assert paths["Severe"]["fx_level"].iloc[-1] >= paths["Adverse"]["fx_level"].iloc[-1]


def test_historical_calibrator_rejects_bad_directions_and_unstable_ar_process():
    history = _history()
    with pytest.raises(ValueError, match="adverse_directions"):
        calibrate_historical_scenario_paths(history, 6, {"inflation": 1})
    unstable = history.copy()
    unstable["explosive"] = np.cumsum(np.repeat(1.0, len(unstable)))
    with pytest.raises(ValueError, match="not stationary"):
        calibrate_historical_scenario_paths(
            unstable,
            6,
            {"inflation": 1, "fx_change": 1, "fx_level": 1, "explosive": 1},
        )


def test_historical_calibrator_rejects_missing_data_and_invalid_quantiles():
    history = _history()
    history.iloc[4, 0] = np.nan
    with pytest.raises(ValueError, match="complete and finite"):
        calibrate_historical_scenario_paths(
            history, 6, {"inflation": 1, "fx_change": 1, "fx_level": 1}
        )
    with pytest.raises(ValueError, match="severe_quantile"):
        calibrate_historical_scenario_paths(
            _history(), 6,
            {"inflation": 1, "fx_change": 1, "fx_level": 1},
            adverse_quantile=0.98, severe_quantile=0.95,
        )
