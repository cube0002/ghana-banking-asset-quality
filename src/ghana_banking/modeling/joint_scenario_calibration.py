"""Joint historical macro scenarios from aligned contiguous residual blocks."""
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
        if index.freq is None or not pd.period_range(index[0], index[-1], freq=index.freq).equals(index):
            raise ValueError("Historical PeriodIndex must be regular.")
        return pd.period_range(index[-1] + 1, periods=horizon, freq=index.freq)
    if pd.api.types.is_numeric_dtype(index.dtype):
        if len(index) < 2:
            raise ValueError("Numeric historical index requires at least two observations.")
        delta = np.diff(np.asarray(index, dtype=float))
        if delta[-1] <= 0 or not np.allclose(delta, delta[-1]):
            raise ValueError("Numeric historical index must be equally spaced.")
        return pd.Index([float(index[-1]) + delta[-1] * i for i in range(1, horizon + 1)], name=index.name)
    raise TypeError("Index must be a regular DatetimeIndex, PeriodIndex or numeric index.")


def calibrate_joint_historical_scenario_paths(
    historical_exog: pd.DataFrame,
    horizon: int,
    adverse_directions: Mapping[str, int],
    integrated_variables: Sequence[str] = (),
    adverse_quantile: float = 0.90,
    severe_quantile: float = 0.975,
    min_observations: int = 40,
) -> Dict[str, pd.DataFrame]:
    """Build paths from aligned AR(1) innovation blocks selected by joint severity.

    AR(1) models are estimated per variable, in levels or first differences
    for variables listed in integrated_variables. Contiguous aligned residual
    vectors are scored by the equal-weight mean of direction-adjusted,
    standardised innovations. Empirical score quantiles select adverse and
    severe historical blocks. This preserves contemporaneous dependence and
    ordering within each selected block, but does not imply joint probabilities,
    causal shocks, or official supervisory scenarios.
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
    columns = list(historical_exog.columns)
    if set(adverse_directions) != set(columns):
        raise ValueError("adverse_directions must specify every historical variable exactly.")
    if any(direction not in (-1, 1) for direction in adverse_directions.values()):
        raise ValueError("Every adverse direction must be either +1 or -1.")
    integrated = set(integrated_variables)
    if not integrated.issubset(columns):
        raise ValueError("integrated_variables contains unknown variable names.")
    if not all(pd.api.types.is_numeric_dtype(historical_exog[c]) for c in columns):
        raise TypeError("All historical exogenous variables must be numeric.")
    if not np.isfinite(historical_exog.to_numpy(dtype=float)).all():
        raise ValueError("Historical exogenous variables must be complete and finite.")
    if len(historical_exog) < min_observations:
        raise ValueError(f"At least {min_observations} historical observations are required.")

    future_index = _future_index(historical_exog.index, horizon)
    forecasts, residual_columns, metadata = {}, {}, []
    for variable in columns:
        raw = historical_exog[variable].astype(float)
        is_integrated = variable in integrated
        process = raw.diff().dropna() if is_integrated else raw
        fitted = AutoReg(process, lags=1, trend="c", old_names=False).fit()
        phi = float(np.asarray(fitted.params)[-1])
        if not np.isfinite(phi) or abs(phi) >= 1:
            raise ValueError(f"AR(1) persistence for {variable!r} is not stationary.")
        predicted = np.asarray(
            fitted.predict(start=len(process), end=len(process) + horizon - 1, dynamic=True),
            dtype=float,
        )
        residual = pd.Series(np.asarray(fitted.resid, dtype=float), index=process.index[1:])
        scale = float(residual.std(ddof=1))
        if not np.isfinite(scale) or scale <= 0:
            raise ValueError(f"Residual scale for {variable!r} must be positive.")
        forecasts[variable] = (predicted, float(raw.iloc[-1]), is_integrated)
        residual_columns[variable] = residual / scale * int(adverse_directions[variable])
        metadata.append({
            "variable": variable,
            "process_modelled": "first_difference" if is_integrated else "level",
            "adverse_direction": int(adverse_directions[variable]),
            "ar1_coefficient": phi,
            "innovation_scale": scale,
            "innovation_observations": int(len(residual)),
        })

    aligned = pd.DataFrame(residual_columns).dropna()
    residual_values = aligned.to_numpy(dtype=float)
    n_blocks = len(residual_values) - horizon + 1
    if n_blocks < 2:
        raise ValueError("Not enough candidate historical residual blocks for this horizon.")
    scores = np.array([
        residual_values[start:start + horizon].mean() for start in range(n_blocks)
    ])
    ordered = np.argsort(scores, kind="stable")
    adverse_rank = min(int(np.ceil(adverse_quantile * (n_blocks - 1))), n_blocks - 1)
    severe_rank = min(int(np.ceil(severe_quantile * (n_blocks - 1))), n_blocks - 1)
    starts = {"Adverse": int(ordered[adverse_rank]), "Severe": int(ordered[severe_rank])}

    baseline = pd.DataFrame(index=future_index, columns=columns, dtype=float)
    for variable in columns:
        predicted, last_level, is_integrated = forecasts[variable]
        baseline[variable] = last_level + np.cumsum(predicted) if is_integrated else predicted

    paths = {"Baseline": baseline}
    for name, start in starts.items():
        selected = residual_values[start:start + horizon]
        frame = pd.DataFrame(index=future_index, columns=columns, dtype=float)
        for j, variable in enumerate(columns):
            predicted, last_level, is_integrated = forecasts[variable]
            scale = metadata[j]["innovation_scale"]
            direction = metadata[j]["adverse_direction"]
            original_shock = selected[:, j] * scale * direction
            process_path = predicted + original_shock
            frame[variable] = last_level + np.cumsum(process_path) if is_integrated else process_path
        paths[name] = frame

    if not all(np.isfinite(frame.to_numpy(dtype=float)).all() for frame in paths.values()):
        raise RuntimeError("Joint scenario paths contain non-finite values.")
    common = {
        "method": "aligned_contiguous_AR1_innovation_blocks",
        "score": "equal-weight mean of direction-adjusted standardised innovations",
        "candidate_blocks": int(n_blocks),
        "horizon": int(horizon),
        "adverse_quantile": float(adverse_quantile),
        "severe_quantile": float(severe_quantile),
        "adverse_block_start": starts["Adverse"],
        "severe_block_start": starts["Severe"],
        "adverse_block_score": float(scores[starts["Adverse"]]),
        "severe_block_score": float(scores[starts["Severe"]]),
        "adverse_block_start_period": str(aligned.index[starts["Adverse"]]),
        "adverse_block_end_period": str(aligned.index[starts["Adverse"] + horizon - 1]),
        "severe_block_start_period": str(aligned.index[starts["Severe"]]),
        "severe_block_end_period": str(aligned.index[starts["Severe"] + horizon - 1]),
        "variables": metadata,
        "cross_variable_dependence": "preserved within selected historical residual blocks",
        "temporal_dependence": "historical ordering preserved within selected contiguous block",
    }
    for name, frame in paths.items():
        frame.attrs["calibration"] = common
        frame.attrs["scenario_type"] = f"joint historical residual-block {name.lower()} path"
    return paths
