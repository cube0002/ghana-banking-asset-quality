"""Load and prepare Ghana banking sector data.
from __future__ import annotations
Combines monthly banking indicators from BoG with quarterly GDP from GSS.
The tricky part: GDP is quarterly, everything else is monthly. We interpolate
GDP to get a consistent monthly dataset.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Optional


def load_banking_data(raw_data_path: Optional[str] = None) -> pd.DataFrame:
    """Load banking and macroeconomic data, aligned to monthly frequency.
    
    Reads the raw BoG/GSS CSV files and returns a clean monthly time series
    with NPL ratio, policy rate, CPI, exchange rate, and GDP.
    
    The quarterly GDP gets interpolated to monthly using linear interpolation
    to match the other monthly indicators.
    
    Args:
        raw_data_path: Where the CSV files live. Defaults to ../data/raw/
    
    Returns:
        DataFrame indexed by date with all variables ready to use.
    
    Raises:
        FileNotFoundError: If data_first.csv or data_first2.csv are missing.
        ValueError: If required columns don't exist in the data.
    
    Example:
        df = load_banking_data()
        print(df.shape)  # (192, 8) - 192 months, 8 variables
        print(df['Non Performing Loan Ratio'].describe())
    """
    if raw_data_path is None:
        raw_data_path = Path(__file__).parent.parent.parent.parent / "data" / "raw"
    else:
        raw_data_path = Path(raw_data_path)
    
    # Load raw files
    monthly_file = raw_data_path / "data_first.csv"
    gdp_file = raw_data_path / "data_first2.csv"
    
    if not monthly_file.exists():
        raise FileNotFoundError(f"Monthly data file not found: {monthly_file}")
    if not gdp_file.exists():
        raise FileNotFoundError(f"GDP data file not found: {gdp_file}")
    
    # Load monthly banking data
    df_monthly = pd.read_csv(monthly_file)
    df_gdp = pd.read_csv(gdp_file)
    
    # Clean data - remove footer rows
    df_monthly_clean = df_monthly.iloc[:192].copy()
    df_gdp_clean = df_gdp.iloc[:79].copy()
    
    # Convert date columns
    df_monthly_clean['Date'] = pd.to_datetime(df_monthly_clean['Name of Series'], format='%d/%m/%Y')
    df_gdp_clean['Date'] = pd.PeriodIndex(df_gdp_clean['Name of Series'], freq='Q').to_timestamp()
    
    # Convert text columns to numeric
    cols_to_fix = [col for col in df_monthly_clean.columns if col not in ['Name of Series', 'Date']]
    for col in cols_to_fix:
        df_monthly_clean[col] = pd.to_numeric(df_monthly_clean[col], errors='coerce')
    
    # Extract GDP column
    df_gdp_clean['GDP_Real'] = pd.to_numeric(
        df_gdp_clean['Gross Domestic Product (GDP), production, real'], 
        errors='coerce'
    )
    
    # Interpolate quarterly to monthly
    df_gdp_clean = df_gdp_clean.set_index('Date')
    df_gdp_monthly = df_gdp_clean[['GDP_Real']].resample('MS').interpolate(method='linear')
    df_gdp_monthly = df_gdp_monthly.reset_index()
    
    # Merge datasets
    master_df = pd.merge(
        df_monthly_clean.drop(columns=['Name of Series']),
        df_gdp_monthly,
        on='Date',
        how='inner'
    )
    
    # Set date as index and sort
    master_df['Date'] = pd.to_datetime(master_df['Date'])
    master_df = master_df.set_index('Date').sort_index()
    
    return master_df


def interpolate_quarterly_to_monthly(
    quarterly_series: pd.Series,
    method: str = 'linear'
) -> pd.Series:
    """Convert quarterly data to monthly by interpolating in between.
    
    Simple linear interpolation between quarterly data points. Useful for
    matching quarterly GDP to monthly banking indicators.
    
    Args:
        quarterly_series: Series with quarterly frequency
        method: How to interpolate ('linear' works best for economics)
    
    Returns:
        Series resampled to monthly frequency
    
    Example:
        q_gdp = pd.Series([100, 105, 110], 
                         index=pd.PeriodIndex(['2020Q1', '2020Q2', '2020Q3'], freq='Q'))
        m_gdp = interpolate_quarterly_to_monthly(q_gdp)
        # Now you have monthly estimates like 100.0, 101.7, 103.3, 105.0, ...
    """
    if isinstance(quarterly_series.index, pd.PeriodIndex):
        quarterly_series.index = quarterly_series.index.to_timestamp()
    
    resampled = quarterly_series.resample('MS').interpolate(method=method)
    return resampled


def handle_missing_values(df: pd.DataFrame, method: str = 'forward_fill') -> pd.DataFrame:
    """Fill in missing values in time series data.
    
    Args:
        df: DataFrame with NaN values
        method: 'forward_fill' (repeat last value), 'backward_fill' (use next value),
                or 'interpolate' (linear fill between points)
    
    Returns:
        DataFrame with NaN values handled
    
    Example:
        df = pd.DataFrame({'NPL': [10, np.nan, 12], 'Rate': [20, 21, np.nan]})
        df_clean = handle_missing_values(df, method='forward_fill')
        # NPL: [10, 10, 12], Rate: [20, 21, 21]
    """
    df_copy = df.copy()
    
    if method == 'forward_fill':
         df_copy = df_copy.ffill()
    elif method == 'backward_fill':
        df_copy = df_copy.bfill()
    elif method == 'interpolate':
        df_copy = df_copy.interpolate(method='linear')
    else:
        raise ValueError(f"Unknown method: {method}")
    
    # Drop any remaining NaN values
    df_copy = df_copy.dropna()
    
    return df_copy


def standardize_features(
    df: pd.DataFrame,
    cols: Optional[list] = None,
    return_params: bool = False
) -> Tuple[pd.DataFrame, dict] | pd.DataFrame:
    """Normalize variables to mean=0, std=1 (Z-score standardization).
    
    Useful before feeding into models that are sensitive to scale 
    (like sklearn's algorithms). Statsmodels is more forgiving.
    
    Args:
        df: Input data
        cols: Which columns to standardize. If None, does all numeric columns.
        return_params: If True, also return the mean/std used for inverse transform
    
    Returns:
        Standardized dataframe, optionally with scaling parameters
    
    Example:
        df_std = standardize_features(df, cols=['NPL', 'Rate'])
        # NPL now has mean~0 and std~1
    """
    df_std = df.copy()
    
    if cols is None:
        cols = df.select_dtypes(include=['number']).columns.tolist()
    
    scaling_params = {}
    
    for col in cols:
        if col in df_std.columns:
            mean_val = df_std[col].mean()
            std_val = df_std[col].std()
            df_std[col] = (df_std[col] - mean_val) / std_val
            scaling_params[col] = {'mean': mean_val, 'std': std_val}
    
    if return_params:
        return df_std, scaling_params
    else:
        return df_std


def validate_data(df: pd.DataFrame) -> bool:
    """Quick sanity check on the data before running analysis.
    
    Checks for:
    - Required columns exist
    - Enough data points (at least 12 months)
    - Not too many NaNs (>10% is suspicious)
    
    Args:
        df: Data to validate
    
    Returns:
        True if all checks pass
    
    Raises:
        ValueError: If something looks wrong
    
    Example:
        try:
            validate_data(df)
            print("Data looks good!")
        except ValueError as e:
            print(f"Problem: {e}")
    """
    # Check required columns
    required_cols = [
        'Non Performing Loan Ratio',
        'Monetary Policy Rate (%)',
        'GDP_Real'
    ]
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Check for sufficient data
    if len(df) < 12:
        raise ValueError(f"Insufficient data points: {len(df)} < 12")
    
    # Check for excessive missing data
    na_ratio = df.isna().sum().sum() / (df.shape[0] * df.shape[1])
    if na_ratio > 0.1:
        raise ValueError(f"Too many missing values: {na_ratio:.1%}")
    
    return True
