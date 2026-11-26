"""Tests for historical-support scenario auditing."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest

from ghana_banking.modeling import audit_scenario_historical_support


def _example():
    index = pd.date_range("2010-01-01", periods=60, freq="MS")
    historical = pd.DataFrame({
        "inflation": np.linspace(2.0, 4.0, 60) + np.sin(np.arange(60)) * 0.2,
        "policy_rate": np.linspace(10.0, 15.0, 60),
    }, index=index)
    future = pd.date_range(index[-1] + pd.offsets.MonthBegin(1), periods=6, freq="MS")
    baseline = pd.DataFrame({
        "inflation": np.repeat(historical["inflation"].iloc[-1], 6),
        "policy_rate": np.repeat(historical["policy_rate"].iloc[-1], 6),
    }, index=future)
    adverse = baseline.copy()
    adverse["inflation"] += np.arange(1, 7) * 2
    adverse["policy_rate"] += np.arange(1, 7) * 0.5
    return historical, {"Baseline": baseline, "Adverse": adverse}


def test_scenario_support_audit_flags_marginal_exceedance_and_baseline_contrasts():
    historical, scenarios = _example()
    result = audit_scenario_historical_support(
        historical, scenarios, integrated_variables=["inflation"]
    )
    table = result.diagnostics
    adverse_inflation = table[
        (table["scenario"] == "Adverse") & (table["variable"] == "inflation")
    ].iloc[0]
    assert adverse_inflation["comparison_scale"] == "first_difference"
    assert adverse_inflation["share_outside_historical_range"] > 0
    assert adverse_inflation["terminal_difference_vs_baseline"] > 0
    baseline = table[table["scenario"] == "Baseline"]
    assert np.allclose(baseline["terminal_difference_vs_baseline"], 0.0)
    assert "not a probability" in result.to_dict()["interpretation"]


def test_scenario_support_audit_compares_non_integrated_variables_in_levels():
    historical, scenarios = _example()
    result = audit_scenario_historical_support(historical, scenarios)
    row = result.diagnostics[
        (result.diagnostics["scenario"] == "Adverse")
        & (result.diagnostics["variable"] == "policy_rate")
    ].iloc[0]
    assert row["comparison_scale"] == "level"
    assert row["terminal_difference_vs_baseline"] == pytest.approx(3.0)


def test_scenario_support_audit_rejects_invalid_paths_and_settings():
    historical, scenarios = _example()
    with pytest.raises(ValueError, match="baseline"):
        audit_scenario_historical_support(historical, {"Adverse": scenarios["Adverse"]})
    broken = scenarios["Adverse"].copy()
    broken.iloc[0, 0] = np.nan
    with pytest.raises(ValueError, match="complete"):
        audit_scenario_historical_support(
            historical, {"Baseline": scenarios["Baseline"], "Adverse": broken}
        )
    with pytest.raises(ValueError, match="integrated_variables"):
        audit_scenario_historical_support(
            historical, scenarios, integrated_variables=["unknown"]
        )
    with pytest.raises(ValueError, match="strictly increasing"):
        audit_scenario_historical_support(
            historical, scenarios, quantile_levels=[0.95, 0.05]
        )
