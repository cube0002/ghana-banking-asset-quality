"""Load and prepare Ghana banking-sector data.

The source files combine monthly banking indicators with quarterly GDP.
Quarterly GDP is linearly interpolated to month-start dates for alignment;
these interpolated values are estimates, not observed monthly GDP.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np
import pandas as pd


def load_banking_data(raw_data_path: Optional[str] = None) -> pd.DataFrame:
    """Load the source CSV files and return a date-indexed monthly dataset.

    Parameters
    ----------
    raw_data_path:
        Directory containing data_first.csv and data_first2.csv.
        By default, the repository's data/raw directory is used.

    Returns
    -------
    pandas.DataFrame
        Monthly banking indicators joined to linearly interpolated monthly
        estimates of quarterly real GDP.

    Raises
    ------
    FileNotFoundError
        If either source file is missing.
    ValueError
        If expected date or GDP fields are absent or no dates overlap.
    """
    if raw_data_path is None:
        # loaders.py -> data -> ghana_banking -> src -> repository root
        raw_data_path = Path(__file__).resolve().parents[3] / "data" / "raw"
    else:
        raw_data_path = Path(raw_data_path)

    monthly_file = raw_data_path / "data_first.csv"
    gdp_file = raw_data_path / "data_first2.csv"

    if not monthly_file.is_file():
        raise FileNotFoundError(f"Monthly data file not found: {monthly_file}")
    if not gdp_file.is_file():
        raise FileNotFoundError(f"GDP data file not found: {gdp_file}")

    df_monthly = pd.read_csv(monthly_file)
    df_gdp = pd.read_csv(gdp_file)

    if "Name of Series" not in df_monthly.columns:
        raise ValueError("Monthly source is missing the Name of Series date column.")
    required_gdp = {"Name of Series", "Gross Domestic Product (GDP), production, real"}
    if not required_gdp.issubset(df_gdp.columns):
        raise ValueError("GDP source is missing its expected date or GDP column.")

    # Source files include metadata rows after observations. Parse dates and
    # retain valid observations instead of relying on fixed row counts.
    df_monthly["Date"] = pd.to_datetime(
        df_monthly["Name of Series"], format="%d/%m/%Y", errors="coerce"
    )
    df_monthly = df_monthly.loc[df_monthly["Date"].notna()].copy()

    df_gdp["Quarter"] = df_gdp["Name of Series"].astype(str).str.extract(
        r"(\d{4}Q[1-4])", expand=False
    )
    df_gdp = df_gdp.loc[df_gdp["Quarter"].notna()].copy()
    if df_gdp.empty:
        raise ValueError("No valid quarterly GDP observations were found.")

    df_monthly = df_monthly.drop(columns=["Name of Series"])
    for column in df_monthly.columns:
        if column != "Date":
            df_monthly[column] = pd.to_numeric(df_monthly[column], errors="coerce")

    df_gdp["Date"] = pd.PeriodIndex(df_gdp["Quarter"], freq="Q").to_timestamp()
    df_gdp["GDP_Real"] = pd.to_numeric(
        df_gdp["Gross Domestic Product (GDP), production, real"],
        errors="coerce",
    )
    df_gdp = (
        df_gdp.loc[df_gdp["GDP_Real"].notna(), ["Date", "GDP_Real"]]
        .sort_values("Date")
        .drop_duplicates("Date")
        .set_index("Date")
    )

    # This is a frequency-alignment convenience, not a temporal-
    # disaggregation model. Interpret monthly GDP values accordingly.
    gdp_monthly = (
        df_gdp.resample("MS")
        .interpolate(method="linear")
        .rename_axis("Date")
        .reset_index()
    )

    monthly = df_monthly.sort_values("Date").drop_duplicates("Date")
    master_df = monthly.merge(gdp_monthly, on="Date", how="inner")
    master_df = master_df.set_index("Date").sort_index()

    if master_df.empty:
        raise ValueError("No overlapping monthly banking and GDP dates were found.")

    return master_df


def load_quarterly_gdp(raw_data_path: Optional[str] = None) -> pd.DataFrame:
    """Load real GDP at its original quarterly frequency.

    Unlike ``load_banking_data``, this function does not interpolate GDP to
    monthly dates. It preserves the source frequency for quarterly analysis.

    Returns
    -------
    pandas.DataFrame
        A one-column dataframe indexed by a quarterly PeriodIndex.
    """
    if raw_data_path is None:
        raw_data_path = Path(__file__).resolve().parents[3] / "data" / "raw"
    else:
        raw_data_path = Path(raw_data_path)

    gdp_file = raw_data_path / "data_first2.csv"
    if not gdp_file.is_file():
        raise FileNotFoundError(f"GDP data file not found: {gdp_file}")

    source = pd.read_csv(gdp_file)
    required = {
        "Name of Series",
        "Gross Domestic Product (GDP), production, real",
    }
    if not required.issubset(source.columns):
        raise ValueError("GDP source is missing its expected date or GDP column.")

    quarters = source["Name of Series"].astype(str).str.extract(
        r"(\\d{4}Q[1-4])", expand=False
    )
    values = pd.to_numeric(
        source["Gross Domestic Product (GDP), production, real"],
        errors="coerce",
    )
    result = pd.DataFrame({"Quarter": quarters, "GDP_Real": values})
    result = result.dropna(subset=["Quarter", "GDP_Real"])
    result["Quarter"] = pd.PeriodIndex(result["Quarter"], freq="Q")
    result = result.sort_values("Quarter").drop_duplicates("Quarter")
    return result.set_index("Quarter")[["GDP_Real"]]


def interpolate_quarterly_to_monthly(
    quarterly_series: pd.Series,
    method: str = "linear",
) -> pd.Series:
    """Interpolate a quarterly series to month-start frequency.

    Values between quarterly observations are estimates, not observed
    monthly measurements.
    """
    series = quarterly_series.copy()
    if isinstance(series.index, pd.PeriodIndex):
        series.index = series.index.to_timestamp()
    return series.resample("MS").interpolate(method=method)


def handle_missing_values(
    df: pd.DataFrame, method: str = "forward_fill"
) -> pd.DataFrame:
    """Handle missing values using forward fill, backward fill or interpolation."""
    df_copy = df.copy()

    if method == "forward_fill":
        df_copy = df_copy.ffill()
    elif method == "backward_fill":
        df_copy = df_copy.bfill()
    elif method == "interpolate":
        df_copy = df_copy.interpolate(method="linear")
    else:
        raise ValueError(f"Unknown method: {method}")

    return df_copy.dropna()


def standardize_features(
    df: pd.DataFrame,
    cols: Optional[list] = None,
    return_params: bool = False,
) -> Union[Tuple[pd.DataFrame, dict], pd.DataFrame]:
    """Z-score selected numeric columns.

    For predictive evaluation, estimate scaling parameters on the training
    sample only and apply those parameters to held-out observations.
    """
    df_std = df.copy()
    if cols is None:
        cols = df.select_dtypes(include=["number"]).columns.tolist()

    scaling_params = {}
    for col in cols:
        if col not in df_std.columns:
            raise ValueError(f"Column not found: {col}")
        if not pd.api.types.is_numeric_dtype(df_std[col]):
            raise TypeError(f"Column is not numeric: {col}")

        mean_val = df_std[col].mean()
        std_val = df_std[col].std()
        if pd.isna(std_val) or std_val == 0:
            raise ValueError(f"Cannot standardize constant or empty column: {col}")

        df_std[col] = (df_std[col] - mean_val) / std_val
        scaling_params[col] = {"mean": mean_val, "std": std_val}

    if return_params:
        return df_std, scaling_params
    return df_std


def validate_data(df: pd.DataFrame) -> bool:
    """Check required columns, minimum sample length and missingness."""
    required_cols = [
        "Non Performing Loan Ratio",
        "Monetary Policy Rate (%)",
        "GDP_Real",
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    if len(df) < 12:
        raise ValueError(f"Insufficient data points: {len(df)} < 12")
    if df.empty or df.shape[1] == 0:
        raise ValueError("Dataframe is empty.")

    na_ratio = df.isna().sum().sum() / (df.shape[0] * df.shape[1])
    if na_ratio > 0.1:
        raise ValueError(f"Too many missing values: {na_ratio:.1%}")
    return True
