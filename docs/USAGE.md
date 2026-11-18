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

The Bank of Ghana's monthly financial soundness indicators are also published in a GSS StatsBank PxWeb table. The table identifies the Bank of Ghana as the original source and includes capital adequacy, non-performing loans, liquidity, ROA, ROE and cost/income measures.

Run the connector manually:

```bash
PYTHONPATH=src python -m ghana_banking.data.bog --raw-data-path data/raw
```

It reads the table metadata, selects the monthly time dimension and indicator dimension, and writes long-format observations to `data/raw/bog_financial_soundness.csv`. It does not overwrite `data_first.csv` or `data_first2.csv`. The connector is experimental until its live API response is retrieved and reconciled with the BoG publication. The GSS StatsBank table is a publication route; the original data source is the Bank of Ghana.

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
