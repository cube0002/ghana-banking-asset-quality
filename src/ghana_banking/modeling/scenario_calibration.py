"""Historical calibration of conditional macroeconomic scenario paths.

This module creates transparent illustrative paths from historical AR(1)
innovation distributions. It is not a supervisory scenario generator and
does not claim that marginal shocks occur jointly with the calibrated
probabilities.
"""
from __future__ import annotations

from typing import Dict, Mapping, Sequence

import numpy as np
import pandas as pd
from statsmodels.tsa.ar_model import AutoReg


def _future_index(index: pd.Index, horizon: int) -> pd.Index:
    if isinstance(index, pd.DatetimeIndex):
        frequency = pd.infer_freq(index)
        if frequency is None:
            raise ValueError("Historical DatetimeIndex must be regular.")
        return pd.date_range(index[-1], periods=horizon + 1, freq=frequency)[1:]
    if isinstance(index, pd.PeriodIndex):
        if index.freq is None:
            raise ValueError("Historical PeriodIndex must have a defined frequency.")
        expected = pd.period_range(index[0], index[-1], freq=index.freq)
        if not expected.equals(index):
            raise ValueError("Historical PeriodIndex must be regular with no missing periods.")
        return pd.period_range(index[-1] + 1, periods=horizon, freq=index.freq)
    if pd.api.types.is_numeric_dtype(index.dtype):
        if len(index) < 2:
            raise ValueError("Numeric historical index requires at least two observations.")
        differences = np.diff(np.asarray(index, dtype=float))
        spacing = float(differences[-1])
        if spacing <= 0 or not np.allclose(differences, spacing):
            raise ValueError("Numeric historical index must be strictly increasing and equally spaced.")
        return pd.Index(
            [float(index[-1]) + spacing * step for step in range(1, horizon + 1)],
            name=index.name,
        )
    raise TypeError("Index must be a regular DatetimeIndex, PeriodIndex or numeric index.")


