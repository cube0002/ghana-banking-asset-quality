# Usage

## Refresh source data

I have added a validated refresh utility. It downloads the monthly banking CSV and quarterly GDP CSV from configurable export URLs, checks the expected schemas and observation dates, and only replaces the local files after both downloads pass validation. It refuses to replace a newer local dataset with an older download.

The refresh utility does not guess source URLs. Configure the official CSV export URLs supplied by the relevant data providers:

```bash
export MONTHLY_DATA_URL="https://provider.example/monthly-export.csv"
export GDP_DATA_URL="https://provider.example/quarterly-gdp-export.csv"
PYTHONPATH=src python -m ghana_banking.data.refresh
```

On Windows PowerShell, set the variables with `$env:MONTHLY_DATA_URL` and `$env:GDP_DATA_URL` before running the command.

The GitHub Actions workflow supports manual refresh and a weekly schedule. Add repository Actions secrets named `MONTHLY_DATA_URL` and `GDP_DATA_URL` before enabling it. The scheduled workflow runs from the repository's default branch; manual runs can be launched against a selected branch. A successful refresh commits changed raw CSVs, while unchanged files are left alone.

**Current limitation:** the refresh mechanism is ready, but the provider export URLs still need to be configured. It does not yet connect to a live Bank of Ghana or Ghana Statistical Service API, and it cannot promise real-time updates where the providers publish data periodically.

### Refresh Bank of Ghana financial soundness indicators (experimental)

The Bank of Ghana's monthly financial soundness indicators are published in the GSS StatsBank [Financial Soundness Indicators table](https://statsbank.statsghana.gov.gh/pxweb/en/Search%20Bar/-/fin_sound.px/). This table contains eight indicators and currently lists observations through June 2024. A separate nine-indicator table stops at December 2023, so I target the newer table.

Run the connector manually:

```bash
PYTHONPATH=src python -m ghana_banking.data.bog --raw-data-path data/raw
```

It reads the table metadata, selects the monthly time dimension and indicator dimension, maps the published indicator codes to readable labels, and writes long-format observations to `data/raw/bog_financial_soundness.csv`. It does not overwrite `data_first.csv` or `data_first2.csv`. The connector is experimental until its live API response is retrieved and reconciled with the BoG publication. The selected StatsBank page advertises 222 monthly periods from January 2006 through June 2024; check the latest returned month rather than assuming the mirror is up to date. BoG reports that CAR from April 2023 is adjusted for regulatory reliefs, so the CAR series has a documented comparability break. The GSS StatsBank table is a publication route; the original data source is the Bank of Ghana.

### Refresh quarterly GDP directly from GSS StatsBank (experimental)

I have added a separate PxWeb connector for the GSS quarterly GDP table. It uses the documented StatsBank API root (`https://statsbank.statsghana.gov.gh:443/api/v1/en/`), reads the table metadata, identifies the time dimension and the real-GDP/total categories, then requests the observations. It deliberately stops if the provider's metadata is ambiguous. The published table labels the aggregate `Total GDP` and the real series `Real GDP (constant 2013 prices)`.

Run it manually:

```bash
PYTHONPATH=src python -m ghana_banking.data.gss --raw-data-path data/raw
```

The connector writes the normalised quarterly observations to `data/raw/data_first2.csv`, preserves GSS's provisional (`**`) and revised (`*`) observation flags in an `Observation Status` column, and refuses to replace a newer local file with older data. The live GSS API response has not yet been validated end to end, so treat this as experimental until a manual run succeeds and the returned values are reconciled with the published GSS table. It is not currently part of the scheduled refresh workflow.

## Load the prepared data

```python
from ghana_banking.data import load_banking_data

df = load_banking_data()
print(df.head())
print(df.index.min(), df.index.max())
print(df.isna().sum())
```

The loader joins monthly indicators to linearly interpolated monthly estimates of quarterly GDP. These interpolated GDP values are not observed monthly data; see the project README and data dictionary before using them in time-series models.

