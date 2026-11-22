"""Guarded ARDL/UECM estimation and bounds testing."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from statsmodels.tsa.ardl import UECM, ardl_select_order

from .eligibility import assess_model_eligibility


@dataclass(frozen=True)
class ARDLBoundsResult:
    """Auditable ARDL selection, UECM bounds test and conditional long-run effects."""

    dependent_variable: str
    regressors: List[str]
    input_observations: int
    estimation_observations: int
    sample_start: str
    sample_end: str
    estimation_sample_start: str
    estimation_sample_end: str
    integration_assessments: Dict[str, str]
    selected_ar_lag: int
    selected_distributed_lags: Dict[str, List[int]]
    selection_ic: str
    selected_ic_value: float
    deterministic_trend: str
    bounds_case: int
    bounds_statistic: float
    bounds_lower_pvalue: float
    bounds_upper_pvalue: float
    bounds_decision: str
    bounds_critical_values: List[dict]
    alpha: float
    ardl_parameters: List[dict]
    uecm_parameters: List[dict]
    long_run_multipliers: Optional[Dict[str, float]]
    asymptotic_bounds: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _parameter_records(result) -> List[dict]:
    return [
        {
            "term": str(name),
            "coefficient": float(result.params[name]),
            "standard_error": float(result.bse[name]),
            "p_value": float(result.pvalues[name]),
        }
        for name in result.params.index
    ]


def fit_ardl_bounds_model(
    data: pd.DataFrame,
    dependent_variable: str,
    regressors: List[str],
    integration_assessments: Dict[str, str],
    max_ar_lag: int = 6,
    max_distributed_lag: int = 6,
    selection_ic: str = "bic",
    trend: str = "c",
    bounds_case: int = 3,
    alpha: float = 0.05,
    asymptotic_bounds: bool = True,
    nsim: int = 10000,
    seed: int = 12345,
) -> ARDLBoundsResult:
    """Select an ARDL, convert to UECM and perform Pesaran-Shin-Smith bounds test.

    The input must pass the project's I(0)/I(1) screening gate. This routine
    rejects all-I(0), uncertain and possible-I(2) systems. The caller must
    choose the deterministic bounds case consistently with the economic
    specification. Long-run multipliers are returned only when the upper
    bounds p-value is below alpha. This is not causal identification.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame.")
    if not regressors or len(set(regressors)) != len(regressors):
        raise ValueError("regressors must be a non-empty list of unique columns.")
    if dependent_variable in regressors:
        raise ValueError("The dependent variable cannot also be a regressor.")
    columns = [dependent_variable] + list(regressors)
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    if not data.index.is_unique or not data.index.is_monotonic_increasing:
        raise ValueError("Index must be unique and sorted in increasing order.")
    frame = data[columns].copy()
    if not all(pd.api.types.is_numeric_dtype(frame[c]) for c in columns):
        raise TypeError("All ARDL variables must be numeric.")
    if frame.isna().any().any() or not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError("ARDL input must be complete and finite; resolve missingness explicitly.")
    if len(frame) < 60:
        raise ValueError("At least 60 complete observations are required for this ARDL workflow.")
    if not isinstance(max_ar_lag, int) or max_ar_lag < 1:
        raise ValueError("max_ar_lag must be a positive integer.")
    if not isinstance(max_distributed_lag, int) or max_distributed_lag < 1:
        raise ValueError("max_distributed_lag must be a positive integer.")
    if selection_ic not in {"aic", "bic"}:
        raise ValueError("selection_ic must be 'aic' or 'bic'.")
    if trend not in {"n", "c", "ct"}:
        raise ValueError("trend must be 'n', 'c' or 'ct'.")
    if bounds_case not in {1, 3, 5}:
        raise ValueError("This wrapper supports bounds_case 1, 3 or 5; cases 2 and 4 require restricted deterministic terms.")
    expected_case = {"n": 1, "c": 3, "ct": 5}[trend]
    if bounds_case != expected_case:
        raise ValueError(
            f"trend={trend!r} must be paired with bounds_case={expected_case} "
            "in this wrapper. Use a custom specification for restricted cases."
        )
    if not 0 < alpha < 1:
        raise ValueError("alpha must be strictly between 0 and 1.")
    if not isinstance(nsim, int) or nsim < 1000:
        raise ValueError("nsim must be an integer of at least 1000.")
    if not isinstance(seed, int):
        raise ValueError("seed must be an integer.")

    expected_names = set(columns)
    if set(integration_assessments) != expected_names:
        raise ValueError(
            "integration_assessments must contain exactly the dependent and regressor names."
        )
    eligibility = assess_model_eligibility(integration_assessments)
    if not eligibility["candidate_models"]["ARDL_bounds"]["eligible"]:
        raise ValueError(
            "ARDL bounds workflow blocked by integration evidence or an all-I(0) system. "
            "Review the model eligibility assessment."
        )

    selection = ardl_select_order(
        endog=frame[dependent_variable],
        maxlag=max_ar_lag,
        exog=frame[regressors],
        maxorder=max_distributed_lag,
        trend=trend,
        ic=selection_ic,
        missing="raise",
    )
    selected_model = selection.model
    selected_ar_lag = selected_model.ardl_order[0]
    if selected_ar_lag is None or int(selected_ar_lag) < 1:
        raise ValueError(
            "The selected ARDL has no autoregressive lag and cannot be converted "
            "to the required UECM. Reconsider the prespecified lag search or "
            "report a stationary short-run model instead."
        )
    distributed_lags = {
        str(name): [int(lag) for lag in lags]
        for name, lags in selected_model.dl_lags.items()
    }
    if any(not lags or max(lags) < 1 for lags in distributed_lags.values()):
        raise ValueError(
            "The selected ARDL gives at least one regressor no lagged level term, "
            "so it cannot be converted to the required UECM. Reconsider the "
            "prespecified lag search or report a short-run model instead."
        )

    ardl_result = selected_model.fit()
    uecm_result = UECM.from_ardl(selected_model).fit()
    bounds = uecm_result.bounds_test(
        case=bounds_case,
        asymptotic=asymptotic_bounds,
        nsim=nsim,
        seed=seed,
    )
    lower_p = float(bounds.p_values["lower"])
    upper_p = float(bounds.p_values["upper"])
    if upper_p < alpha:
        decision = "evidence_of_level_relationship"
    elif lower_p > alpha:
        decision = "no_evidence_of_level_relationship"
    else:
        decision = "inconclusive_bounds_test"

    long_run = None
    if decision == "evidence_of_level_relationship":
        ar_sum = sum(
            float(ardl_result.params.get(f"{dependent_variable}.L{lag}", 0.0))
            for lag in range(1, int(selected_model.ardl_order[0]) + 1)
        )
        denominator = 1.0 - ar_sum
        if abs(denominator) > 1e-8:
            long_run = {}
            for name, lags in distributed_lags.items():
                numerator = sum(
                    float(ardl_result.params.get(f"{name}.L{lag}", 0.0))
                    for lag in lags
                )
                long_run[name] = numerator / denominator

    crit = bounds.crit_vals
    critical_values = [
        {
            "percentile": float(percentile),
            "lower": float(row["lower"]),
            "upper": float(row["upper"]),
        }
        for percentile, row in crit.iterrows()
    ]
    selected_ic_series = selection.bic if selection_ic == "bic" else selection.aic
    selected_ic_value = float(selected_ic_series.iloc[0])
    return ARDLBoundsResult(
        dependent_variable=dependent_variable,
        regressors=list(regressors),
        input_observations=int(len(frame)),
        estimation_observations=int(ardl_result.nobs),
        sample_start=str(frame.index[0]),
        sample_end=str(frame.index[-1]),
        estimation_sample_start=str(ardl_result.resid.index[0]),
        estimation_sample_end=str(ardl_result.resid.index[-1]),
        integration_assessments=dict(integration_assessments),
        selected_ar_lag=int(selected_model.ardl_order[0]),
        selected_distributed_lags=distributed_lags,
        selection_ic=selection_ic,
        selected_ic_value=selected_ic_value,
        deterministic_trend=trend,
        bounds_case=bounds_case,
        bounds_statistic=float(bounds.stat),
        bounds_lower_pvalue=lower_p,
        bounds_upper_pvalue=upper_p,
        bounds_decision=decision,
        bounds_critical_values=critical_values,
        alpha=float(alpha),
        ardl_parameters=_parameter_records(ardl_result),
        uecm_parameters=_parameter_records(uecm_result),
        long_run_multipliers=long_run,
        asymptotic_bounds=bool(asymptotic_bounds),
    )
