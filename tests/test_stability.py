"""Tests for regression parameter-stability diagnostics."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest

from ghana_banking.econometrics.stability import run_ols_stability_diagnostics


def _regression_data(n=150, seed=8, coefficient_break=False):
    rng = np.random.default_rng(seed)
    index = pd.date_range("2010-01-01", periods=n, freq="MS")
    x = rng.normal(size=n)
    beta = np.where(np.arange(n) >= n // 2, 2.0, 0.5) if coefficient_break else 1.2
    y = 1.0 + beta * x + rng.normal(scale=0.5, size=n)
    return pd.DataFrame({"y": y, "x": x}, index=index)


def test_stability_api_returns_tests_and_rolling_coefficients():
    result = run_ols_stability_diagnostics(
        _regression_data(), "y", ["x"], rolling_window=60
    )
    assert result.observations == 150
    assert 0 <= result.cusum_pvalue <= 1
    assert result.rolling_window == 60
    assert len(result.rolling_coefficients) == 91
    assert "const" in result.rolling_coefficients[0]
    assert "x" in result.rolling_coefficients[0]


def test_stability_api_rejects_incomplete_or_invalid_data():
    data = _regression_data()
    data.loc[data.index[5], "x"] = np.nan
    with pytest.raises(ValueError, match="complete and finite"):
        run_ols_stability_diagnostics(data, "y", ["x"])
    with pytest.raises(ValueError, match="Missing columns"):
        run_ols_stability_diagnostics(_regression_data(), "y", ["missing"])
    with pytest.raises(ValueError, match="rolling_window"):
        run_ols_stability_diagnostics(_regression_data(), "y", ["x"], 150)
