"""Tests for guarded VECM estimation and residual diagnostics."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest

from ghana_banking.econometrics.vecm import fit_vecm_model


def _cointegrated_data(n=240, seed=19):
    rng = np.random.default_rng(seed)
    common_walk = np.cumsum(rng.normal(size=n))
    equilibrium_error = np.zeros(n)
    innovations = rng.normal(size=n)
    for t in range(1, n):
        equilibrium_error[t] = 0.35 * equilibrium_error[t - 1] + innovations[t]
    second_walk = common_walk + equilibrium_error
    return pd.DataFrame(
        {"log_npl": common_walk, "log_credit": second_walk},
        index=pd.date_range("2005-01-01", periods=n, freq="MS"),
    )


def test_vecm_fit_returns_parameters_and_residual_diagnostics():
    data = _cointegrated_data()
    result = fit_vecm_model(
        data,
        integration_assessments={"log_npl": "I(1)", "log_credit": "I(1)"},
        cointegration_rank=1,
        k_ar_diff=1,
        deterministic="co",
        whiteness_lags=12,
    )
    payload = result.to_dict()
    assert payload["observations"] == 240
    assert payload["cointegration_rank"] == 1
    assert np.asarray(payload["adjustment_coefficients"]).shape == (2, 1)
    assert np.asarray(payload["cointegrating_vectors"]).shape == (2, 1)
    assert np.asarray(payload["residual_covariance"]).shape == (2, 2)
    assert 0 <= payload["whiteness_pvalue"] <= 1
    assert 0 <= payload["normality_pvalue"] <= 1


def test_vecm_requires_i1_evidence_and_reviewed_cointegration_rank():
    data = _cointegrated_data()
    with pytest.raises(ValueError, match=r"reviewed I\(1\) evidence"):
        fit_vecm_model(
            data,
            {"log_npl": "I(1)", "log_credit": "I(0)"},
            cointegration_rank=1,
        )
    with pytest.raises(ValueError, match="cointegration_rank"):
        fit_vecm_model(
            data,
            {"log_npl": "I(1)", "log_credit": "I(1)"},
            cointegration_rank=2,
        )


def test_vecm_rejects_incomplete_and_irregular_samples():
    data = _cointegrated_data()
    data.iloc[3, 0] = np.nan
    with pytest.raises(ValueError, match="complete and finite"):
        fit_vecm_model(
            data,
            {"log_npl": "I(1)", "log_credit": "I(1)"},
            cointegration_rank=1,
        )
    data = _cointegrated_data().drop(index=_cointegrated_data().index[10])
    with pytest.raises(ValueError, match="regular"):
        fit_vecm_model(
            data,
            {"log_npl": "I(1)", "log_credit": "I(1)"},
            cointegration_rank=1,
        )
