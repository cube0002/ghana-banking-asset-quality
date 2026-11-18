"""Bank of Ghana financial soundness data via the official GSS StatsBank mirror.

The GSS PxWeb table identifies the Bank of Ghana as the original data source.
This connector keeps the provider's monthly indicator observations in a
separate long-format file and does not overwrite the project's existing
Bank of Ghana monthly macroeconomic source file.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Dict
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd


_BOG_FSI_TABLE_PATH = "Search Bar/-/financial_sector_soundness.px"
FSI_INDICATOR_LABELS = {
    "CAR": "Capital Adequacy Ratio",
    "CDR": "Credit to Deposits",
    "CLASTL": "Core Liquid Assets to Short-term Liabilities",
    "CLATA": "Core Liquid Assets to Total Assets",
    "NPL": "Non-Performing Loans",
    "OC_I": "Operational Cost/Income",
    "ROA": "Return on Assets - Before Tax",
    "ROE": "Return on Equity - After Tax",
    "TCGIR": "Total Cost to Gross Income Ratio",
}


DEFAULT_BOG_FSI_API_URL = (
    "https://statsbank.statsghana.gov.gh:443/api/v1/en/"
    + quote(_BOG_FSI_TABLE_PATH, safe="/")
)


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
        raise RuntimeError("Bank of Ghana FSI StatsBank request failed: {}".format(exc)) from exc
    if not payload:
        raise ValueError("Bank of Ghana FSI StatsBank returned an empty response.")
    return payload


def build_bog_fsi_query(metadata: Dict) -> Dict:
    """Select all months and all indicators from the FSI table metadata."""
    variables = metadata.get("variables", [])
    if not variables:
        raise ValueError("Bank of Ghana FSI table metadata contains no variables.")

    time_variables = [variable for variable in variables if variable.get("time")]
    if len(time_variables) != 1:
        raise ValueError("Could not identify exactly one monthly time dimension.")

    indicator_variables = []
    for variable in variables:
        if variable is time_variables[0]:
            continue
        values = [str(value).strip().upper() for value in variable.get("values", [])]
        labels = [str(value).strip().upper() for value in variable.get("valueTexts", [])]
        available_codes = set(values) | set(labels)
        if {"CAR", "NPL", "ROA"}.issubset(available_codes):
            indicator_variables.append(variable)
    if len(indicator_variables) != 1:
        raise ValueError("Could not identify the unique financial-soundness indicator dimension.")
    indicator = indicator_variables[0]

    query = []
    for variable in variables:
        code = variable.get("code")
        if variable is time_variables[0]:
            selection = {"filter": "all", "values": ["*"]}
        elif variable is indicator:
            selection = {"filter": "all", "values": ["*"]}
        else:
            values = variable.get("values", [])
            if len(values) != 1:
                raise ValueError(
                    "Unexpected multi-valued dimension {!r} in the FSI table.".format(code)
                )
            selection = {"filter": "item", "values": [values[0]]}
        query.append({"code": code, "selection": selection})

    return {"query": query, "response": {"format": "csv"}}


def _parse_bog_fsi_csv(payload: bytes) -> pd.DataFrame:
    """Normalise the FSI PxWeb CSV to month, indicator and value columns."""
    from io import BytesIO

    try:
        frame = pd.read_csv(BytesIO(payload))
    except Exception as exc:
        raise ValueError("Bank of Ghana FSI response was not a readable CSV.") from exc
    if frame.empty or len(frame.columns) < 3:
        raise ValueError("Bank of Ghana FSI response did not contain a data table.")

    month_col = None
    indicator_col = None
    for column in frame.columns:
        if frame[column].astype(str).str.contains(r"\d{4}M\d{2}", regex=True).any():
            month_col = column
            break
    if month_col is None:
        raise ValueError("Could not identify month column in FSI response.")

    # PxWeb CSVs may be parsed with pandas' dedicated string dtype rather
    # than NumPy object dtype. Identify the categorical indicator column by
    # excluding the month field and columns that are fully numeric.
    categorical_columns = []
    for column in frame.columns:
        if column == month_col:
            continue
        converted = pd.to_numeric(frame[column], errors="coerce")
        if converted.notna().sum() < frame[column].notna().sum():
            categorical_columns.append(column)

    if len(categorical_columns) != 1:
        raise ValueError("Could not identify a unique indicator column in FSI response.")
    indicator_col = categorical_columns[0]

    value_columns = [
        column for column in frame.columns
        if column not in (month_col, indicator_col)
    ]
    if len(value_columns) != 1:
        raise ValueError("Expected exactly one numeric value column in FSI response.")
    value_col = value_columns[0]

    raw_indicators = frame[indicator_col].astype(str).str.strip()

    def identify_indicator_code(value: str) -> str:
        upper_value = value.upper()
        if upper_value in FSI_INDICATOR_LABELS:
            return upper_value
        normalized_value = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
        for code, label in FSI_INDICATOR_LABELS.items():
            normalized_label = re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()
            if normalized_value == normalized_label or normalized_value.startswith(normalized_label + " "):
                return code
        return ""

    indicator_codes = raw_indicators.map(identify_indicator_code)
    canonical_labels = raw_indicators.copy()
    for code, label in FSI_INDICATOR_LABELS.items():
        canonical_labels = canonical_labels.mask(indicator_codes == code, label)

    result = pd.DataFrame({
        "Month": frame[month_col].astype(str).str.extract(r"(\\d{4}M\\d{2})", expand=False),
        "Indicator Code": indicator_codes,
        "Indicator": canonical_labels,
        "Value": pd.to_numeric(frame[value_col], errors="coerce"),
    }).dropna(subset=["Month", "Value"])
    result = result[result["Indicator"].str.strip() != ""]
    if result.duplicated(["Month", "Indicator"]).any():
        raise ValueError("FSI response contains duplicate month-indicator observations.")

    normalized_indicators = {
        re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
        for value in result["Indicator"].unique()
    }
    required_prefixes = {
        "capital adequacy ratio": lambda value: value.startswith("capital adequacy ratio"),
        "non performing loans": lambda value: value.startswith("non performing loan"),
        "return on assets": lambda value: value.startswith("return on assets"),
    }
    missing = [
        label for label, matches in required_prefixes.items()
        if not any(matches(value) for value in normalized_indicators)
    ]
    if missing:
        raise ValueError(
            "FSI response is missing required core indicators: {}".format(missing)
        )

    result = result.sort_values(["Month", "Indicator"])
    if result["Month"].nunique() < 12:
        raise ValueError("FSI response contained fewer than twelve distinct monthly observations.")
    return result.reset_index(drop=True)


def fetch_bog_financial_soundness(
    api_url: str = None, timeout: int = 60
) -> pd.DataFrame:
    """Fetch all monthly Bank of Ghana financial soundness indicators."""
    if api_url is None:
        api_url = os.getenv("BOG_FSI_API_URL", DEFAULT_BOG_FSI_API_URL)
    if not api_url.startswith("https://"):
        raise ValueError("Bank of Ghana FSI API URL must use HTTPS.")
    metadata_payload = _request_bytes(api_url, timeout=timeout)
    try:
        metadata = json.loads(metadata_payload.decode("utf-8"))
    except Exception as exc:
        raise ValueError("FSI table metadata was not valid JSON.") from exc
    query = build_bog_fsi_query(metadata)
    payload = _request_bytes(
        api_url, data=json.dumps(query).encode("utf-8"), timeout=timeout
    )
    return _parse_bog_fsi_csv(payload)


def update_bog_financial_soundness(
    raw_data_path: str = None, api_url: str = None, timeout: int = 60
) -> Dict[str, str]:
    """Atomically save FSI data separately, preserving existing source files."""
    if raw_data_path is None:
        raw_data_path = Path(__file__).resolve().parents[3] / "data" / "raw"
    else:
        raw_data_path = Path(raw_data_path)
    raw_data_path.mkdir(parents=True, exist_ok=True)

    frame = fetch_bog_financial_soundness(api_url=api_url, timeout=timeout)
    destination = raw_data_path / "bog_financial_soundness.csv"

    if destination.exists():
        current = pd.read_csv(destination)
        if {"Month", "Indicator"}.issubset(current.columns):
            old_latest = current["Month"].astype(str).max()
            new_latest = frame["Month"].max()
            if new_latest < old_latest:
                raise ValueError(
                    "FSI download is stale ({} vs local {}); no file was changed.".format(
                        new_latest, old_latest
                    )
                )

    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=str(raw_data_path),
            prefix="bog_financial_soundness.csv.", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            frame.to_csv(handle, index=False)
        os.replace(str(temporary), str(destination))
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()

    return {
        "source": "Bank of Ghana via Ghana Statistical Service StatsBank",
        "latest_month": frame["Month"].max(),
        "indicators": str(frame["Indicator"].nunique()),
        "observations": str(len(frame)),
        "file": str(destination),
    }


def main() -> int:
    """Manual command-line refresh for Bank of Ghana FSI data."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch monthly Bank of Ghana financial soundness indicators."
    )
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--raw-data-path", default=None)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    try:
        result = update_bog_financial_soundness(
            raw_data_path=args.raw_data_path,
            api_url=args.api_url,
            timeout=args.timeout,
        )
    except Exception as exc:
        parser.exit(1, "Bank of Ghana FSI refresh failed: {}\n".format(exc))
    for key, value in result.items():
        print("{}: {}".format(key, value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
