"""Parameter-uncertainty simulation for conditional ARDL scenario forecasts.

Coefficient draws use the fitted estimator's asymptotic covariance matrix.
The resulting bands isolate parameter uncertainty conditional on the selected
model and supplied exogenous paths; they are not full predictive intervals.
"""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


def forecast_ardl_parameter_uncertainty(
    fitted_results,
    scenarios: Dict[str, pd.DataFrame],
    baseline_name: str = "Baseline",
    draws: int = 2000,
    significance_level: float = 0.05,
    seed: int | None = 12345,
) -> pd.DataFrame:
    """Simulate ARDL forecasts over asymptotic coefficient draws.

    The same coefficient draw is applied to every scenario, preserving paired
    scenario contrasts. Coefficients are drawn jointly from a multivariate
    normal distribution centred on the fitted parameters, using the fitted
    estimator's covariance matrix. Future exogenous paths and the selected
    ARDL specification are held fixed.

    Returned quantiles describe parameter uncertainty only. They exclude
    future innovation uncertainty, uncertainty in scenario calibration,
    model-selection uncertainty, structural change and non-normal parameter
    uncertainty. They must not be labelled as full prediction intervals.
    """
    if not isinstance(scenarios, dict) or not scenarios:
        raise ValueError("scenarios must be a non-empty mapping of names to DataFrames.")
    if baseline_name not in scenarios:
        raise ValueError(f"A baseline scenario named {baseline_name!r} is required.")
    if not isinstance(draws, int) or draws < 100:
        raise ValueError("draws must be an integer of at least 100.")
    if not isinstance(significance_level, (int, float)) or not 0 < significance_level < 1:
        raise ValueError("significance_level must lie strictly between 0 and 1.")
    if not hasattr(fitted_results, "model") or not hasattr(fitted_results, "cov_params"):
        raise TypeError("fitted_results must be fitted statsmodels ARDL results.")
    model = fitted_results.model
    if getattr(model, "fixed", None) is not None:
        raise NotImplementedError("ARDL models with fixed regressors are not supported.")
    original_endog = model.data.orig_endog
    original_exog = model.data.orig_exog
    if not isinstance(original_endog, (pd.Series, pd.DataFrame)):
        raise TypeError("Fit the ARDL model with pandas objects carrying an index.")
    if not isinstance(original_exog, pd.DataFrame) or original_exog.shape[1] == 0:
        raise ValueError("The fitted ARDL model must contain named exogenous regressors.")
    expected_columns = list(original_exog.columns)
    training_index = original_endog.index
    prepared = {}

    from .ardl_scenarios import _validate_future_index

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

    params = np.asarray(fitted_results.params, dtype=float).reshape(-1)
    covariance = np.asarray(fitted_results.cov_params(), dtype=float)
    if covariance.shape != (len(params), len(params)):
        raise ValueError("Parameter covariance matrix has an incompatible shape.")
    if not np.isfinite(params).all() or not np.isfinite(covariance).all():
        raise ValueError("Fitted parameters and covariance matrix must be finite.")
    covariance = (covariance + covariance.T) / 2
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    tolerance = max(1.0, float(np.max(np.abs(eigenvalues)))) * 1e-10
    if float(eigenvalues.min()) < -tolerance:
        raise ValueError("Parameter covariance matrix must be positive semidefinite.")
    covariance_psd = (eigenvectors * np.clip(eigenvalues, 0.0, None)) @ eigenvectors.T

    rng = np.random.default_rng(seed)
    parameter_draws = rng.multivariate_normal(params, covariance_psd, size=draws)
    nobs = len(original_endog)
    simulated = {name: np.empty((draws, common_horizon), dtype=float) for name in prepared}
    for draw_index, parameter_vector in enumerate(parameter_draws):
        for name, path in prepared.items():
            prediction = model.predict(
                params=parameter_vector,
                start=nobs,
                end=nobs + common_horizon - 1,
                dynamic=True,
                exog_oos=path,
            )
            values = np.asarray(prediction, dtype=float).reshape(-1)
            if len(values) != common_horizon or not np.isfinite(values).all():
                raise RuntimeError("A parameter draw produced invalid ARDL forecasts.")
            simulated[name][draw_index] = values

    lower_q = float(significance_level) / 2
    upper_q = 1 - lower_q
    baseline_draws = simulated[baseline_name]
    records = []
    for name, values in simulated.items():
        contrasts = values - baseline_draws
        for position, period in enumerate(common_index):
            records.append({
                "scenario": name,
                "period": str(period),
                "parameter_mean": float(values[:, position].mean()),
                "parameter_median": float(np.median(values[:, position])),
                "parameter_lower": float(np.quantile(values[:, position], lower_q)),
                "parameter_upper": float(np.quantile(values[:, position], upper_q)),
                "baseline_parameter_mean": float(baseline_draws[:, position].mean()),
                "change_vs_baseline_mean": float(contrasts[:, position].mean()),
                "change_vs_baseline_lower": float(np.quantile(contrasts[:, position], lower_q)),
                "change_vs_baseline_upper": float(np.quantile(contrasts[:, position], upper_q)),
                "draws": int(draws),
                "significance_level": float(significance_level),
                "uncertainty_type": "asymptotic parameter uncertainty only",
            })
    result = pd.DataFrame(records)
    numeric = result.select_dtypes(include=[np.number]).to_numpy(dtype=float)
    if not np.isfinite(numeric).all():
        raise RuntimeError("Parameter-uncertainty output contains non-finite values.")
    if (result["parameter_lower"] > result["parameter_upper"]).any():
        raise RuntimeError("Parameter-uncertainty bounds are reversed.")
    return result
