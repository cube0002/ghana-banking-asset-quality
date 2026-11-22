"""Reusable one-break unit-root diagnostics.

Zivot-Andrews is a sensitivity test for a unit root with one unknown break.
It does not estimate a general multiple-break model or replace parameter-
stability analysis.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import zivot_andrews


@dataclass(frozen=True)
class ZivotAndrewsResult:
    """Auditable Zivot-Andrews test result, including the estimated break date."""

    series_name: str
    statistic: float
    pvalue: float
    critical_values: Dict[str, float]
    null_hypothesis: str
    alternative_hypothesis: str
    regression: str
    observations: int
    sample_start: str
    sample_end: str
    break_index: int
    break_date: str
    selected_lags: int
    lag_method: str
    max_lags: Optional[int]
    trim: float
    significance_level: float
    frequency: Optional[str] = None
    transformation: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def run_zivot_andrews_test(
    series: pd.Series,
    series_name: Optional[str] = None,
    regression: str = "ct",
    max_lags: Optional[int] = 12,
    autolag: str = "BIC",
    trim: float = 0.15,
    alpha: float = 0.05,
    frequency: Optional[str] = None,
    transformation: Optional[str] = "level",
) -> ZivotAndrewsResult:
    """Run the Zivot-Andrews one-break unit-root test on a complete series.

    regression choices follow statsmodels: 'c' (intercept break), 't'
    (trend break), or 'ct' (intercept and trend break). The estimated break
    index is zero-based and break_date is taken from the input index.
    """
    if not isinstance(series, pd.Series):
        raise TypeError("series must be a pandas Series.")
    if series.empty or not pd.api.types.is_numeric_dtype(series.dtype):
        raise TypeError("series must be a non-empty numeric pandas Series.")
    if series.index.has_duplicates:
        raise ValueError("series index must not contain duplicate observations.")
    if not series.index.is_monotonic_increasing:
        raise ValueError("series index must be sorted in increasing time order.")
    values = series.astype(float)
    if not np.isfinite(values.to_numpy()).all():
        raise ValueError("series must contain only finite, non-missing observations.")
    if len(values) < 40:
        raise ValueError("At least 40 observations are required for this break test.")
    if values.nunique() < 2:
        raise ValueError("series must contain variation.")
    if regression not in {"c", "t", "ct"}:
        raise ValueError("regression must be 'c', 't' or 'ct'.")
    if autolag not in {"AIC", "BIC", "t-stat"}:
        raise ValueError("autolag must be 'AIC', 'BIC' or 't-stat'.")
    if max_lags is not None and (
        not isinstance(max_lags, int) or max_lags < 0
    ):
        raise ValueError("max_lags must be a non-negative integer or None.")
    if not 0 < trim < 0.5:
        raise ValueError("trim must be strictly between 0 and 0.5.")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be strictly between 0 and 1.")

    statistic, pvalue, critical_values, selected_lags, break_index = (
        zivot_andrews(
            values.to_numpy(),
            trim=trim,
            maxlag=max_lags,
            regression=regression,
            autolag=autolag,
        )
    )
    name = series_name or (
        str(series.name) if series.name is not None else "series"
    )
    return ZivotAndrewsResult(
        series_name=name,
        statistic=float(statistic),
        pvalue=float(pvalue),
        critical_values={
            str(key): float(value) for key, value in critical_values.items()
        },
        null_hypothesis="The series has a unit root with one structural break.",
        alternative_hypothesis=(
            "The series is stationary with one structural break."
        ),
        regression=regression,
        observations=int(len(values)),
        sample_start=str(values.index[0]),
        sample_end=str(values.index[-1]),
        break_index=int(break_index),
        break_date=str(values.index[int(break_index)]),
        selected_lags=int(selected_lags),
        lag_method=autolag,
        max_lags=max_lags,
        trim=float(trim),
        significance_level=float(alpha),
        frequency=frequency,
        transformation=transformation,
    )
