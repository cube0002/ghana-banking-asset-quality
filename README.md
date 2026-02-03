# Ghana-banking-asset-quality
An empirical analysis of asset quality and macroeconomic resilience in Ghana’s banking sector (2010–2025)
=======
## Data Sources

This project uses official macroeconomic and banking-sector data for Ghana from the following institutions:

### Banking & Financial Indicators
- **Bank of Ghana (BoG)**  
  - Policy Interest Rate (GHA_INR_1)  
  - Exchange Rate, GHS/USD (GHA_EXR_1)  
  - Monetary Aggregates (GHA_MAG_8)  
  - Financial Soundness Indicators:
    - Capital Adequacy Ratio (GHA_FSI_5)
    - Return on Assets (GHA_FSI_2)
    - Non-Performing Loans Ratio (GHA_FSI_1)

### Inflation
- **Ghana Statistical Service (GSS)**  
  - Consumer Price Index (GH_PRI_1)

### Commodity Prices
- **Reuters**
  - Gold Price, USD per fine ounce (GHA_CMP_06)

### Output / Economic Activity
- **Ghana Statistical Service (GSS)**  
  - Real Gross Domestic Product, quarterly (GHA_NAT_1)

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
