# Data sources and dictionary

This directory separates the downloaded source files from the prepared analysis dataset.

- `raw/data_first.csv`: monthly banking and macro-financial indicators.
- `raw/data_first2.csv`: quarterly real GDP observations.
- `processed/ghana_banking_master.csv`: a prepared dataset retained from the original workflow.

The source files include metadata rows after the observations. The loader identifies dated observations by parsing the date or quarter field rather than relying on a fixed number of rows.

## Variable dictionary

| Source field / indicator | Mnemonic | Description | Unit | Frequency | Source recorded in file |
|---|---|---|---|---|---|
| Monetary Policy Rate (%) | GHA_INR_1 | Monetary policy interest rate | Percent p.a. | Monthly | Bank of Ghana |
| Consumer Price Index, All Items | GH_PRI_1 | Consumer price index | Index (2021=100) | Monthly | Ghana Statistical Service |
| USD Exchange Rate, monthly averages | GHA_EXR_1 | Ghana cedi per US dollar | GHS/USD | Monthly | Bank of Ghana |
| Total Liquidity (M2+) | GHA_MAG_8 | Broad money aggregate | GHS million | Monthly | Bank of Ghana |
| Gold Price (Realised Gold Price) | GHA_CMP_06 | Gold price | USD/fine ounce | Monthly | Reuters |
| Return on Assets | GHA_FSI_2 | Banking-sector return on assets | Percent | Monthly | Bank of Ghana |
| Non Performing Loan Ratio | GHA_FSI_1 | Non-performing loans ratio | Percent | Monthly | Bank of Ghana |
| Capital Adequacy Ratio | GHA_FSI_5 | Capital adequacy ratio | Percent | Monthly | Bank of Ghana |
| Gross Domestic Product (GDP), production, real | GHA_NAT_1 | Real GDP at 2013 prices | GHS million | Quarterly | Ghana Statistical Service |

## Frequency treatment

The banking indicators are monthly. GDP is quarterly. The current loader linearly interpolates GDP onto month-start dates to permit a monthly merge. This is a convenience for exploratory alignment, not a formal temporal-disaggregation procedure. Interpolated GDP values are estimates and should not be described as observed monthly output.

Some monthly series have missing observations near the end of the sample. Do not assume that every model uses the full source-file date range; inspect the effective sample after selecting variables and handling missing values.

## Sources

- [Bank of Ghana](https://www.bog.gov.gh/)
- [Ghana Statistical Service](https://statsghana.gov.gh/)
- [Reuters](https://www.reuters.com/)

The source names above reflect the metadata included in the downloaded files. Consult the providers for updated definitions, revisions and terms of use.

## Updating the source files

The repository includes a configurable refresh script and a GitHub Actions workflow. The script expects CSV export URLs for the monthly banking dataset and quarterly GDP dataset. It validates the required columns and date coverage before replacing local files, and rejects a download that is older than the current local data.

The URLs are not hard-coded because the provider export endpoints must be confirmed and may change. Configure the repository Actions secrets `MONTHLY_DATA_URL` and `GDP_DATA_URL` to enable manual or scheduled refreshes. See [the usage guide](../docs/USAGE.md#refresh-source-data) for setup instructions.

A refresh is only as current as the provider's latest published release. The workflow does not imply real-time data availability.