For analysis that should preserve the source frequency, load quarterly GDP separately:

```python
from ghana_banking.data import load_quarterly_gdp

gdp_quarterly = load_quarterly_gdp()
print(gdp_quarterly.head())
print(gdp_quarterly.index.freq)
```

This returns the original quarterly GDP observations as a quarterly `PeriodIndex`. It does not interpolate them or create artificial monthly observations. Monthly banking indicators and quarterly GDP should be modelled at a compatible frequency; do not combine them in a monthly VAR by treating interpolated GDP as observed monthly data.

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

## Guarded VECM estimation

A VECM is available for a small system whose included variables have all
been reviewed as I(1) and whose Johansen rank evidence supports a
cointegrating relationship. The rank is supplied explicitly after reviewing
the trace and maximum-eigenvalue tests; the estimator does not select it
automatically:

```python
from ghana_banking.econometrics import fit_vecm_model

vecm_result = fit_vecm_model(
    data=cointegrated_i1_data,
    integration_assessments={
        "log NPL": "I(1)",
        "log credit": "I(1)",
    },
    cointegration_rank=1,  # reviewed Johansen decision
    k_ar_diff=1,
    deterministic="co",
    whiteness_lags=12,
)
print(vecm_result.to_dict())
```

The output includes adjustment coefficients, normalized cointegrating
vectors, short-run coefficients, residual covariance, Portmanteau
whiteness and joint normality tests, log likelihood and effective sample
metadata. The deterministic specification and lagged-difference order must
be justified and checked for sensitivity. A VECM fit does not prove that a
long-run relation is economically meaningful, and its reduced-form
innovations do not identify structural shocks. Do not estimate a VECM when
the integration evidence is uncertain, variables are not all I(1), or the
cointegration rank is zero.

## VAR impulse-response uncertainty and chronological forecast evaluation

After a stationary VAR has been selected and its stability and residual
diagnostics reviewed, obtain Monte Carlo impulse-response bands:

```python
from ghana_banking.modeling import VARModel

var_model = VARModel(lags=2).fit(stationary_var_data, use_diff=False)
bands = var_model.impulse_response_bands(
    periods=12,
    orthogonalized=False,
    replications=1000,
    significance_level=0.05,
    seed=12345,
)
```

The method returns pointwise Monte Carlo simulation bands. Reduced-form
responses are not structural shocks. If `orthogonalized=True`, statsmodels
uses a Cholesky decomposition, so responses depend on the ordering of
endogenous variables; document and justify that ordering. These bands are
conditional on the fitted VAR, its lag order, deterministic terms and
residual distribution. They are not simultaneous confidence bands and do
not establish causal effects.

For out-of-sample predictive evaluation, use expanding-window backtesting on
a pre-transformed, stationary data set:

```python
from ghana_banking.modeling import expanding_window_var_backtest

backtest = expanding_window_var_backtest(
    data=stationary_var_data,
    lag_order=2,
    initial_window=80,
    horizons=[1, 3, 6, 12],
    step=1,
)
print(backtest.metrics)
```

At each forecast origin the VAR is re-estimated using only observations
available at that date. Metrics are reported by variable and horizon, with
an expanding historical-mean benchmark. The lag order is held fixed across
origins. If lag selection, transformations, scaling or variable selection
are part of the forecasting pipeline, repeat those steps using only each
origin's training sample; otherwise information can leak from the future.
The input must already be on a defensible stationary modelling scale and
have a regular, complete time index. Report MAE and RMSE by horizon and
compare the VAR with the benchmark rather than reporting VAR accuracy in
isolation. A successful backtest is predictive evidence, not causal evidence.

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

## Reusable unit-root diagnostic API

The package exposes the same ADF, Phillips-Perron and KPSS diagnostic engine
used by notebook 03:

