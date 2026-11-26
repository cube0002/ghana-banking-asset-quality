"""Expanding-window conditional ARDL forecast evaluation.

Future exogenous observations are supplied at their realised values. This
isolates the conditional NPL-model component but is an oracle-information
exercise, not an operational forecast using forecasted macro variables.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from statsmodels.tsa.ardl import ARDL
from statsmodels.tsa.ar_model import AutoReg


@dataclass(frozen=True)
class ARDLBacktestResult:
    """Chronological conditional ARDL forecasts and benchmark metrics."""

    dependent_variable: str
    regressors: list[str]
    ar_lags: int
    distributed_lags: object
    initial_window: int
    horizons: list[int]
    step: int
    trend: str
    hold_back: int | None
    forecast_origins: int
    information_set: str
    forecast_records: list[dict]
    metrics: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


def expanding_window_ardl_backtest(
    data: pd.DataFrame,
    dependent_variable: str,
    regressors: Sequence[str],
    ar_lags: int,
    distributed_lags,
    initial_window: int,
    horizons: Sequence[int] = (1, 3, 6),
    step: int = 1,
    trend: str = "c",
    hold_back: int | None = None,
    benchmark_ar_lags: int = 2,
    significance_level: float = 0.05,
) -> ARDLBacktestResult:
    """Evaluate a fixed ARDL specification using expanding chronological windows.

    At each origin the ARDL and univariate AR benchmark are re-estimated using
    only the training sample. Future exogenous regressors are set to their
    subsequently realised values. Therefore, ARDL performance is conditional
    on perfect knowledge of future macro regressors and must not be described
    as operational forecast accuracy. It is useful for separating conditional
    NPL-equation performance from the additional task of forecasting the
    macroeconomic inputs.

    Lag orders and transformations are fixed by the caller. If they were
    selected from data, that selection must be repeated within each origin
    rather than using the full sample.
    """
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise TypeError("data must be a non-empty pandas DataFrame.")
    if not data.columns.is_unique:
        raise ValueError("Data columns must be unique.")
    if data.index.has_duplicates or not data.index.is_monotonic_increasing:
        raise ValueError("Data index must be unique and sorted.")
    if not isinstance(dependent_variable, str) or dependent_variable not in data:
        raise ValueError("dependent_variable must name a column in data.")
    if not isinstance(regressors, (list, tuple)) or not regressors:
        raise ValueError("regressors must be a non-empty list or tuple.")
    if len(set(regressors)) != len(regressors) or dependent_variable in regressors:
        raise ValueError("Regressors must be unique and exclude the dependent variable.")
    missing = sorted(set(regressors) - set(data.columns))
    if missing:
        raise ValueError(f"Missing regressor columns: {missing}")
    selected = data[[dependent_variable] + list(regressors)]
    if not all(pd.api.types.is_numeric_dtype(selected[c]) for c in selected):
        raise TypeError("All model variables must be numeric.")
    values = selected.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Backtest data must be complete and finite.")
    if not isinstance(ar_lags, int) or ar_lags < 1:
        raise ValueError("ar_lags must be a positive integer.")
    if not isinstance(benchmark_ar_lags, int) or benchmark_ar_lags < 1:
        raise ValueError("benchmark_ar_lags must be a positive integer.")
    if not isinstance(initial_window, int) or initial_window <= max(ar_lags, benchmark_ar_lags) + 5:
        raise ValueError("initial_window is too small for the selected AR lags.")
    if not isinstance(horizons, (list, tuple)) or not horizons:
        raise ValueError("horizons must be a non-empty sequence.")
    if any(not isinstance(h, int) or h < 1 for h in horizons) or len(set(horizons)) != len(horizons):
        raise ValueError("horizons must contain unique positive integers.")
    horizon_list = sorted(horizons)
    if not isinstance(step, int) or step < 1:
        raise ValueError("step must be a positive integer.")
    if trend not in {"n", "c", "ct", "ctt"}:
        raise ValueError("trend must be one of 'n', 'c', 'ct', or 'ctt'.")
    if not isinstance(significance_level, (int, float)) or not 0 < significance_level < 1:
        raise ValueError("significance_level must lie strictly between 0 and 1.")
    if hold_back is not None and (not isinstance(hold_back, int) or hold_back < ar_lags):
        raise ValueError("hold_back must be None or an integer at least as large as ar_lags.")
    max_horizon = max(horizon_list)
    if initial_window + max_horizon > len(selected):
        raise ValueError("Insufficient observations after initial_window for maximum horizon.")

    endog = selected[dependent_variable].astype(float)
    exog = selected[list(regressors)].astype(float)
    origins = list(range(initial_window, len(selected) - max_horizon + 1, step))
    records = []

    for origin in origins:
        train_y = endog.iloc[:origin]
        train_x = exog.iloc[:origin]
        future_x = exog.iloc[origin:origin + max_horizon]
        fitted = ARDL(
            endog=train_y,
            lags=ar_lags,
            exog=train_x,
            order=distributed_lags,
            trend=trend,
            hold_back=hold_back,
        ).fit()
        prediction = fitted.get_prediction(
            start=origin,
            end=origin + max_horizon - 1,
            dynamic=True,
            exog_oos=future_x,
        ).summary_frame(alpha=float(significance_level))

        ar_fit = AutoReg(
            train_y, lags=benchmark_ar_lags, trend=trend, old_names=False
        ).fit()
        ar_prediction = ar_fit.get_prediction(
            start=origin,
            end=origin + max_horizon - 1,
            dynamic=True,
        ).summary_frame(alpha=float(significance_level))

        no_change = float(train_y.iloc[-1])
        historical_mean = float(train_y.mean())
        for horizon in horizon_list:
            position = horizon - 1
            target = origin + position
            row = prediction.iloc[position]
            ar_row = ar_prediction.iloc[position]
            records.append({
                "origin": str(data.index[origin - 1]),
                "target_date": str(data.index[target]),
                "horizon": int(horizon),
                "actual": float(endog.iloc[target]),
                "ardl_forecast": float(row["mean"]),
                "ardl_interval_lower": float(row["mean_ci_lower"]),
                "ardl_interval_upper": float(row["mean_ci_upper"]),
                "ar_forecast": float(ar_row["mean"]),
                "no_change_forecast": no_change,
                "expanding_mean_forecast": historical_mean,
                "information_set": "realised_future_exogenous_regressors",
            })

    forecast_frame = pd.DataFrame(records)
    metrics = []
    for horizon, group in forecast_frame.groupby("horizon", sort=True):
        actual = group["actual"].to_numpy(dtype=float)
        row = {"horizon": int(horizon), "n_forecasts": int(len(group))}
        for name, column in (
            ("ardl_conditional", "ardl_forecast"),
            ("ar", "ar_forecast"),
            ("no_change", "no_change_forecast"),
            ("expanding_mean", "expanding_mean_forecast"),
        ):
            errors = actual - group[column].to_numpy(dtype=float)
            row[f"{name}_mae"] = float(np.mean(np.abs(errors)))
            row[f"{name}_rmse"] = float(np.sqrt(np.mean(errors ** 2)))
        row["ardl_interval_coverage"] = float(np.mean(
            (actual >= group["ardl_interval_lower"].to_numpy(dtype=float))
            & (actual <= group["ardl_interval_upper"].to_numpy(dtype=float))
        ))
        row["ardl_mean_interval_width"] = float(np.mean(
            group["ardl_interval_upper"].to_numpy(dtype=float)
            - group["ardl_interval_lower"].to_numpy(dtype=float)
        ))
        metrics.append(row)

    return ARDLBacktestResult(
        dependent_variable=dependent_variable,
        regressors=list(regressors),
        ar_lags=ar_lags,
        distributed_lags=distributed_lags,
        initial_window=initial_window,
        horizons=horizon_list,
        step=step,
        trend=trend,
        hold_back=hold_back,
        forecast_origins=len(origins),
        information_set="realised_future_exogenous_regressors",
        forecast_records=records,
        metrics=metrics,
    )
