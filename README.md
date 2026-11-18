# Ghana Banking Asset Quality

An empirical study of non-performing loans and macro-financial conditions in Ghana.

This project examines how banking-sector asset quality has evolved alongside monetary, price, exchange-rate and real-economy conditions. It brings together exploratory analysis, regression modelling, multivariate time-series methods and scenario analysis using published Ghanaian banking and macroeconomic indicators.

The aim is not to claim that one model explains every movement in non-performing loans. It is to document the data, make the modelling choices visible, and assess what the available aggregate evidence can—and cannot—say about credit risk.

## Research question

**How have macroeconomic conditions and banking-sector indicators moved alongside the NPL ratio in Ghana, and what do econometric and scenario-based models suggest about the transmission of macro-financial shocks?**

The analysis is organised around four tasks:

1. Describe the evolution of the NPL ratio and selected macro-financial indicators.
2. Examine contemporaneous associations between NPLs and potential explanatory variables.
3. Explore dynamic relationships among selected variables using a vector autoregression (VAR).
4. Translate selected macroeconomic assumptions into conditional NPL scenarios.

## Data

The repository contains two source files:

- data/raw/data_first.csv: monthly banking and macro-financial indicators.
- data/raw/data_first2.csv: quarterly real GDP observations.

The monthly source file contains observations from January 2010 to December 2025. The GDP source file contains quarterly observations from 2006Q1 to 2025Q3. These are source-file coverage dates, not a claim that every model uses every observation. Missing values and transformations can change the effective estimation sample.

| Indicator | Description | Source recorded in the source file |
|---|---|---|
| NPL ratio | Non-performing loans ratio | Bank of Ghana |
| Monetary policy rate | Policy interest rate | Bank of Ghana |
| CPI | Consumer price index | Ghana Statistical Service |
| Exchange rate | Ghana cedi per US dollar | Bank of Ghana |
| Broad money | Monetary aggregate (M2+) | Bank of Ghana |
| Gold price | Realised gold price, USD per fine ounce | Reuters |
| Return on assets | Banking-sector profitability indicator | Bank of Ghana |
| Capital adequacy ratio | Banking-sector capital indicator | Bank of Ghana |
| Real GDP | Quarterly GDP at 2013 prices | Ghana Statistical Service |

See data/README.md for the variable dictionary and source notes.

### Frequency and measurement

Most banking and macro-financial series are monthly, while real GDP is quarterly. The current preparation workflow converts quarterly GDP to a monthly index by linear interpolation so that it can be aligned with monthly indicators. Those interpolated values are estimates between quarterly observations; they are **not observed monthly GDP**. This choice should be considered when interpreting monthly regression or VAR results. A more complete macroeconomic study would compare this approach with quarterly modelling or a documented temporal-disaggregation method.

The raw monthly file also contains missing values for some indicators near the end of the sample. Estimation samples should therefore be reported for each model rather than assumed to be identical.

## Analytical approach

### Exploratory analysis

The notebooks examine the time paths, distributions and pairwise relationships of the main indicators. Figures in figures/ are exploratory outputs; their interpretation should be read alongside the notebook code and data definitions.

### OLS regression

The regression module provides a reusable ordinary least squares wrapper. OLS is used as a descriptive conditional-association model. With trending macroeconomic series, serially correlated residuals and possible structural changes, a high in-sample fit or a small conventional p-value is not, by itself, evidence of a stable economic relationship or causality.

Previously reported coefficient significance and fit statistics are not presented here as independently verified headline findings. They should be regenerated from the current data and code before being used in a research summary.

### Vector autoregression

The VAR module supports multivariate lag models and impulse-response calculations. The transformation applied before estimation, lag order, variable ordering and identification assumptions matter for the interpretation of impulse responses. A reduced-form VAR response should not automatically be described as a causal structural shock.

### Scenario analysis

The stress-testing module fits a standardised linear regression and evaluates user-specified predictor values. This is best understood as a **conditional scenario exercise**, not a bank-level regulatory stress test or a validated forecast. Its results depend on the historical sample, model specification and plausibility of the scenario inputs. Extrapolation beyond the observed data range should be treated cautiously.

## Selected figures

The repository includes the following existing outputs:

- [NPL timeline](figures/initial_npl_trend.png)
- [Correlation matrix](figures/correlation_matrix.png)
- [Monetary policy dynamics](figures/monetary_policy_dynamics.png)
- [Impulse responses](figures/irf_npl_shocks.png)
- [Scenario results](figures/npl_stress_testing_results.png)

These figures are analysis outputs, not a substitute for inspecting the notebooks that generated them.

## Repository structure

~~~text
.
├── data/
│   ├── raw/                 # Source CSV files
│   ├── processed/           # Prepared analysis dataset
│   └── README.md            # Data dictionary and source notes
├── docs/                    # Installation and usage notes
├── figures/                 # Saved analysis figures
├── notebooks/               # Research workflow
├── src/ghana_banking/
│   ├── data/                # Data loading and preparation
│   ├── modeling/            # OLS, VAR and scenario models
│   └── plotting/            # Time-series and diagnostic plots
├── tests/                   # Unit tests
├── requirements.txt
├── requirements-dev.txt
└── setup.py
~~~

## Reproducing the analysis

The project uses Python. The steps below assume Git and Python are installed.

~~~bash
git clone https://github.com/cube0002/ghana-banking-asset-quality.git
cd ghana-banking-asset-quality
python -m venv .venv
~~~

Activate the environment.

**Windows PowerShell**
~~~powershell
.venv\Scripts\Activate.ps1
~~~

**macOS / Linux**
~~~bash
source .venv/bin/activate
~~~

Install the project and development dependencies:

~~~bash
python -m pip install --upgrade pip
pip install -e .
pip install -r requirements-dev.txt
~~~

Run the tests and open the notebooks:

~~~bash
pytest tests/ -v
jupyter lab notebooks/
~~~

Run the notebooks in numerical order, starting with data preparation. The notebooks are the research record; the package under src/ contains reusable functions.

## Interpretation and limitations

- The data are aggregate banking-sector indicators. They do not identify differences across individual banks or borrower groups.
- The analysis is observational. Contemporaneous regression coefficients and correlations do not establish causal effects.
- Linear interpolation of quarterly GDP creates estimated monthly values and can affect time-series inference.
- Macro-financial series may be non-stationary, serially correlated, collinear or affected by structural breaks. These properties require explicit testing and suitable inference.
- VAR impulse responses depend on model specification and the shock-identification convention.
- The scenario model is a reduced-form linear exercise. It does not model bank-level balance sheets, capital depletion, feedback loops or supervisory loss parameters.
- Results are conditional on the supplied data and assumptions. They should not be interpreted as forecasts or policy recommendations without further validation.

These limitations are part of the research, not footnotes to hide.

## Sources

The source files identify the Bank of Ghana, Ghana Statistical Service and Reuters as data providers. For background and updated releases, consult the institutions directly:

- [Bank of Ghana](https://www.bog.gov.gh/)
- [Ghana Statistical Service](https://statsghana.gov.gh/)
- [Reuters](https://www.reuters.com/)

The original downloaded source files are retained in data/raw/. Consult the source institutions for current definitions, revisions and usage conditions.

## Author and citation

**Kwame Ansere-Mensah**

~~~bibtex
@software{ansere_mensah_ghana_banking_asset_quality,
  author = {Ansere-Mensah, Kwame},
  title  = {Ghana Banking Asset Quality},
  year   = {2025},
  url    = {https://github.com/cube0002/ghana-banking-asset-quality}
}
~~~

## License

This repository is distributed under the MIT License. See LICENSE for details.
