# UCI Online Retail II — benchmark results

**Execution status:** Full source workbook downloaded from UCI and processed successfully.  
**Citation:** Chen, D. (2012). *Online Retail II* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D  
**License:** CC BY 4.0  
**Coverage:** 1 December 2009 – 9 December 2011  
**Currency:** GBP

## Dataset processing

| Metric | Result |
|---|---:|
| Source invoice lines | 1,067,371 |
| Retained invoice lines | 1,061,164 |
| Excluded lines | 6,207 |
| Invalid date rows | 0 |
| Invalid numeric rows | 0 |
| Cancellation/return lines retained | 19,494 |
| Missing customer IDs retained as unknown | 236,871 |
| Months after calendar completion | 25 |
| Countries | 43 |
| Unique invoices | 48,369 |
| Customers with IDs | 5,939 |

Exclusions are zero-quantity rows and non-positive unit prices, plus any invalid dates/numeric values. Negative quantity and cancellation invoice lines remain in the dataset as reversals. Gross sales, refunds and net sales are calculated separately.

## Financial summary

| Measure | GBP |
|---|---:|
| Gross sales | £20,972,968.14 |
| Refunds / reversals | £1,527,041.43 |
| Net sales | £19,445,926.71 |

## Forecast evaluation

Expanding-window rolling-origin backtest; 12-month minimum training window, up to 3-month horizon, 13 forecast origins and 36 held-out predictions per method.

| Method | MAE (GBP) | WAPE |
|---|---:|---:|
| Last observation | £305,889.14 | 39.86% |
| Trailing 3-month average | £319,079.38 | 41.57% |
| Linear trend | £329,784.35 | 42.97% |
| Seasonal naive (12 months) | **£130,068.99** | **16.95%** |

**Finding:** Seasonal-naive forecasting materially outperformed the other three baselines on this dataset. This is evidence to add a seasonal baseline to LeakLens forecasting when at least 24 monthly observations exist, while still comparing models per dataset rather than assuming one model is universally best.

## Geography insight

United Kingdom accounted for £16,541,260.04 net sales of £19,445,926.71 total. The country field is customer geography, not a branch identifier. Aggregated country metrics are in [country_sales.csv](../data/benchmarks/uci_online_retail_ii/country_sales.csv).

Monthly outputs: [monthly_sales.csv](../data/benchmarks/uci_online_retail_ii/monthly_sales.csv). Machine-readable summary: [benchmark_results.json](../data/benchmarks/uci_online_retail_ii/benchmark_results.json).

## Scope and limitations

This is one retailer and an old historical period. It can validate sales aggregation, return handling, customer/country reporting and revenue forecast evaluation. It cannot validate operating expenses, supplier payments, payroll, cash balances, subscription usage, company branches, or fraud/leak-detection precision and recall. It contains no fraud labels. Do not use it to train a supervised fraud model or present sales outliers as confirmed fraud.

Raw workbook and customer/invoice-level records are not committed to this repository. Only aggregated monthly/country metrics and a non-identifying benchmark summary are retained.
