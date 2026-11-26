# Research design and econometric protocol

**Status:** Research protocol, version 1.7  
**Project:** Ghana Banking Asset Quality  
**Branch:** portfolio/research-overhaul  
**Protocol date:** 22 November 2026

## 1. Purpose and status

This document sets out the research design to be followed before the project reports new econometric findings. It is a versioned protocol, not a record of completed empirical results. The hypotheses below are motivated expectations to be assessed, not conclusions already supported by the data.

The purpose is to make the empirical work reproducible and academically defensible: define the research question, explain the economic channels, document the data and frequency choices, select models only after examining time-series properties, and report diagnostics and robustness checks alongside estimates.

The analysis uses aggregate banking-sector data. It cannot identify differences between individual banks, borrower groups, industries or loan currencies. It is observational and should be interpreted as evidence about conditional associations and dynamic co-movement unless a defensible identification strategy is added.

## 2. Research question and objectives

### Main research question

**What are the short-run and long-run relationships between macroeconomic conditions and banking-sector asset quality in Ghana, and how do those relationships change during periods of macro-financial stress?**

### Objectives

1. Describe the evolution of the aggregate non-performing loan (NPL) ratio and selected macro-financial indicators.
2. Test whether the NPL ratio is associated with inflation, exchange-rate movements, monetary conditions and real economic activity, allowing for delayed effects where supported by the data.
3. Determine whether a stable long-run relationship is supported by the time-series evidence, rather than assuming one.
4. Examine dynamic interactions among a small, economically justified set of variables where the sample and diagnostics support a VAR or VECM.
5. Evaluate conditional NPL scenarios and their uncertainty using chronological, out-of-sample validation.

### Research questions for the empirical chapters

- How has the NPL ratio evolved over the available monthly sample, and do its movements coincide with changes in macro-financial conditions?
- Do inflation, cedi depreciation and monetary-policy changes have short-run associations with subsequent NPL movements?
- Is there evidence of a long-run level relationship between the NPL ratio and selected macro-financial variables?
- Are the estimated relationships stable across the sample, or do they vary around identifiable macro-financial regime changes?
- How accurately can a parsimonious model predict NPL movements at realistic forecast horizons, and how sensitive are conditional scenarios to their assumptions?

## 3. Economic framework and hypotheses

The working transmission mechanism is that macroeconomic conditions can affect household and business cash flows, debt-servicing capacity, funding costs and the value of foreign-currency liabilities. These mechanisms can influence loan performance with delays. The aggregate data do not directly measure all of these channels, so the hypotheses must remain cautious.

| Factor | Expected transmission mechanism | Working expectation |
|---|---|---|
| Real GDP growth | Stronger output and income generally improve repayment capacity; a slowdown can weaken borrower cash flows. | Higher GDP growth is expected to be associated with lower NPLs. |
| Cedi depreciation | Depreciation can increase the local-currency cost of foreign-currency debt and imported inputs for exposed borrowers. | Greater depreciation may be associated with higher NPLs, potentially with lags. The aggregate dataset does not identify borrowers' currency exposures. |
| Inflation | Higher prices can reduce real household income and increase firms' operating costs, but nominal revenue, loan growth and policy responses can complicate the effect. | A positive association with NPLs is plausible, but the sign is not treated as predetermined. |
| Monetary policy rate | Higher rates may pass through to lending rates and debt-service costs; policy rates can also rise in response to inflation or financial conditions. | Increases may precede higher NPLs, but reverse policy responses and endogeneity must be considered. |
| Broad money growth (M2+) | Liquidity and credit conditions can support repayment, while rapid credit expansion can also weaken underwriting standards. | No unambiguous sign is imposed. |
| Capital adequacy and profitability | Capital and returns can affect resilience, but they may also deteriorate as asset quality worsens. | Treat as potentially endogenous banking-sector outcomes, not automatically as exogenous causes of NPLs. |

These expectations lead to the following hypotheses for empirical assessment:

- **H1:** Weaker real economic activity is associated with a higher NPL ratio.
- **H2:** Cedi depreciation is associated with a higher NPL ratio, potentially after a delay.
- **H3:** Higher inflation and tighter monetary conditions may be followed by higher NPLs, although the estimated relationship may be sensitive to lag structure and policy endogeneity.
- **H4:** The relationships are not necessarily constant over the full sample; structural change or regime sensitivity is plausible and will be tested rather than assumed.

The project will not present these hypotheses as causal statements. A causal interpretation would require additional identification assumptions and data that are not currently available.