```python
from ghana_banking.econometrics import (
    run_unit_root_suite,
    assess_integration_order,
)

level_results = run_unit_root_suite(
    series=df["Non Performing Loan Ratio"],
    series_name="NPL ratio",
    deterministic="c",
    adf_method="bic",
    frequency="monthly",
    transformation="level",
)

difference_results = run_unit_root_suite(
    series=df["Non Performing Loan Ratio"].diff().dropna(),
    series_name="NPL ratio",
    deterministic="c",
    adf_method="bic",
    frequency="monthly",
    transformation="first difference",
)

assessment = assess_integration_order(level_results, difference_results)
print([result.to_dict() for result in level_results])
print(assessment)
```

The result object records the null and alternative hypotheses, statistic,
p-value, critical values, selected lag/bandwidth, deterministic terms,
effective observation count and sample endpoints. The common deterministic
specification is restricted to an intercept (`c`) or intercept plus trend
(`ct`), because KPSS does not offer the no-constant specification. The
engine rejects missing or infinite observations rather than silently dropping
dates. Resolve missingness and verify regular time spacing before calling it.

The integration assessment is deliberately conservative: it reports I(0)
only when both unit-root tests reject and KPSS does not reject stationarity;
it reports I(1) only when levels show unit-root evidence and first differences
show stationarity evidence. Conflicting evidence remains uncertain. These
labels are working assessments, not automatic model-selection decisions.

## Reusable structural-break diagnostic API

The package also exposes a Zivot–Andrews one-break unit-root test. It records
the estimated break date and index, selected lag, deterministic specification,
critical values and sample metadata:

```python
from ghana_banking.econometrics import run_zivot_andrews_test

za = run_zivot_andrews_test(
    series=df["Non Performing Loan Ratio"],
    series_name="NPL ratio",
    regression="ct",       # intercept and trend break
    max_lags=12,
    autolag="BIC",
    trim=0.15,
    frequency="monthly",
    transformation="level",
)
print(za.to_dict())
```

The supported deterministic break specifications are `c` (intercept),
`t` (trend), and `ct` (intercept and trend). The reported break date is
the test's estimated breakpoint within the supplied sample; it is not an
economic event date without independent historical corroboration. The test
allows one break and does not replace multiple-break estimation or parameter-
stability diagnostics. Use it as sensitivity evidence alongside ADF, PP and
KPSS, not as a mechanical override of conflicting results.

## Guarded ARDL/UECM bounds estimation

After the exact dependent variable and regressors have been assessed as I(0)
and/or I(1), with no possible I(2) variable, the project can select an ARDL
lag structure, estimate its unrestricted error-correction representation
(UECM), and conduct the Pesaran–Shin–Smith bounds test:

```python
from ghana_banking.econometrics import fit_ardl_bounds_model

result = fit_ardl_bounds_model(
    data=monthly_model_data,
    dependent_variable="NPL ratio (%)",
    regressors=["inflation", "cedi depreciation", "policy rate"],
    integration_assessments={
        "NPL ratio (%)": "I(1)",
        "inflation": "I(0)",
        "cedi depreciation": "I(1)",
        "policy rate": "I(0)",
    },
    max_ar_lag=6,
    max_distributed_lag=6,
    selection_ic="bic",
    trend="c",
    bounds_case=3,
)
print(result.to_dict())
```

The integration labels must be the reviewed working assessments for exactly
the variables in the equation. The routine blocks uncertain, possible-I(2)
and all-I(0) systems. All-I(0) variables should normally be handled with a
stationary dynamic model; bounds testing is not a shortcut around that route.
A mixed I(0)/I(1) or all-I(1) system is only a candidate for the bounds test.

The bounds case must match the deterministic specification. Statsmodels'
case definitions are: 1 (no intercept/no trend), 2 (restricted intercept),
3 (unrestricted intercept/no trend), 4 (unrestricted intercept/restricted
trend), and 5 (unrestricted intercept and trend). This reusable wrapper
supports the directly matched combinations `trend="n", bounds_case=1`,
`trend="c", bounds_case=3`, and `trend="ct", bounds_case=5`. Restricted
cases 2 and 4 require a custom deterministic specification and are not
silently approximated by this wrapper. The default `trend="c"` and
`bounds_case=3` represent an intercept with no deterministic trend. Do not
choose the case after inspecting which produces significance.

