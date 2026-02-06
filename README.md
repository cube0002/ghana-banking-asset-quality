# Ghana-banking-asset-quality
An empirical analysis of asset quality and macroeconomic resilience in Ghana’s banking sector (2010–2025)
=======
## Data Sources

This project uses official macroeconomic and banking-sector data for Ghana from the following institutions:

### Banking & Financial Indicators
**Bank of Ghana (BoG)**  
  Policy Interest Rate (GHA_INR_1)  
  Exchange Rate, GHS/USD (GHA_EXR_1)  
  Monetary Aggregates (GHA_MAG_8)  
  Financial Soundness Indicators:
    Capital Adequacy Ratio (GHA_FSI_5)
    Return on Assets (GHA_FSI_2)
    Non-Performing Loans Ratio (GHA_FSI_1)

### Inflation
**Ghana Statistical Service (GSS)**  
  Consumer Price Index (GH_PRI_1)

### Commodity Prices
**Reuters**
  - Gold Price, USD per fine ounce (GHA_CMP_06)

### Output / Economic Activity
**Ghana Statistical Service (GSS)**  
  Real Gross Domestic Product, quarterly (GHA_NAT_1)

All monthly indicators are harmonized to a common monthly frequency. Quarterly GDP data is converted to monthly frequency using linear interpolation for analytical consistency.
---
## Variable Definitions

| Variable | Mnemonic | Description | Unit | Frequency | Source |
|--------|---------|------------|------|----------|--------|
| Policy Rate | GHA_INR_1 | Monetary policy interest rate | % p.a. | Monthly | Bank of Ghana |
| Inflation (CPI) | GH_PRI_1 | Consumer Price Index (2021=100) | Index | Monthly | GSS |
| Exchange Rate | GHA_EXR_1 | GHS per USD | GHC/USD | Monthly | BoG |
| Money Supply | GHA_MAG_8 | Broad money | GHC million | Monthly | BoG |
| Gold Price | GHA_CMP_06 | Gold price | USD/oz | Monthly | Reuters |
| Capital Adequacy | GHA_FSI_5 | Capital adequacy ratio | % | Monthly | BoG |
| ROA | GHA_FSI_2 | Return on assets | % | Monthly | BoG |
| NPL Ratio | GHA_FSI_1 | Non-performing loans ratio | % | Monthly | BoG |
| Real GDP | GHA_NAT_1 | Real GDP (2013 prices) | GHC million | Quarterly | GSS |
##  Exploratory Data Analysis (EDA)

This section summarizes the key insights from the exploratory phase, focusing on the interaction between macroeconomic volatility and the resilience of Ghana’s banking sector.

### 1. Macro-Financial Timeline & Structural Shocks

The Non-Performing Loan (NPL) Ratio was analyzed alongside major macroeconomic and regulatory events:

 **2017–2019 Banking Sector Cleanup:**  
  A sharp spike in NPLs (peaking above 20%) reflects regulatory enforcement and the recognition of legacy bad debts following the Bank of Ghana–led sector cleanup. This period represents a transparency shock rather than a sudden deterioration in borrower fundamentals.

 **COVID-19 Period (2020–2021):**  
  Contrary to expectations, asset quality remained relatively stable. This likely reflects regulatory forbearance, loan restructuring programs, and swift policy interventions that cushioned borrowers and financial institutions.

**2022–2023 Domestic Debt Crisis:**  
  The Domestic Debt Exchange Programme (DDEP), combined with inflation exceeding 50%, represents the most severe macro-financial stress episode in the dataset, with renewed pressure on bank balance sheets and borrower repayment capacity.

### 2. Monetary Policy & Inflation Dynamics

Monetary policy conditions were examined by comparing the Monetary Policy Rate (MPR) with inflation dynamics:

**Policy Discipline:**  
  For much of the sample period, the central bank maintained positive real interest rates, supporting currency stability and anchoring inflation expectations.

**2022 Policy Lag:**  
  During the inflation surge of 2022, inflation significantly outpaced the policy rate, resulting in negative real interest rates. This environment placed pressure on bank margins and weakened borrower repayment capacity.

### 3. Sectoral Health: Profitability vs. Capitalization

To assess the structural resilience of the banking sector, profitability and capitalization indicators were analyzed:

**Profitability (ROA):**  
  Return on Assets is predominantly clustered between 3% and 5%, indicating that despite periods of elevated risk, the banking sector remained broadly profitable.

**Solvency (CAR):**  
  The Capital Adequacy Ratio remains well above the 13% regulatory minimum for most banks, suggesting that post-2017 reforms created a durable capital buffer against macroeconomic shocks.

### 4. Correlation & Leading Indicators of Credit Risk

Correlation and regression analysis were used to identify macro-financial drivers of asset quality:

**Exchange Rate Channel:**  
  USD/GHS depreciation exhibits the strongest positive relationship with NPL growth (R² ≈ 0.51), highlighting the role of foreign exchange exposure and imported inflation in credit risk transmission.

**Growth as a Stabilizer:**  
  Real GDP growth shows a consistent inverse relationship with NPLs, underscoring the counter-cyclical nature of credit risk and the importance of macroeconomic growth for financial stability.

Overall, the EDA results motivate a formal modeling and stress-testing framework to quantify macroeconomic impacts on banking sector asset quality.


## Statistical Modeling & Macroeconomic Drivers of NPLs

### Overview
This study employs a two-stage econometric strategy to analyze the determinants and dynamic propagation of credit risk in Ghana’s banking sector. The modelling framework combines static regression analysis with dynamic multivariate time-series methods to ensure both interpretability and robustness.

Beginning with a multivariate Ordinary Least Squares (OLS) regression to identify contemporaneous macro-financial drivers of banking sector asset quality.

$$NPL_{t} = \alpha + \beta_{1}MPR_{t} + \beta_{2}CPI_{t} + \beta_{3}USD_{t} + \beta_{4}M2_{t} + \beta_{5}Gold_{t} + \beta_{6}GDP_{t} + \beta_{7}CAR_{t} + \beta_{8}ROA_{t} + \varepsilon_{t}$$

Where:

NPL = Non-Performing Loan Ratio

MPR = Monetary Policy Rate

CPI = Consumer Price Index (inflation proxy)

USD = USD/GHS exchange rate

M2 = Total liquidity

Gold = Realised gold price

GDP = Real GDP

CAR = Capital Adequacy Ratio

ROA = Return on Assets

**Analysis Period:** January 2010 – July 2025 (187 monthly observations) 
**Model Performance:** R² = 0.597 (explains 59.7% of NPL variation), F-statistic = 32.96 (p < 0.001)

% (further deterioration expected)

**Statistically Significant Drivers (5% level):**

Inflation (CPI): Positive and significant → inflation deteriorates asset quality

Exchange Rate (USD/GHS): Significant → currency instability amplifies credit risk

Real GDP: Negative → economic growth improves loan performance

Gold Prices: Negative → safe-haven effects and portfolio rebalancing

ROA: Strong negative effect → profitable banks manage credit risk better

Non-significant variables:
Monetary Policy Rate, Total Liquidity (M2+), Capital Adequacy Ratio

Diagnostic Notes

Durbin-Watson ≈ 0.40 indicates serial correlation, motivating dynamic modelling.

High condition number suggests multicollinearity, expected in macroeconomic systems.

Residuals exhibit non-normality, reinforcing the need for time-series methods.

### Vector Autoregression (VAR)

Impulse Response Functions (12-month horizon) reveal how shocks propagate through the financial system:

**Exchange Rate Shock** 
- Impact at 1 month: +0.25 pp NPL increase
- Peak effect: Months 1–2
- Duration: 12+ months with gradual decay
- Severity: **CRITICAL**

**NPL Shock (Persistence)** 
- Impact at 1 month: +0.0175 pp persistence
- Decay pattern: Sharp decline Months 1–3
- Duration: 12+ months
- Severity: **MODERATE**

**Monetary Policy Shock** 
- Impact at 1 month: -0.0157 pp
- Pattern: Months 2–4 oscillation
- Duration: Visible throughout 12-month window
- Severity: **MODERATE**

**GDP Shock** 
- Impact at 1 month: -0.00018 pp (minimal)
- Duration: Limited persistence
- Severity: **LOW**

## Stress Testing & Scenario Analysis
**Overview**

