"""Tests for Bank of Ghana publication-vintage reconciliation."""

import pandas as pd
import pytest

from ghana_banking.data.revisions import build_bog_revision_report


def _snapshot(rows, publication_date, source):
    return pd.DataFrame([
        {
            "Date": date,
            "Indicator Code": code,
            "Indicator": label,
            "Value": value,
            "Unit": unit,
            "Publication Date": publication_date,
            "Source URL": source,
        }
        for date, code, label, value, unit in rows
    ])


def test_revision_report_identifies_revisions_additions_and_removals():
    previous = _snapshot(
        [
            ("2026-08-01", "NPL", "NPL ratio", 14.0, "Percent"),
            ("2026-09-01", "NPL", "NPL ratio", 13.8, "Percent"),
            ("2026-09-01", "CAR", "Capital adequacy ratio", 18.2, "Percent"),
        ],
        "2026-10-17", "https://bog.gov.gh/old.pdf",
    )
    current = _snapshot(
        [
            ("2026-08-01", "NPL", "NPL ratio", 13.9, "Percent"),
            ("2026-09-01", "NPL", "NPL ratio", 13.8, "Percent"),
            ("2026-10-01", "NPL", "NPL ratio", 13.1, "Percent"),
        ],
        "2026-11-17", "https://bog.gov.gh/new.pdf",
    )
    report = build_bog_revision_report(previous, current)
    statuses = report.set_index(["Date", "Indicator Code"])["Observation Status"]
    assert statuses.loc[(pd.Timestamp("2026-08-01"), "NPL")] == "revised"
    assert statuses.loc[(pd.Timestamp("2026-09-01"), "NPL")] == "unchanged"
    assert statuses.loc[(pd.Timestamp("2026-09-01"), "CAR")] == "removed"
    assert statuses.loc[(pd.Timestamp("2026-10-01"), "NPL")] == "added"
    revised = report[
        (report["Date"] == pd.Timestamp("2026-08-01"))
        & (report["Indicator Code"] == "NPL")
    ].iloc[0]
    assert revised["Value Change"] == pytest.approx(-0.1)
    assert revised["Previous Source URL"].endswith("old.pdf")
    assert revised["Current Source URL"].endswith("new.pdf")


def test_revision_report_respects_tolerance_and_flags_definition_changes():
    previous = _snapshot(
        [("2026-08-01", "NPL", "NPL ratio", 14.00, "Percent")],
        "2026-10-17", "https://bog.gov.gh/old.pdf",
    )
    current = _snapshot(
        [("2026-08-01", "NPL", "Non-performing loan ratio", 14.04, "Percent")],
        "2026-11-17", "https://bog.gov.gh/new.pdf",
    )
    report = build_bog_revision_report(previous, current, tolerance=0.05)
    assert report.loc[0, "Observation Status"] == "unchanged"
    assert bool(report.loc[0, "Metadata Changed"])


def test_revision_report_rejects_negative_tolerance():
    frame = _snapshot(
        [("2026-08-01", "NPL", "NPL ratio", 14.0, "Percent")],
        "2026-10-17", "https://bog.gov.gh/source.pdf",
    )
    with pytest.raises(ValueError, match="non-negative"):
        build_bog_revision_report(frame, frame, tolerance=-0.1)


def test_revision_report_rejects_duplicate_observations():
    frame = _snapshot(
        [
            ("2026-08-01", "NPL", "NPL ratio", 14.0, "Percent"),
            ("2026-08-01", "NPL", "NPL ratio", 14.0, "Percent"),
        ],
        "2026-10-17", "https://bog.gov.gh/source.pdf",
    )
    with pytest.raises(ValueError, match="duplicate"):
        build_bog_revision_report(frame, frame)
