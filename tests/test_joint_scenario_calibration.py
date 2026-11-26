"""Tests for joint historical scenario calibration."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest

from ghana_banking.modeling import calibrate_joint_historical_scenario_paths


def _history(n=220, seed=41):
    rng = np.random.default_rng(seed)
    shocks = rng.multivariate_normal([0.0, 0.0], [[1.0, 0.75], [0.75, 1.0]], size=n)
    x, z = np.zeros(n), np.zeros(n)
    for t in range(1, n):
        x[t] = 0.35 * x[t - 1] + shocks[t, 0]
        z[t] = 0.25 * z[t - 1] + shocks[t, 1]
    idx = pd.date_range("2008-01-01", periods=n, freq="MS")
    return pd.DataFrame({"inflation": x, "depreciation": z}, index=idx)


def test_joint_calibrator_returns_aligned_paths_and_preserves_joint_blocks():
    result = calibrate_joint_historical_scenario_paths(
        _history(), 6, {"inflation": 1, "depreciation": 1}
    )
    assert set(result) == {"Baseline", "Adverse", "Severe"}
    assert all(path.shape == (6, 2) for path in result.values())
    meta = result["Severe"].attrs["calibration"]
    assert meta["cross_variable_dependence"].startswith("preserved")
    assert meta["temporal_dependence"].startswith("historical ordering")
    assert meta["candidate_blocks"] > 2
    assert meta["severe_block_score"] >= meta["adverse_block_score"]


def test_joint_calibrator_handles_integrated_variables():
    history = _history()
    history["fx_level"] = 5 + history["depreciation"].cumsum()
    result = calibrate_joint_historical_scenario_paths(
        history, 5,
        {"inflation": 1, "depreciation": 1, "fx_level": 1},
        integrated_variables=["fx_level"],
    )
    assert np.isfinite(result["Severe"].to_numpy()).all()
    assert result["Severe"].attrs["calibration"]["variables"][2]["process_modelled"] == "first_difference"
    assert result["Baseline"]["fx_level"].index.equals(result["Severe"].index)


def test_joint_calibrator_rejects_invalid_inputs_and_short_history():
    history = _history()
    with pytest.raises(ValueError, match="adverse_directions"):
        calibrate_joint_historical_scenario_paths(history, 4, {"inflation": 1})
    broken = history.copy()
    broken.iloc[0, 0] = np.nan
    with pytest.raises(ValueError, match="complete and finite"):
        calibrate_joint_historical_scenario_paths(
            broken, 4, {"inflation": 1, "depreciation": 1}
        )
    with pytest.raises(ValueError, match="candidate historical"):
        calibrate_joint_historical_scenario_paths(
            history.iloc[:41], 40, {"inflation": 1, "depreciation": 1}
        )



def test_joint_calibrator_accepts_and_records_normalized_severity_weights():
    history = _history()
    result = calibrate_joint_historical_scenario_paths(
        history, 6,
        {"inflation": 1, "depreciation": 1},
        severity_weights={"inflation": 3.0, "depreciation": 1.0},
    )
    weights = result["Severe"].attrs["calibration"]["severity_weights"]
    assert weights == {"inflation": 0.75, "depreciation": 0.25}
    assert result["Severe"].attrs["calibration"]["score"].startswith("weighted")


def test_joint_calibrator_rejects_invalid_severity_weights():
    history = _history()
    directions = {"inflation": 1, "depreciation": 1}
    with pytest.raises(ValueError, match="specify every variable"):
        calibrate_joint_historical_scenario_paths(
            history, 6, directions, severity_weights={"inflation": 1.0}
        )
    with pytest.raises(ValueError, match="non-negative"):
        calibrate_joint_historical_scenario_paths(
            history, 6, directions,
            severity_weights={"inflation": 1.0, "depreciation": -1.0},
        )
    with pytest.raises(ValueError, match="positive sum"):
        calibrate_joint_historical_scenario_paths(
            history, 6, directions,
            severity_weights={"inflation": 0.0, "depreciation": 0.0},
        )


def test_joint_calibrator_uses_longer_episode_for_selection_but_forecast_horizon_for_paths():
    history = _history(n=220)
    result = calibrate_joint_historical_scenario_paths(
        history, 6,
        {"inflation": 1, "depreciation": 1},
        block_length=12,
    )
    assert all(path.shape == (6, 2) for path in result.values())
    meta = result["Severe"].attrs["calibration"]
    assert meta["horizon"] == 6
    assert meta["selection_block_length"] == 12
    assert meta["candidate_blocks"] == len(history) - 1 - 12 + 1
    assert meta["severe_block_end_period"] > meta["severe_forecast_shock_end_period"]


def test_joint_calibrator_rejects_selection_block_shorter_than_forecast_horizon():
    with pytest.raises(ValueError, match="greater than or equal to horizon"):
        calibrate_joint_historical_scenario_paths(
            _history(), 6,
            {"inflation": 1, "depreciation": 1},
            block_length=5,
        )