The output reports the lower- and upper-bound p-values. Evidence of a level
relationship is recorded only when the upper-bound p-value is below alpha;
no evidence is recorded when the lower-bound p-value is above alpha; otherwise
the result is inconclusive. Long-run multipliers are returned only in the
first case. If the lag selection chooses a distributed-lag order that cannot
be represented as a UECM, the routine stops and reports the issue rather than
silently forcing a different model. Asymptotic bounds are the default; for
finite-sample simulation, set `asymptotic_bounds=False` and record `nsim`
and `seed`.

This is an estimation workflow, not an automatic final-model selector.
Inspect residual serial correlation, heteroskedasticity, functional form,
parameter stability, lag sensitivity and economic plausibility before
interpreting coefficients. A statistically supported level relationship is
not causal identification.

## Johansen cointegration-rank diagnostics

For a small system whose included variables have been assessed as I(1),
the project provides Johansen trace and maximum-eigenvalue rank tests:

```python
from ghana_banking.econometrics import run_johansen_cointegration_test

rank_result = run_johansen_cointegration_test(
    data=cointegration_system,
    integration_assessments={
        "NPL ratio": "I(1)",
        "inflation": "I(1)",
    },
    det_order=0,       # constant in the cointegrating relation
    k_ar_diff=1,       # lagged differences in the VECM
    significance_level=0.05,
    frequency="monthly",
)
print(rank_result.to_dict())
```

The output retains both test statistics, their critical values and the
sequential rank decisions. The function requires reviewed I(1) labels for exactly the variables in the system. It does not establish integration order; confirm that the variables are I(1) first, and do not include I(2) variables.
Trace and maximum-eigenvalue tests can disagree; report that disagreement
rather than selecting the preferred rank after seeing the estimates.
The deterministic specification and lag order must be justified and checked
for sensitivity. A VECM is not justified by the rank output alone.

## Parameter-stability diagnostics

After selecting a stationary and economically justified regression equation,
the reusable stability API reports CUSUM and Hansen parameter-constancy
tests alongside rolling-window coefficient estimates:

```python
from ghana_banking.econometrics import run_ols_stability_diagnostics

stability = run_ols_stability_diagnostics(
    data=stationary_model_data,
    dependent_variable="NPL_change_pp",
    regressors=[
        "Policy_rate_change_pp",
        "Inflation_mom_pct",
        "Cedi_depreciation_mom_pct",
    ],
    rolling_window=60,
)
print(stability.to_dict())
```

The input must be complete, finite, ordered and numeric. Missing dates or
values must be resolved explicitly before estimation. The CUSUM and Hansen
tests are conditional on the supplied OLS specification; rolling coefficients
are descriptive. Do not apply these tests to a potentially spurious levels
regression or interpret a rejection as proof of a specific economic event.

## Reusable OLS residual diagnostics and HAC inference

After selecting a defensible stationary regression specification, use the
residual-diagnostics API to examine serial correlation, heteroskedasticity,
conditional-variance dynamics, normality and functional form. It reports
Breusch–Godfrey, Breusch–Pagan, White, ARCH-LM, Jarque–Bera and Ramsey RESET
tests, alongside Durbin–Watson and conventional versus Newey–West/HAC
coefficient inference:

```python
from ghana_banking.econometrics import run_ols_residual_diagnostics

diagnostics = run_ols_residual_diagnostics(
    data=stationary_model_data,
    dependent_variable="NPL_change_pp",
    regressors=[
        "Policy_rate_change_pp",
        "Inflation_mom_pct",
        "Cedi_depreciation_mom_pct",
    ],
    autocorrelation_lags=12,
    arch_lags=12,
)
print(diagnostics.to_dict())
```