## 4. Data, provenance and sample design

### 4.1 Current source files

The current repository records the following source coverage:

| Dataset | Frequency | Recorded coverage | Main use |
|---|---|---|---|
| Monthly banking and macro-financial indicators | Monthly | January 2010–December 2025 | Main monthly analysis |
| Real GDP at 2013 constant prices | Quarterly | 2006Q1–2025Q3 | Separate quarterly analysis and robustness |

These are source-file coverage dates, not guaranteed estimation samples. Missing observations, transformations, lags and the intersection of variables will determine the effective sample for each model. Every results table must report its first and last observation, frequency, number of observations and variables used.

### 4.2 Frequency discipline

The main specification will be monthly and will **exclude interpolated GDP**. The quarterly GDP series must remain at its source frequency. Linear interpolation of quarterly GDP does not create observed monthly activity or new independent information; it must not be used as if it were a measured monthly series in the primary monthly VAR or ARDL.

A separate quarterly robustness dataset may be constructed by aligning observed quarterly GDP with monthly banking and macro-financial indicators aggregated using documented rules. The initial overlap with the monthly banking sample begins no earlier than 2010 unless a separately validated banking series supports an earlier start. This leaves a much smaller quarterly sample, so that exercise should be parsimonious and described as a robustness analysis rather than the main source of inference.

Quarterly aggregation rules must follow the economic meaning of each series:
- For point-in-time ratios or balance-sheet stocks, use the quarter-end observation as the primary convention, subject to confirming the provider's measurement definition.
- For monthly-average exchange rates, use the arithmetic quarterly average if the objective is to represent the average exchange-rate environment during the quarter.
- For price indices and monetary stocks, define whether the quarter-end or quarterly average is appropriate and keep that convention consistent across specifications.
- Calculate quarterly GDP growth from the original quarterly real-GDP series, not from interpolated monthly values.

Where economically defensible, report an alternative aggregation convention as a sensitivity check. Do not switch aggregation rules after inspecting which version gives the preferred coefficient.

### 4.3 Data validation and vintage control

Before estimation, maintain a source and measurement register with one row per series. Record its provider, source URL, published definition, unit, frequency, first and last available observations, date downloaded, source vintage, known revisions, missingness, transformation and any known comparability break.

Required checks include:
- parse dates and numeric values explicitly; remove metadata/footer rows only through documented rules;
- check duplicate dates, duplicate indicator codes, impossible values and unexpected changes in units;
- report missing values by variable and date; do not silently fill gaps;
- inspect extreme changes against the original publication before winsorising, deleting or transforming them;
- preserve the original downloaded files and record each new data vintage;
- reconcile variable definitions before joining series from different publications.

The Bank of Ghana publication snapshots archived in the repository are rounded, manually transcribed publication extracts. The July, September and November 2026 PDFs carry a DRAFT watermark and state that figures are subject to revision. They are useful for documenting publication vintages and conducting cautious overlap checks, but they must not be treated as certified final data or spliced into the long monthly series without checking definitions, units, transcription accuracy and overlap with the underlying source. Identical values at one-decimal precision do not rule out revisions below the displayed precision.

The experimental GSS StatsBank connectors and configurable CSV refresh process must be described as experimental or configurable until a live extraction has been run successfully and reconciled against provider publications. A workflow existing in the repository is not evidence that the project is connected to a live official data feed.

### 4.4 Core and secondary variables

The primary dependent variable is the published aggregate NPL ratio. Before estimation, document whether the provider defines it as a ratio of NPLs to gross loans, how the numerator and denominator are classified, and whether there are changes in classification or reporting conventions.

The initial monthly macro-financial candidate set is:
- CPI, used to construct monthly inflation;
- GHS per USD exchange rate, used to construct cedi depreciation;
- M2+, used to construct broad-money growth;
- monetary policy rate, represented in level or change according to its measured properties and the economic specification.

GDP growth is reserved for the quarterly analysis. CAR and ROA may be examined in supplementary specifications or descriptive analysis, but should not be placed in the core explanatory set without addressing simultaneity and their potential response to asset quality. Gold price is an optional control only if its economic transmission channel and measurement comparability are justified in advance.

## 5. Variable transformations

Transformations will be chosen using economic interpretation and time-series diagnostics, not solely to obtain statistical significance.

Candidate transformations include:

