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
    pd.DataFrame({
        "Date": ["2026-10-01", "2026-10-01"],
        "Indicator Code": ["NPL", "NPL"],
        "Indicator": ["NPL", "NPL"],
        "Value": [13.1, 13.1],
        "Unit": ["Percent", "Percent"],
        "Publication Date": ["2026-11-17", "2026-11-17"],
        "Source URL": ["https://bog.gov.gh/source.pdf"] * 2,
    }).to_csv(path, index=False)
    with pytest.raises(ValueError, match="duplicate"):
        load_bog_summary_snapshot(str(path))


def test_bog_snapshot_matches_existing_series_at_published_precision():
    raw = pd.read_csv(ROOT / "data" / "raw" / "data_first.csv")
    raw["Date"] = pd.to_datetime(
        raw["Name of Series"], format="%d/%m/%Y", errors="coerce"
    )
    raw = raw.loc[raw["Date"].notna()].set_index("Date")
    snapshot = load_bog_summary_snapshot(
        str(ROOT / "data" / "raw" / "bog_summary_nov_2026.csv")
    )
    overlap_dates = pd.to_datetime(["2025-10-01", "2025-11-01", "2025-12-01"])
    overlap = snapshot[snapshot["Date"].isin(overlap_dates)]
    source_columns = {
        "CAR": "Capital Adequacy Ratio",
        "NPL": "Non Performing Loan Ratio",
        "ROA": "Return on Assets",
    }
    for code, column in source_columns.items():
        values = overlap[overlap["Indicator Code"] == code].set_index("Date")["Value"]
        original = pd.to_numeric(raw.loc[values.index, column])
        assert (original.round(1) == values).all()



def test_july_and_november_bog_vintages_match_on_common_observations():
    july = load_bog_summary_snapshot(
        str(ROOT / "data" / "raw" / "bog_summary_jul_2026.csv")
    )
    november = load_bog_summary_snapshot(
        str(ROOT / "data" / "raw" / "bog_summary_nov_2026.csv")
    )
    overlap = july.merge(
        november,
        on=["Date", "Indicator Code"],
        suffixes=("_july", "_november"),
        validate="one_to_one",
    )

    assert len(overlap) == 9 * 11
    assert overlap["Value_july"].equals(overlap["Value_november"])
