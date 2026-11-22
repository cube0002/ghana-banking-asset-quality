"""Tests for Johansen cointegration-rank diagnostics."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest

from ghana_banking.econometrics.cointegration import run_johansen_cointegration_test


def _cointegrated_data(n=180, seed=77):
    rng = np.random.default_rng(seed)
    common = np.cumsum(rng.normal(size=n))
    x = common + rng.normal(scale=0.2, size=n)
    y = 1.8 * common + rng.normal(scale=0.3, size=n)
    index = pd.date_range("2005-01-01", periods=n, freq="MS")
    return pd.DataFrame({"x": x, "y": y}, index=index)


def test_johansen_result_contains_both_rank_tests_and_metadata():
    result = run_johansen_cointegration_test(
        _cointegrated_data(), det_order=0, k_ar_diff=1, frequency="monthly"
    )
    payload = result.to_dict()
    assert payload["variables"] == ["x", "y"]
    assert payload["observations"] == 180
    assert len(payload["trace_statistics"]) == 2
    assert len(payload["max_eigen_statistics"]) == 2
    assert 0 <= payload["trace_rank"] <= 2
    assert 0 <= payload["max_eigen_rank"] <= 2
    assert payload["frequency"] == "monthly"


def test_johansen_rejects_incomplete_or_invalid_input():
    data = _cointegrated_data()
    data.iloc[4, 0] = np.nan
    with pytest.raises(ValueError, match="complete and finite"):
        run_johansen_cointegration_test(data)

    with pytest.raises(ValueError, match="at least two"):
        run_johansen_cointegration_test(_cointegrated_data()[["x"]])

    with pytest.raises(ValueError, match="det_order"):
        run_johansen_cointegration_test(_cointegrated_data(), det_order=2)

    with pytest.raises(ValueError, match="significance_level"):
        run_johansen_cointegration_test(_cointegrated_data(), significance_level=0.025)
