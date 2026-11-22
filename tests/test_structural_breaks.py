"""Tests for reusable structural-break diagnostics."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest

from ghana_banking.econometrics.structural_breaks import run_zivot_andrews_test


def _broken_trend(n=180, seed=42):
    rng = np.random.default_rng(seed)
    index = pd.date_range("2010-01-01", periods=n, freq="MS")
    trend = np.arange(n) * 0.03
    shift = np.where(np.arange(n) >= 95, 2.5, 0.0)
    noise = rng.normal(scale=0.25, size=n)
    return pd.Series(trend + shift + noise, index=index, name="broken")


def test_zivot_andrews_returns_auditable_break_metadata():
    result = run_zivot_andrews_test(
        _broken_trend(), regression="ct", max_lags=8, autolag="BIC",
        frequency="monthly",
    )
    payload = result.to_dict()
    assert payload["series_name"] == "broken"
    assert payload["observations"] == 180
    assert 0 <= payload["break_index"] < 180
    assert payload["break_date"] == str(_broken_trend().index[payload["break_index"]])
    assert 0 <= payload["pvalue"] <= 1
    assert payload["selected_lags"] >= 0
    assert set(payload["critical_values"]) == {"1%", "5%", "10%"}


@pytest.mark.parametrize("regression", ["c", "t", "ct"])
def test_supported_break_regressions(regression):
    result = run_zivot_andrews_test(_broken_trend(), regression=regression)
    assert result.regression == regression


def test_rejects_invalid_series_and_options():
    with pytest.raises(ValueError, match="finite"):
        run_zivot_andrews_test(_broken_trend().replace(2.0, np.nan))
    with pytest.raises(ValueError, match="duplicate"):
        duplicate = _broken_trend()
        duplicate.index = [duplicate.index[0]] * len(duplicate)
        run_zivot_andrews_test(duplicate)
    with pytest.raises(ValueError, match="regression"):
        run_zivot_andrews_test(_broken_trend(), regression="invalid")
    with pytest.raises(ValueError, match="40 observations"):
        run_zivot_andrews_test(_broken_trend(n=30))
