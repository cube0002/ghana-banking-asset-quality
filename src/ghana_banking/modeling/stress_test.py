"""Legacy static regression scenario utility.

This module predicts one outcome from contemporaneous inputs. It is not a
dynamic macro-financial stress test and should not be used as the primary
research scenario engine. See ardl_scenarios for conditional path forecasts."""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from typing import Dict, Optional


class StressTest:
    """Legacy static regression predictions for supplied scenario inputs.

    The model uses contemporaneous regressors and does not propagate
    macroeconomic paths through time. Its outputs are conditional regression
    predictions, not regulatory stress-test losses or dynamic NPL forecasts.
    Prefer the ARDL scenario-path engine for a reviewed dynamic specification.
    
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
        if not 0 < train_ratio < 1:
            raise ValueError("train_ratio must be strictly between 0 and 1.")

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
        if n_train < len(stress_vars) + 1 or len(data) - n_train < 1:
            raise ValueError(
                "The chronological split leaves too few observations for "
                "training or testing. Adjust train_ratio or provide more data."
            )

        # Preserve time order: fit preprocessing and model on the training
        # period only, then evaluate on the later holdout period.
        data_train = data.iloc[:n_train]
        data_test = data.iloc[n_train:]
        X_train = data_train[stress_vars].values
        y_train = data_train[target_var].values
        X_test = data_test[stress_vars].values
        y_test = data_test[target_var].values

        self.scaler = StandardScaler()
        self._X_train_scaled = self.scaler.fit_transform(X_train)
        self._X_test_scaled = self.scaler.transform(X_test)
        self._y_train = y_train
        self._y_test = y_test

        # Fit regression model on the training period only.
        self.regression_model = LinearRegression()
        self.regression_model.fit(self._X_train_scaled, self._y_train)
        self.feature_names = stress_vars
        self.target_var = target_var
    
    def run_scenario(self, scenario_values: Dict) -> float:
        """Return a one-period static regression prediction for supplied inputs.
        
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
        """Report chronological holdout performance and training fit.

        The test period follows the training period. Scaling parameters are
        estimated on training observations only, avoiding look-ahead leakage.
        The returned r2_score is the holdout R-squared for backwards
        compatibility; it is None when the holdout has fewer than two rows.
        """
        train_predictions = self.regression_model.predict(self._X_train_scaled)
        test_predictions = self.regression_model.predict(self._X_test_scaled)

        train_r2 = r2_score(self._y_train, train_predictions)
        test_r2 = (
            r2_score(self._y_test, test_predictions)
            if len(self._y_test) >= 2
            else None
        )
        test_rmse = float(np.sqrt(mean_squared_error(self._y_test, test_predictions)))

        return {
            "intercept": self.regression_model.intercept_,
            "n_features": len(self.feature_names),
            "r2_score": test_r2,
            "train_r2": train_r2,
            "test_r2": test_r2,
            "test_rmse": test_rmse,
            "n_train": len(self._y_train),
            "n_test": len(self._y_test),
        }
