"""Complementary unit-root and stationarity diagnostics.

ADF and Phillips-Perron test the null of a unit root. KPSS tests the null
of level or trend stationarity. Their p-values must not be combined as if
all three tests shared the same null hypothesis.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from arch.unitroot import ADF, KPSS, PhillipsPerron


@dataclass(frozen=True)
class UnitRootResult:
    """Auditable result from one unit-root/stationarity test."""

    series_name: str
    test: str
    statistic: float
    pvalue: float
    critical_values: Dict[str, float]
    null_hypothesis: str
    alternative_hypothesis: str
    deterministic: str
    observations: int
    effective_observations: int
    sample_start: Optional[str]
    sample_end: Optional[str]
    selected_lags: Optional[int]
    lag_method: str
    significance_level: float
    frequency: Optional[str] = None
    transformation: Optional[str] = None

    def to_dict(self) -> dict:
        """Return a serialization-friendly representation."""
        return asdict(self)


def _validate_series(series: pd.Series, series_name: Optional[str]) -> tuple:
    if not isinstance(series, pd.Series):
        raise TypeError("series must be a pandas Series.")
    if series.empty:
        raise ValueError("series cannot be empty.")
    if not pd.api.types.is_numeric_dtype(series.dtype):
        raise TypeError("series must contain numeric observations.")
    if series.index.has_duplicates:
        raise ValueError("series index must not contain duplicate observations.")
    if not series.index.is_monotonic_increasing:
        raise ValueError("series index must be sorted in increasing time order.")

    values = series.astype(float)
    if not np.isfinite(values.to_numpy()).all():
        raise ValueError(
            "series must contain only finite, non-missing observations. "
            "Resolve missing values without silently compressing the time index."
        )
    if len(values) < 8:
        raise ValueError("At least 8 observations are required to run the test suite.")

    name = series_name or (str(series.name) if series.name is not None else "series")
    start = str(series.index[0])
    end = str(series.index[-1])
    return values, name, start, end


def _critical_values(result) -> Dict[str, float]:
    return {str(key): float(value) for key, value in result.critical_values.items()}


def run_unit_root_suite(
    series: pd.Series,
    series_name: Optional[str] = None,
    deterministic: str = "c",
    adf_max_lags: Optional[int] = None,
    adf_method: str = "aic",
    adf_lags: Optional[int] = None,
    pp_lags: Optional[int] = None,
    kpss_lags: Optional[int] = None,
    alpha: float = 0.05,
    frequency: Optional[str] = None,
    transformation: Optional[str] = None,
) -> List[UnitRootResult]:
    """Run ADF, Phillips-Perron and KPSS tests on one complete series.

    deterministic is 'c' for an intercept or 'ct' for an intercept and
    linear trend. KPSS does not provide a no-constant specification, so
    'n' is deliberately not accepted as a common specification.

    ADF lag selection is automatic unless adf_lags is supplied. PP and KPSS
    use their package defaults unless explicit lag counts are supplied.
    Missing and infinite observations are rejected rather than silently
    dropped, because dropping dates can change time spacing.
    """
    values, name, start, end = _validate_series(series, series_name)

    if deterministic not in {"c", "ct"}:
        raise ValueError("deterministic must be 'c' or 'ct'.")
    if adf_method not in {"aic", "bic", "t-stat"}:
        raise ValueError("adf_method must be 'aic', 'bic' or 't-stat'.")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be strictly between 0 and 1.")
    for label, lag in (
        ("adf_max_lags", adf_max_lags),
        ("adf_lags", adf_lags),
        ("pp_lags", pp_lags),
        ("kpss_lags", kpss_lags),
    ):
        if lag is not None and (not isinstance(lag, int) or lag < 0):
            raise ValueError(f"{label} must be a non-negative integer or None.")
    if adf_lags is not None and adf_max_lags is not None:
        raise ValueError("Specify adf_lags or adf_max_lags, not both.")

    common = {
        "series_name": name,
        "deterministic": deterministic,
        "observations": int(values.shape[0]),
        "significance_level": float(alpha),
        "sample_start": start,
        "sample_end": end,
        "frequency": frequency,
        "transformation": transformation,
    }

    if adf_lags is not None:
        adf = ADF(values, lags=adf_lags, trend=deterministic)
        adf_lag_method = "fixed"
    else:
        adf = ADF(
            values,
            max_lags=adf_max_lags,
            method=adf_method,
            trend=deterministic,
        )
        adf_lag_method = "automatic:" + adf_method

    pp = PhillipsPerron(
        values,
        lags=pp_lags,
        trend=deterministic,
        test_type="tau",
    )
    kpss = KPSS(values, lags=kpss_lags, trend=deterministic)

    return [
        UnitRootResult(
            **common,
            effective_observations=int(adf.nobs),
            test="ADF",
            statistic=float(adf.stat),
            pvalue=float(adf.pvalue),
            critical_values=_critical_values(adf),
            null_hypothesis="The series has a unit root.",
            alternative_hypothesis="The series is stationary under the specified deterministic terms.",
            selected_lags=int(adf.lags),
            lag_method=adf_lag_method,
        ),
        UnitRootResult(
            **common,
            effective_observations=int(pp.nobs),
            test="Phillips-Perron",
            statistic=float(pp.stat),
            pvalue=float(pp.pvalue),
            critical_values=_critical_values(pp),
            null_hypothesis="The series has a unit root.",
            alternative_hypothesis="The series is stationary under the specified deterministic terms.",
            selected_lags=int(pp.lags),
            lag_method=(
                "fixed" if pp_lags is not None
                else "automatic:Newey-West bandwidth"
            ),
        ),
        UnitRootResult(
            **common,
            effective_observations=int(values.shape[0]),
            test="KPSS",
            statistic=float(kpss.stat),
            pvalue=float(kpss.pvalue),
            critical_values=_critical_values(kpss),
            null_hypothesis=(
                "The series is level-stationary."
                if deterministic == "c"
                else "The series is trend-stationary."
            ),
            alternative_hypothesis="The series has a unit root (is non-stationary).",
            selected_lags=int(kpss.lags),
            lag_method=(
                "fixed" if kpss_lags is not None
                else "automatic:default bandwidth"
            ),
        ),
    ]


def _evidence(results: List[UnitRootResult], alpha: float) -> str:
    by_test = {result.test: result for result in results}
    required = {"ADF", "Phillips-Perron", "KPSS"}
    if set(by_test) != required:
        raise ValueError(
            "Each assessment requires ADF, Phillips-Perron and KPSS results."
        )

    adf_rejects = by_test["ADF"].pvalue < alpha
    pp_rejects = by_test["Phillips-Perron"].pvalue < alpha
    kpss_rejects = by_test["KPSS"].pvalue < alpha

    if adf_rejects and pp_rejects and not kpss_rejects:
        return "stationarity_evidence"
    if not adf_rejects and not pp_rejects and kpss_rejects:
        return "unit_root_evidence"
    return "mixed_or_inconclusive"


def assess_integration_order(
    level_results: List[UnitRootResult],
    difference_results: Optional[List[UnitRootResult]] = None,
    alpha: float = 0.05,
) -> dict:
    """Assess I(0)/I(1) evidence without majority-vote classification.

    I(1) requires unit-root evidence in levels and stationarity evidence
    in first differences. Persistent unit-root evidence in differences is
    flagged as I(2)-or-higher-or-unresolved, not proof of I(2).
    """
    if not 0 < alpha < 1:
        raise ValueError("alpha must be strictly between 0 and 1.")

    level_evidence = _evidence(level_results, alpha)
    difference_evidence = (
        _evidence(difference_results, alpha)
        if difference_results is not None
        else None
    )

    if level_evidence == "stationarity_evidence":
        order = "I(0)"
    elif (
        level_evidence == "unit_root_evidence"
        and difference_evidence == "stationarity_evidence"
    ):
        order = "I(1)"
    elif (
        level_evidence == "unit_root_evidence"
        and difference_evidence == "unit_root_evidence"
    ):
        order = "I(2)_or_higher_or_unresolved"
    else:
        order = "uncertain"

    return {
        "integration_assessment": order,
        "level_evidence": level_evidence,
        "first_difference_evidence": difference_evidence,
        "alpha": alpha,
        "interpretation": (
            "Working assessment only. Review deterministic terms, structural "
            "breaks, sample size and economic context before model selection."
        ),
    }