| Series | Candidate transformation | Interpretation |
|---|---|---|
| CPI index | 100 × change in log CPI | Approximate monthly inflation rate; not annualised unless explicitly stated. |
| GHS per USD | 100 × change in log exchange rate | Approximate cedi depreciation; a positive value means more cedis per US dollar. |
| M2+ | 100 × change in log M2+ | Approximate monthly broad-money growth; not annualised unless explicitly stated. |
| Real GDP | 100 × quarterly log difference | Approximate quarterly real-GDP growth. |
| Policy rate | Level and/or first difference | Percentage-point level or change; choose based on integration properties and theoretical specification. |
| NPL ratio | Level and/or first difference | Percentage level or percentage-point change; do not confuse a percentage-point change with a percentage growth rate. |
| CAR and ROA | Levels and/or changes | Retain provider units and definitions; investigate breaks and potential simultaneity. |

For any transformed variable, state the formula, unit, timing convention and sample loss. A log transformation is not appropriate for non-positive observations. Seasonal adjustment should not be introduced without checking whether seasonality is present and explaining the method.

## 6. Empirical strategy and model-selection rules

Model choice is conditional on the observed properties of the data. No single model will be designated as the preferred model before the data diagnostics are complete.

### Stage 1: Descriptive and exploratory analysis

Produce:
- time-series plots with units, source and sample dates;
- descriptive statistics and missingness summaries;
- pairwise correlations clearly labelled as descriptive;
- plots of transformed series;
- a dated record of any apparent outliers, definitional changes or candidate break periods.

Correlation is not evidence of direction or causality. The exploratory stage must not be used to select a model solely because it produces favourable coefficients.

### Stage 2: Time-series properties

For each series considered in an estimated model:
1. Plot the level and candidate transformed series.
2. Assess the deterministic specification: intercept, deterministic trend or neither, based on the plot and economic context.
3. Apply the Augmented Dickey–Fuller (ADF) test and Phillips–Perron (PP) test, recording the null hypothesis, deterministic terms, lag or bandwidth choice and effective sample.
4. Complement unit-root tests with KPSS, which reverses the null relative to common unit-root tests.
5. Examine sensitivity to lag selection and plausible structural breaks. A break-aware unit-root test such as Zivot–Andrews may be used as a sensitivity analysis, not as a mechanical replacement for economic judgment.
6. Record the evidence and uncertainty about the integration order for each series.

Do not classify a variable as I(1) based on a single test. Conflicting tests, break-sensitive results and low power in finite samples must be discussed. The project must not apply standard ARDL bounds critical values when any model variable is I(2) or higher.

### Stage 3: Model eligibility and cointegration screening

Working integration assessments are passed through a conservative screening gate. All-I(0) systems may proceed to stationary dynamic regression or VAR candidates. Mixed I(0)/I(1) systems may be considered for ARDL bounds testing only when no variable is I(2), the sample and deterministic case are suitable, and a plausible level relationship exists. All-I(1) systems may proceed to Johansen trace and maximum-eigenvalue rank testing; a VECM is eligible only if rank evidence supports cointegration. Conflicting or unresolved integration evidence blocks automatic model selection. The software gate is a screening aid, not a substitute for reviewing the test tables and economic specification.

### Stage 4: Primary monthly model

The main candidate is a parsimonious dynamic single-equation model for the NPL ratio, with inflation, cedi depreciation, monetary conditions and appropriate lags. An ARDL/error-correction framework is eligible only if the integration evidence supports it.

- If the variables are a mixture of I(0) and I(1), none is I(2), the sample is adequate, and a level relationship is economically plausible, estimate an ARDL and conduct bounds testing using the appropriate deterministic case and critical values.
- If a level relationship is supported, report the error-correction representation, long-run coefficients, short-run dynamics, adjustment coefficient and diagnostics. Explain the economic units of every coefficient.
- If the bounds test does not support a level relationship, do not report long-run multipliers as established. Use a stationary short-run model in the appropriate transformations.
- If all included variables are stationary, use a parsimonious stationary dynamic regression or VAR as justified by the research question; cointegration machinery is unnecessary.
- If the relevant system variables are I(1) and cointegrated, a VECM may be considered. Select the cointegrating rank and deterministic specification transparently and keep the system small enough for the available sample.
- If the variables are stationary after transformation and the question concerns joint dynamics, a stationary VAR may be used with a parsimonious lag order.

