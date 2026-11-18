# Research and econometric audit

## Scope

This is a first-pass audit of the saved outputs and code in
`notebooks/03_modeling.ipynb`, `notebooks/04_stress_testing.ipynb`, and
`src/ghana_banking/modeling/`. The notebook outputs are historical saved
outputs; they have not yet been reproduced from a clean kernel. Treat all
reported numerical results below as **reported notebook results**, not as
independently verified estimates.

## Main findings

### 1. Levels OLS is descriptive, not a reliable inferential model

The saved OLS output reports 187 observations, R-squared 0.597, Durbin-Watson
0.399, and a condition number of approximately 3.11 million. The very low
Durbin-Watson statistic is strong evidence of residual serial correlation.
The large condition number also flags scaling and/or multicollinearity
problems. Conventional non-robust OLS standard errors and p-values should
therefore not be used to claim that the listed macroeconomic variables cause
or reliably explain NPL movements.

The levels regression should remain a descriptive baseline only until the
series' integration properties, deterministic trends, structural breaks,
cointegration relationships, and residual dependence have been assessed.
At minimum, compare a suitably specified dynamic model and HAC/Newey-West
inference; do not treat robust standard errors as a cure for a spurious
levels regression.

### 2. The ADF results do not support a blanket I(1) statement

The saved ADF output reports that first differences of CPI and M2+ remain
non-stationary at the 5% level (reported p-values approximately 0.491 and
0.336). The selected four-variable VAR uses first differences of NPL, the
policy rate, the USD exchange rate, and GDP; the saved ADF output reports
these first differences as stationary. Keep the stationarity conclusion
specific to the variables actually included in each model. Revisit lag
selection and deterministic terms, and consider complementary tests and
structural-break sensitivity before describing the integration order as
settled.

### 3. Monthly GDP is an interpolated proxy

The source GDP observations are quarterly. The monthly master data linearly
interpolate between quarterly GDP observations. Those intermediate values
are not observed monthly GDP and do not create new independent information.
Any monthly VAR that includes this interpolated series must say so clearly;
inference and effective sample size should not be interpreted as if GDP were
measured monthly. A quarterly model, mixed-frequency approach, or model
excluding interpolated GDP should be considered as a robustness check.

### 4. VAR specification and impulse responses need further validation

The saved notebook selects eight lags by AIC for a four-variable VAR in
monthly first differences. That is a relatively parameter-heavy specification.
Before interpreting the impulse responses, report and inspect:
- lag-order criteria across AIC, BIC and HQIC;
- companion-matrix stability;
- residual serial-correlation and heteroskedasticity diagnostics;
- sensitivity to lag length and variable ordering.

The notebook uses the reduced-form `irf.irfs` responses. Reduced-form
innovations can be contemporaneously correlated, so they should not be
described as clean, independently identified structural shocks. If using
orthogonalized responses, state the identification scheme and justify the
variable ordering; alternatively report generalized impulse responses.
The plotted horizon is monthly, so the axis label should say “Months after
shock”, not “Quarters after shock”.

### 5. Stress scenarios are conditional static simulations, not forecasts

The saved stress notebook fits a contemporaneous linear regression using the
full sample, scales predictors using the full sample, and evaluates scenarios
on that same fitted relationship. It does not report a chronological
out-of-sample backtest or prediction intervals. The reported baseline
prediction (24.39%) differs from the latest observed NPL ratio (21.74%).
That is a model prediction at the selected macroeconomic inputs, not the
current observed NPL ratio.

The saved severe-currency-crisis result (27.21%) and other scenario values
should be described as conditional outputs under analyst-selected shocks,
not as likely outcomes or validated forecasts. Scenario assumptions should
be sourced or explicitly labelled as illustrative. Report uncertainty and
out-of-sample performance before making stronger claims.

## Code changes in this branch

- The `StressTest` class now preserves chronological order, fits its scaler
  on the training period only, and reports holdout R-squared and RMSE alongside
  training R-squared and sample sizes.
- Tests cover the chronological split, training-only scaling, holdout metrics,
  and invalid split ratios.
- The Python 3.9 annotation and plotting syntax issues identified during the
  first CI review have also been corrected.

## Recommended next steps

1. Reproduce all notebooks from a clean environment and refresh saved outputs.
2. Add a dedicated time-series diagnostics section and document each series'
   transformation and integration order.
3. Re-estimate the VAR with a parsimonious lag choice, verify stability and
   residual diagnostics, and report a transparent IRF identification scheme.
4. Rebuild stress testing around a documented scenario design, chronological
   validation, and prediction uncertainty.
5. Only then update the README with defensible empirical conclusions.
