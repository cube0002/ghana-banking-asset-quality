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
This section presents quantitative analysis of the macroeconomic variables that statistically drive Non-Performing Loan (NPLs) ratios in Ghana's banking sector. Using OLS regression, time series econometric modelling.

**Analysis Period:** January 2010 – July 2025 (187 monthly observations)  
**Model Specification:** OLS Multiple Regression with 8 macroeconomic regressors  
**Model Performance:** R² = 0.597 (explains 59.7% of NPL variation), F-statistic = 32.96 (p < 0.001)

% (further deterioration expected)

### Primary Statistical Drivers of NPLs

#### 1. **Inflation (Consumer Price Index)** 
- **Correlation:** +0.584 (STRONGEST)
- **Regression Coefficient:** +0.123 (p < 0.001) ✓ HIGHLY SIGNIFICANT
- **Elasticity:** +1.23 pp NPL increase per 10-point CPI rise
- **Mechanism:** Inflation erodes borrower real income and increases debt servicing burden
- **Current CPI:** 259.1 (elevated risk)

#### 2. **USD Exchange Rate Depreciation** 
- **Correlation:** +0.554 (SECOND STRONGEST)
- **Regression Coefficient:** -0.772 (p = 0.008) ✓ STATISTICALLY SIGNIFICANT
- **Elasticity:** +0.77 pp NPL per 1 GHS/USD depreciation
- **30% Depreciation Scenario:** +4.64 pp increase in NPL ratio
- **Mechanism:** FX-exposed borrowers face margin compression; import costs surge; export revenues decline
- **Current Rate:** 10.42 GHS/USD

#### 3. **Return on Assets (ROA)** 
- **Correlation:** -0.311 (ONLY NEGATIVE DRIVER)
- **Regression Coefficient:** -1.290 (p < 0.001) ✓ HIGHLY SIGNIFICANT
- **Elasticity:** -1.29 pp NPL reduction per 1% ROA increase
- **Mechanism:** Profitable banks maintain stronger underwriting, active monitoring, and provisioning capacity
- **Current ROA:** 5.59%

#### 4. **Real GDP Growth** —
- **Correlation:** +0.421 (moderate, counterintuitive)
- **Regression Coefficient:** -0.0002 (p = 0.395) NOT SIGNIFICANT
- **Interpretation:** Direct channel weak; effects operate through sectoral composition

#### 5. **Monetary Policy Rate** 
- **Correlation:** +0.453
- **Regression Coefficient:** -0.030 (p = 0.678) NOT SIGNIFICANT
- **Interpretation:** Works indirectly through growth/inflation channels; policy endogeneity

#### 6. **Total Liquidity (M2+)** 
- **Correlation:** +0.559
- **Regression Coefficient:** 0.000009 (p = 0.337) NOT SIGNIFICANT
- **Interpretation:** Reflects policy responses to crises rather than independent driver

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