The ARDL approach follows the bounds-testing framework of Pesaran, Shin and Smith (2001). The method accommodates regressors that are I(0) or I(1), but not I(2); the deterministic case and finite-sample limitations matter. The Johansen framework is the reference for system cointegration and VECM analysis. The reusable VECM wrapper requires reviewed I(1) labels for every included series and an explicitly reviewed cointegration rank; it reports adjustment coefficients, cointegrating vectors, short-run coefficients, residual covariance, and residual whiteness/normality diagnostics. It does not select the rank or infer structural causality.

### Stage 5: VAR/VECM analysis

A multivariate model is supplementary to the main NPL equation unless the research objectives and sample justify it. Limit the system to a small group of variables supported by the economic framework and data availability.

For every VAR/VECM:
- compare AIC, BIC and HQIC over a prespecified feasible lag range;
- justify the final lag choice in light of sample size and parameter count;
- report the estimation sample, transformations and deterministic terms;
- test stability and residual serial correlation;
- inspect heteroskedasticity and residual distribution, noting that normality is not a substitute for other diagnostics;
- assess sensitivity to lag length, sample period and variable composition.

Reduced-form VAR innovations are not automatically structural economic shocks. If orthogonalised impulse responses are reported, state and justify the ordering and contemporaneous restrictions. Generalised impulse responses can be reported as an alternative, with their interpretation stated clearly. Where feasible, provide uncertainty bands. The reusable VAR implementation now exposes pointwise Monte Carlo simulation bands; report the replication count, seed, significance level, whether responses are orthogonalised, and the variable ordering if Cholesky orthogonalisation is used. These are conditional simulation bands, not simultaneous confidence bands or causal identification. Label the response horizon in the correct time unit (months for a monthly model, quarters for a quarterly model).

Forecast error variance decompositions and impulse responses are conditional on the chosen specification and identification convention. Do not describe a reduced-form impulse response as a causal policy effect without defensible structural restrictions.

Toda–Yamamoto augmented VAR testing may be considered as a supplementary test of predictive content when its integration-order and lag assumptions are met. Any result should be described as Granger-predictive evidence, not structural causality.

### Stage 6: Structural change and stability

The sample spans different macro-financial environments. Parameter constancy must be investigated rather than assumed.

Use recursive estimates, rolling estimates, CUSUM-type procedures and parameter-constancy tests where suitable. The current reusable implementation reports OLS CUSUM and Hansen parameter-stability tests alongside rolling-window coefficients. These diagnostics are conditional on a prespecified, defensible stationary regression; rolling coefficients are descriptive and do not identify formal break dates. A Bai–Perron multiple-break analysis may be considered separately for a sufficiently parsimonious regression with an adequate sample and defensible trimming/minimum segment size. Do not describe rolling coefficient changes or a one-break Zivot–Andrews unit-root test as a Bai–Perron multiple-break result. Report the break-selection procedure and uncertainty around estimated dates.

Known-event indicators may be used only where the event date and mechanism are justified by an external source and specified transparently. Avoid adding event dummies or selecting subsamples solely because they improve the result. Report full-sample results alongside pre-specified or statistically justified regime sensitivities.

### Stage 7: Diagnostics and inference

At a minimum, assess the following for the selected model:

| Issue | Relevant checks | Reporting requirement |
|---|---|---|
| Residual autocorrelation | Breusch–Godfrey or Ljung–Box for single equations; Portmanteau/LM tests for VARs | Report test, lag order, p-value and implication. |
| Heteroskedasticity | Breusch–Pagan/White or ARCH-type tests as appropriate | Report whether variance instability is material. |
| Functional form | Residual plots and RESET where meaningful | Explain limitations of the test. |
| Collinearity | Correlation matrix and VIF/condition diagnostics | Treat as a coefficient-precision issue, not an automatic reason to delete variables. |
| Stability | Recursive estimates, CUSUM-type checks, VAR roots | Report the relevant stability criterion. |
| Distribution and outliers | Residual plots, Q-Q plot and influence analysis | Do not remove observations without a documented data or modelling reason. |

Use heteroskedasticity-and-autocorrelation-consistent (HAC) standard errors as a sensitivity or inference choice where appropriate for a correctly specified regression. HAC inference does not repair non-stationary or spurious regressions, omitted-variable bias, simultaneity, endogeneity or an incorrect functional form. State the kernel and bandwidth choice and test whether conclusions are sensitive to reasonable alternatives.

## 7. Robustness and sensitivity plan

The empirical chapter should report a compact set of planned robustness checks, not an unstructured search across specifications:

