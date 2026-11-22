"""Time-series diagnostics and econometric utilities."""
from .cointegration import JohansenResult, run_johansen_cointegration_test
from .eligibility import assess_model_eligibility
from .stability import OLSStabilityResult, run_ols_stability_diagnostics
from .structural_breaks import ZivotAndrewsResult, run_zivot_andrews_test
from .unit_root import UnitRootResult, assess_integration_order, run_unit_root_suite

__all__ = [
    "UnitRootResult",
    "JohansenResult",
    "ZivotAndrewsResult",
    "OLSStabilityResult",
    "assess_integration_order",
    "assess_model_eligibility",
    "run_unit_root_suite",
    "run_zivot_andrews_test",
    "run_ols_stability_diagnostics",
    "run_johansen_cointegration_test",
]
