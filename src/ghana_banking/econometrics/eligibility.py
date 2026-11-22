"""Evidence-based model eligibility rules for integrated time series."""
from __future__ import annotations

from typing import Dict


VALID_ORDERS = {"I(0)", "I(1)", "I(2)_or_higher_or_unresolved", "uncertain"}


def assess_model_eligibility(integration_assessments: Dict[str, str]) -> dict:
    """Return candidate model classes implied by documented integration labels.

    This is a screening gate, not model selection. ARDL bounds eligibility
    additionally requires a defensible level relationship, adequate sample,
    appropriate deterministic case and no I(2) regressors. VECM eligibility
    requires a subsequent cointegration-rank analysis. A stationary VAR
    requires every included series to be stationary in its chosen scale.
    """
    if not isinstance(integration_assessments, dict) or not integration_assessments:
        raise ValueError("Provide a non-empty mapping of series names to integration labels.")
    invalid = {
        name: order for name, order in integration_assessments.items()
        if order not in VALID_ORDERS
    }
    if invalid:
        raise ValueError(f"Unsupported integration labels: {invalid}")

    orders = set(integration_assessments.values())
    has_i2_or_unresolved = "I(2)_or_higher_or_unresolved" in orders
    has_uncertain = "uncertain" in orders
    all_i0 = orders == {"I(0)"}
    all_i1 = orders == {"I(1)"}
    mixed_i0_i1 = orders.issubset({"I(0)", "I(1)"}) and not all_i0 and not all_i1

    candidates = {
        "stationary_dynamic_regression_or_VAR": {
            "eligible": all_i0,
            "condition": "All included variables have I(0) evidence in the chosen scale.",
        },
        "ARDL_bounds": {
            "eligible": not has_i2_or_unresolved and not has_uncertain and (mixed_i0_i1 or all_i1),
            "condition": (
                "Screening eligibility only for a non-all-I(0) I(0)/I(1) set: no I(2) variable. Also require a plausible "
                "level relationship, adequate sample and a justified deterministic case; "
                "perform bounds testing before reporting long-run estimates."
            ),
        },
        "VECM": {
            "eligible": all_i1,
            "condition": (
                "All included variables have I(1) evidence. Johansen rank and deterministic "
                "specification must still support cointegration before fitting a VECM."
            ),
        },
        "standard_ARDL_bounds_prohibited": {
            "eligible": has_i2_or_unresolved,
            "condition": "Do not use standard ARDL bounds critical values if any variable may be I(2) or higher.",
        },
    }
    return {
        "series_assessments": dict(integration_assessments),
        "overall_status": (
            "blocked_uncertain" if has_uncertain
            else "blocked_possible_I2" if has_i2_or_unresolved
            else "screening_complete_model_tests_required"
        ),
        "candidate_models": candidates,
        "interpretation": (
            "Integration labels are working evidence. This gate does not establish "
            "cointegration, causal identification, model adequacy or forecast credibility."
        ),
    }
