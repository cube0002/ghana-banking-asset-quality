"""Residual specification tests and HAC inference for prespecified OLS models.

The diagnostics are conditional on the supplied stationary regression
specification. They do not repair non-stationarity, endogeneity, omitted
variables or an invalid causal design.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import (
    acorr_breusch_godfrey,
    het_arch,
    het_breuschpagan,
    het_white,
    linear_reset,
)
from statsmodels.stats.stattools import durbin_watson, jarque_bera


@dataclass(frozen=True)
class OLSResidualDiagnosticsResult:
    """Auditable residual tests, conventional/HAC inference and sample details."""

    dependent_variable: str
    regressors: List[str]
    observations: int
    sample_start: str
    sample_end: str
    residual_tests: Dict[str, dict]
    durbin_watson_statistic: float
    hac_lags: int
    conventional_parameters: List[dict]
    hac_parameters: List[dict]
    hac_covariance: List[List[float]]
    r_squared: float
    adjusted_r_squared: float
    aic: float
    bic: float

    def to_dict(self) -> dict:
        return asdict(self)


def _test_record(statistic: float, pvalue: float, null_hypothesis: str) -> dict:
    return {
        "statistic": float(statistic),
        "p_value": float(pvalue),
        "null_hypothesis": null_hypothesis,
    }


def _parameter_records(result, names: List[str]) -> List[dict]:
    params = np.asarray(result.params, dtype=float)
    standard_errors = np.asarray(result.bse, dtype=float)
    t_statistics = np.asarray(result.tvalues, dtype=float)
    p_values = np.asarray(result.pvalues, dtype=float)
    intervals = np.asarray(result.conf_int(), dtype=float)
    return [
        {
            "term": str(name),
            "coefficient": float(params[index]),
            "standard_error": float(standard_errors[index]),
            "t_statistic": float(t_statistics[index]),
            "p_value": float(p_values[index]),
            "confidence_interval_lower": float(intervals[index, 0]),
            "confidence_interval_upper": float(intervals[index, 1]),
        }
        for index, name in enumerate(names)
    ]


def run_ols_residual_diagnostics(
    data: pd.DataFrame,
    dependent_variable: str,
    regressors: List[str],
    autocorrelation_lags: int = 12,
    arch_lags: int = 12,
    hac_lags: Optional[int] = None,
    reset_power: int = 2,
) -> OLSResidualDiagnosticsResult:
    """Fit a prespecified OLS equation and test its residual specification.

    Reports Breusch-Godfrey serial-correlation, Breusch-Pagan and White
    heteroskedasticity, ARCH, Jarque-Bera normality, RESET functional-form,
    and Durbin-Watson diagnostics. Also reports Newey-West/HAC coefficient
    inference alongside conventional OLS inference.

    HAC standard errors address specified forms of heteroskedasticity and
    autocorrelation in coefficient covariance estimation; they do not fix a
    misspecified conditional mean, non-stationarity or endogeneity.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame.")
    if not isinstance(regressors, list) or not regressors or len(set(regressors)) != len(regressors):
        raise ValueError("regressors must be a non-empty list of unique columns.")
    if dependent_variable in regressors:
        raise ValueError("The dependent variable cannot also be a regressor.")
    columns = [dependent_variable] + regressors
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    if not data.index.is_unique or not data.index.is_monotonic_increasing:
        raise ValueError("data index must be unique and sorted in increasing order.")
    frame = data[columns].copy()
    if not all(pd.api.types.is_numeric_dtype(frame[column]) for column in columns):
        raise TypeError("All model variables must be numeric.")
    if frame.isna().any().any() or not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError("data must be complete and finite; resolve missingness explicitly.")

    n = len(frame)
    k = len(regressors) + 1
    if n < max(40, 10 * k):
        raise ValueError(f"Insufficient observations for residual diagnostics: {n}.")
    for name, value in (("autocorrelation_lags", autocorrelation_lags), ("arch_lags", arch_lags)):
        if not isinstance(value, int) or value < 1 or value >= n // 2:
            raise ValueError(f"{name} must be a positive integer smaller than half the sample.")
    if not isinstance(reset_power, int) or reset_power < 2:
        raise ValueError("reset_power must be an integer of at least 2.")
    if hac_lags is None:
        hac_lags = max(1, int(np.floor(4 * (n / 100) ** (2 / 9))))
    if not isinstance(hac_lags, int) or hac_lags < 1 or hac_lags >= n:
        raise ValueError("hac_lags must be a positive integer smaller than the sample size.")

    y = frame[dependent_variable]
    x = sm.add_constant(frame[regressors], has_constant="add")
    if np.linalg.matrix_rank(x.to_numpy(dtype=float)) < x.shape[1]:
        raise ValueError("The regression design matrix is rank deficient.")

    fitted = sm.OLS(y, x).fit()
    if not np.isfinite(np.asarray(fitted.resid, dtype=float)).all():
        raise ValueError("OLS residuals are not finite.")
    robust = fitted.get_robustcov_results(cov_type="HAC", maxlags=hac_lags, use_correction=True)

    bg = acorr_breusch_godfrey(fitted, nlags=autocorrelation_lags)
    bp = het_breuschpagan(fitted.resid, fitted.model.exog, robust=True)
    white = het_white(fitted.resid, fitted.model.exog)
    arch = het_arch(fitted.resid, nlags=arch_lags)
    jb_stat, jb_pvalue, _, _ = jarque_bera(fitted.resid)
    reset = linear_reset(fitted, power=reset_power, use_f=True)

    residual_tests = {
        "breusch_godfrey": _test_record(
            bg[0], bg[1],
            f"No residual autocorrelation through lag {autocorrelation_lags}.",
        ),
        "breusch_pagan": _test_record(
            bp[0], bp[1], "Homoskedasticity: residual variance is constant.",
        ),
        "white": _test_record(
            white[0], white[1], "Homoskedasticity: residual variance is constant.",
        ),
        "arch_lm": _test_record(
            arch[0], arch[1],
            f"No ARCH effects through lag {arch_lags}.",
        ),
        "jarque_bera": _test_record(
            jb_stat, jb_pvalue, "Residuals are normally distributed.",
        ),
        "ramsey_reset": _test_record(
            reset.fvalue, reset.pvalue,
            f"The conditional mean is correctly specified against RESET powers through {reset_power}.",
        ),
    }

    hac_cov = np.asarray(robust.cov_params(), dtype=float)
    return OLSResidualDiagnosticsResult(
        dependent_variable=dependent_variable,
        regressors=list(regressors),
        observations=int(n),
        sample_start=str(frame.index[0]),
        sample_end=str(frame.index[-1]),
        residual_tests=residual_tests,
        durbin_watson_statistic=float(durbin_watson(fitted.resid)),
        hac_lags=int(hac_lags),
        conventional_parameters=_parameter_records(fitted, list(x.columns)),
        hac_parameters=_parameter_records(robust, list(x.columns)),
        hac_covariance=hac_cov.tolist(),
        r_squared=float(fitted.rsquared),
        adjusted_r_squared=float(fitted.rsquared_adj),
        aic=float(fitted.aic),
        bic=float(fitted.bic),
    )
