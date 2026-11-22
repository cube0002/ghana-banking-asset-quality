"""Sensitivity analysis for calibrated ARDL macroeconomic scenarios."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

from .ardl_scenarios import forecast_ardl_scenarios
from .scenario_calibration import calibrate_historical_scenario_paths


@dataclass(frozen=True)
class ARDLScenarioSensitivityResult:
    """Summary and detailed forecasts across scenario calibration assumptions."""

    summary: List[dict]
    forecasts: List[dict]
    quantile_pairs: List[dict]
    persistence_values: List[float]
    horizon: int
    significance_level: float

    def to_dict(self) -> dict:
        return asdict(self)


def run_ardl_scenario_sensitivity(
    fitted_results,
    historical_exog: pd.DataFrame,
    horizon: int,
    adverse_directions: Mapping[str, int],
    integrated_variables: Sequence[str] = (),
    quantile_pairs: Sequence[Tuple[float, float]] = ((0.90, 0.975), (0.95, 0.99)),
    persistence_values: Sequence[float] = (0.30, 0.70, 0.90),
    significance_level: float = 0.05,
) -> ARDLScenarioSensitivityResult:
    """Vary shock quantiles and persistence, then reforecast each scenario.

    The fitted ARDL specification and historical calibration sample remain
    fixed. Only the historical innovation quantiles and the analyst-assumed
    geometric shock persistence vary. This isolates scenario-assumption
    sensitivity; it does not capture model-selection or parameter uncertainty.
    """
    if not isinstance(quantile_pairs, (list, tuple)) or not quantile_pairs:
        raise ValueError("quantile_pairs must be a non-empty sequence of quantile pairs.")
    if not isinstance(persistence_values, (list, tuple)) or not persistence_values:
        raise ValueError("persistence_values must be a non-empty sequence.")
    if not isinstance(significance_level, (int, float)) or not 0 < significance_level < 1:
        raise ValueError("significance_level must lie strictly between 0 and 1.")
    normalized_pairs = []
    for pair in quantile_pairs:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("Each quantile pair must contain adverse and severe quantiles.")
        adverse_q, severe_q = float(pair[0]), float(pair[1])
        if not 0 < adverse_q < severe_q < 1:
            raise ValueError("Each pair must satisfy 0 < adverse < severe < 1.")
        normalized_pairs.append((adverse_q, severe_q))
    normalized_persistence = [float(value) for value in persistence_values]
    if any(not 0 <= value <= 1 for value in normalized_persistence):
        raise ValueError("Every persistence value must lie between 0 and 1.")
    if len(set(normalized_pairs)) != len(normalized_pairs):
        raise ValueError("quantile_pairs must not contain duplicates.")
    if len(set(normalized_persistence)) != len(normalized_persistence):
        raise ValueError("persistence_values must not contain duplicates.")

    summary_records = []
    forecast_records = []
    for adverse_q, severe_q in normalized_pairs:
        for persistence in normalized_persistence:
            paths = calibrate_historical_scenario_paths(
                historical_exog=historical_exog,
                horizon=horizon,
                adverse_directions=adverse_directions,
                integrated_variables=integrated_variables,
                adverse_quantile=adverse_q,
                severe_quantile=severe_q,
                persistence=persistence,
            )
            forecasts = forecast_ardl_scenarios(
                fitted_results=fitted_results,
                scenarios=paths,
                baseline_name="Baseline",
                significance_level=float(significance_level),
            )
            forecasts["adverse_quantile"] = adverse_q
            forecasts["severe_quantile"] = severe_q
            forecasts["shock_persistence"] = persistence
            forecast_records.extend(forecasts.to_dict(orient="records"))

            for scenario_name in ("Adverse", "Severe"):
                group = forecasts.loc[forecasts["scenario"] == scenario_name].copy()
                group = group.sort_values("period")
                peak_index = group["forecast"].idxmax()
                baseline_values = group["baseline_forecast"].to_numpy(dtype=float)
                changes = group["change_vs_baseline"].to_numpy(dtype=float)
                summary_records.append({
                    "scenario": scenario_name,
                    "adverse_quantile": adverse_q,
                    "severe_quantile": severe_q,
                    "shock_persistence": persistence,
                    "horizon": int(horizon),
                    "terminal_forecast": float(group["forecast"].iloc[-1]),
                    "terminal_baseline": float(group["baseline_forecast"].iloc[-1]),
                    "terminal_change_vs_baseline": float(changes[-1]),
                    "maximum_forecast": float(group["forecast"].max()),
                    "maximum_change_vs_baseline": float(np.max(changes)),
                    "minimum_change_vs_baseline": float(np.min(changes)),
                    "peak_period": str(group.loc[peak_index, "period"]),
                    "minimum_interval_lower": float(group["interval_lower"].min()),
                    "maximum_interval_upper": float(group["interval_upper"].max()),
                    "n_periods": int(len(group)),
                })

    if not summary_records or not forecast_records:
        raise RuntimeError("Scenario sensitivity produced no forecast records.")
    numeric_summary = pd.DataFrame(summary_records).select_dtypes(include=[np.number])
    if not np.isfinite(numeric_summary.to_numpy(dtype=float)).all():
        raise RuntimeError("Scenario sensitivity summary contains non-finite values.")
    return ARDLScenarioSensitivityResult(
        summary=summary_records,
        forecasts=forecast_records,
        quantile_pairs=[
            {"adverse_quantile": adverse_q, "severe_quantile": severe_q}
            for adverse_q, severe_q in normalized_pairs
        ],
        persistence_values=normalized_persistence,
        horizon=int(horizon),
        significance_level=float(significance_level),
    )