1. **Transformation sensitivity:** compare economically defensible level and difference/growth-rate representations where supported by the integration evidence.
2. **Lag sensitivity:** compare parsimonious alternatives and report whether key conclusions depend on one lag choice.
3. **Sample sensitivity:** assess whether conclusions change when the end of sample is restricted to avoid incomplete latest observations, and when a clearly justified subperiod is used.
4. **Break sensitivity:** compare stable-parameter estimates with justified break or regime specifications.
5. **Frequency sensitivity:** compare the main monthly model excluding GDP with a separate quarterly specification using original GDP observations.
6. **Variable-set sensitivity:** add CAR, ROA or gold price only in clearly labelled supplementary models with the endogeneity or measurement caveats stated.
7. **Inference sensitivity:** compare conventional and HAC inference only after the stationarity and specification requirements have been addressed.

Do not report only the specification with the strongest significance. Maintain a model register containing each candidate, its theoretical rationale, transformations, sample, lag selection, diagnostics and reason for retention or rejection.

## 8. Conditional NPL scenario analysis and forecasting

The scenario component will be described as **conditional aggregate NPL scenario analysis**, not a regulatory bank-level stress test. The current data do not include bank-level loan books, borrower exposures, credit migration matrices, loss-given-default, exposure-at-default, capital waterfall or detailed supervisory balance-sheet information.

A defensible scenario exercise should:
- define a baseline, adverse and severe macroeconomic path over a stated horizon;
- identify each scenario variable, shock size, direction, timing and persistence;
- calibrate shocks from documented historical distributions or authoritative external scenarios; label analyst-designed assumptions as illustrative. The reusable historical calibration estimates univariate AR(1) innovation quantiles, applies explicit adverse directions and geometric shock-persistence assumptions, and does not preserve cross-variable dependence or joint tail probabilities;
- test sensitivity to prespecified shock quantiles and persistence values while holding the fitted ARDL specification fixed; this isolates scenario-assumption sensitivity and does not capture parameter or model-selection uncertainty;
- propagate macroeconomic paths through a dynamic NPL model where supported, rather than treating a static contemporaneous fitted value as a forecast. The reusable ARDL scenario-path engine now accepts common-horizon baseline/adverse/severe exogenous paths and returns conditional forecasts, pointwise intervals and point-estimate differences from baseline;
- report point estimates and prediction intervals or another justified uncertainty measure;
- compare performance with simple benchmarks such as a no-change forecast and a univariate autoregressive model;
- use expanding-window or rolling-origin backtesting, never random train/test splitting for time-series forecasting;
- report MAE and RMSE by forecast horizon, alongside the evaluation dates and benchmark results;
- compare the model with transparent benchmarks; the reusable VAR backtest includes an expanding historical-mean benchmark, while the reusable univariate AR benchmark reports no-change and expanding-mean comparisons with pointwise prediction-interval coverage and width;
- repeat every data-driven transformation, scaling, variable-selection and lag-selection step within each forecast origin's training sample;
- check for preprocessing leakage and ensure that all scalers, transformations and model selection steps use only information available at each forecast origin.

A scenario outcome is conditional on both the assumed macroeconomic path and the estimated model. It is not a probability statement unless scenario probabilities are separately justified. A model that performs poorly in chronological backtests should not be presented as a reliable forecast engine.

## 9. Interpretation, limitations and reporting standards

The final report must distinguish among:
- **descriptive evidence:** what happened in the observed data;
- **conditional association:** how variables relate after conditioning on the model's included variables;
- **predictive evidence:** whether past information improves forecasts or predictive tests;
- **causal evidence:** an effect identified under explicit assumptions that are credible for the data and research design.

The current aggregate observational dataset is best suited to the first three categories. Statistical significance alone does not establish causality.

Each main results table should report coefficient estimates, standard errors, confidence intervals or p-values, units, sample period, observation count, transformations, lag specification and relevant diagnostics. Figures should show units, frequency, date coverage and source. Explain economically meaningful magnitudes, not only statistical significance.

The final paper should include:
- a reproducible data and source-vintage appendix;
- a table defining each variable and transformation;
- a model-specification register;
- unit-root and cointegration decision tables;
- diagnostic and robustness results;
- forecast backtesting and scenario assumptions;
- a concise limitations section describing aggregate-data and identification constraints.

All notebooks must execute from a clean environment in numerical order before their outputs are treated as reproduced research evidence. Preserve code, environment/dependency versions and dated outputs. The passing unit-test suite validates tested software behaviour; it does not by itself validate the empirical model, source transcription or notebook outputs.

## 10. Decision gates before results are promoted