The API requires a complete, ordered, full-rank sample and does not silently
drop observations. The test null hypotheses are included in the returned
records. A small p-value is evidence against the corresponding null, not an
automatic instruction to transform or delete observations. Interpret tests
jointly and revisit the conditional-mean specification where indicated.
HAC standard errors adjust covariance-based inference for heteroskedasticity
and autocorrelation under the selected lag truncation; they do not cure
non-stationarity, endogeneity, omitted-variable bias or a misspecified
conditional mean. Select the HAC bandwidth as a sensitivity choice and report
it. Residual normality is not a prerequisite for consistency, but can matter
for small-sample inference.

## Model eligibility screening

The integration-order labels reviewed from unit-root evidence can be passed
to a screening helper:

```python
from ghana_banking.econometrics import assess_model_eligibility

review = assess_model_eligibility({
    "NPL ratio": "I(1)",
    "inflation": "I(0)",
    "cedi depreciation": "I(1)",
    "policy rate": "I(0)",
})
print(review)
```

The helper screens candidate model classes; it does not perform cointegration
tests or choose the final model. Standard ARDL bounds critical values are
blocked if any variable may be I(2) or unresolved. A mixed I(0)/I(1) set is
only a candidate for bounds testing, while a VECM candidate still requires
Johansen rank evidence. All-I(0) evidence can support a stationary dynamic
regression or VAR, subject to residual and stability diagnostics.

## Run the notebooks and tests

```bash
jupyter lab notebooks/
pytest tests/ -v
```

Run the research notebooks in this order:

1. `01_data_cleaning.ipynb` — prepares monthly banking observations and quarterly GDP separately.
2. `02_exploratory_analysis.ipynb` — audits missingness, constructs preliminary transformations and explores the monthly data.
3. `03_time_series_diagnostics.ipynb` — runs ADF, Phillips–Perron and KPSS tests on levels and first differences, adds a reusable one-break Zivot–Andrews sensitivity test with estimated break dates, checks large monthly changes and tests quarterly GDP at its original frequency.

The third notebook uses `arch` for Phillips–Perron and `statsmodels` for Zivot–Andrews. Both are included in the project dependencies. After pulling the branch, refresh the environment with:

```bash
pip install -e ".[dev]"
```

The diagnostics notebook does not automatically assign integration orders or select a final econometric model. Review deterministic terms, test conflicts, outlier flags and structural-break evidence before enabling its optional VAR lag-order cell. Its results are diagnostics, not causal findings.


### Load the November 2026 Bank of Ghana publication snapshot

The official BoG November 2026 summary PDF has been transcribed into a separate, source-attributed CSV. It covers October 2025 to October 2026 and should be treated as a rounded publication snapshot, not a live feed.

```python
from ghana_banking.data import load_bog_summary_snapshot

fsi = load_bog_summary_snapshot(
    "data/raw/bog_summary_nov_2026.csv"
)
print(fsi.tail())
```

The loader validates dates, numeric values, source attribution and duplicate month-indicator rows. The snapshot is kept separate from the original monthly macro dataset. An overlap test checks that CAR, NPL and ROA for October–December 2025 agree with the original source after rounding to the one-decimal precision used in the BoG publication. The comparison is a consistency check, not a full historical-series reconciliation.


### Compare Bank of Ghana publication vintages

I am adding a revision-audit step so a new BoG publication does not silently replace an earlier vintage. Keep each downloaded or transcribed publication as a separate CSV, then compare the two versions:

```python
from ghana_banking.data import (
    load_bog_summary_snapshot,
    build_bog_revision_report,
)

# The July 2026 vintage is included as a separate source snapshot.
previous = load_bog_summary_snapshot(
    "data/raw/bog_summary_sep_2026.csv"
)
current = load_bog_summary_snapshot(
    "data/raw/bog_summary_nov_2026.csv"
)
revisions = build_bog_revision_report(previous, current)
print(revisions[revisions["Observation Status"] != "unchanged"])
```

