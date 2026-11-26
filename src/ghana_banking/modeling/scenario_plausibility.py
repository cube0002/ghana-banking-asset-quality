"""Historical-support audit for conditional macroeconomic scenario paths.

This is a descriptive plausibility screen, not a probability forecast or an
economic validation of a scenario narrative.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ScenarioPlausibilityResult:
    """Historical-support diagnostics for every scenario-variable pair."""

    diagnostics: pd.DataFrame
    baseline_name: str
    integrated_variables: list[str]
    quantile_levels: list[float]

    def to_dict(self) -> dict:
        return {
            "diagnostics": self.diagnostics.to_dict(orient="records"),
            "baseline_name": self.baseline_name,
            "integrated_variables": list(self.integrated_variables),
            "quantile_levels": list(self.quantile_levels),
            "interpretation": (
                "Descriptive comparison with historical marginal support; "
                "not a probability, causal assessment or supervisory scenario validation."
            ),
        }


def audit_scenario_historical_support(
    historical_data: pd.DataFrame,
    scenarios: Mapping[str, pd.DataFrame],
    baseline_name: str = "Baseline",
    integrated_variables: Sequence[str] = (),
    quantile_levels: Sequence[float] = (0.01, 0.05, 0.50, 0.95, 0.99),
) -> ScenarioPlausibilityResult:
    """Compare scenario paths with historical levels or historical changes.

    Variables listed in integrated_variables are compared in first differences.
    The first scenario change is measured from the final historical observation.
    Other variables are compared in levels. All scenario frames must contain
    exactly the historical columns in the same order and share one future index.
    """
    if not isinstance(historical_data, pd.DataFrame):
        raise TypeError("historical_data must be a pandas DataFrame.")
    if historical_data.empty or historical_data.shape[1] < 1:
        raise ValueError("historical_data must contain observations and variables.")
    if not historical_data.columns.is_unique:
        raise ValueError("Historical variable names must be unique.")
    if historical_data.index.has_duplicates or not historical_data.index.is_monotonic_increasing:
        raise ValueError("Historical index must be unique and sorted.")
    if historical_data.isna().any().any():
        raise ValueError("historical_data must be complete; handle missingness explicitly.")
    if not all(pd.api.types.is_numeric_dtype(historical_data[c]) for c in historical_data):
        raise TypeError("All historical variables must be numeric.")
    historical_values = historical_data.to_numpy(dtype=float)
    if not np.isfinite(historical_values).all():
        raise ValueError("historical_data must contain only finite values.")
    if len(historical_data) < 20:
        raise ValueError("At least 20 historical observations are required.")

    if not isinstance(scenarios, Mapping) or not scenarios:
        raise ValueError("scenarios must be a non-empty mapping.")
    if baseline_name not in scenarios:
        raise ValueError(f"A baseline scenario named {baseline_name!r} is required.")
    if any(not isinstance(name, str) or not name.strip() for name in scenarios):
        raise ValueError("Scenario names must be non-empty strings.")
    if not isinstance(integrated_variables, (list, tuple, set)):
        raise TypeError("integrated_variables must be a sequence of variable names.")
    integrated = list(integrated_variables)
    if len(set(integrated)) != len(integrated) or not set(integrated).issubset(historical_data.columns):
        raise ValueError("integrated_variables must be unique names present in historical_data.")

    levels = list(quantile_levels)
    if len(levels) < 2 or any(
        not isinstance(q, (int, float)) or not 0 < q < 1 for q in levels
    ):
        raise ValueError("quantile_levels must contain at least two probabilities strictly between 0 and 1.")
    if levels != sorted(set(levels)):
        raise ValueError("quantile_levels must be unique and strictly increasing.")

    expected_columns = list(historical_data.columns)
    future_index = None
    prepared = {}
    for name, path in scenarios.items():
        if not isinstance(path, pd.DataFrame):
            raise TypeError(f"Scenario {name!r} must be a pandas DataFrame.")
        if list(path.columns) != expected_columns:
            raise ValueError(f"Scenario {name!r} columns and order must match historical_data.")
        if path.empty or path.isna().any().any():
            raise ValueError(f"Scenario {name!r} must contain complete future paths.")
        if path.index.has_duplicates or not path.index.is_monotonic_increasing:
            raise ValueError(f"Scenario {name!r} index must be unique and sorted.")
        values = path.to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"Scenario {name!r} must contain only finite numeric values.")
        if future_index is None:
            future_index = path.index
        elif not path.index.equals(future_index):
            raise ValueError("All scenarios must share the same future index and horizon.")
        if path.index[0] <= historical_data.index[-1]:
            raise ValueError("Scenario paths must start strictly after the historical sample.")
        prepared[name] = path.astype(float)

    baseline = prepared[baseline_name]
    records = []
    for variable in expected_columns:
        if variable in integrated:
            historical_scale = historical_data[variable].diff().dropna().to_numpy(dtype=float)
            scenario_scale = {
                name: np.diff(np.concatenate([
                    [historical_data[variable].iloc[-1]],
                    path[variable].to_numpy(dtype=float),
                ]))
                for name, path in prepared.items()
            }
            scale_label = "first_difference"
        else:
            historical_scale = historical_data[variable].to_numpy(dtype=float)
            scenario_scale = {
                name: path[variable].to_numpy(dtype=float)
                for name, path in prepared.items()
            }
            scale_label = "level"

        if len(historical_scale) < 10:
            raise ValueError(f"Insufficient historical observations for {variable!r} on the audit scale.")
        quantiles = np.quantile(historical_scale, levels)
        historical_min = float(np.min(historical_scale))
        historical_max = float(np.max(historical_scale))
        q_map = {q: float(value) for q, value in zip(levels, quantiles)}
        baseline_scale = scenario_scale[baseline_name]

        for scenario_name, values in scenario_scale.items():
            values = np.asarray(values, dtype=float)
            ranks = np.searchsorted(np.sort(historical_scale), values, side="right") / len(historical_scale)
            difference = values - baseline_scale
            row = {
                "scenario": scenario_name,
                "variable": variable,
                "comparison_scale": scale_label,
                "historical_observations": int(len(historical_scale)),
                "scenario_horizon": int(len(values)),
                "historical_min": historical_min,
                "historical_max": historical_max,
                "scenario_min": float(np.min(values)),
                "scenario_max": float(np.max(values)),
                "share_outside_historical_range": float(np.mean(
                    (values < historical_min) | (values > historical_max)
                )),
                "mean_historical_percentile_rank": float(np.mean(ranks)),
                "terminal_difference_vs_baseline": float(difference[-1]),
                "mean_difference_vs_baseline": float(np.mean(difference)),
            }
            for q, value in q_map.items():
                row[f"historical_q{q:g}"] = value
            if 0.01 in q_map:
                row["share_below_historical_1pct"] = float(np.mean(values < q_map[0.01]))
            if 0.99 in q_map:
                row["share_above_historical_99pct"] = float(np.mean(values > q_map[0.99]))
            records.append(row)

    return ScenarioPlausibilityResult(
        diagnostics=pd.DataFrame(records),
        baseline_name=baseline_name,
        integrated_variables=integrated,
        quantile_levels=levels,
    )
