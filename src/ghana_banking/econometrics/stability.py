"""Parameter-stability diagnostics for a prespecified OLS equation.

These procedures assess coefficient constancy conditional on the supplied
regression specification. They do not identify causal breaks or select an
economic model. Candidate break dates should be justified independently.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import breaks_cusumolsresid, breaks_hansen


@dataclass(frozen=True)
class OLSStabilityResult:
    """Auditable stability diagnostics and rolling-coefficient metadata."""

    dependent_variable: str
    regressors: list
    observations: int
    sample_start: str
    sample_end: str
    cusum_statistic: float
    cusum_pvalue: float
    cusum_critical_values: Dict[str, float]
    hansen_statistic: float
    hansen_critical_values: Dict[str, float]
    rolling_window: int
    rolling_coefficients: list

    def to_dict(self) -> dict:
        return asdict(self)


def run_ols_stability_diagnostics(
    data: pd.DataFrame,
    dependent_variable: str,
    regressors: list,
    rolling_window: Optional[int] = None,
) -> OLSStabilityResult:
    """Fit a prespecified OLS equation and report CUSUM/Hansen stability tests.

    Input rows must be complete and finite; observations are not silently
    dropped. The default rolling window is max(36, 60% of the sample).
    A rolling window is descriptive and should not be used to choose a
    favourable subsample.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame.")
    if not regressors or len(set(regressors)) != len(regressors):
        raise ValueError("regressors must be a non-empty list of unique columns.")
    columns = [dependent_variable] + list(regressors)
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    if data.index.has_duplicates or not data.index.is_monotonic_increasing:
        raise ValueError("data index must be unique and sorted in increasing order.")
    frame = data[columns].copy()
    if not all(pd.api.types.is_numeric_dtype(frame[c]) for c in columns):
        raise TypeError("All model variables must be numeric.")
    if frame.isna().any().any() or not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError("data must be complete and finite; resolve missingness explicitly.")
    n, k = frame.shape[0], len(regressors) + 1
    if n < max(40, 5 * k):
        raise ValueError(f"Insufficient observations for stability diagnostics: {n}.")
    if rolling_window is None:
        rolling_window = max(36, int(np.ceil(0.60 * n)))
    if not isinstance(rolling_window, int) or rolling_window <= k or rolling_window >= n:
        raise ValueError("rolling_window must be an integer greater than model parameters and less than sample size.")

    y = frame[dependent_variable]
    x = sm.add_constant(frame[regressors], has_constant="add")
    fitted = sm.OLS(y, x).fit()

    cusum_stat, cusum_p, cusum_crit = breaks_cusumolsresid(
        fitted.resid, ddof=int(fitted.df_model) + 1
    )
    hansen_stat, hansen_crit = breaks_hansen(fitted)

    rolling_rows = []
    for end in range(rolling_window, n + 1):
        window = frame.iloc[end - rolling_window:end]
        rolling_fit = sm.OLS(
            window[dependent_variable],
            sm.add_constant(window[regressors], has_constant="add"),
        ).fit()
        row = {
            "window_start": str(window.index[0]),
            "window_end": str(window.index[-1]),
        }
        row.update({str(name): float(value) for name, value in rolling_fit.params.items()})
        rolling_rows.append(row)

    return OLSStabilityResult(
        dependent_variable=dependent_variable,
        regressors=list(regressors),
        observations=int(n),
        sample_start=str(frame.index[0]),
        sample_end=str(frame.index[-1]),
        cusum_statistic=float(cusum_stat),
        cusum_pvalue=float(cusum_p),
        cusum_critical_values={
            str(key): float(value) for key, value in cusum_crit.items()
        },
        hansen_statistic=float(hansen_stat),
        hansen_critical_values={
            str(key): float(value) for key, value in hansen_crit.items()
        },
        rolling_window=int(rolling_window),
        rolling_coefficients=rolling_rows,
    )
