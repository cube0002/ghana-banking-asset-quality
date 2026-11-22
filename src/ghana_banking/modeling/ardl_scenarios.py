"""Conditional multi-period scenario forecasts from a fitted ARDL model.

Scenario paths are supplied in the exact exogenous-variable scale used for
estimation. Forecasts are conditional on the fitted model and do not identify
causal effects or account for model-selection uncertainty.
"""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


def _validate_future_index(training_index: pd.Index, future_index: pd.Index) -> None:
    if future_index.has_duplicates or not future_index.is_monotonic_increasing:
        raise ValueError("Scenario index must be unique and sorted.")
    if len(future_index) < 1:
        raise ValueError("Scenario paths must contain at least one future period.")

    if isinstance(training_index, pd.DatetimeIndex):
        frequency = pd.infer_freq(training_index)
        if frequency is None:
            raise ValueError("ARDL estimation DatetimeIndex must be regular.")
        if not isinstance(future_index, pd.DatetimeIndex):
            raise TypeError("Scenario index type must match the estimation DatetimeIndex.")
        expected = pd.date_range(
            start=training_index[-1], periods=len(future_index) + 1, freq=frequency
        )[1:]
        if not expected.equals(future_index):
            raise ValueError("Scenario dates must continue the estimation sample at its frequency.")
    elif isinstance(training_index, pd.PeriodIndex):
        if training_index.freq is None:
            raise ValueError("ARDL estimation PeriodIndex must have a defined frequency.")
        if not isinstance(future_index, pd.PeriodIndex):
            raise TypeError("Scenario index type must match the estimation PeriodIndex.")
        expected = pd.period_range(
            start=training_index[-1] + 1, periods=len(future_index), freq=training_index.freq
        )
        if not expected.equals(future_index):
            raise ValueError("Scenario periods must continue the estimation sample without gaps.")
    elif pd.api.types.is_numeric_dtype(training_index.dtype):
        if not pd.api.types.is_numeric_dtype(future_index.dtype):
            raise TypeError("Scenario index type must match the numeric estimation index.")
        combined = np.concatenate([
            np.asarray(training_index[-2:], dtype=float),
            np.asarray(future_index, dtype=float),
        ])
        differences = np.diff(combined)
        if len(differences) and not np.allclose(differences, differences[0]):
            raise ValueError("Scenario numeric index must continue the estimation spacing.")
    else:
        raise TypeError("ARDL estimation index must be datetime, period or numeric.")


def forecast_ardl_scenarios(
    fitted_results,
    scenarios: Dict[str, pd.DataFrame],
    baseline_name: str = "Baseline",
    significance_level: float = 0.05,
) -> pd.DataFrame:
    """Propagate named exogenous paths through a fitted ARDL model.

    Parameters
    ----------
    fitted_results:
        Fitted statsmodels ARDL results (or results wrapper).
    scenarios:
        Mapping from scenario names to future exogenous-variable DataFrames.
        Every frame must contain exactly the fitted exogenous columns, in the
        same order, with a common future index and identical horizon.
    baseline_name:
        Name of the scenario used as the reference path.
    significance_level:
        Two-sided interval significance level passed to statsmodels.

    Returns
    -------
    pandas.DataFrame
        Long-form scenario forecasts with pointwise forecast intervals,
        baseline forecasts and point-estimate differences from baseline.

    Notes
    -----
    Scenario paths must already be expressed in the same transformations and
    units as the fitted ARDL regressors. The function does not interpolate,
    transform or calibrate macroeconomic shocks. Prediction intervals are
    conditional on the fitted specification; differences from baseline are
    point-estimate contrasts, not confidence intervals for scenario effects.
    """
    if not isinstance(scenarios, dict) or not scenarios:
        raise ValueError("scenarios must be a non-empty mapping of names to DataFrames.")
    if baseline_name not in scenarios:
        raise ValueError(f"A baseline scenario named {baseline_name!r} is required.")
    if not isinstance(significance_level, (int, float)) or not 0 < significance_level < 1:
        raise ValueError("significance_level must lie strictly between 0 and 1.")
    if not hasattr(fitted_results, "get_prediction") or not hasattr(fitted_results, "model"):
        raise TypeError("fitted_results must be fitted statsmodels ARDL results.")
    model = fitted_results.model
    if getattr(model, "fixed", None) is not None:
        raise NotImplementedError("ARDL models with fixed regressors are not supported.")
    original_endog = model.data.orig_endog
    if not isinstance(original_endog, (pd.Series, pd.DataFrame)):
        raise TypeError("Fit the ARDL model with pandas objects carrying a dated or numeric index.")
    original_exog = model.data.orig_exog
    if not isinstance(original_exog, pd.DataFrame) or original_exog.shape[1] == 0:
        raise ValueError("The fitted ARDL model must contain named exogenous regressors.")
    expected_columns = list(original_exog.columns)
    training_index = original_endog.index
    prepared = {}
    common_index = None
    common_horizon = None

    for name, path in scenarios.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Scenario names must be non-empty strings.")
        if not isinstance(path, pd.DataFrame):
            raise TypeError(f"Scenario {name!r} must be a pandas DataFrame.")
        if list(path.columns) != expected_columns:
            raise ValueError(
                f"Scenario {name!r} columns and order must match fitted exogenous variables: "
                f"{expected_columns}."
            )
        if path.empty or path.isna().any().any():
            raise ValueError(f"Scenario {name!r} must contain complete future paths.")
        values = path.to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"Scenario {name!r} must contain only finite numeric values.")
        _validate_future_index(training_index, path.index)
        if common_index is None:
            common_index = path.index
            common_horizon = len(path)
        elif not path.index.equals(common_index) or len(path) != common_horizon:
            raise ValueError("All scenarios must share the same future index and horizon.")
        prepared[name] = path.astype(float)

    nobs = len(model.data.orig_endog)
    baseline_frame = fitted_results.get_prediction(
        start=nobs,
        end=nobs + common_horizon - 1,
        dynamic=True,
        exog_oos=prepared[baseline_name],
    ).summary_frame(alpha=float(significance_level))
    baseline_mean = baseline_frame["mean"].to_numpy(dtype=float)
    dependent_name = str(model.endog_names)
    records = []

    for name, path in prepared.items():
        prediction = fitted_results.get_prediction(
            start=nobs,
            end=nobs + common_horizon - 1,
            dynamic=True,
            exog_oos=path,
        ).summary_frame(alpha=float(significance_level))
        for position, period in enumerate(common_index):
            records.append({
                "scenario": name,
                "period": str(period),
                "dependent_variable": dependent_name,
                "forecast": float(prediction["mean"].iloc[position]),
                "interval_lower": float(prediction["mean_ci_lower"].iloc[position]),
                "interval_upper": float(prediction["mean_ci_upper"].iloc[position]),
                "baseline_forecast": float(baseline_mean[position]),
                "change_vs_baseline": float(
                    prediction["mean"].iloc[position] - baseline_mean[position]
                ),
                "significance_level": float(significance_level),
                "interval_type": "pointwise conditional forecast interval",
            })

    result = pd.DataFrame(records)
    numeric_columns = [
        "forecast", "interval_lower", "interval_upper",
        "baseline_forecast", "change_vs_baseline",
    ]
    if not np.isfinite(result[numeric_columns].to_numpy(dtype=float)).all():
        raise RuntimeError("ARDL scenario forecasts contain non-finite values.")
    if (result["interval_lower"] > result["interval_upper"]).any():
        raise RuntimeError("ARDL scenario forecast interval bounds are reversed.")
    return result
