# Data sources and dictionary

This directory separates the downloaded source files from the prepared analysis dataset.

- `raw/data_first.csv`: monthly banking and macro-financial indicators.
- `raw/data_first2.csv`: quarterly real GDP observations.
- `processed/ghana_banking_master.csv`: a prepared dataset retained from the original workflow.

The source files include metadata rows after the observations. The loader identifies dated observations by parsing the date or quarter field rather than relying on a fixed number of rows.

- `raw/bog_financial_soundness.csv`: historical monthly Bank of Ghana financial soundness indicators from the GSS StatsBank mirror (experimental connector; kept separate from the original monthly macro file).
- `raw/bog_summary_jul_2026.csv`: manually transcribed July 2026 Bank of Ghana banking-sector indicator vintage, covering June 2025–June 2026. The PDF is publicly posted on the official BoG website but carries a DRAFT watermark; this status is retained in each row's source note.\n- `raw/bog_summary_sep_2026.csv`: manually transcribed September 2026 BoG vintage, covering August 2025–August 2026. Its PDF also carries a DRAFT watermark.\n- `raw/bog_summary_nov_2026.csv`: manually transcribed monthly banking-sector indicators from the Bank of Ghana's 17 November 2026 Summary of Economic and Financial Data, covering October 2025–October 2026. Its PDF also carries a DRAFT watermark. Each observation retains the publication date and official PDF URL.

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

## Sources and refresh readiness

The source names below are recorded in the CSV metadata. These official portals are the first places to verify updated observations and revisions:

| Data group | Recorded source | Official data access | Automation status |
|---|---|---|---|
| Monetary policy rate, exchange rates, M2+, NPLs, ROA and capital adequacy | Bank of Ghana | [BoG economic data](https://www.bog.gov.gh/economic-data/) and [time-series catalogue](https://www.bog.gov.gh/economic-data/time-series/) | Portal/export route must be confirmed for a reproducible download |
| CPI | Ghana Statistical Service | [GSS StatsBank](https://statsbank.statsghana.gov.gh/pxweb/en/) | Table and export route must be confirmed |
| Real GDP, quarterly | Ghana Statistical Service | [Quarterly GDP Production Approach table](https://statsbank.statsghana.gov.gh/pxweb/en/Macroeconomic%20Indicators/Macroeconomic%20Indicators__Real%20Sector%20%28GDP%29__Quarterly%20GDP/qgdp_p_px.px/) | Official table identified; machine-readable query/export still needs to be wired into the refresh script |
| Gold price | Reuters | [Reuters](https://www.reuters.com/) | Requires a licensed or otherwise permitted source/export; do not silently substitute a different gold benchmark |

The Bank of Ghana says its database portal contains monthly and quarterly series from the Bank and other institutions, with updates and revisions made according to its published data release calendar. The portal is therefore the right place to investigate a consolidated macro-financial export, but its current downloadable interface must be tested before automating it. The GSS StatsBank quarterly production-approach table exposes the dimensions `Quarter`, `GDP_Series` and `Variable`, with the required categories `Real GDP (constant 2013 prices)` and `Total GDP`. I have added a metadata-driven PxWeb connector in `src/ghana_banking/data/gss.py` that discovers dimension codes rather than hard-coding them. It also preserves the provider's provisional (`**`) and revised (`*`) markers in an `Observation Status` column. The public table confirms the labels and marker definitions, but the API request has not yet been validated end-to-end against a live response; this connector remains experimental.

The GSS StatsBank [Financial Soundness Indicators table](https://statsbank.statsghana.gov.gh/pxweb/en/Search%20Bar/-/fin_sound.px/) publishes eight monthly Bank of Ghana indicators: CAR, CLASTL, CLATA, NPL, OC_I, ROA, ROE and TCGIR. Its current public table page lists 222 months, with the latest displayed month June 2024. A separate [Financial Sector Soundness table](https://statsbank.statsghana.gov.gh/pxweb/en/Search%20Bar/-/financial_sector_soundness.px/) lists nine indicators but stops at December 2023. I have selected the newer eight-indicator table for the connector; it is still not current enough to replace the project's latest observations. The separate BoG Database Portal was announced as a central extraction and visualisation environment, with 255 monthly and 86 quarterly series at launch. Its current disclaimer says data revisions may occur without prior notice. I have not yet verified a stable public API/export endpoint for it.\n\nThe source names above reflect the metadata included in the downloaded files. Consult the providers for updated definitions, revisions, release calendars and terms of use. The existing refresh workflow accepts CSV URLs, but these are not yet verified provider export URLs. It must not be described as connected to live official data until each source has been tested end to end.


## Updating the source files

The repository includes a configurable refresh script and a GitHub Actions workflow. The script expects CSV export URLs for the monthly banking dataset and quarterly GDP dataset. It validates the required columns and date coverage before replacing local files, and rejects a download that is older than the current local data.

The URLs are not hard-coded because the provider export endpoints must be confirmed and may change. Configure the repository Actions secrets `MONTHLY_DATA_URL` and `GDP_DATA_URL` to enable manual or scheduled refreshes. See [the usage guide](../docs/USAGE.md#refresh-source-data) for setup instructions.

A refresh is only as current as the provider's latest published release. The workflow does not imply real-time data availability.


### Bank of Ghana financial-soundness definitions and comparability

The FSI connector uses the official GSS StatsBank table `Search Bar/-/financial_sector_soundness.px`, whose source is the Bank of Ghana. The nine indicator codes and labels are:

| Code | Published indicator | Interpretation |
|---|---|---|
| CAR | Capital Adequacy Ratio | Capital relative to risk-weighted assets and current liabilities |
| CDR | Credit to Deposits | Banking-industry credit divided by deposits |
| CLASTL | Core Liquid Assets to Short-term Liabilities | Short-term liquidity coverage |
| CLATA | Core Liquid Assets to Total Assets | Core liquid assets relative to total assets |
| NPL | Non-Performing Loans | Loans more than 90 days in arrears divided by total loans |
| OC_I | Operational Cost/Income | Operating efficiency |
| ROA | Return on Assets - Before Tax | Profitability before tax relative to assets |
| ROE | Return on Equity - After Tax | Profitability after tax relative to equity |
| TCGIR | Total Cost to Gross Income Ratio | Operating expenses relative to operating income |

**Comparability warning:** the Bank of Ghana states that CAR from April 2023 is adjusted for regulatory reliefs. Its July 2025 publication reports June 2025 CAR of 19.7%, CAR without regulatory reliefs of 18.2%, NPL of 23.1%, NPL excluding the loss category of 8.5%, ROA before tax of 5.6%, and ROE after tax of 32.2%. These definitions are not interchangeable. A time-series analysis must preserve the relief-adjusted CAR break and must not substitute the adjusted NPL measure for headline NPL.

The selected StatsBank table advertises 222 monthly periods beginning January 2006 and ending June 2024. The alternative nine-indicator table advertises 216 months ending December 2023. The connector now targets the newer table and maps descriptive labels to stable indicator codes. The selected source is a data-extraction prototype until its API response and overlapping observations are reconciled with BoG monthly publications. BoG notes that data are subject to revision.


## Bank of Ghana November 2026 publication snapshot

I have added `raw/bog_summary_nov_2026.csv`, a separate publication snapshot transcribed from the Bank of Ghana's [November 2026 Summary of Economic and Financial Data](https://www.bog.gov.gh/wp-content/uploads/2026/11/Summary-of-Economic-and-Financial-Data-November-2026.pdf), published 17 November 2026. It contains 11 banking-sector indicators for each month from October 2025 through October 2026 (143 rows). The source publication reports values to one decimal place and states that data are subject to revision.

The snapshot includes headline and adjusted NPL, headline and regulatory-relief-excluded CAR, profitability, liquidity and efficiency measures. It is deliberately stored separately: it does not overwrite `data_first.csv`, because the latter also contains macroeconomic variables and more precise historical observations. Use `load_bog_summary_snapshot()` to load and validate the snapshot while retaining its source metadata.

### Initial overlap check

For October–December 2025, the original monthly file's CAR, NPL and ROA values round to the one-decimal figures in the November 2026 BoG publication. This is a useful consistency check, not proof that the complete historical series is identical. The publication snapshot should be treated as a rounded, later-vintage reference, and the original values should remain intact until the full series is reconciled.

The snapshot is manually transcribed from the cited PDF; it is not yet an automated PDF ingestion pipeline or a live feed. Future updates should add a new dated snapshot and compare revisions rather than silently replace prior values.


### Publication-vintage overlap check (July vs November 2026)

I have archived the July 2026 BoG summary as a separate vintage rather than treating the November release as the only available snapshot. The July PDF is hosted on the official BoG website and states a 21 July 2026 release date, but it also carries a DRAFT watermark. That caveat is recorded in the CSV and must remain visible when interpreting the comparison.

The three snapshots form two adjacent comparisons:
- July to September: 11 overlapping months (August 2025–June 2026) × 11 indicators = 121 matched observations.
- September to November: 11 overlapping months (October 2025–August 2026) × 11 indicators = 121 matched observations.
- July to November: nine overlapping months (October 2025–June 2026) × 11 indicators = 99 matched observations.

All matched values are identical at the one-decimal precision displayed in the PDFs. This is evidence of consistency between the three publicly posted files at displayed precision; it does not prove that no underlying revisions occurred below that precision or that the PDFs are final versions. All three PDFs carry a DRAFT watermark despite being hosted in the BoG publication archive. Treat these as archived official-site publication vintages with an explicit draft-status caveat, not as certified final data.

The adjacent comparisons and July-to-November overlap are covered by regression tests. All source files remain separately attributed and unchanged.
