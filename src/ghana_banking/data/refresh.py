"""Refresh the raw Ghana banking datasets from configured CSV export URLs.

The URLs are supplied by the repository owner. The refresh process validates
both downloads before replacing either local source file.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd


MONTHLY_FILE = "data_first.csv"
GDP_FILE = "data_first2.csv"
MONTHLY_REQUIRED = {
    "Name of Series",
    "Monetary Policy Rate (%)",
    "Consumer Price Index, All Items",
    "USD Exchange Rate, monthly averages",
    "Total Liquidity (M2+)",
    "Gold Price (Realised Gold Price)",
    "Return on Assets",
    "Non Performing Loan Ratio",
    "Capital Adequacy Ratio",
}
GDP_REQUIRED = {
    "Name of Series",
    "Gross Domestic Product (GDP), production, real",
}


def _download_csv(url: str, label: str, timeout: int = 60) -> bytes:
    """Download a CSV over HTTPS (HTTP is allowed for explicitly configured sources)."""
    if not url or not url.startswith(("https://", "http://")):
        raise ValueError(f"{label} URL must start with http:// or https://")
    request = Request(url, headers={"User-Agent": "ghana-banking-asset-quality-data-refresh/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not download {label} CSV: {exc}") from exc
    if not payload:
        raise ValueError(f"{label} download was empty.")
    return payload


def _parse_monthly(payload: bytes) -> Tuple[pd.DataFrame, pd.Timestamp]:
    """Parse and validate a monthly source CSV without changing its contents."""
    from io import BytesIO

    try:
        frame = pd.read_csv(BytesIO(payload))
    except Exception as exc:
        raise ValueError(f"Monthly download is not a readable CSV: {exc}") from exc
    missing = MONTHLY_REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(f"Monthly CSV is missing required columns: {sorted(missing)}")
    dates = pd.to_datetime(frame["Name of Series"], format="%d/%m/%Y", errors="coerce")
    valid_dates = dates.dropna()
    if len(valid_dates) < 12:
        raise ValueError("Monthly CSV must contain at least 12 valid monthly observations.")
    if valid_dates.max() < valid_dates.min():
        raise ValueError("Monthly date range is invalid.")
    return frame, valid_dates.max()


def _parse_gdp(payload: bytes) -> Tuple[pd.DataFrame, pd.Period]:
    """Parse and validate a quarterly GDP source CSV."""
    from io import BytesIO

    try:
        frame = pd.read_csv(BytesIO(payload))
    except Exception as exc:
        raise ValueError(f"GDP download is not a readable CSV: {exc}") from exc
    missing = GDP_REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(f"GDP CSV is missing required columns: {sorted(missing)}")
    quarters = frame["Name of Series"].astype(str).str.extract(
        r"(\d{4}Q[1-4])", expand=False
    )
    values = pd.to_numeric(
        frame["Gross Domestic Product (GDP), production, real"], errors="coerce"
    )
    valid = pd.DataFrame({"quarter": quarters, "value": values}).dropna()
    if len(valid) < 8:
        raise ValueError("GDP CSV must contain at least eight valid quarterly observations.")
    parsed = pd.PeriodIndex(valid["quarter"], freq="Q")
    return frame, parsed.max()


def _latest_existing_month(path: Path):
    if not path.exists():
        return None
    try:
        existing = pd.read_csv(path, usecols=["Name of Series"])
        dates = pd.to_datetime(existing["Name of Series"], format="%d/%m/%Y", errors="coerce")
        return dates.max() if dates.notna().any() else None
    except Exception:
        return None


def _latest_existing_quarter(path: Path):
    if not path.exists():
        return None
    try:
        existing = pd.read_csv(path, usecols=["Name of Series"])
        quarters = existing["Name of Series"].astype(str).str.extract(
            r"(\d{4}Q[1-4])", expand=False
        ).dropna()
        return pd.PeriodIndex(quarters, freq="Q").max() if not quarters.empty else None
    except Exception:
        return None


def refresh_source_data(
    monthly_url: str,
    gdp_url: str,
    raw_data_path: str = None,
    timeout: int = 60,
) -> Dict[str, str]:
    """Download, validate and replace both source CSVs.

    A downloaded file is rejected if its latest observation is older than
    the corresponding local source. Both downloads are validated before
    writing, and the original CSV payloads are preserved byte-for-byte.
    """
    if raw_data_path is None:
        raw_data_path = Path(__file__).resolve().parents[4] / "data" / "raw"
    else:
        raw_data_path = Path(raw_data_path)
    raw_data_path.mkdir(parents=True, exist_ok=True)

    monthly_payload = _download_csv(monthly_url, "monthly", timeout)
    gdp_payload = _download_csv(gdp_url, "quarterly GDP", timeout)

    _, monthly_latest = _parse_monthly(monthly_payload)
    _, gdp_latest = _parse_gdp(gdp_payload)

    monthly_path = raw_data_path / MONTHLY_FILE
    gdp_path = raw_data_path / GDP_FILE
    current_month = _latest_existing_month(monthly_path)
    current_quarter = _latest_existing_quarter(gdp_path)

    if current_month is not None and monthly_latest < current_month:
        raise ValueError(
            f"Monthly download is stale ({monthly_latest.date()}) compared with "
            f"the local file ({current_month.date()}); no files were changed."
        )
    if current_quarter is not None and gdp_latest < current_quarter:
        raise ValueError(
            f"GDP download is stale ({gdp_latest}) compared with the local file "
            f"({current_quarter}); no files were changed."
        )

    staged = []
    try:
        for destination, payload in (
            (monthly_path, monthly_payload),
            (gdp_path, gdp_payload),
        ):
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=str(raw_data_path), prefix=destination.name + ".",
                suffix=".tmp", delete=False
            ) as handle:
                handle.write(payload)
                staged.append((Path(handle.name), destination))
        for temporary, destination in staged:
            os.replace(str(temporary), str(destination))
    finally:
        for temporary, _ in staged:
            if temporary.exists():
                temporary.unlink()

    return {
        "monthly_latest": monthly_latest.strftime("%Y-%m-%d"),
        "gdp_latest": str(gdp_latest),
        "monthly_rows": str(len(_parse_monthly(monthly_payload)[0])),
        "gdp_rows": str(len(_parse_gdp(gdp_payload)[0])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh Ghana banking source CSV files.")
    parser.add_argument("--monthly-url", default=os.getenv("MONTHLY_DATA_URL"))
    parser.add_argument("--gdp-url", default=os.getenv("GDP_DATA_URL"))
    parser.add_argument("--raw-data-path", default=None)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    if not args.monthly_url or not args.gdp_url:
        parser.error(
            "Provide --monthly-url and --gdp-url, or set MONTHLY_DATA_URL and GDP_DATA_URL."
        )
    try:
        result = refresh_source_data(
            args.monthly_url, args.gdp_url, args.raw_data_path, args.timeout
        )
    except Exception as exc:
        print(f"Data refresh failed: {exc}", file=sys.stderr)
        return 1

    print("Data refresh completed successfully.")
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
