# Usage

## Load the prepared data

```python
from ghana_banking.data import load_banking_data

df = load_banking_data()
print(df.head())
print(df.index.min(), df.index.max())
print(df.isna().sum())
```

The loader joins monthly indicators to linearly interpolated monthly estimates of quarterly GDP. These interpolated GDP values are not observed monthly data; see the project README and data dictionary before using them in time-series models.

## Fit an OLS model

```python
from ghana_banking.modeling import OLSModel

model = OLSModel()
model.fit(
    df,
    y_col="Non Performing Loan Ratio",
    x_cols=["Monetary Policy Rate (%)", "GDP_Real"],
)
print(model.summary())
print(model.get_diagnostics())
```

The default OLS summary uses conventional standard errors. For macroeconomic time series, inspect residual autocorrelation, stationarity, structural stability and collinearity before interpreting conventional p-values. A fitted association is not a causal estimate.

## Fit a VAR

```python
from ghana_banking.modeling import VARModel

variables = df[
    ["Non Performing Loan Ratio", "Monetary Policy Rate (%)", "GDP_Real"]
].dropna()

var_model = VARModel(lags=2)
var_model.fit(variables, use_diff=True)
print(var_model.summary())

# Compare candidate lag orders before settling on a specification
lag_selection = var_model.get_lag_order(maxlags=8)
print(lag_selection["selected_orders"])

# Check stability and residual behaviour before interpreting IRFs
diagnostics = var_model.get_diagnostics(whiteness_lags=12)
print(diagnostics)
```

The `use_diff` argument controls whether first differences are used. Choose transformations based on time-series diagnostics rather than assuming that differencing is always appropriate. Interpret impulse responses in the units and transformations of the fitted system. The diagnostic method reports a companion-matrix stability check, a Portmanteau residual-whiteness test and a joint residual-normality test. These are minimum specification checks, not proof that the model is correct. The lag-selection output reports the lag count selected by AIC, BIC, FPE and HQIC; these criteria can disagree. I should compare candidate orders and then check residual whiteness and stability rather than treating one criterion as an automatic answer.

When forecasting a model fitted with `use_diff=True`, pass the last `lags` observations of the differenced data, in the same column order. Forecasts remain in differences; the current method does not reconstruct level forecasts.

## Run a scenario exercise

```python
from ghana_banking.modeling import StressTest

stress = StressTest(
    df,
    target_var="Non Performing Loan Ratio",
    stress_vars=["Monetary Policy Rate (%)", "GDP_Real"],
)

scenario = {
    "Monetary Policy Rate (%)": 20.0,
    "GDP_Real": float(df["GDP_Real"].iloc[-1]),
}
print(stress.run_scenario(scenario))
```

This is a conditional prediction from a fitted linear model, not a validated supervisory stress test. Scenario values should be documented, economically justified and checked against the model's estimation range.

## Run the notebooks and tests

```bash
jupyter lab notebooks/
pytest tests/ -v
```
