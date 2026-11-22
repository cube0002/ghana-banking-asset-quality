"""Tests for OLS residual specification diagnostics and HAC inference."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest

from ghana_banking.econometrics.residuals import run_ols_residual_diagnostics


def _data(n=180, seed=41, serial_correlation=False):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    errors = rng.normal(size=n)
    if serial_correlation:
        for i in range(1, n):
            errors[i] += 0.75 * errors[i - 1]
    y = 1.0 + 0.8 * x1 - 0.4 * x2 + errors
    return pd.DataFrame(
        {"y": y, "x1": x1, "x2": x2},
        index=pd.date_range("2010-01-01", periods=n, freq="MS"),
    )


def test_residual_diagnostics_returns_tests_and_hac_inference():
    result = run_ols_residual_diagnostics(
        _data(), "y", ["x1", "x2"], autocorrelation_lags=6, arch_lags=6
    )
    payload = result.to_dict()
    expected_tests = {
        "breusch_godfrey", "breusch_pagan", "white",
        "arch_lm", "jarque_bera", "ramsey_reset",
    }
    assert set(payload["residual_tests"]) == expected_tests
    for record in payload["residual_tests"].values():
        assert np.isfinite(record["statistic"])
        assert 0 <= record["p_value"] <= 1
        assert record["null_hypothesis"]
    assert 1 <= payload["durbin_watson_statistic"] <= 3
    assert payload["hac_lags"] >= 1
    assert len(payload["conventional_parameters"]) == 3
    assert len(payload["hac_parameters"]) == 3
    assert np.asarray(payload["hac_covariance"]).shape == (3, 3)
    assert payload["observations"] == 180


def test_breusch_godfrey_detects_strong_serial_correlation():
    result = run_ols_residual_diagnostics(
        _data(serial_correlation=True), "y", ["x1", "x2"],
        autocorrelation_lags=6, arch_lags=6,
    )
    assert result.residual_tests["breusch_godfrey"]["p_value"] < 0.05


def test_residual_diagnostics_rejects_incomplete_or_rank_deficient_data():
    data = _data()
    data.iloc[3, 0] = np.nan
    with pytest.raises(ValueError, match="complete and finite"):
        run_ols_residual_diagnostics(data, "y", ["x1", "x2"])

    data = _data()
    data["x2"] = data["x1"]
    with pytest.raises(ValueError, match="rank deficient"):
        run_ols_residual_diagnostics(data, "y", ["x1", "x2"])


def test_residual_diagnostics_rejects_invalid_lag_settings():
    with pytest.raises(ValueError, match="autocorrelation_lags"):
        run_ols_residual_diagnostics(_data(), "y", ["x1"], autocorrelation_lags=0)
    with pytest.raises(ValueError, match="hac_lags"):
        run_ols_residual_diagnostics(_data(), "y", ["x1"], hac_lags=180)
