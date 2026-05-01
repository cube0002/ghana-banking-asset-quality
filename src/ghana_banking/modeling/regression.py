"""OLS regression for understanding what drives NPL ratios."""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import r2_score, mean_squared_error
from typing import Dict, Tuple, Optional


class OLSModel:
    """Plain vanilla OLS regression for NPL analysis.
    
    Figure out which macroeconomic variables actually move the needle on
    non-performing loans. Simple, interpretable, good for policy work.
    
    Attributes:
        results: The fitted statsmodels result object
        model: The OLS model itself
        X_cols: Which variables we used as predictors
        y_name: The target variable name
    
    Example:
        model = OLSModel()
        model.fit(df, 'Non Performing Loan Ratio', 
                  ['Monetary Policy Rate (%)', 'GDP_Real'])
        print(model.summary())
    """
    
    def __init__(self):
        """Set up an empty model."""
        self.results = None
        self.model = None
        self.X_cols = None
        self.y_name = None
    
    def fit(
        self,
        df: pd.DataFrame,
        y_col: str,
        x_cols: list
    ) -> 'OLSModel':
        """Fit the regression.
        
        Args:
            df: DataFrame with all the data
            y_col: Column name for NPL (dependent variable)
            x_cols: Which variables to use as predictors
        
        Returns:
            Self, so you can chain methods
        
        Raises:
            ValueError: If columns are missing or data is too sparse
        
        Example:
            model.fit(df, 'NPL', ['Rate', 'GDP', 'CPI'])
        """
        # Validate inputs
        missing_cols = [col for col in [y_col] + x_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Columns not found in dataframe: {missing_cols}")
        
        # Extract variables and drop missing values
        data = df[[y_col] + x_cols].dropna()
        
        if len(data) < len(x_cols) + 2:
            raise ValueError(
                f"Insufficient data: need at least {len(x_cols) + 2} observations, "
                f"got {len(data)}"
            )
        
        # Prepare data
        y = data[y_col]
        X = data[x_cols]
        X = sm.add_constant(X)  # Add intercept
        
        # Fit model
        self.model = sm.OLS(y, X)
        self.results = self.model.fit()
        self.X_cols = x_cols
        self.y_name = y_col
        
        return self
    
    def summary(self) -> str:
        """Get the regression table (R², coefficients, p-values, etc).
        
        This is what you'd print in a report to show your analysis.
        
        Returns:
            Nicely formatted regression results as text
        
        Example:
            print(model.summary())
        """
        if self.results is None:
            raise ValueError("Model not fitted yet. Call fit() first.")
        
        return self.results.summary().as_text()
    
    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Make predictions on new data.
        
        Args:
            df: Data with the same predictor columns
        
        Returns:
            Array of predicted NPL values
        
        Example:
            predictions = model.predict(df_test)
        """
        if self.results is None:
            raise ValueError("Model not fitted yet. Call fit() first.")
        
        X = df[self.X_cols].copy()
        X = sm.add_constant(X)
        return self.results.predict(X).values
    
    def get_diagnostics(self) -> Dict:
        """Grab key model stats (R², AIC, F-stat, etc).
        
        Returns:
            Dictionary with R-squared, AIC, Durbin-Watson, etc.
        
        Example:
            diags = model.get_diagnostics()
            print(f"R²: {diags['r_squared']:.3f}")
        """
        if self.results is None:
            raise ValueError("Model not fitted yet. Call fit() first.")
        
        return {
            'r_squared': self.results.rsquared,
            'adj_r_squared': self.results.rsquared_adj,
            'aic': self.results.aic,
            'bic': self.results.bic,
            'f_statistic': self.results.fvalue,
            'f_pvalue': self.results.f_pvalue,
            'durbin_watson': sm.stats.durbin_watson(self.results.resid),
            'condition_number': self.results.condition_number
        }
    
    def get_coefficients(self) -> pd.DataFrame:
        """Extract coefficients with t-stats and p-values.
        
        Shows which variables matter and how confident we are about them.
        
        Returns:
            DataFrame with coefficients, std errors, and significance stars
        
        Example:
            coefs = model.get_coefficients()
            print(coefs[coefs['Significant']])  # Only significant vars
        """
        if self.results is None:
            raise ValueError("Model not fitted yet. Call fit() first.")
        
        coef_data = pd.DataFrame({
            'Variable': self.results.params.index[1:],
            'Coefficient': self.results.params.values[1:],
            'Std Error': self.results.bse.values[1:],
            'T-Stat': self.results.tvalues.values[1:],
            'P-value': self.results.pvalues.values[1:],
            'Significant': self.results.pvalues.values[1:] < 0.05
        })
        
        return coef_data.sort_values('Coefficient', ascending=False)
    
    def get_residuals(self) -> np.ndarray:
        """Get the model errors (actual - predicted).
        
        Useful for diagnostic plots to check if the model is reasonable.
        
        Returns:
            Residual values
        
        Example:
            residuals = model.get_residuals()
            # Plot to check for patterns (shouldn't have any)
        """
        if self.results is None:
            raise ValueError("Model not fitted yet. Call fit() first.")
        
        return self.results.resid.values
