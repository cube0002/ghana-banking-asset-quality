"""Configuration constants for the analysis."""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "figures"
REPORTS_DIR = PROJECT_ROOT / "reports"

# Ensure directories exist
for path in [DATA_RAW, DATA_PROCESSED, FIGURES_DIR, REPORTS_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# Analysis parameters
RANDOM_SEED = 42
ANALYSIS_START = "2010-01-01"
ANALYSIS_END = "2025-07-31"

# VAR parameters
VAR_LAGS = 2
VAR_IC = "aic"
IMPULSE_HORIZON = 12

# Model variables
DEPENDENT_VAR = "NPL_Ratio"
REGRESSION_VARS = [
    "Policy_Rate",
    "CPI",
    "USD_GHS",
    "Money_Supply",
    "Gold_Price",
    "Real_GDP",
    "Capital_Adequacy",
    "ROA",
]
VAR_VARS = ["NPL_Ratio", "Policy_Rate", "CPI", "USD_GHS", "Real_GDP"]

# Stress test scenarios
STRESS_SCENARIOS = {
    "baseline": {
        "description": "Continuation of prevailing conditions",
        "mpr_shock": 0.0,
        "usd_shock": 0.0,
        "cpi_shock": 0.0,
        "gdp_shock": 0.0,
    },
    "moderate_tightening": {
        "description": "Policy-induced rate increase + mild deceleration",
        "mpr_shock": 2.0,
        "usd_shock": 0.0,
        "cpi_shock": 1.0,
        "gdp_shock": -0.5,
    },
    "severe_currency_crisis": {
        "description": "Sharp depreciation + high inflation + tight money",
        "mpr_shock": 3.0,
        "usd_shock": 15.0,
        "cpi_shock": 10.0,
        "gdp_shock": -1.0,
    },
    "severe_recession": {
        "description": "Real contraction + weaker inflation",
        "mpr_shock": 1.0,
        "usd_shock": 5.0,
        "cpi_shock": 2.0,
        "gdp_shock": -3.0,
    },
}