Following the identification of key macroeconomic drivers and their dynamic interactions, a forward-looking stress testing framework is implemented to quantify the vulnerability of Ghana’s banking sector asset quality under adverse but plausible macro-financial scenarios.

Stress testing is conducted in a separate notebook to ensure modularity and conceptual separation from the econometric modeling stage. While the VAR framework captures dynamic shock propagation, the stress tests translate macroeconomic stress into levels of NPL ratios, which are directly relevant for supervisory and policy analysis.

**Methodology**
A reduced form predictive model is estimated using macroeconomic variables identified as economically and statistically relevant in prior analysis. To ensure comparability across drivers, all regressors are standardized prior to estimation.

The stress testing relationship can be summarized as:

NPLₜ = f(MPRₜ, USDₜ, CPIₜ, GDPₜ)

Where:

MPR – Monetary Policy Rate (financing cost channel)

USD – USD/GHS exchange rate (currency mismatch and imported inflation)

CPI – Consumer Price Index (macroeconomic instability proxy)

GDP – Real Gross Domestic Product (repayment capacity channel)

The model is calibrated using historical data and evaluated under counterfactual macroeconomic scenarios relative to the most recent observed conditions.

**Stress Scenarios**

Four macro-financial scenarios are considered:

Baseline
Continuation of prevailing macroeconomic conditions.

Moderate Monetary Tightening
A policy-induced increase in interest rates combined with mild output deceleration.

Severe Currency Crisis
Sharp exchange-rate depreciation accompanied by elevated inflation and tighter monetary conditions.

Severe Economic Recession
A significant contraction in real economic activity with weaker price pressures.

## Stress Test Results

| Scenario | Predicted NPL (%) | Δ vs Current (pp) | vs Baseline (pp) |
| :--- | :---: | :---: | :---: |
| **Baseline** | 24.39 | +2.65 | 0.00 |
| **Moderate Tightening** | 25.26 | +3.52 | +0.87 |
| **Severe Currency Crisis** | 27.21 | +5.47 | +2.82 |
| **Severe Recession** | 24.89 | +3.15 | +0.50 |

Interpretation of Stress Outcomes

Key findings from the stress tests are as follows:

Exchange Rate Dominance:
The Severe Currency Crisis scenario produces the largest deterioration in asset quality, confirming the exchange-rate channel as the most critical driver of systemic credit risk.

Monetary Tightening Effects:
Interest rate increases materially worsen loan performance through higher debt servicing costs, though the effect is smaller than under currency stress.

Growth Sensitivity":
Economic contractions increase NPLs, but their impact is more moderate unless combined with financial instability.

Baseline Vulnerability:
Even under baseline conditions, predicted NPL levels remain elevated, suggesting persistent structural fragilities despite post-2017 banking sector reforms.

**Conclusion**

This study provides an empirical assessment of asset quality dynamics and macroeconomic resilience in Ghana’s banking sector over the period 2010–2025. By integrating exploratory data analysis, multivariate regression, dynamic VAR modelling, and scenario-based stress testing, the analysis offers both structural and forward-looking insights into the drivers of non-performing loans (NPLs).

The results confirm that macroeconomic instability is the dominant transmission channel for credit risk in Ghana. Exchange rate depreciation and inflation emerge as the most statistically and economically significant drivers of NPL deterioration, while real economic growth plays a stabilising role. Profitability (ROA) is shown to materially mitigate credit risk, highlighting the importance of internal bank strength alongside macroeconomic conditions.

Dynamic analysis using Vector Autoregression reveals strong shock persistence, particularly from exchange rate disturbances, which generate immediate and prolonged increases in NPLs. In contrast, monetary policy shocks exhibit more moderate and transitory effects, while GDP shocks have comparatively limited short-run impact. These findings underscore the asymmetric nature of macro-financial shock propagation in a small open economy with high import dependence and foreign-currency exposure.

The stress testing framework reinforces these conclusions. Under severe but plausible macroeconomic scenarios, especially a currency crisis, the banking sector experiences substantial increases in predicted NPL ratios relative to both current conditions and baseline expectations. While post-2017 regulatory reforms have strengthened capital buffers, the results indicate that systemic vulnerability remains closely tied to external and inflationary shocks.


### Project status: Complete
*Last updated: 05/01/26*
