# Public dataset study — UCI Online Retail II

## Why this dataset

LeakLens needs validation against business transactions beyond its hand-authored demo ledger. UCI Online Retail II is a public, real-world retail transaction dataset with 1,067,371 invoice-line records from a UK non-store retailer, dated 1 December 2009 through 9 December 2011. It includes invoice IDs, product codes/descriptions, quantities, invoice timestamps, unit prices, customer IDs and customer countries.

- Dataset: https://archive.ics.uci.edu/dataset/502/online+retail+ii
- DOI: https://doi.org/10.24432/C5CG6D
- Citation: Chen, D. (2012). *Online Retail II* [Dataset]. UCI Machine Learning Repository.
- License: Creative Commons Attribution 4.0 International (CC BY 4.0).
- The raw workbook is downloaded locally and is intentionally excluded from Git history.

## What the research pipeline does

Run from the repository root:

```powershell
cd backend
python scripts/benchmark_uci_online_retail_ii.py --download
```

Or pass a workbook already downloaded from UCI:

```powershell
python scripts/benchmark_uci_online_retail_ii.py --input ..\data\raw\online_retail_II.xlsx
```

Outputs are written to `artifacts/uci_online_retail_ii/`:
- `benchmark.json` — dataset quality, descriptive totals, limitations and rolling-origin forecast evaluation.
- `monthly_sales.csv` — monthly gross sales, refunds, net sales, invoice lines, invoices and customer counts.
- `country_sales.csv` — customer-country aggregates (not branch results).
- `invoice_features.csv` — invoice-level revenue and product-count features for exploratory analysis.

## Data treatment

- The two populated workbook sheets are combined without assuming they have identical row counts.
- Invoice timestamps are parsed with day-first interpretation, as used by the source dataset.
- Negative quantities and cancellation invoice identifiers are retained as refunds/reversals; gross sales, refunds and net sales are reported separately.
- Invalid dates/numeric rows, zero quantities and non-positive unit prices are excluded and counted.
- Missing customer IDs are preserved as unknown rather than imputed.
- Sales are calculated as quantity × unit price in GBP.

## Forecast evaluation

The pipeline uses an expanding-window rolling-origin backtest with up to a three-month horizon. It compares last-observation, trailing-three-month average, linear trend and (when sufficient history exists) seasonal-naive 12-month forecasts. It reports MAE and WAPE, number of predictions and number of evaluation origins. Each origin is trained only on earlier months.

This evaluates revenue time-series methods on one historical retailer. It does not validate current market conditions or guarantee future accuracy.

## What this dataset can and cannot validate

**Can help validate:** revenue aggregation, cancellation/refund handling, time-series feature preparation, monthly revenue forecasts, customer counts, product mix and customer-country reporting.

**Cannot validate:** expense analytics, supplier payment spikes, subscription costs, business cash balances, branch comparisons, or fraud/anomaly precision and recall. It contains no expense ledger and no ground-truth fraud labels. Country is the customer's country, not a company branch.

LeakLens must not train a supervised fraud classifier or report fraud precision/recall from this dataset. Any exploratory statistical outlier is a review candidate, not confirmed fraud.

## Automated tests

```powershell
cd backend
$env:PYTHONPATH = "."
pytest tests/test_public_dataset_benchmark.py
```

The tests use a small synthetic fixture to verify parsing logic, refund arithmetic, aggregation, forecast evaluation and scope disclosures. They do not substitute for running the pipeline against the full workbook.