def calibrate_historical_scenario_paths(
    historical_exog: pd.DataFrame,
    horizon: int,
    adverse_directions: Mapping[str, int],
    integrated_variables: Sequence[str] = (),
    adverse_quantile: float = 0.90,
    severe_quantile: float = 0.975,
    persistence: float = 0.70,
    min_observations: int = 40,
) -> Dict[str, pd.DataFrame]:
    """Generate baseline, adverse and severe paths using historical AR(1) shocks.

    Parameters
    ----------
    historical_exog:
        Complete historical exogenous-variable sample in exactly the units and
        transformations used by the downstream ARDL model.
    horizon:
        Number of future periods to generate.
    adverse_directions:
        Mapping of every variable to +1 or -1. +1 means an increase is adverse;
        -1 means a decrease is adverse. This direction is an explicit economic
        assumption, not inferred from correlations.
    integrated_variables:
        Variables treated as I(1) in levels. Their first differences are
        modelled with AR(1), and forecast changes are accumulated back to levels.
        All other variables are modelled in levels.
    adverse_quantile, severe_quantile:
        Upper-tail quantiles of historically estimated, direction-adjusted AR(1)
        innovations. The severe quantile must exceed the adverse quantile.
    persistence:
        Geometric persistence applied to the initial shock across future periods.
        This is an analyst assumption, not estimated persistence.
    min_observations:
        Minimum complete historical observations required per variable.

    Returns
    -------
    dict[str, pandas.DataFrame]
        DataFrames named Baseline, Adverse and Severe. Their columns preserve the
        input order and can be passed directly to forecast_ardl_scenarios().

    Notes
    -----
    Each variable's AR(1) innovation distribution is calibrated marginally.
    The generated adverse/severe paths therefore do not preserve the empirical
    cross-variable dependence of macroeconomic shocks. They are transparent
    sensitivity scenarios, not joint probability statements, official scenarios,
    causal shocks or supervisory stress tests.
    """
    if not isinstance(historical_exog, pd.DataFrame):
        raise TypeError("historical_exog must be a pandas DataFrame.")
    if historical_exog.empty or historical_exog.shape[1] < 1:
        raise ValueError("historical_exog must contain variables and observations.")
    if not historical_exog.columns.is_unique:
        raise ValueError("Historical variable names must be unique.")
    if historical_exog.index.has_duplicates or not historical_exog.index.is_monotonic_increasing:
        raise ValueError("Historical index must be unique and sorted.")
    if not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be a positive integer.")
    if not isinstance(min_observations, int) or min_observations < 20:
        raise ValueError("min_observations must be an integer of at least 20.")
    if not 0 < adverse_quantile < severe_quantile < 1:
        raise ValueError("Require 0 < adverse_quantile < severe_quantile < 1.")
    if not isinstance(persistence, (int, float)) or not 0 <= persistence <= 1:
        raise ValueError("persistence must lie between 0 and 1.")
    columns = list(historical_exog.columns)
    if set(adverse_directions) != set(columns):
        raise ValueError("adverse_directions must specify every historical variable exactly.")
    if any(direction not in (-1, 1) for direction in adverse_directions.values()):
        raise ValueError("Every adverse direction must be either +1 or -1.")
    integrated = set(integrated_variables)
    if not integrated.issubset(set(columns)):
        raise ValueError("integrated_variables contains unknown variable names.")
    if not all(pd.api.types.is_numeric_dtype(historical_exog[c]) for c in columns):
        raise TypeError("All historical exogenous variables must be numeric.")
    values = historical_exog.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Historical exogenous variables must be complete and finite.")
    if len(historical_exog) < min_observations:
        raise ValueError(
            f"At least {min_observations} historical observations are required."
        )

    future = _future_index(historical_exog.index, horizon)
    baseline = pd.DataFrame(index=future, columns=columns, dtype=float)
    adverse = pd.DataFrame(index=future, columns=columns, dtype=float)
    severe = pd.DataFrame(index=future, columns=columns, dtype=float)
    calibration_records = []

    for variable in columns:
        raw = historical_exog[variable].astype(float)
        is_integrated = variable in integrated
        model_series = raw.diff().dropna() if is_integrated else raw
        if len(model_series) < min_observations - int(is_integrated):
            raise ValueError(f"Insufficient transformed history for {variable!r}.")
        fitted = AutoReg(model_series, lags=1, trend="c", old_names=False).fit()
        phi = float(np.asarray(fitted.params)[-1])
        if not np.isfinite(phi) or abs(phi) >= 1:
            raise ValueError(
                f"AR(1) persistence for {variable!r} is not stationary; "
                "review the integration classification or use a different process."
            )
        innovations = np.asarray(fitted.resid, dtype=float)
        direction = int(adverse_directions[variable])
        directional_innovations = direction * innovations
        adverse_shock = float(np.quantile(directional_innovations, adverse_quantile))
        severe_shock = float(np.quantile(directional_innovations, severe_quantile))
        if adverse_shock <= 0 or severe_shock <= 0:
            raise ValueError(
                f"Historical directional innovation quantiles for {variable!r} "
                "are not positive; review the adverse direction and calibration sample."
            )

        baseline_process = np.asarray(
            fitted.predict(start=len(model_series), end=len(model_series) + horizon - 1, dynamic=True),
            dtype=float,
        )
        shock_decay = persistence ** np.arange(horizon, dtype=float)
        adverse_process = baseline_process + direction * adverse_shock * shock_decay
        severe_process = baseline_process + direction * severe_shock * shock_decay

        if is_integrated:
            last_level = float(raw.iloc[-1])
            baseline[variable] = last_level + np.cumsum(baseline_process)
            adverse[variable] = last_level + np.cumsum(adverse_process)
            severe[variable] = last_level + np.cumsum(severe_process)
        else:
            baseline[variable] = baseline_process
            adverse[variable] = adverse_process
            severe[variable] = severe_process

        calibration_records.append({
            "variable": variable,
            "process_modelled": "first_difference" if is_integrated else "level",
            "adverse_direction": direction,
            "ar1_coefficient": phi,
            "innovation_observations": int(len(innovations)),
            "adverse_quantile": float(adverse_quantile),
            "adverse_shock_magnitude": adverse_shock,
            "severe_quantile": float(severe_quantile),
            "severe_shock_magnitude": severe_shock,
            "shock_persistence_assumption": float(persistence),
        })

    for frame in (baseline, adverse, severe):
        if not np.isfinite(frame.to_numpy(dtype=float)).all():
            raise RuntimeError("Calibrated scenario paths contain non-finite values.")

    baseline.attrs["calibration"] = calibration_records
    adverse.attrs["calibration"] = calibration_records
    severe.attrs["calibration"] = calibration_records
    baseline.attrs["scenario_type"] = "historical AR(1) baseline"
    adverse.attrs["scenario_type"] = "historical marginal adverse-quantile shocks"
    severe.attrs["scenario_type"] = "historical marginal severe-quantile shocks"
    baseline.attrs["cross_variable_dependence"] = "not preserved"
    adverse.attrs["cross_variable_dependence"] = "not preserved"
    severe.attrs["cross_variable_dependence"] = "not preserved"

    return {"Baseline": baseline, "Adverse": adverse, "Severe": severe}
