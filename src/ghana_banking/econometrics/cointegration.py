"""Johansen cointegration-rank diagnostics for multivariate time series."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from statsmodels.tsa.vector_ar.vecm import coint_johansen


@dataclass(frozen=True)
class JohansenResult:
    """Auditable trace and maximum-eigenvalue cointegration diagnostics."""

    variables: List[str]
    observations: int
    sample_start: str
    sample_end: str
    deterministic_order: int
    deterministic_description: str
    lagged_differences: int
    significance_level: float
    trace_statistics: List[float]
    trace_critical_values: List[float]
    max_eigen_statistics: List[float]
    max_eigen_critical_values: List[float]
    trace_rank: int
    max_eigen_rank: int
    null_hypotheses: List[str]
    frequency: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _sequential_rank(statistics, critical_values) -> int:
    """Return first non-rejected rank under sequential 5% testing."""
    for rank, (statistic, critical) in enumerate(zip(statistics, critical_values)):
        if statistic <= critical:
            return rank
    return len(statistics)


def run_johansen_cointegration_test(
    data: pd.DataFrame,
    det_order: int = 0,
    k_ar_diff: int = 1,
    significance_level: float = 0.05,
    frequency: Optional[str] = None,
) -> JohansenResult:
    """Run Johansen trace and max-eigenvalue tests on a complete I(1) system.

    This function does not test whether variables are I(1); establish that
    separately. Do not include I(2) variables. The rank outputs are sequential
    test decisions at the requested significance level, not proof of a
    structural long-run relationship.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame.")
    if data.shape[1] < 2:
        raise ValueError("Johansen testing requires at least two variables.")
    if not data.columns.is_unique:
        raise ValueError("Variable names must be unique.")
    if not data.index.is_unique or not data.index.is_monotonic_increasing:
        raise ValueError("Index must be unique and sorted in increasing order.")
    if not all(pd.api.types.is_numeric_dtype(data[c]) for c in data.columns):
        raise TypeError("All variables must be numeric.")
    if data.isna().any().any() or not np.isfinite(data.to_numpy(dtype=float)).all():
        raise ValueError("Data must be complete and finite; resolve missingness explicitly.")
    if data.shape[0] < max(40, 10 * data.shape[1]):
        raise ValueError("Insufficient observations for the requested Johansen system.")
    if det_order not in {-1, 0, 1}:
        raise ValueError("det_order must be -1 (none), 0 (constant) or 1 (linear trend).")
    if not isinstance(k_ar_diff, int) or k_ar_diff < 1:
        raise ValueError("k_ar_diff must be a positive integer.")
    if k_ar_diff >= data.shape[0] // 3:
        raise ValueError("k_ar_diff is too large relative to the sample.")
    if significance_level not in {0.10, 0.05, 0.01}:
        raise ValueError("significance_level must be 0.10, 0.05 or 0.01.")

    result = coint_johansen(
        data.to_numpy(dtype=float),
        det_order=det_order,
        k_ar_diff=k_ar_diff,
    )
    critical_column = {0.10: 0, 0.05: 1, 0.01: 2}[significance_level]
    trace_stats = [float(value) for value in result.trace_stat]
    trace_crit = [
        float(row[critical_column]) for row in result.trace_stat_crit_vals
    ]
    max_stats = [float(value) for value in result.max_eig_stat]
    max_crit = [
        float(row[critical_column]) for row in result.max_eig_stat_crit_vals
    ]
    det_description = {
        -1: "no deterministic terms",
        0: "constant",
        1: "linear trend",
    }[det_order]
    variables = [str(column) for column in data.columns]
    return JohansenResult(
        variables=variables,
        observations=int(len(data)),
        sample_start=str(data.index[0]),
        sample_end=str(data.index[-1]),
        deterministic_order=det_order,
        deterministic_description=det_description,
        lagged_differences=k_ar_diff,
        significance_level=float(significance_level),
        trace_statistics=trace_stats,
        trace_critical_values=trace_crit,
        max_eigen_statistics=max_stats,
        max_eigen_critical_values=max_crit,
        trace_rank=_sequential_rank(trace_stats, trace_crit),
        max_eigen_rank=_sequential_rank(max_stats, max_crit),
        null_hypotheses=[
            f"Cointegration rank is at most {rank}."
            for rank in range(data.shape[1])
        ],
        frequency=frequency,
    )
