"""Guarded VECM estimation and residual diagnostics.

The wrapper requires externally reviewed I(1) assessments and a manually
reviewed cointegration rank. It does not select the rank or establish
structural causality.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List

import numpy as np
import pandas as pd
from statsmodels.tsa.vector_ar.vecm import VECM


@dataclass(frozen=True)
class VECMResult:
    """VECM estimates, adjustment/cointegration parameters and diagnostics."""

    variables: List[str]
    observations: int
    effective_observations: int
    estimated_parameter_count: int
    sample_start: str
    sample_end: str
    cointegration_rank: int
    lagged_differences: int
    deterministic: str
    adjustment_coefficients: List[List[float]]
    cointegrating_vectors: List[List[float]]
    short_run_coefficients: List[List[float]]
    residual_covariance: List[List[float]]
    whiteness_lags: int
    whiteness_statistic: float
    whiteness_pvalue: float
    normality_statistic: float
    normality_pvalue: float
    log_likelihood: float

    def to_dict(self) -> dict:
        return asdict(self)


def fit_vecm_model(
    data: pd.DataFrame,
    integration_assessments: Dict[str, str],
    cointegration_rank: int,
    k_ar_diff: int = 1,
    deterministic: str = "co",
    whiteness_lags: int = 12,
) -> VECMResult:
    """Estimate a VECM after I(1) and cointegration-rank review.

    Every included variable must have an explicit reviewed I(1) assessment.
    The cointegration rank must be between one and the number of variables
    minus one. The rank should be selected from reviewed Johansen evidence,
    not chosen to improve coefficient significance.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame.")
    if data.shape[1] < 2:
        raise ValueError("VECM requires at least two endogenous variables.")
    if not data.columns.is_unique:
        raise ValueError("VECM variable names must be unique.")
    if data.index.has_duplicates or not data.index.is_monotonic_increasing:
        raise ValueError("VECM index must be unique and sorted in increasing order.")
    if isinstance(data.index, pd.DatetimeIndex) and pd.infer_freq(data.index) is None:
        raise ValueError("VECM DatetimeIndex must be regular with no missing periods.")
    if not all(pd.api.types.is_numeric_dtype(data[c]) for c in data.columns):
        raise TypeError("All VECM variables must be numeric.")
    if data.isna().any().any() or not np.isfinite(data.to_numpy(dtype=float)).all():
        raise ValueError("VECM data must be complete and finite.")
    variables = [str(c) for c in data.columns]
    if not isinstance(integration_assessments, dict):
        raise TypeError("integration_assessments must be a dictionary.")
    if set(integration_assessments) != set(variables):
        raise ValueError("Integration assessments must match exactly the VECM variables.")
    if any(value != "I(1)" for value in integration_assessments.values()):
        raise ValueError("VECM requires reviewed I(1) evidence for every included variable.")
    if not isinstance(cointegration_rank, int) or not 1 <= cointegration_rank < data.shape[1]:
        raise ValueError("cointegration_rank must be between 1 and number of variables minus one.")
    if not isinstance(k_ar_diff, int) or k_ar_diff < 0:
        raise ValueError("k_ar_diff must be a non-negative integer.")
    allowed_deterministic = {"n", "ci", "co", "li", "lo", "coli", "colo"}
    if deterministic not in allowed_deterministic:
        raise ValueError(f"deterministic must be one of {sorted(allowed_deterministic)}.")
    n, k = data.shape
    if n < max(60, 10 * k + 10 * k_ar_diff):
        raise ValueError(f"Insufficient observations for VECM estimation: {n}.")
    if not isinstance(whiteness_lags, int) or whiteness_lags <= k_ar_diff + 1:
        raise ValueError("whiteness_lags must exceed the implied VAR lag order (k_ar_diff + 1).")
    if np.linalg.matrix_rank(data.to_numpy(dtype=float)) < k:
        raise ValueError("VECM input matrix is rank deficient.")

    fitted = VECM(
        data,
        k_ar_diff=k_ar_diff,
        coint_rank=cointegration_rank,
        deterministic=deterministic,
    ).fit()
    whiteness = fitted.test_whiteness(nlags=whiteness_lags)
    normality = fitted.test_normality()

    return VECMResult(
        variables=variables,
        observations=int(n),
        effective_observations=int(fitted.nobs),
        estimated_parameter_count=int(np.asarray(fitted.stderr_params).size),
        sample_start=str(data.index[0]),
        sample_end=str(data.index[-1]),
        cointegration_rank=int(cointegration_rank),
        lagged_differences=int(k_ar_diff),
        deterministic=deterministic,
        adjustment_coefficients=np.asarray(fitted.alpha, dtype=float).tolist(),
        cointegrating_vectors=np.asarray(fitted.beta, dtype=float).tolist(),
        short_run_coefficients=np.asarray(fitted.gamma, dtype=float).tolist(),
        residual_covariance=np.asarray(fitted.sigma_u, dtype=float).tolist(),
        whiteness_lags=int(whiteness_lags),
        whiteness_statistic=float(whiteness.test_statistic),
        whiteness_pvalue=float(whiteness.pvalue),
        normality_statistic=float(normality.test_statistic),
        normality_pvalue=float(normality.pvalue),
        log_likelihood=float(fitted.llf),
    )
