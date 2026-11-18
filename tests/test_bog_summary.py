"""Tests for the Bank of Ghana November 2026 publication snapshot."""

from pathlib import Path

import pandas as pd
import pytest

from ghana_banking.data.bog import load_bog_summary_snapshot


ROOT = Path(__file__).resolve().parents[1]


def test_bog_summary_snapshot_has_documented_monthly_coverage():
    path = ROOT / "data" / "raw" / "bog_summary_nov_2026.csv"
    frame = load_bog_summary_snapshot(str(path))

    assert frame["Date"].min() == pd.Timestamp("2025-10-01")
    assert frame["Date"].max() == pd.Timestamp("2026-10-01")
    assert frame["Date"].nunique() == 13
    assert frame["Indicator Code"].nunique() == 11
    assert len(frame) == 13 * 11
    assert frame["Source URL"].str.contains("bog.gov.gh").all()


def test_bog_summary_snapshot_contains_published_october_2026_values():
    path = ROOT / "data" / "raw" / "bog_summary_nov_2026.csv"
    frame = load_bog_summary_snapshot(str(path))
    latest = frame[frame["Date"] == pd.Timestamp("2026-10-01")].set_index(
        "Indicator Code"
    )["Value"]

    assert latest["CAR"] == pytest.approx(18.5)
    assert latest["NPL"] == pytest.approx(13.1)
    assert latest["NPL_EXCL_LOSS"] == pytest.approx(3.3)
    assert latest["ROA"] == pytest.approx(3.6)
    assert latest["ROE"] == pytest.approx(19.0)


def test_bog_summary_snapshot_rejects_duplicate_observations(tmp_path):
    path = tmp_path / "duplicate.csv"
    pd.DataFrame(
        {
            "Date": ["2026-10-01", "2026-10-01"],
            "Indicator Code": ["NPL", "NPL"],
            "Indicator": ["NPL", "NPL"],
            "Value": [13.1, 13.1],
            "Unit": ["Percent", "Percent"],
            "Publication Date": ["2026-11-17", "2026-11-17"],
            "Source URL": ["https://bog.gov.gh/source.pdf"] * 2,
        }
    ).to_csv(path, index=False)

    with pytest.raises(ValueError, match="duplicate"):
        load_bog_summary_snapshot(str(path))
