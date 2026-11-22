"""Tests for evidence-based model eligibility screening."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from ghana_banking.econometrics.eligibility import assess_model_eligibility


def test_all_stationary_supports_stationary_model_candidates():
    result = assess_model_eligibility({"NPL": "I(0)", "inflation": "I(0)"})
    assert result["candidate_models"]["stationary_dynamic_regression_or_VAR"]["eligible"]
    assert not result["candidate_models"]["ARDL_bounds"]["eligible"]
    assert not result["candidate_models"]["VECM"]["eligible"]


def test_mixed_i0_i1_is_ardl_screening_candidate_only():
    result = assess_model_eligibility({"NPL": "I(1)", "inflation": "I(0)"})
    assert result["candidate_models"]["ARDL_bounds"]["eligible"]
    assert not result["candidate_models"]["VECM"]["eligible"]


def test_all_i1_requires_cointegration_test_before_vecm():
    result = assess_model_eligibility({"NPL": "I(1)", "fx": "I(1)"})
    assert result["candidate_models"]["VECM"]["eligible"]
    assert "Johansen" in result["candidate_models"]["VECM"]["condition"]


def test_possible_i2_blocks_standard_ardl_bounds():
    result = assess_model_eligibility({"NPL": "I(1)", "x": "I(2)_or_higher_or_unresolved"})
    assert result["candidate_models"]["standard_ARDL_bounds_prohibited"]["eligible"]
    assert not result["candidate_models"]["ARDL_bounds"]["eligible"]


def test_uncertain_integration_order_blocks_model_screening():
    result = assess_model_eligibility({"NPL": "uncertain"})
    assert result["overall_status"] == "blocked_uncertain"
    assert not result["candidate_models"]["ARDL_bounds"]["eligible"]


def test_rejects_unknown_labels():
    with pytest.raises(ValueError, match="Unsupported"):
        assess_model_eligibility({"NPL": "I(3)"})
