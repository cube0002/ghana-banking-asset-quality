"""Tests for modeling modules."""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ghana_banking.modeling.regression import OLSModel
from ghana_banking.modeling.var_model import VARModel
from ghana_banking.modeling.stress_test import StressTest


@pytest.fixture
def sample_timeseries():
    """Create sample time series data for testing."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range('2015-01-01', periods=n, freq='MS')
    return pd.DataFrame({
        'Date': dates,
        'Non Performing Loan Ratio': np.random.uniform(10, 25, n),
        'Monetary Policy Rate (%)': np.random.uniform(15, 35, n),
        'CPI': np.random.uniform(100, 150, n),
        'USD_GHS': np.random.uniform(5, 15, n),
        'GDP_Real': np.random.uniform(1000, 2000, n),
    }).set_index('Date')


class TestOLSModel:
    """Tests for OLSModel class."""
    
    def test_ols_model_fit(self, sample_timeseries):
        """Test that OLS model fits successfully."""
        model = OLSModel()
        model.fit(
            sample_timeseries,
            'Non Performing Loan Ratio',
            ['Monetary Policy Rate (%)', 'CPI', 'USD_GHS']
        )
        assert model.results is not None
    
    def test_ols_model_predict(self, sample_timeseries):
        """Test that OLS model makes predictions."""
        model = OLSModel()
        model.fit(
            sample_timeseries,
            'Non Performing Loan Ratio',
            ['Monetary Policy Rate (%)', 'CPI']
        )
        predictions = model.predict(sample_timeseries)
        assert len(predictions) > 0
        assert predictions.shape == (len(sample_timeseries),)
    
    def test_ols_model_summary(self, sample_timeseries):
        """Test that OLS model summary works."""
        model = OLSModel()
        model.fit(
            sample_timeseries,
            'Non Performing Loan Ratio',
            ['Monetary Policy Rate (%)']
        )
        summary = model.summary()
        assert isinstance(summary, str)
        assert 'OLS' in summary or 'Regression' in summary
    
    def test_ols_model_diagnostics(self, sample_timeseries):
        """Test that OLS model diagnostics work."""
        model = OLSModel()
        model.fit(
            sample_timeseries,
            'Non Performing Loan Ratio',
            ['Monetary Policy Rate (%)']
        )
        diags = model.get_diagnostics()
        assert isinstance(diags, dict)
        assert 'r_squared' in diags
        assert 'aic' in diags
    
    def test_ols_model_coefficients(self, sample_timeseries):
        """Test that OLS model returns coefficients."""
        model = OLSModel()
        model.fit(
            sample_timeseries,
            'Non Performing Loan Ratio',
            ['Monetary Policy Rate (%)', 'CPI']
        )
        coefs = model.get_coefficients()
        assert isinstance(coefs, pd.DataFrame)
        assert 'Coefficient' in coefs.columns
        assert len(coefs) > 0
    
    def test_ols_model_residuals(self, sample_timeseries):
        """Test that OLS model returns residuals."""
        model = OLSModel()
        model.fit(
            sample_timeseries,
            'Non Performing Loan Ratio',
            ['Monetary Policy Rate (%)']
        )
        residuals = model.get_residuals()
        assert len(residuals) > 0
    
    def test_ols_model_error_unfitted(self):
        """Test that unfitted model raises error."""
        model = OLSModel()
        with pytest.raises(ValueError):
            model.summary()
    
    def test_ols_model_error_missing_columns(self, sample_timeseries):
        """Test that missing columns raise error."""
        model = OLSModel()
        with pytest.raises(ValueError):
            model.fit(
                sample_timeseries,
                'NonExistent',
                ['Monetary Policy Rate (%)']
            )


class TestVARModel:
    """Tests for VARModel class."""
    
    def test_var_model_fit(self, sample_timeseries):
        """Test that VAR model fits successfully."""
        model = VARModel(lags=2)
        data = sample_timeseries[['Non Performing Loan Ratio', 'Monetary Policy Rate (%)', 'GDP_Real']]
        model.fit(data, use_diff=True)
        assert model.results is not None
    
    def test_var_model_impulse_responses(self, sample_timeseries):
        """Test that VAR model calculates IRF."""
        model = VARModel(lags=2)
        data = sample_timeseries[['Non Performing Loan Ratio', 'Monetary Policy Rate (%)', 'GDP_Real']]
        model.fit(data, use_diff=True)
        irf = model.impulse_responses(periods=6)
        assert irf.irfs.shape[0] == 7  # periods + 1
        assert irf.irfs.shape[1] == 3  # n variables
        assert irf.irfs.shape[2] == 3  # n variables
    
    def test_var_model_forecast(self, sample_timeseries):
        """Test that VAR model forecasts."""
        model = VARModel(lags=2)
        data = sample_timeseries[['Non Performing Loan Ratio', 'Monetary Policy Rate (%)', 'GDP_Real']]
        model.fit(data.diff().dropna(), use_diff=False)
        
        # Get last 2 observations for forecast
        last_obs = data.diff().dropna().iloc[-2:]
        forecast = model.forecast(last_obs, steps=3)
        
        assert isinstance(forecast, pd.DataFrame)
        assert len(forecast) == 3
    
    def test_var_model_diagnostics(self, sample_timeseries):
        """Test stability and residual diagnostic output."""
        model = VARModel(lags=2)
        data = sample_timeseries[
            ['Non Performing Loan Ratio', 'Monetary Policy Rate (%)', 'GDP_Real']
        ]
        model.fit(data, use_diff=True)

        diagnostics = model.get_diagnostics(whiteness_lags=4)

        assert isinstance(diagnostics['stable'], bool)
        assert diagnostics['whiteness_lags'] == 4
        assert 0 <= diagnostics['whiteness_pvalue'] <= 1
        assert 0 <= diagnostics['normality_pvalue'] <= 1

    def test_var_model_diagnostics_reject_invalid_lags(self, sample_timeseries):
        """Whiteness test lag count must exceed the fitted VAR order."""
        model = VARModel(lags=2)
        data = sample_timeseries[
            ['Non Performing Loan Ratio', 'Monetary Policy Rate (%)', 'GDP_Real']
        ]
        model.fit(data, use_diff=True)

        with pytest.raises(ValueError):
            model.get_diagnostics(whiteness_lags=2)

    def test_var_model_forecast_rejects_wrong_lag_count(self, sample_timeseries):
        """Forecast input must contain exactly the fitted lag count."""
        model = VARModel(lags=2)
        data = sample_timeseries[
            ['Non Performing Loan Ratio', 'Monetary Policy Rate (%)', 'GDP_Real']
        ]
        model.fit(data, use_diff=True)

        with pytest.raises(ValueError, match="exactly 2 rows"):
            model.forecast(data.diff().dropna().iloc[-1:], steps=3)

    def test_var_model_forecast_rejects_wrong_column_order(self, sample_timeseries):
        """Forecast input columns must match the fitted variable order."""
        model = VARModel(lags=2)
        data = sample_timeseries[
            ['Non Performing Loan Ratio', 'Monetary Policy Rate (%)', 'GDP_Real']
        ]
        model.fit(data, use_diff=True)
        last_diff = data.diff().dropna().iloc[-2:][
            ['GDP_Real', 'Monetary Policy Rate (%)', 'Non Performing Loan Ratio']
        ]

        with pytest.raises(ValueError, match="columns and order"):
            model.forecast(last_diff, steps=3)

    def test_var_model_invalid_lag_order(self):
        """A VAR must have a positive lag order."""
        with pytest.raises(ValueError):
            VARModel(lags=0)

    def test_var_model_summary(self, sample_timeseries):
        """Test that VAR model summary works."""
        model = VARModel(lags=2)
        data = sample_timeseries[['Non Performing Loan Ratio', 'Monetary Policy Rate (%)', 'GDP_Real']]
        model.fit(data, use_diff=True)
        summary = model.summary()
        assert isinstance(summary, str)
    
    def test_var_model_lag_order(self, sample_timeseries):
        """Test that VAR model determines lag order."""
        model = VARModel(lags=2)
        data = sample_timeseries[['Non Performing Loan Ratio', 'Monetary Policy Rate (%)', 'GDP_Real']]
        model.fit(data, use_diff=True)
        lag_order = model.get_lag_order(maxlags=4)
        assert isinstance(lag_order, dict)
        assert 'aic' in lag_order
    
    def test_var_model_error_insufficient_data(self):
        """Test that insufficient data raises error."""
        model = VARModel(lags=5)
        df_small = pd.DataFrame({
            'A': [1, 2, 3, 4],
            'B': [1, 2, 3, 4]
        })
        with pytest.raises(ValueError):
            model.fit(df_small, use_diff=True)


class TestStressTest:
    """Tests for StressTest class."""
    
    def test_stress_test_init(self, sample_timeseries):
        """Test that StressTest initializes correctly."""
        stress_test = StressTest(
            sample_timeseries,
            'Non Performing Loan Ratio',
            ['Monetary Policy Rate (%)', 'CPI', 'USD_GHS']
        )
        assert stress_test.target_var == 'Non Performing Loan Ratio'
        assert len(stress_test.feature_names) == 3
    
    def test_stress_test_run_scenario(self, sample_timeseries):
        """Test that StressTest runs single scenario."""
        stress_test = StressTest(
            sample_timeseries,
            'Non Performing Loan Ratio',
            ['Monetary Policy Rate (%)', 'CPI']
        )
        scenario = {
            'Monetary Policy Rate (%)': 25,
            'CPI': 120
        }
        result = stress_test.run_scenario(scenario)
        assert isinstance(result, (int, float, np.number))
    
    def test_stress_test_run_scenarios(self, sample_timeseries):
        """Test that StressTest runs multiple scenarios."""
        stress_test = StressTest(
            sample_timeseries,
            'Non Performing Loan Ratio',
            ['Monetary Policy Rate (%)', 'CPI']
        )
        scenarios = {
            'Baseline': {'Monetary Policy Rate (%)': 20, 'CPI': 110},
            'Crisis': {'Monetary Policy Rate (%)': 30, 'CPI': 140}
        }
        results = stress_test.run_scenarios(scenarios)
        assert isinstance(results, pd.DataFrame)
        assert len(results) == 2
    
    def test_stress_test_sensitivity(self, sample_timeseries):
        """Test that StressTest runs sensitivity analysis."""
        stress_test = StressTest(
            sample_timeseries,
            'Non Performing Loan Ratio',
            ['Monetary Policy Rate (%)', 'CPI']
        )
        base = {'Monetary Policy Rate (%)': 20, 'CPI': 110}
        sensitivity = stress_test.sensitivity_analysis(
            base,
            'Monetary Policy Rate (%)',
            range_pct=0.2,
            n_points=5
        )
        assert isinstance(sensitivity, pd.DataFrame)
        assert len(sensitivity) == 5
    
    def test_stress_test_coefficients(self, sample_timeseries):
        """Test that StressTest returns coefficients."""
        stress_test = StressTest(
            sample_timeseries,
            'Non Performing Loan Ratio',
            ['Monetary Policy Rate (%)', 'CPI']
        )
        coefs = stress_test.get_model_coefficients()
        assert isinstance(coefs, pd.DataFrame)
        assert 'Coefficient' in coefs.columns
    
    def test_stress_test_reports_chronological_holdout_metrics(self, sample_timeseries):
        """Diagnostics should report performance on later, unseen observations."""
        features = ['Monetary Policy Rate (%)', 'CPI']
        stress_test = StressTest(
            sample_timeseries,
            'Non Performing Loan Ratio',
            features,
            train_ratio=0.8
        )

        diagnostics = stress_test.get_model_diagnostics()

        assert diagnostics['n_train'] == 80
        assert diagnostics['n_test'] == 20
        assert diagnostics['r2_score'] == diagnostics['test_r2']
        assert diagnostics['test_r2'] is not None
        assert diagnostics['test_rmse'] >= 0
        assert np.allclose(
            stress_test.scaler.mean_,
            sample_timeseries.iloc[:80][features].mean().values
        )

    def test_stress_test_rejects_invalid_train_ratio(self, sample_timeseries):
        """Training split must leave valid training and test samples."""
        with pytest.raises(ValueError):
            StressTest(
                sample_timeseries,
                'Non Performing Loan Ratio',
                ['Monetary Policy Rate (%)', 'CPI'],
                train_ratio=1.0
            )

    def test_stress_test_error_missing_var(self, sample_timeseries):
        """Test that missing stress variable raises error."""
        with pytest.raises(ValueError):
            StressTest(
                sample_timeseries,
                'Non Performing Loan Ratio',
                ['NonExistent']
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
