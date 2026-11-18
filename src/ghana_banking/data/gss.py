"""Ghana Statistical Service StatsBank quarterly GDP connector.

The connector discovers PxWeb dimension codes from table metadata rather
than assuming provider-specific codes. It fails closed if the requested GDP
series or aggregate cannot be identified unambiguously.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Dict
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd


_GSS_TABLE_PATH = (
    "Macroeconomic Indicators/"
    "Macroeconomic Indicators__Real Sector (GDP)__Quarterly GDP/"
    "qgdp_p_px.px"
)
DEFAULT_GSS_GDP_API_URL = (
    "https://statsbank.statsghana.gov.gh:443/api/v1/en/"
    + quote(_GSS_TABLE_PATH, safe="/")
)
GDP_SERIES_TERMS = ("real", "2013")
GDP_TOTAL_TERMS = ("overall", "total")


def _request_bytes(url: str, data: bytes = None, timeout: int = 60) -> bytes:
    headers = {"User-Agent": "ghana-banking-asset-quality/1.0"}
    method = "GET"
    if data is not None:
        headers.update({"Content-Type": "application/json", "Accept": "text/csv"})
        method = "POST"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except Exception as exc:
        raise RuntimeError("GSS StatsBank request failed: {}".format(exc)) from exc
    if not payload:
        raise ValueError("GSS StatsBank returned an empty response.")
    return payload


def build_gss_gdp_query(metadata: Dict) -> Dict:
    """Build a PxWeb query from live table metadata, rejecting ambiguity."""
    variables = metadata.get("variables", [])
    if not variables:
        raise ValueError("GSS table metadata contains no variables.")

    time_variables = [variable for variable in variables if variable.get("time")]
    if len(time_variables) != 1:
        raise ValueError("Could not identify exactly one quarterly time dimension.")

    matched_series = []
    matched_total = []
    for variable in variables:
        if variable is time_variables[0]:
            continue
        values = variable.get("values", [])
        labels = variable.get("valueTexts", values)
        for value, label in zip(values, labels):
            combined = (str(label) + " " + str(value)).lower()
            if all(term in combined for term in GDP_SERIES_TERMS):
                matched_series.append((variable.get("code"), value))
            if any(term in combined for term in GDP_TOTAL_TERMS):
                matched_total.append((variable.get("code"), value))

    if len(matched_series) != 1:
        raise ValueError("Could not identify one unique real-GDP-at-2013-prices category.")
    if len(matched_total) != 1:
        raise ValueError("Could not identify one unique total-GDP category.")
    if matched_series[0][0] == matched_total[0][0]:
        raise ValueError("GSS GDP series and aggregate matched the same dimension.")

    selected = []
    for variable in variables:
        code = variable.get("code")
        if variable is time_variables[0]:
            selection = {"filter": "all", "values": ["*"]}
        elif code == matched_series[0][0]:
            selection = {"filter": "item", "values": [matched_series[0][1]]}
        elif code == matched_total[0][0]:
            selection = {"filter": "item", "values": [matched_total[0][1]]}
        else:
            values = variable.get("values", [])
            if len(values) != 1:
                raise ValueError(
                    "GSS table has an additional multi-valued dimension {!r}; "
                    "its intended GDP category must be specified explicitly.".format(code)
                )
            selection = {"filter": "item", "values": [values[0]]}
        selected.append({"code": code, "selection": selection})

    return {"query": selected, "response": {"format": "csv"}}


def _parse_pxweb_gdp_csv(payload: bytes) -> pd.DataFrame:
    """Convert a PxWeb CSV response to the repository's two-column GDP schema."""
    from io import BytesIO

    try:
        frame = pd.read_csv(BytesIO(payload))
    except Exception as exc:
        raise ValueError("GSS PxWeb response was not a readable CSV.") from exc
    if frame.empty or len(frame.columns) < 2:
        raise ValueError("GSS PxWeb response did not contain a GDP data table.")

    period_col = None
    for column in frame.columns:
        periods = frame[column].astype(str).str.extract(r"(\d{4}Q[1-4])", expand=False)
        if periods.notna().any():
            period_col = column
            break
    if period_col is None:
        raise ValueError("GSS PxWeb response did not contain quarterly period labels.")

    value_col = [column for column in frame.columns if column != period_col][-1]
    raw_periods = frame[period_col].astype(str)
    periods = raw_periods.str.extract(r"(\d{4}Q[1-4])", expand=False)
    status = raw_periods.map(
        lambda value: "provisional" if "**" in value else ("revised" if "*" in value else "unmarked")
    )
    values = pd.to_numeric(frame[value_col], errors="coerce")
    result = pd.DataFrame({
        "Name of Series": periods,
        "Gross Domestic Product (GDP), production, real": values,
        "Observation Status": status,
    }).dropna(subset=["Name of Series", "Gross Domestic Product (GDP), production, real"])
    result["Name of Series"] = result["Name of Series"].astype(str)
    result = result.drop_duplicates("Name of Series").sort_values("Name of Series")
    if len(result) < 8:
        raise ValueError("GSS PxWeb response contained fewer than eight valid quarterly GDP observations.")
    return result.reset_index(drop=True)


def fetch_gss_quarterly_gdp(api_url: str = None, timeout: int = 60) -> pd.DataFrame:
    """Retrieve quarterly real GDP using the GSS StatsBank PxWeb API."""
    if api_url is None:
        api_url = os.getenv("GSS_GDP_API_URL", DEFAULT_GSS_GDP_API_URL)
    if not api_url.startswith("https://"):
        raise ValueError("GSS StatsBank API URL must use HTTPS.")

    metadata_payload = _request_bytes(api_url, timeout=timeout)
    try:
        metadata = json.loads(metadata_payload.decode("utf-8"))
    except Exception as exc:
        raise ValueError("GSS PxWeb table metadata was not valid JSON.") from exc
    query = build_gss_gdp_query(metadata)
    payload = _request_bytes(api_url, data=json.dumps(query).encode("utf-8"), timeout=timeout)
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
                        "GSS GDP download is stale ({}) compared with the local file "
                        "({}); no file was changed.".format(incoming_latest, current_latest)
                    )
        except ValueError:
            raise
        except Exception:
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


def main() -> int:
    """Command-line entry point for a manual GSS GDP refresh."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch and update quarterly real GDP from GSS StatsBank."
    )
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--raw-data-path", default=None)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    try:
        result = update_gss_quarterly_gdp(
            raw_data_path=args.raw_data_path,
            api_url=args.api_url,
            timeout=args.timeout,
        )
    except Exception as exc:
        parser.exit(1, "GSS GDP refresh failed: {}\\n".format(exc))
    for key, value in result.items():
        print("{}: {}".format(key, value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
