"""Sensitivity of conditional ARDL scenario forecasts to candidate specifications.

Candidates must be supplied explicitly by the analyst. Results compare
specification-conditional forecasts; they are not model probabilities or
model-averaged predictive distributions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping

import numpy as np
import pandas as pd

from .ardl_scenarios import forecast_ardl_scenarios


@dataclass
class ARDLModelSelectionSensitivityResult:
    """Auditable forecasts and summaries across prespecified ARDL candidates."""

    forecasts: pd.DataFrame
    summary: pd.DataFrame
    specifications: pd.DataFrame
    baseline_name: str
    significance_level: float

    def to_dict(self) -> dict:
        return {
            "forecasts": self.forecasts.to_dict(orient="records"),
            "summary": self.summary.to_dict(orient="records"),
            "specifications": self.specifications.to_dict(orient="records"),
            "baseline_name": self.baseline_name,
            "significance_level": self.significance_level,
            "interpretation": (
                "Specification sensitivity only; no model-selection probabilities "
                "or model-averaged forecasts are produced."
            ),
        }


def _criterion_value(results, name: str):
    value = getattr(results, name, np.nan)
    try:
        value = float(value)
    except (TypeError, ValueError):
        return np.nan
    return value if np.isfinite(value) else np.nan


def run_ardl_model_selection_sensitivity(
    candidate_models: Mapping[str, object],
    scenarios_by_model: Mapping[str, Dict[str, pd.DataFrame]],
    baseline_name: str = "Baseline",
    significance_level: float = 0.05,
) -> ARDLModelSelectionSensitivityResult:
    """Compare scenario forecasts from an explicit set of fitted ARDL models.

    Each candidate may have a different lag structure and regressor set, so
    its scenario paths are supplied separately. All candidates must forecast
    the same dependent variable, scenario names and future periods. The
    analyst is responsible for prespecifying candidates on a common estimation
    sample and documenting why each specification is defensible.
    """
    if not isinstance(candidate_models, Mapping) or not candidate_models:
        raise ValueError("candidate_models must be a non-empty mapping.")
    if not isinstance(scenarios_by_model, Mapping):
        raise TypeError("scenarios_by_model must be a mapping.")
    candidate_names = list(candidate_models)
    if any(not isinstance(name, str) or not name.strip() for name in candidate_names):
        raise ValueError("Candidate model names must be non-empty strings.")
    if len(set(candidate_names)) != len(candidate_names):
        raise ValueError("Candidate model names must be unique.")
    if set(scenarios_by_model) != set(candidate_names):
        raise ValueError("scenarios_by_model must contain exactly one scenario mapping per candidate.")
    if not isinstance(significance_level, (int, float)) or not 0 < significance_level < 1:
        raise ValueError("significance_level must lie strictly between 0 and 1.")

    forecast_frames = []
    specification_records = []
    reference_scenarios = None
    reference_periods = None
    reference_dependent = None

    for candidate_name in candidate_names:
        fitted = candidate_models[candidate_name]
        model = getattr(fitted, "model", None)
        if model is None:
            raise TypeError(f"Candidate {candidate_name!r} is not fitted statsmodels ARDL results.")
        dependent = str(model.endog_names)
        scenarios = scenarios_by_model[candidate_name]
        if not isinstance(scenarios, Mapping):
            raise TypeError(f"Scenarios for candidate {candidate_name!r} must be a mapping.")
        if baseline_name not in scenarios:
            raise ValueError(f"Candidate {candidate_name!r} is missing baseline {baseline_name!r}.")

        forecasts = forecast_ardl_scenarios(
            fitted_results=fitted,
            scenarios=dict(scenarios),
            baseline_name=baseline_name,
            significance_level=significance_level,
        )
        scenario_names = list(scenarios)
        periods = list(forecasts.loc[forecasts["scenario"] == baseline_name, "period"])
        if reference_scenarios is None:
            reference_scenarios = scenario_names
            reference_periods = periods
            reference_dependent = dependent
        else:
            if set(scenario_names) != set(reference_scenarios):
                raise ValueError("All candidate models must use the same scenario names.")
            if periods != reference_periods:
                raise ValueError("All candidate models must forecast the same future periods.")
            if dependent != reference_dependent:
                raise ValueError("All candidate models must use the same dependent variable.")

        forecasts.insert(0, "candidate_model", candidate_name)
        forecast_frames.append(forecasts)

        ar_lags = getattr(model, "ardl_order", None)
        dl_lags = getattr(model, "dl_lags", None)
        specification_records.append({
            "candidate_model": candidate_name,
            "dependent_variable": dependent,
            "ar_lags": repr(ar_lags),
            "distributed_lags": repr(dl_lags),
            "nobs": int(getattr(fitted, "nobs", len(model.data.orig_endog))),
            "aic": _criterion_value(fitted, "aic"),
            "bic": _criterion_value(fitted, "bic"),
        })

    all_forecasts = pd.concat(forecast_frames, ignore_index=True)
    summary_records = []
    for (candidate_name, scenario_name), group in all_forecasts.groupby(
        ["candidate_model", "scenario"], sort=False
    ):
        group = group.reset_index(drop=True)
        peak_position = int(group["forecast"].to_numpy().argmax())
        trough_position = int(group["forecast"].to_numpy().argmin())
        summary_records.append({
            "candidate_model": candidate_name,
            "scenario": scenario_name,
            "dependent_variable": reference_dependent,
            "horizon": len(group),
            "terminal_forecast": float(group["forecast"].iloc[-1]),
            "terminal_change_vs_baseline": float(group["change_vs_baseline"].iloc[-1]),
            "peak_forecast": float(group["forecast"].iloc[peak_position]),
            "peak_period": group["period"].iloc[peak_position],
            "trough_forecast": float(group["forecast"].iloc[trough_position]),
            "trough_period": group["period"].iloc[trough_position],
            "significance_level": float(significance_level),
        })

    return ARDLModelSelectionSensitivityResult(
        forecasts=all_forecasts,
        summary=pd.DataFrame(summary_records),
        specifications=pd.DataFrame(specification_records),
        baseline_name=baseline_name,
        significance_level=float(significance_level),
    )