The report joins on observation date and indicator code. It labels observations as `revised`, `unchanged`, `added` or `removed`, reports the numeric change, retains both publication dates and source URLs, and flags changes to indicator labels or units. The optional `tolerance` argument can treat small rounding differences as unchanged.

This is a vintage comparison, not a claim that every difference is a statistical revision: additions and removals can reflect changed publication coverage, and metadata changes need substantive review. The repository now contains July, September and November 2026 snapshots. All three PDFs are hosted in the official BoG publication archive, but each carries a DRAFT watermark; the caveat is retained in each CSV's source note. The adjacent July–September and September–November comparisons each have 121 matched date-indicator observations, and the July–November comparison has 99. All matched values agree exactly at one-decimal precision. This supports cross-publication consistency, not proof that unrounded data were never revised or that these are final certified releases.


## Univariate AR forecast benchmark and prediction intervals

The expanding-window AR benchmark provides a univariate autoregressive
forecast for each supplied series, with pointwise prediction intervals and
two simple benchmarks:

```python
from ghana_banking.modeling import expanding_window_ar_backtest

result = expanding_window_ar_backtest(
    data=stationary_npl_change,
    lag_order=2,
    initial_window=80,
    horizons=[1, 3, 6],
    step=1,
    significance_level=0.05,
)
print(result.metrics)
```

At each origin the AR model is re-estimated using only the available training
observations. The output reports MAE and RMSE by variable and horizon for the
AR forecast, a no-change forecast and an expanding historical-mean forecast.
It also reports empirical coverage and average width of the pointwise AR
prediction intervals. These coverage estimates are descriptive and can be
noisy when the number of forecast origins is small.

The input must be complete, regular and already transformed to a defensible
stationary modelling scale. The lag order is fixed across origins; if lag
selection or transformations are data-driven, repeat them inside each
training window rather than using the full sample. Prediction intervals are
conditional on the fitted AR specification and do not account for model
selection uncertainty or structural breaks. This is a predictive benchmark,
not a causal model.


## Dynamic ARDL scenario-path propagation

For a defensible ARDL specification, the project can propagate multiple
future macroeconomic paths through the fitted dynamic equation:

```python
from statsmodels.tsa.ardl import ARDL
from ghana_banking.modeling import forecast_ardl_scenarios

# Fit only after reviewing integration evidence, lag choice and bounds results.
fitted_ardl = ARDL(
    endog=npl_ratio,
    lags=2,
    exog=historical_macro_variables,
    order=1,
    trend="c",
).fit()

scenario_results = forecast_ardl_scenarios(
    fitted_results=fitted_ardl,
    scenarios={
        "Baseline": baseline_macro_path,
        "Adverse": adverse_macro_path,
        "Severe": severe_macro_path,
    },
    baseline_name="Baseline",
    significance_level=0.05,
)
print(scenario_results)
```

Each scenario DataFrame must contain exactly the fitted exogenous variables,
in the same order, over the same regular future index and horizon. Values must
already use the model's estimation transformations and units. The ARDL's
autoregressive terms propagate the NPL path dynamically; this is not a
one-period static regression shock. The output includes pointwise conditional
forecast intervals and point-estimate differences from the baseline.

The difference from baseline is not itself a confidence interval for the
scenario effect. Intervals condition on the fitted specification and do not
include model-selection uncertainty, parameter instability or uncertainty in
the scenario assumptions. Scenario paths must be documented and calibrated
from defensible evidence; illustrative analyst assumptions must be labelled
as such. The legacy `StressTest` class remains a static contemporaneous
regression utility and should not be described as the primary dynamic
stress-testing method.


## Historical calibration of conditional scenario paths

The historical calibration utility generates baseline, adverse and severe exogenous paths from univariate AR(1) models estimated on the supplied historical sample:

