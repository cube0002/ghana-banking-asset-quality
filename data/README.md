# Data Sources & Dictionary

## Variable Definitions

| Variable | Mnemonic | Description | Unit | Source |
|----------|----------|-------------|------|--------|
| Policy Rate | GHA_INR_1 | Monetary policy interest rate | % p.a. | Bank of Ghana |
| Inflation (CPI) | GH_PRI_1 | Consumer Price Index (2021=100) | Index | Ghana Statistical Service |
| Exchange Rate | GHA_EXR_1 | GHS per USD | GHC/USD | Bank of Ghana |
| Money Supply | GHA_MAG_8 | Broad money | GHC million | Bank of Ghana |
| Gold Price | GHA_CMP_06 | Gold price | USD/oz | Reuters |
| Capital Adequacy | GHA_FSI_5 | Capital adequacy ratio | % | Bank of Ghana |
| ROA | GHA_FSI_2 | Return on assets | % | Bank of Ghana |
| NPL Ratio | GHA_FSI_1 | Non-performing loans ratio | % | Bank of Ghana |
| Real GDP | GHA_NAT_1 | Real GDP (2013 prices) | GHC million | Ghana Statistical Service |

## Data Sources

- **Bank of Ghana**: https://www.bog.gov.gh/
- **Ghana Statistical Service**: https://www.statsghana.gov.gh/
- **Reuters**: https://www.reuters.com/

## How to Download

Run: `python data/download_data.py`