The project will use the following gates:

| Gate | Required evidence | What it permits |
|---|---|---|
| 1. Data integrity | Source/definition register, raw-file preservation, validation and missingness audit | Promote descriptive outputs to the main analysis record. |
| 2. Reproducibility | Clean end-to-end notebook execution and recorded environment | Treat generated tables and figures as reproduced. |
| 3. Time-series properties | Documented transformations, unit-root evidence and break sensitivity | Choose eligible model classes. |
| 4. Model adequacy | Parsimonious specification, residual and stability diagnostics | Interpret conditional coefficients and dynamic responses. |
| 5. Robustness | Planned sensitivity checks with transparent model register | Assess whether conclusions are specification-dependent. |
| 6. Forecast/scenario credibility | Chronological backtests, benchmark comparisons and uncertainty | Present forecast performance and conditional scenarios with calibrated caveats. |

No empirical conclusion should be promoted to the README's headline findings until the relevant gates have been met.

## 11. Core methodological references

- Bai, J. and Perron, P. (2003). “Computation and analysis of multiple structural change models.” *Journal of Applied Econometrics*, 18(1), 1–22. https://doi.org/10.1002/jae.659
- Johansen, S. (1991). “Estimation and hypothesis testing of cointegration vectors in Gaussian vector autoregressive models.” *Econometrica*, 59(6), 1551–1580. https://doi.org/10.2307/2938278
- Kwiatkowski, D., Phillips, P. C. B., Schmidt, P. and Shin, Y. (1992). “Testing the null hypothesis of stationarity against the alternative of a unit root.” *Journal of Econometrics*, 54(1–3), 159–178. https://doi.org/10.1016/0304-4076(92)90104-Y
- Dickey, D. A. and Fuller, W. A. (1979). “Distribution of the estimators for autoregressive time series with a unit root.” *Journal of the American Statistical Association*, 74(366a), 427–431. https://doi.org/10.1080/01621459.1979.10482531
- Phillips, P. C. B. and Perron, P. (1988). “Testing for a unit root in time series regression.” *Biometrika*, 75(2), 335–346. https://doi.org/10.1093/biomet/75.2.335
- Newey, W. K. and West, K. D. (1987). “A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix.” *Econometrica*, 55(3), 703–708. https://doi.org/10.2307/1913610
- Pesaran, M. H., Shin, Y. and Smith, R. J. (2001). “Bounds testing approaches to the analysis of level relationships.” *Journal of Applied Econometrics*, 16(3), 289–326. https://doi.org/10.1002/jae.616
- Sims, C. A. (1980). “Macroeconomics and reality.” *Econometrica*, 48(1), 1–48. https://doi.org/10.2307/1912017
- Toda, H. Y. and Yamamoto, T. (1995). “Statistical inference in vector autoregressions with possibly integrated processes.” *Journal of Econometrics*, 66(1–2), 225–250. https://doi.org/10.1016/0304-4076(94)01616-8
- Zivot, E. and Andrews, D. W. K. (1992). “Further evidence on the great crash, the oil-price shock, and the unit-root hypothesis.” *Journal of Business & Economic Statistics*, 10(3), 251–270. https://doi.org/10.1080/07350015.1992.10509904

For broader guidance on scenario design and the limits of system-wide stress testing, see the IMF's *Macro-Financial Stress Testing: Principles and Practices*, Chapter 2: https://www.elibrary.imf.org/display/book/9781484310717/ch002.xml

---

**Version 1.10 change note (26 November 2026):** Separates the forecast horizon from the historical episode length used to rank joint residual-block scenarios. The default episode length remains equal to the forecast horizon; longer prespecified episodes are scored in full, with only the first forecast-horizon innovations propagated. Metadata records the candidate count, selected episode dates and forecast-shock segment dates. This adds historical episode-length selection sensitivity; it does not create bootstrap uncertainty or joint probability calibration. Version 1.9 added normalised variable severity weights and a gated weight-sensitivity workflow; version 1.8 added joint historical scenario calibration using aligned residual blocks; version 1.7 added marginal scenario-assumption sensitivity analysis; version 1.6 added marginal historical AR(1)-innovation calibration; version 1.5 added conditional multi-period ARDL scenario-path propagation. The research question, sample, variable definitions and substantive model-selection principles are unchanged.

**Protocol note:** This document should be updated through a dated, version-controlled change whenever the research question, sample, variable definitions or model-selection rules materially change. Any such change should be explained rather than silently substituted after inspecting the results.