```python
from ghana_banking.modeling import (
    calibrate_historical_scenario_paths,
    forecast_ardl_scenarios,
)

scenario_paths = calibrate_historical_scenario_paths(
    historical_exog=historical_macro_variables,
    horizon=12,
    adverse_directions={
        "inflation": 1,
        "cedi_depreciation": 1,
        "policy_rate_change": 1,
    },
    integrated_variables=[],
    adverse_quantile=0.90,
    severe_quantile=0.975,
    persistence=0.70,
)

scenario_forecasts = forecast_ardl_scenarios(
    fitted_results=fitted_ardl,
    scenarios=scenario_paths,
    baseline_name="Baseline",
)
```

The historical data must be complete, regular and expressed in the same units and transformations used by the ARDL regressors. `adverse_directions` is an explicit economic assumption: +1 means an increase is adverse; -1 means a decrease is adverse. For variables treated as I(1) in levels, list them in `integrated_variables`; the calibration models their first differences and accumulates forecast changes back to levels. Other variables are modelled in levels.

The baseline uses AR(1) conditional forecasts. Adverse and severe scenarios add direction-adjusted historical innovation quantiles, with geometric shock decay controlled by the explicitly assumed `persistence` parameter. The quantile and persistence choices must be reported and sensitivity-tested. The AR(1) calibration is intentionally transparent and parsimonious; it is not a substitute for a validated multivariate macroeconomic forecasting model.

**Important limitation:** innovation quantiles are calibrated separately for each variable. The resulting paths do not preserve cross-variable dependence or represent joint probabilities. They are illustrative conditional sensitivity scenarios, not official Bank of Ghana/IMF scenarios, causal shocks or supervisory stress tests. Do not interpret the 90th or 97.5th marginal quantiles as a joint 10% or 2.5% macroeconomic tail event.


## Scenario-assumption sensitivity analysis

The sensitivity routine holds the fitted ARDL model and historical calibration sample fixed while varying the adverse/severe innovation quantiles and geometric shock persistence:

```python
from ghana_banking.modeling import run_ardl_scenario_sensitivity

sensitivity = run_ardl_scenario_sensitivity(
    fitted_results=fitted_ardl,
    historical_exog=historical_macro_variables,
    horizon=12,
    adverse_directions=adverse_directions,
    integrated_variables=integrated_variables,
    quantile_pairs=[(0.90, 0.975), (0.95, 0.99)],
    persistence_values=[0.30, 0.70, 0.90],
)
summary = pd.DataFrame(sensitivity.summary)
forecasts = pd.DataFrame(sensitivity.forecasts)
```

The summary reports terminal forecasts, terminal differences from baseline,
peak forecasts, peak periods and forecast-interval envelopes for each scenario
assumption combination. The detailed output preserves each horizon-level
forecast. This is a sensitivity analysis of scenario assumptions conditional
on one fitted model; it does not incorporate parameter uncertainty, model
selection uncertainty, or joint cross-variable dependence. The quantile and
persistence grids must be prespecified and reported, not selected to produce
an attractive result.


## Joint historical macro scenario calibration

Where a multivariate historical sample is available, the joint calibrator selects contiguous blocks of aligned AR(1) innovations rather than calibrating each regressor's shock independently:

```python
from ghana_banking.modeling import calibrate_joint_historical_scenario_paths

joint_paths = calibrate_joint_historical_scenario_paths(
    historical_exog=historical_macro_variables,
    horizon=12,
    adverse_directions={
        "inflation": 1,
        "cedi_depreciation": 1,
        "policy_rate_change": 1,
    },
    integrated_variables=[],
    adverse_quantile=0.90,
    severe_quantile=0.975,
    # Optional: use explicit, economically justified weights instead of equal weights.
    severity_weights={"inflation": 1.0, "cedi_depreciation": 1.0, "policy_rate_change": 1.0},
)
```

