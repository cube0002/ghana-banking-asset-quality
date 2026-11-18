"""Compare Bank of Ghana publication vintages without overwriting source snapshots."""

from typing import Union

import pandas as pd

_REQUIRED_COLUMNS = {
    "Date", "Indicator Code", "Indicator", "Value", "Unit",
    "Publication Date", "Source URL",
}


def _prepare_snapshot(snapshot: Union[str, pd.DataFrame], label: str) -> pd.DataFrame:
    """Read and validate one publication vintage."""
    frame = pd.read_csv(snapshot) if isinstance(snapshot, str) else snapshot.copy()
    missing = _REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError("{} snapshot is missing columns: {}".format(label, sorted(missing)))
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame["Publication Date"] = pd.to_datetime(frame["Publication Date"], errors="coerce")
    frame["Value"] = pd.to_numeric(frame["Value"], errors="coerce")
    if frame[["Date", "Publication Date", "Value"]].isna().any().any():
        raise ValueError("{} snapshot contains invalid dates or values.".format(label))
    if frame["Indicator Code"].isna().any() or (frame["Indicator Code"].astype(str).str.strip() == "").any():
        raise ValueError("{} snapshot contains blank indicator codes.".format(label))
    if frame["Source URL"].isna().any() or (frame["Source URL"].astype(str).str.strip() == "").any():
        raise ValueError("{} snapshot must retain a source URL for every row.".format(label))
    if frame.duplicated(["Date", "Indicator Code"]).any():
        raise ValueError("{} snapshot contains duplicate date-indicator rows.".format(label))
    return frame


def build_bog_revision_report(
    previous: Union[str, pd.DataFrame],
    current: Union[str, pd.DataFrame],
    tolerance: float = 0.0,
) -> pd.DataFrame:
    """Compare two BoG publication vintages at date-indicator level.

    Inputs may be CSV paths or DataFrames. Tolerance is the maximum absolute
    numeric difference treated as unchanged. Neither input vintage is altered.
    """
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)):
        raise TypeError("tolerance must be a non-negative number.")
    if tolerance < 0:
        raise ValueError("tolerance must be a non-negative number.")

    old = _prepare_snapshot(previous, "Previous").rename(columns={
        "Value": "Previous Value",
        "Indicator": "Previous Indicator",
        "Unit": "Previous Unit",
        "Publication Date": "Previous Publication Date",
        "Source URL": "Previous Source URL",
    })
    new = _prepare_snapshot(current, "Current").rename(columns={
        "Value": "Current Value",
        "Indicator": "Current Indicator",
        "Unit": "Current Unit",
        "Publication Date": "Current Publication Date",
        "Source URL": "Current Source URL",
    })
    report = old.merge(
        new, on=["Date", "Indicator Code"], how="outer",
        indicator=True, validate="one_to_one",
    )
    report["Observation Status"] = report["_merge"].map({
        "left_only": "removed", "right_only": "added", "both": "unchanged",
    })
    matched = report["_merge"] == "both"
    changed = matched & (
        (report["Current Value"] - report["Previous Value"]).abs() > tolerance
    )
    report.loc[changed, "Observation Status"] = "revised"
    report["Value Change"] = report["Current Value"] - report["Previous Value"]

    report["Metadata Changed"] = False
    report.loc[matched, "Metadata Changed"] = (
        report.loc[matched, "Previous Indicator"].fillna("").astype(str).to_numpy()
        != report.loc[matched, "Current Indicator"].fillna("").astype(str).to_numpy()
    ) | (
        report.loc[matched, "Previous Unit"].fillna("").astype(str).to_numpy()
        != report.loc[matched, "Current Unit"].fillna("").astype(str).to_numpy()
    )
    columns = [
        "Date", "Indicator Code", "Previous Indicator", "Current Indicator",
        "Previous Unit", "Current Unit", "Previous Value", "Current Value",
        "Value Change", "Observation Status", "Metadata Changed",
        "Previous Publication Date", "Current Publication Date",
        "Previous Source URL", "Current Source URL",
    ]
    return report[columns].sort_values(
        ["Date", "Indicator Code"]
    ).reset_index(drop=True)
