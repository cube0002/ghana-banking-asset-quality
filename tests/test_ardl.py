"""Tests for guarded ARDL/UECM bounds estimation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest

from ghana_banking.econometrics.ardl import fit_ardl_bounds_model


def _ardl_data(n=180, seed=123):
    rng = np.random.default_rng(seed)
    x = np.cumsum(rng.normal(size=n))
    error = np.zeros(n)
    for i in range(1, n):
        error[i] = 0.5 * error[i - 1] + rng.normal(scale=0.5)
    y = 1.2 * x + error
    index = pd.date_range("2010-01-01", periods=n, freq="MS")
    return pd.DataFrame({"NPL": y, "FX": x}, index=index)


def test_ardl_bounds_workflow_returns_selection_and_bounds_metadata():
    data = _ardl_data()
    result = fit_ardl_bounds_model(
        data=data,
        dependent_variable="NPL",
        regressors=["FX"],
        integration_assessments={"NPL": "I(1)", "FX": "I(1)"},
        max_ar_lag=3,
        max_distributed_lag=3,
        selection_ic="bic",
        bounds_case=3,
    )
    payload = result.to_dict()
    assert payload["observations"] == 180
    assert payload["selected_ar_lag"] >= 1
    assert np.isfinite(payload["selected_ic_value"])
    assert payload["long_run_multipliers"] is not None
    assert payload["bounds_decision"] in {
        "evidence_of_level_relationship",
        "no_evidence_of_level_relationship",
        "inconclusive_bounds_test",
    }
    assert 0 <= payload["bounds_lower_pvalue"] <= 1
    assert 0 <= payload["bounds_upper_pvalue"] <= 1
    assert payload["ardl_parameters"]
    assert payload["uecm_parameters"]


def test_ardl_bounds_gate_rejects_all_stationary_system():
    with pytest.raises(ValueError, match="blocked"):
        fit_ardl_bounds_model(
            _ardl_data(), "NPL", ["FX"],
            {"NPL": "I(0)", "FX": "I(0)"},
            max_ar_lag=2, max_distributed_lag=2,
        )


def test_ardl_bounds_gate_rejects_possible_i2():
    with pytest.raises(ValueError, match="blocked"):
        fit_ardl_bounds_model(
            _ardl_data(), "NPL", ["FX"],
            {"NPL": "I(1)", "FX": "I(2)_or_higher_or_unresolved"},
            max_ar_lag=2, max_distributed_lag=2,
        )


def test_ardl_bounds_rejects_mismatched_deterministic_case():
    with pytest.raises(ValueError, match="paired with bounds_case"):
        fit_ardl_bounds_model(
            _ardl_data(), "NPL", ["FX"],
            {"NPL": "I(1)", "FX": "I(1)"},
            max_ar_lag=2, max_distributed_lag=2,
            trend="ct", bounds_case=3,
        )


def test_ardl_bounds_rejects_incomplete_input():
    data = _ardl_data()
    data.iloc[5, 0] = np.nan
    with pytest.raises(ValueError, match="complete and finite"):
        fit_ardl_bounds_model(
            data, "NPL", ["FX"], {"NPL": "I(1)", "FX": "I(1)"}
        )