Each variable is first modelled with an AR(1), using first differences for variables explicitly classified as I(1). Residuals are standardised and direction-adjusted, then aligned by date. Every candidate horizon-length contiguous block receives a weighted mean severity score; equal weights are used by default, while `severity_weights` allows an explicitly specified non-negative weight for each variable. Weights are normalised to sum to one. The empirical adverse and severe score quantiles select the historical blocks. The selected residual vectors retain observed contemporaneous co-movement and within-block time ordering. I(1) paths are reconstructed by accumulating forecasted and shocked differences.

This is a transparent historical-analogue method, not a structural VAR, a causal shock identification scheme, or a probability-calibrated joint tail event. Variable weights are modelling choices and must be prespecified, justified and reported; the selected historical block may not represent a future crisis. Results depend on the historical sample, AR(1) filtering, variable transformations, adverse directions and horizon. Compare the joint method with the marginal calibrator and report the selected block dates/indices and score metadata. The routine does not claim that a 90th or 97.5th score quantile is a 10% or 2.5% joint probability.


### Historical episode-length sensitivity for joint scenarios

The joint historical calibrator now separates the forecast horizon from the historical episode length used to rank candidate residual blocks. By default, `block_length` equals `horizon`, preserving the original behaviour. To test whether block selection depends on the length of the historical episode, prespecify longer episode lengths (each must be at least the forecast horizon):

```python
from ghana_banking.modeling import calibrate_joint_historical_scenario_paths

horizon = 12
block_lengths = [12, 18, 24]
block_length_results = {}

for episode_length in block_lengths:
    paths = calibrate_joint_historical_scenario_paths(
        historical_exog=historical_macro_variables,
        horizon=horizon,
        block_length=episode_length,
        adverse_directions=adverse_directions,
        integrated_variables=integrated_variables,
        adverse_quantile=0.90,
        severe_quantile=0.975,
        severity_weights=severity_weights,
    )
    block_length_results[episode_length] = paths

# Selection metadata distinguishes the full historical episode from the
# forecast shock segment actually propagated through the model.
for episode_length, paths in block_length_results.items():
    print(episode_length, paths["Severe"].attrs["calibration"])
```

Candidate blocks are scored over the full `block_length` episode, but only the first `horizon` aligned innovations of the selected episode are propagated into the forecast. Thus, longer episodes alter the ranking and selected historical analogue without changing the forecast horizon. The metadata records both the selected episode's start/end dates and the end date of the forecast shock segment. Longer episode lengths reduce the number of available candidate blocks; report that count and do not compare results as if the candidate pools were identical. This is historical-analogue selection sensitivity, not a bootstrap confidence interval or a probability statement. The candidate episode lengths and quantiles should be prespecified rather than chosen after seeing the NPL outcomes.



## Conditional ARDL parameter-uncertainty simulation

The parameter-uncertainty utility draws the complete ARDL coefficient vector jointly from a multivariate normal approximation centred on the fitted estimates, using the estimator's covariance matrix. The same coefficient draw is applied to every scenario so that scenario-versus-baseline contrasts are paired:

```python
from ghana_banking.modeling import forecast_ardl_parameter_uncertainty

parameter_uncertainty = forecast_ardl_parameter_uncertainty(
    fitted_results=fitted_ardl,
    scenarios=joint_paths,
    baseline_name="Baseline",
    draws=2000,
    significance_level=0.05,
    seed=20261126,
)
print(parameter_uncertainty)
```

The output reports parameter-draw means, medians and quantiles for each scenario, plus paired quantiles for the scenario-minus-baseline contrast. These are **parameter-uncertainty intervals conditional on the selected ARDL specification and supplied scenario paths**. They are not full forecast prediction intervals: future innovation uncertainty, scenario-calibration uncertainty, model-selection uncertainty, structural breaks and departures from the multivariate-normal approximation are not included. Do not add these bands to the existing conditional prediction intervals or describe either one as covering all sources of uncertainty. Report the draw count, seed, covariance estimator and significance level. The utility rejects materially non-positive-semidefinite covariance matrices and clips only tiny negative eigenvalues attributable to numerical round-off.
