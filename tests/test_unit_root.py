"""Tests for the time-series unit-root diagnostic engine."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest

from ghana_banking.econometrics.unit_root import (
    UnitRootResult,
    assess_integration_order,
    run_unit_root_suite,
)


def _stationary_series(seed=123, n=160):
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(size=n), name="stationary")


def _synthetic_results(pvalues):
    nulls = {
        "ADF": "The series has a unit root.",
        "Phillips-Perron": "The series has a unit root.",
        "KPSS": "The series is level-stationary.",
    }
    alternatives = {
        "ADF": "The series is stationary.",
        "Phillips-Perron": "The series is stationary.",
        "KPSS": "The series is non-stationary.",
    }
    return [
        UnitRootResult(
            series_name="synthetic",
            test=test,
            statistic=0.0,
            pvalue=pvalues[test],
            critical_values={"5%": 0.0},
            null_hypothesis=nulls[test],
            alternative_hypothesis=alternatives[test],
            deterministic="c",
            observations=100,
            sample_start="0",
            sample_end="99",
            selected_lags=1,
            lag_method="fixed",
        )
        for test in ("ADF", "Phillips-Perron", "KPSS")
    ]


def test_suite_returns_three_tests_and_auditable_metadata():
    results = run_unit_root_suite(
        _stationary_series(),
        deterministic="c",
        frequency="monthly",
        transformation="level",
    )
    assert [result.test for result in results] == [
        "ADF", "Phillips-Perron", "KPSS"
    ]
    assert all(result.observations == 160 for result in results)
    assert all(result.frequency == "monthly" for result in results)
    assert all(result.transformation == "level" for result in results)
    assert all(0 <= result.pvalue <= 1 for result in results)
    assert all(result.selected_lags >= 0 for result in results)


def test_suite_supports_intercept_and_trend():
    results = run_unit_root_suite(_stationary_series(), deterministic="ct")
    assert all(result.deterministic == "ct" for result in results)


@pytest.mark.parametrize("deterministic", ["n", "invalid", ""])
def test_rejects_unsupported_deterministic_specification(deterministic):
    with pytest.raises(ValueError, match="deterministic"):
        run_unit_root_suite(_stationary_series(), deterministic=deterministic)


def test_rejects_missing_and_infinite_observations():
    missing = _stationary_series()
    missing.iloc[10] = np.nan
    with pytest.raises(ValueError, match="finite"):
        run_unit_root_suite(missing)

    infinite = _stationary_series()
    infinite.iloc[10] = np.inf
    with pytest.raises(ValueError, match="finite"):
        run_unit_root_suite(infinite)


def test_rejects_non_numeric_and_duplicate_index():
    with pytest.raises(TypeError, match="numeric"):
        run_unit_root_suite(pd.Series(["a", "b", "c"] * 10))

    duplicate = _stationary_series()
    duplicate.index = [0] * len(duplicate)
    with pytest.raises(ValueError, match="duplicate"):
        run_unit_root_suite(duplicate)


def test_rejects_conflicting_adf_lag_arguments():
    with pytest.raises(ValueError, match="Specify adf_lags"):
        run_unit_root_suite(
            _stationary_series(), adf_lags=2, adf_max_lags=8
        )


def test_assessment_requires_concordant_evidence():
    stationary = _synthetic_results(
        {"ADF": 0.01, "Phillips-Perron": 0.02, "KPSS": 0.20}
    )
    unit_root = _synthetic_results(
        {"ADF": 0.20, "Phillips-Perron": 0.30, "KPSS": 0.01}
    )
    mixed = _synthetic_results(
        {"ADF": 0.01, "Phillips-Perron": 0.20, "KPSS": 0.01}
    )

    assert assess_integration_order(stationary)["integration_assessment"] == "I(0)"
    assert assess_integration_order(
        unit_root, stationary
    )["integration_assessment"] == "I(1)"
    assert assess_integration_order(mixed)["integration_assessment"] == "uncertain"


def test_first_difference_still_nonstationary_is_flagged():
    unit_root = _synthetic_results(
        {"ADF": 0.20, "Phillips-Perron": 0.30, "KPSS": 0.01}
    )
    result = assess_integration_order(unit_root, unit_root)
    assert result["integration_assessment"] == "I(2)_or_higher_or_unresolved"


def test_result_can_be_serialized():
    result = run_unit_root_suite(_stationary_series())[0]
    payload = result.to_dict()
    assert payload["test"] == "ADF"
    assert payload["null_hypothesis"] == "The series has a unit root."
