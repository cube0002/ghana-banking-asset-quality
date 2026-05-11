"""Test fixtures and configuration."""

import pytest
import numpy as np
import pandas as pd

@pytest.fixture
def sample_timeseries():
    """Create sample time series data for testing."""
    np.random.seed(42)
    n = 100
    return pd.DataFrame({
        "NPL_Ratio": np.random.uniform(10, 25, n),
        "Policy_Rate": np.random.uniform(15, 35, n),
        "CPI": np.random.uniform(100, 150, n),
        "USD_GHS": np.random.uniform(5, 15, n),
    })
