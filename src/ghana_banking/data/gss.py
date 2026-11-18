"""Ghana Statistical Service StatsBank quarterly GDP connector.

This module uses the documented PxWeb v1 query interface. The table endpoint
can be overridden because the provider may reorganise its catalogue.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Dict
from urllib.request import Request, urlopen

import pandas as pd


DEFAULT_GSS_GDP_API_URL = (
    "https://statsbank.statsghana.gov.gh/pxweb/api/v1/en/"
    "Macroeconomic Indicators/"
    "Macroeconomic Indicators__Real Sector (GDP)__Quarterly GDP/"
    "qgdp_p_px.px"
)
GDP_SERIES_LABEL = "Real GDP (constant 2013 prices)"
GDP_AGGREGATE_LABEL = "Overall GDP"


def build_gss_gdp_query() -> Dict:
    """Build a PxWeb query for total real GDP at constant 2013 prices."""
    return {
        "query": [
            {
                "code": "Quarter",
                "selection": {"filter": "all", "values": ["*"]},
            },
            {
                "code": "GDP_Series",
                "selection": {"filter": "item", "values": [GDP_SERIES_LABEL]},
            },
            {
                "code": "Variable",
                "selection": {"filter": "item", "values": [GDP_AGGREGATE_LABEL]},
            },
        ],
        "response": {"format": "csv"},
    }


def _parse_pxweb_gdp_csv(payload: bytes) -> pd.DataFrame:
    """Convert a PxWeb CSV response to the repository's two-column GDP schema."""
    from io import BytesIO

    try:
        frame = pd.read_csv(BytesIO(payload))
    except Exception as exc:
        raise ValueError("GSS PxWeb response was not a readable CSV.") from exc

    if frame.empty or len(frame.columns) < 2:
        raise ValueError("GSS PxWeb response did not contain a GDP data table.")

    # PxWeb returns dimension columns followed by the selected value column.
    period_col = next(
        (col for col in frame.columns if str(col).strip().lower() in {"quarter", "time"}),
        frame.columns[0],
    )
    value_col = next(
        (
            col for col in frame.columns
            if str(col).strip().lower() in {"value", "values", "real gdp (constant 2013 prices)"}
        ),
        frame.columns[-1],
    )

    periods = frame[period_col].astype(str).str.extract(
        r"(\d{4}Q[1-4])", expand=False
    )
    values = pd.to_numeric(frame[value_col], errors="coerce")
    result = pd.DataFrame({"Name of Series": periods, "Gross Domestic Product (GDP), production, real": values})
    result = result.dropna()
    result["Name of Series"] = result["Name of Series"].astype(str)
    result = result.drop_duplicates("Name of Series").sort_values("Name of Series")

    if len(result) < 8:
        raise ValueError(
            "GSS PxWeb response contained fewer than eight valid quarterly GDP observations."
        )
    return result.reset_index(drop=True)


def fetch_gss_quarterly_gdp(
    api_url: str = None,
    timeout: int = 60,
) -> pd.DataFrame:
    """Query GSS StatsBank and return real GDP by quarter.

    The endpoint and query labels are based on the public GSS Quarterly GDP
    table. If GSS changes its table structure or category codes, this
    connector fails explicitly instead of silently updating the local data.
    """
    if api_url is None:
        api_url = os.getenv("GSS_GDP_API_URL", DEFAULT_GSS_GDP_API_URL)
    if not api_url.startswith("https://"):
        raise ValueError("GSS StatsBank API URL must use HTTPS.")

    request = Request(
        api_url,
        data=json.dumps(build_gss_gdp_query()).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "text/csv",
            "User-Agent": "ghana-banking-asset-quality/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except Exception as exc:
        raise RuntimeError(f"Could not retrieve quarterly GDP from GSS StatsBank: {exc}") from exc

    if not payload:
        raise ValueError("GSS StatsBank returned an empty response.")
    return _parse_pxweb_gdp_csv(payload)


def update_gss_quarterly_gdp(
    raw_data_path: str = None,
    api_url: str = None,
    timeout: int = 60,
) -> Dict[str, str]:
    """Fetch GSS quarterly GDP and atomically replace the local source CSV."""
    if raw_data_path is None:
        raw_data_path = Path(__file__).resolve().parents[3] / "data" / "raw"
    else:
        raw_data_path = Path(raw_data_path)
    raw_data_path.mkdir(parents=True, exist_ok=True)

    frame = fetch_gss_quarterly_gdp(api_url=api_url, timeout=timeout)
    destination = raw_data_path / "data_first2.csv"

    if destination.exists():
        try:
            current = pd.read_csv(destination)
            current_periods = current["Name of Series"].astype(str).str.extract(
                r"(\d{4}Q[1-4])", expand=False
            ).dropna()
            if not current_periods.empty:
                current_latest = max(current_periods)
                incoming_latest = frame["Name of Series"].max()
                if incoming_latest < current_latest:
                    raise ValueError(
                        f"GSS GDP download is stale ({incoming_latest}) compared with "
                        f"the local file ({current_latest}); no file was changed."
                    )
        except ValueError:
            raise
        except Exception:
            # If the old file cannot be parsed, the validated provider response
            # may still replace it; the original remains untouched until commit.
            pass

    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=str(raw_data_path),
            prefix="data_first2.csv.", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            frame.to_csv(handle, index=False)
        os.replace(str(temporary), str(destination))
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()

    return {
        "source": "Ghana Statistical Service StatsBank",
        "latest_quarter": frame["Name of Series"].max(),
        "observations": str(len(frame)),
        "file": str(destination),
    }
