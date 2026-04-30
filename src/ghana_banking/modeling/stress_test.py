"""Stress test framework for "what if" scenarios.

Run plausible but extreme macroeconomic scenarios through the model
to see how much damage the banking sector could take."""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from typing import Dict, Optional


class StressTest:
    """Simulate extreme macroeconomic shocks and see the damage.
    
    Useful for regulators and risk managers who need to ask:
    "What if the currency collapses?" or "What if GDP contracts 15%?"
    
    You train on historical relationships, then apply them to stress scenarios.
    
    Attributes:
        regression_model: The fitted predictor
        scaler: Standardization parameters
        feature_names: Which variables we use
    
    Example:
        st = StressTest(df, 'NPL_Ratio', ['Rate', 'GDP', 'CPI'])
        scenarios = {
            'Baseline': {'Rate': 20, 'GDP': 1500, 'CPI': 110},
            'Currency Crisis': {'Rate': 35, 'GDP': 1200, 'CPI': 150}
        }
        results = st.run_scenarios(scenarios)
    """
    
    def __init__(
        self,
        df: pd.DataFrame,
        target_var: str,
        stress_vars: list,
        train_ratio: float = 0.8
    ):
        """Set up stress testing on historical data.
        
        Args:
            df: Historical data to learn relationships from
            target_var: What we're predicting (NPL Ratio)
            stress_vars: Which variables we'll shock
            train_ratio: How much data to use for training
        
        Raises:
            ValueError: If variables don't exist
        """
        # Validate inputs
        missing_vars = [v for v in [target_var] + stress_vars if v not in df.columns]
        if missing_vars:
            raise ValueError(f"Variables not found: {missing_vars}")
        
        # Prepare data
        data = df[[target_var] + stress_vars].dropna()
        
        if len(data) < len(stress_vars) + 5:
            raise ValueError(
                f"Insufficient data for stress testing: {len(data)} observations"
            )
        
        # Split into train/test
        n_train = int(len(data) * train_ratio)
        data_train = data.iloc[:n_train]
        
        # Extract and standardize features
        X = data_train[stress_vars].values
        y = data_train[target_var].values
        
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Fit regression model
        self.regression_model = LinearRegression()
        self.regression_model.fit(X_scaled, y)
        self.feature_names = stress_vars
        self.target_var = target_var
    
    def run_scenario(self, scenario_values: Dict) -> float:
        """Run one stress scenario and get the predicted outcome.
        
        Args:
            scenario_values: Dict like {'Rate': 20, 'GDP': 1500, 'CPI': 110}
        
        Returns:
            What the NPL ratio would be in this scenario
        
        Example:
            npl_crisis = st.run_scenario({'Rate': 35, 'GDP': 1200, 'CPI': 150})
            # NPL would be ~28% if all this happened at once
        """
        # Extract values in correct order
        X = np.array([[scenario_values[var] for var in self.feature_names]])
        
        # Standardize using fitted scaler
        X_scaled = self.scaler.transform(X)
        
        # Predict
        prediction = self.regression_model.predict(X_scaled)[0]
        
        return prediction
    
    def run_scenarios(self, scenarios: Dict) -> pd.DataFrame:
        """Run multiple scenarios side-by-side for comparison.
        
        Shows baseline vs crisis vs optimistic vs whatever you want to test.
        
        Args:
            scenarios: Dict of scenario names to variable dicts
        
        Returns:
            Table with predictions, comparison to baseline
        
        Example:
            scenarios = {
                'Baseline': {'Rate': 20, 'GDP': 1500, 'CPI': 110},
                'Currency Crisis': {'Rate': 35, 'GDP': 1200, 'CPI': 150},
                'Mild Slowdown': {'Rate': 22, 'GDP': 1400, 'CPI': 115}
            }
            results = st.run_scenarios(scenarios)
            # See NPL, delta, etc. for each
        """
        results = []
        baseline_pred = None
        
        for scenario_name, values in scenarios.items():
            pred = self.run_scenario(values)
            
            if scenario_name.lower() == 'baseline':
                baseline_pred = pred
            
            results.append({
                'Scenario': scenario_name,
                f'Predicted_{self.target_var}': round(pred, 2),
                'Delta_vs_Baseline': None  # Will fill in after baseline is known
            })
        
        # Calculate deltas against baseline
        if baseline_pred is not None:
            for result in results:
                result['Delta_vs_Baseline'] = round(
                    result[f'Predicted_{self.target_var}'] - baseline_pred,
                    2
                )
        
        results_df = pd.DataFrame(results)
        return results_df
    
    def sensitivity_analysis(
        self,
        base_scenario: Dict,
        variable: str,
        range_pct: float = 0.2,
        n_points: int = 10
    ) -> pd.DataFrame:
        """See how sensitive NPL is to one variable changing.
        
        For example: if Rate goes from 20% up to 26%, 
        what happens to the NPL ratio? See it at each step.
        
        Args:
            base_scenario: Base case (all variables at normal levels)
            variable: Which one to shake up
            range_pct: How much to vary it (0.2 = ±20%)
            n_points: How many points between min and max
        
        Returns:
            Table showing variable value vs predicted NPL
        
        Example:
            base = {'Rate': 20, 'GDP': 1500, 'CPI': 110}
            # If Rate goes up 30% from baseline
            sens = st.sensitivity_analysis(base, 'Rate', range_pct=0.3)
        """
        if variable not in self.feature_names:
            raise ValueError(f"Variable {variable} not in model")
        
        base_value = base_scenario[variable]
        lower = base_value * (1 - range_pct)
        upper = base_value * (1 + range_pct)
        
        variable_range = np.linspace(lower, upper, n_points)
        results = []
        
        for var_value in variable_range:
            scenario = base_scenario.copy()
            scenario[variable] = var_value
            pred = self.run_scenario(scenario)
            results.append({
                variable: round(var_value, 2),
                'Delta': round((var_value - base_value) / base_value * 100, 1),
                f'Predicted_{self.target_var}': round(pred, 2)
            })
        
        return pd.DataFrame(results)
    
    def get_model_coefficients(self) -> pd.DataFrame:
        """Get which stress variables matter most.
        
        Shows the standardized coefficients - big values = big impact.
        Sorted by absolute impact so you see the heavyweights first.
        
        Returns:
            DataFrame with variable names and impact
        
        Example:
            coefs = st.get_model_coefficients()
            print(coefs)  # GDP impact > Rate impact, etc.
        """
        coeff_df = pd.DataFrame({
            'Variable': self.feature_names,
            'Coefficient': self.regression_model.coef_,
            'Abs_Impact': np.abs(self.regression_model.coef_)
        }).sort_values('Abs_Impact', ascending=False)
        
        return coeff_df
    
    def get_model_diagnostics(self) -> Dict:
        """Check how good the stress model is.
        
        Returns model stats so you know whether to trust the scenarios.
        
        Returns:
            Dictionary with R-squared, intercept, etc.
        
        Example:
            diags = st.get_model_diagnostics()
            if diags['r2_score'] > 0.7:
                print("Good fit, scenarios are trustworthy")
        """
        from sklearn.metrics import r2_score
        
        # Get training data predictions for R2
        if hasattr(self, '_X_train_scaled'):
            y_pred = self.regression_model.predict(self._X_train_scaled)
            r2 = r2_score(self._y_train, y_pred)
        else:
            r2 = None
        
        return {
            'intercept': self.regression_model.intercept_,
            'n_features': len(self.feature_names),
            'r2_score': r2
        }
