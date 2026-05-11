"""Tests for data loading and preprocessing modules."""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ghana_banking.data.loaders import (
    load_banking_data,
    handle_missing_values,
    standardize_features,
    interpolate_quarterly_to_monthly,
    validate_data
)


class TestLoadBankingData:
    """Tests for load_banking_data function."""
    
    def test_load_banking_data_returns_dataframe(self):
        """Test that load_banking_data returns a pandas DataFrame."""
        df = load_banking_data()
        assert isinstance(df, pd.DataFrame)
    
    def test_load_banking_data_has_data(self):
        """Test that loaded data is not empty."""
        df = load_banking_data()
        assert len(df) > 0
        assert df.shape[1] > 0
    
    def test_load_banking_data_has_date_index(self):
        """Test that index is DatetimeIndex."""
        df = load_banking_data()
        assert isinstance(df.index, pd.DatetimeIndex)
    
    def test_load_banking_data_has_npl_column(self):
        """Test that NPL ratio column exists."""
        df = load_banking_data()
        assert 'Non Performing Loan Ratio' in df.columns
    
    def test_load_banking_data_has_gdp_column(self):
        """Test that GDP column exists."""
        df = load_banking_data()
        assert 'GDP_Real' in df.columns
    
    def test_load_banking_data_no_duplicates(self):
        """Test that there are no duplicate dates."""
        df = load_banking_data()
        assert not df.index.duplicated().any()
    
    def test_load_banking_data_sorted_index(self):
        """Test that data is sorted by date."""
        df = load_banking_data()
        assert df.index.is_monotonic_increasing


class TestHandleMissingValues:
    """Tests for handle_missing_values function."""
    
    @pytest.fixture
    def df_with_nans(self):
        """Create a test dataframe with missing values."""
        df = pd.DataFrame({
            'A': [1.0, 2.0, np.nan, 4.0, 5.0],
            'B': [10.0, np.nan, 30.0, 40.0, 50.0],
            'C': [100.0, 200.0, 300.0, 400.0, 500.0]
        })
        return df
    
    def test_forward_fill_removes_nans(self, df_with_nans):
        """Test forward fill removes NaN values."""
        result = handle_missing_values(df_with_nans, method='forward_fill')
        assert result.isna().sum().sum() == 0
    
    def test_interpolate_removes_nans(self, df_with_nans):
        """Test interpolation removes NaN values."""
        result = handle_missing_values(df_with_nans, method='interpolate')
        assert result.isna().sum().sum() == 0
    
    def test_invalid_method_raises_error(self, df_with_nans):
        """Test that invalid method raises ValueError."""
        with pytest.raises(ValueError):
            handle_missing_values(df_with_nans, method='invalid_method')


class TestStandardizeFeatures:
    """Tests for standardize_features function."""
    
    @pytest.fixture
    def df_for_scaling(self):
        """Create a test dataframe."""
        np.random.seed(42)
        return pd.DataFrame({
            'X': np.random.randn(100) * 10 + 50,
            'Y': np.random.randn(100) * 5 + 100,
            'Z': np.random.randn(100) * 2 + 10
        })
    
    def test_standardize_returns_dataframe(self, df_for_scaling):
        """Test that standardize_features returns a DataFrame."""
        result = standardize_features(df_for_scaling, cols=['X', 'Y'])
        assert isinstance(result, pd.DataFrame)
    
    def test_standardize_zero_mean(self, df_for_scaling):
        """Test that standardized data has mean near 0."""
        result = standardize_features(df_for_scaling, cols=['X', 'Y'])
        means = result[['X', 'Y']].mean()
        assert np.allclose(means, 0, atol=1e-10)
    
    def test_standardize_unit_variance(self, df_for_scaling):
        """Test that standardized data has variance near 1."""
        result = standardize_features(df_for_scaling, cols=['X', 'Y'])
        stds = result[['X', 'Y']].std()
        assert np.allclose(stds, 1, atol=1e-10)
    
    def test_standardize_with_params(self, df_for_scaling):
        """Test that standardize returns scaling parameters when requested."""
        result, params = standardize_features(
            df_for_scaling,
            cols=['X', 'Y'],
            return_params=True
        )
        assert isinstance(params, dict)
        assert 'X' in params
        assert 'Y' in params
        assert 'mean' in params['X']
        assert 'std' in params['X']


class TestInterpolateQuarterlyToMonthly:
    """Tests for interpolate_quarterly_to_monthly function."""
    
    def test_interpolation_increases_frequency(self):
        """Test that interpolation increases data points."""
        quarterly = pd.Series(
            [100, 110, 120],
            index=pd.PeriodIndex(['2020Q1', '2020Q2', '2020Q3'], freq='Q')
        )
        monthly = interpolate_quarterly_to_monthly(quarterly)
        assert len(monthly) > len(quarterly)
    
    def test_interpolation_preserves_original_points(self):
        """Test that original quarterly values are preserved."""
        quarterly = pd.Series(
            [100.0, 110.0, 120.0],
            index=pd.PeriodIndex(['2020Q1', '2020Q2', '2020Q3'], freq='Q')
        )
        monthly = interpolate_quarterly_to_monthly(quarterly)
        # Check that values are close to original at quarterly dates
        assert monthly.iloc[0] == 100.0
        assert monthly.iloc[-1] == 120.0


class TestValidateData:
    """Tests for validate_data function."""
    
    @pytest.fixture
    def valid_df(self):
        """Create a valid test dataframe."""
        dates = pd.date_range('2020-01-01', periods=100, freq='MS')
        return pd.DataFrame({
            'Non Performing Loan Ratio': np.random.uniform(10, 25, 100),
            'Monetary Policy Rate (%)': np.random.uniform(15, 35, 100),
            'GDP_Real': np.random.uniform(1000, 2000, 100),
            'Other': np.random.uniform(0, 100, 100)
        }, index=dates)
    
    def test_valid_data_passes(self, valid_df):
        """Test that valid data passes validation."""
        assert validate_data(valid_df) is True
    
    def test_missing_columns_raises_error(self, valid_df):
        """Test that missing required columns raise error."""
        df_bad = valid_df.drop('GDP_Real', axis=1)
        with pytest.raises(ValueError):
            validate_data(df_bad)
    
    def test_insufficient_data_raises_error(self):
        """Test that insufficient data raises error."""
        dates = pd.date_range('2020-01-01', periods=5, freq='MS')
        df_small = pd.DataFrame({
            'Non Performing Loan Ratio': [1, 2, 3, 4, 5],
            'Monetary Policy Rate (%)': [1, 2, 3, 4, 5],
            'GDP_Real': [1, 2, 3, 4, 5]
        }, index=dates)
        with pytest.raises(ValueError):
            validate_data(df_small)
    
    def test_excessive_missing_values_raises_error(self, valid_df):
        """Test that excessive NaN raises error."""
        df_bad = valid_df.copy()
        df_bad.iloc[:80, :] = np.nan
        with pytest.raises(ValueError):
            validate_data(df_bad)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
