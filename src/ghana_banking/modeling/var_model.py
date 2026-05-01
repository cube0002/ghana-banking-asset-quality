"""Vector Autoregression for modeling shock spillovers.

VAR lets you see how one variable's shock ripples through the whole system
over time. Better than OLS for understanding dynamic relationships."""

import numpy as np
import pandas as pd
from statsmodels.tsa.api import VAR as StatsmodelsVAR
from typing import Optional, Tuple


class VARModel:
    """VAR model for analyzing how shocks propagate through the economy.
    
    Ask questions like: "If the exchange rate suddenly spiked 30%, 
    how would NPLs evolve over the next 12 months?" This is more realistic
    than OLS because it captures dynamics.
    
    Attributes:
        lags: How many months of history to include
        results: The fitted VAR model
        var_data: The data we trained on
        column_names: Variable names
    
    Example:
        model = VARModel(lags=2)
        model.fit(df[['NPL', 'Rate', 'GDP']])
        irf = model.impulse_responses(periods=12)
        # See how a 1-unit shock to Rate affects NPL over 12 months
    """
    
    def __init__(self, lags: int = 2):
        """Set up a VAR with specified number of lags."""
        self.lags = lags
        self.results = None
        self.var_data = None
        self.column_names = None
    
    def fit(self, df: pd.DataFrame, use_diff: bool = True) -> 'VARModel':
        """
        Fit VAR model to data.
        
        Parameters
        ----------
        df : pd.DataFrame
            Multivariate time series data. Can have a DatetimeIndex.
        use_diff : bool, default True
            If True, difference the data before fitting (for non-stationary series).
        
        Returns
        -------
        VARModel
            Returns self for method chaining.
        
        Raises
        ------
        ValueError
            If data has insufficient observations or missing values.
        """
        # Validate input
        if len(df) < self.lags + 2:
            raise ValueError(
                f"Insufficient observations for {self.lags} lags: need at least "
                f"{self.lags + 2}, got {len(df)}"
            )
        
        # Drop missing values
        data = df.dropna()
        
        if len(data) < self.lags + 2:
            raise ValueError(
                f"After removing NaNs: insufficient data ({len(data)} < {self.lags + 2})"
            )
        
        # Optionally difference data (for non-stationary series)
        if use_diff:
            data_for_fit = data.diff().dropna()
        else:
            data_for_fit = data
        
        # Store column names and data
        self.column_names = data_for_fit.columns.tolist()
        self.var_data = data_for_fit
        
        # Fit VAR model
        var_model = StatsmodelsVAR(data_for_fit)
        self.results = var_model.fit(self.lags)
        
        return self
    
    def impulse_responses(
        self,
        periods: int = 12,
        impulse_var: Optional[int] = None,
        response_var: Optional[int] = None
    ) -> np.ndarray:
        """Calculate impulse response functions (IRF).
        
        Shows how a shock to one variable ripples through the system over time.
        For example: if Policy Rate jumps 5%, how does NPL ratio respond over 
        the next 12 months? Month 1, Month 2, etc.
        
        Args:
            periods: How many months to track the shock
            impulse_var: Which variable gets the shock (None = all)
            response_var: Which variable shows the response (None = all)
        
        Returns:
            Matrix showing the propagation path
        
        Example:
            irf = model.impulse_responses(periods=12)
            # Shape: (13, 3, 3) - 13 time periods, 3 x 3 shock matrix
        """
        """
        if self.results is None:
            raise ValueError("Model not yet fitted. Call fit() first.")
        
        irf = self.results.irf(periods)
        
        if impulse_var is not None and response_var is not None:
            return irf.irfs[:, response_var, impulse_var]
        
        return irf
    
    def forecast(
        self,
        last_obs: pd.DataFrame,
        steps: int = 6
    ) -> pd.DataFrame:
        """Make predictions for the next several months.
        
        Takes the last few months of data and projects forward.
        
        Args:
            last_obs: The most recent n observations (n = number of lags)
            steps: How many months to forecast
        
        Returns:
            Forecast values with dates and variable names
        
        Example:
            pred = model.forecast(df.iloc[-2:], steps=6)
            # Get 6 months of forecasts starting from today
        """
        if self.results is None:
            raise ValueError("Model not yet fitted. Call fit() first.")
        
        forecast_array = self.results.forecast(last_obs.values, steps=steps)
        forecast_df = pd.DataFrame(forecast_array, columns=self.column_names)
        
        return forecast_df
    
    def summary(self) -> str:
        """Print the full VAR model results.
        
        Shows coefficients, stats, everything you'd need for a report.
        
        Returns:
            Formatted model summary
        
        Example:
            print(model.summary())
        """
        if self.results is None:
            raise ValueError("Model not yet fitted. Call fit() first.")
        
        return str(self.results.summary())
    
    def get_lag_order(self, maxlags: int = 8) -> dict:
        """Find the best number of lags to use.
        
        Tests different lag lengths and shows which is optimal
        according to AIC and BIC criteria.
        
        Args:
            maxlags: Test up to this many lags
        
        Returns:
            Information criteria for each lag option
        
        Example:
            lag_results = model.get_lag_order(maxlags=12)
            # BIC usually picks the most parsimonious model
        """
        if self.var_data is None:
            raise ValueError("Model not yet fitted. Call fit() first.")
        
        var_model = StatsmodelsVAR(self.var_data)
        lag_order = var_model.select_order(maxlags=maxlags)
        
        return {
            'aic': lag_order.aic,
            'bic': lag_order.bic,
            'fpe': lag_order.fpe,
            'hqic': lag_order.hqic,
            'selected_aic': lag_order.aic,
            'selected_bic': lag_order.bic
        }
    
    def get_covariance(self) -> pd.DataFrame:
        """Get residual covariance matrix.
        
        Returns
        -------
        pd.DataFrame
            Covariance matrix of residuals.
        """
        if self.results is None:
            raise ValueError("Model not yet fitted. Call fit() first.")
        
        cov = pd.DataFrame(
            self.results.sigma_u,
            index=self.column_names,
            columns=self.column_names
        )
        
        return cov
    
    def get_correlation(self) -> pd.DataFrame:
        """
        Get residual correlation matrix.
        
        Returns
        -------
        pd.DataFrame
            Correlation matrix of residuals.
        """
        cov_matrix = self.get_covariance()
        std_devs = np.sqrt(np.diag(cov_matrix))
        corr_matrix = cov_matrix.values / np.outer(std_devs, std_devs)
        
        corr = pd.DataFrame(
            corr_matrix,
            index=self.column_names,
            columns=self.column_names
        )
        
        return corr
