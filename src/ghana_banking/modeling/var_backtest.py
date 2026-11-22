"""Expanding-window, chronological VAR forecast evaluation.

Input data must already be transformed to a defensible stationary modelling
scale. The routine keeps lag order fixed across origins; any data-driven lag
selection or preprocessing must be repeated inside each training window if
it is part of the forecasting pipeline.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import List

import numpy as np
import pandas as pd
from statsmodels.tsa.api import VAR


@dataclass(frozen=True)
class VARBacktestResult:
    """Forecast-level records and horizon-specific benchmark comparisons."""

    variables: List[str]
    lag_order: int
    initial_window: int
    step: int
    horizons: List[int]
    forecast_origins: int
    sample_start: str
    sample_end: str
    forecast_records: List[dict]
    metrics: List[dict]

    def to_dict(self) -> dict:
        return asdict(self)


def _validate_regular_index(index: pd.Index) -> None:
    if isinstance(index, pd.PeriodIndex):
        if index.freq is None:
            raise ValueError("PeriodIndex must have a defined frequency.")
        return
    if isinstance(index, pd.DatetimeIndex):
        if pd.infer_freq(index) is None:
            raise ValueError("DatetimeIndex must be regular with no missing periods.")
        return
    if not pd.api.types.is_numeric_dtype(index.dtype):
        raise TypeError("Index must be a regular DatetimeIndex, PeriodIndex or numeric index.")
    if len(index) > 2:
        differences = np.diff(np.asarray(index, dtype=float))
        if not np.all(differences == differences[0]):
            raise ValueError("Index must have equally spaced observations.")


def expanding_window_var_backtest(
    data: pd.DataFrame,
    lag_order: int,
    initial_window: int,
    horizons: List[int] = (1, 3, 6),
    step: int = 1,
    trend: str = "c",
) -> VARBacktestResult:
    """Evaluate fixed-order VAR forecasts using expanding chronological windows.

    The input is treated as already transformed/stationary. At each origin,
    the model is re-estimated using observations available up to that origin.
    An expanding historical-mean forecast is included as a transparent
    benchmark. Metrics are reported separately by variable and horizon.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame.")
    if data.shape[1] < 2:
        raise ValueError("VAR backtesting requires at least two variables.")
    if not data.columns.is_unique:
        raise ValueError("Variable names must be unique.")
    if data.index.has_duplicates or not data.index.is_monotonic_increasing:
        raise ValueError("Index must be unique and sorted in increasing order.")
    _validate_regular_index(data.index)
    if not all(pd.api.types.is_numeric_dtype(data[c]) for c in data.columns):
        raise TypeError("All VAR variables must be numeric.")
    if data.isna().any().any() or not np.isfinite(data.to_numpy(dtype=float)).all():
        raise ValueError("Backtest data must be complete and finite.")
    if not isinstance(lag_order, int) or lag_order < 1:
        raise ValueError("lag_order must be a positive integer.")
    if not isinstance(initial_window, int) or initial_window <= lag_order + data.shape[1] + 1:
        raise ValueError("initial_window is too small for the requested VAR.")
    if not isinstance(horizons, (list, tuple)) or not horizons:
        raise ValueError("horizons must be a non-empty list or tuple of positive integers.")
    horizon_list = sorted(set(horizons))
    if any(not isinstance(h, int) or h < 1 for h in horizon_list):
        raise ValueError("Every forecast horizon must be a positive integer.")
    if len(horizon_list) != len(horizons):
        raise ValueError("horizons must not contain duplicates.")
    if not isinstance(step, int) or step < 1:
        raise ValueError("step must be a positive integer.")
    if trend not in {"n", "c", "ct", "ctt"}:
        raise ValueError("trend must be one of 'n', 'c', 'ct', or 'ctt'.")
    max_horizon = max(horizon_list)
    if initial_window + max_horizon > len(data):
        raise ValueError("Insufficient observations after initial_window for the maximum horizon.")

    records = []
    origins = list(range(initial_window, len(data) - max_horizon + 1, step))
    for origin in origins:
        training = data.iloc[:origin]
        fitted = VAR(training).fit(lag_order, trend=trend)
        forecast_array = fitted.forecast(
            training.iloc[-lag_order:].to_numpy(dtype=float),
            steps=max_horizon,
        )
        benchmark = training.mean(axis=0).to_numpy(dtype=float)
        for horizon in horizon_list:
            actual_row = data.iloc[origin + horizon - 1]
            forecast_row = forecast_array[horizon - 1]
            target_date = data.index[origin + horizon - 1]
            for column_index, variable in enumerate(data.columns):
                records.append({
                    "origin": str(data.index[origin - 1]),
                    "target_date": str(target_date),
                    "horizon": int(horizon),
                    "variable": str(variable),
                    "actual": float(actual_row.iloc[column_index]),
                    "var_forecast": float(forecast_row[column_index]),
                    "expanding_mean_forecast": float(benchmark[column_index]),
                })

    forecast_frame = pd.DataFrame(records)
    metrics = []
    for (variable, horizon), group in forecast_frame.groupby(["variable", "horizon"], sort=False):
        actual = group["actual"].to_numpy(dtype=float)
        var_error = actual - group["var_forecast"].to_numpy(dtype=float)
        mean_error = actual - group["expanding_mean_forecast"].to_numpy(dtype=float)
        metrics.append({
            "variable": str(variable),
            "horizon": int(horizon),
            "n_forecasts": int(len(group)),
            "var_mae": float(np.mean(np.abs(var_error))),
            "var_rmse": float(np.sqrt(np.mean(var_error ** 2))),
            "mean_benchmark_mae": float(np.mean(np.abs(mean_error))),
            "mean_benchmark_rmse": float(np.sqrt(np.mean(mean_error ** 2))),
        })

    return VARBacktestResult(
        variables=[str(column) for column in data.columns],
        lag_order=lag_order,
        initial_window=initial_window,
        step=step,
        horizons=[int(h) for h in horizon_list],
        forecast_origins=len(origins),
        sample_start=str(data.index[0]),
        sample_end=str(data.index[-1]),
        forecast_records=records,
        metrics=metrics,
    )
