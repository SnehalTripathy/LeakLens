from __future__ import annotations

"""Reproducible research pipeline for UCI Online Retail II.

The source workbook is deliberately downloaded to a local data directory and is
never committed to Git. This dataset contains retail sales and cancellations,
not supplier expenses or confirmed fraud labels.
"""

import argparse
import json
import math
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

UCI_URL = "https://archive.ics.uci.edu/static/public/502/online%2Bretail%2Bii.zip"
CITATION = "Chen, D. (2012). Online Retail II [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D."
LICENSE = "CC BY 4.0"
REQUIRED = {"Invoice", "StockCode", "Description", "Quantity", "Price", "Customer ID", "Country"}


def download_dataset(destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(UCI_URL, headers={"User-Agent": "LeakLens-research/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    return destination


def load_workbook(path: Path) -> pd.DataFrame:
    sheets = pd.read_excel(path, sheet_name=None, dtype={"Invoice": str, "StockCode": str, "Customer ID": str})
    frames = []
    for name, frame in sheets.items():
        if frame is None or frame.empty:
            continue
        frame = frame.copy()
        frame["source_sheet"] = str(name)
        frames.append(frame)
    if not frames:
        raise ValueError("The workbook contains no populated worksheets.")
    return pd.concat(frames, ignore_index=True)


def clean_transactions(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    missing = REQUIRED - set(frame.columns)
    if missing:
        raise ValueError(f"Missing expected UCI columns: {', '.join(sorted(missing))}")
    data = frame.copy()
    original_rows = len(data)
    data["Invoice"] = data["Invoice"].astype("string").str.strip()
    data["InvoiceDate"] = pd.to_datetime(data["InvoiceDate"], errors="coerce", dayfirst=True)
    data["Quantity"] = pd.to_numeric(data["Quantity"], errors="coerce")
    data["Price"] = pd.to_numeric(data["Price"], errors="coerce")
    data["line_value"] = data["Quantity"] * data["Price"]
    invalid_date = int(data["InvoiceDate"].isna().sum())
    invalid_numeric = int((data["Quantity"].isna() | data["Price"].isna()).sum())
    data = data.dropna(subset=["InvoiceDate", "Quantity", "Price"])
    data = data[(data["Quantity"] != 0) & (data["Price"] > 0)].copy()
    data["is_cancellation"] = data["Invoice"].str.upper().str.startswith("C", na=False) | (data["Quantity"] < 0)
    data["Country"] = data["Country"].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
    data["Description"] = data["Description"].fillna("Unknown item").astype(str).str.strip()
    data["Customer ID"] = data["Customer ID"].astype("string").str.strip()
    data["month"] = data["InvoiceDate"].dt.to_period("M").astype(str)
    data["date"] = data["InvoiceDate"].dt.date.astype(str)
    data["gross_sales"] = data["line_value"].clip(lower=0)
    data["refund_value"] = (-data["line_value"]).clip(lower=0)
    quality = {
        "source_rows": int(original_rows),
        "retained_rows": int(len(data)),
        "dropped_rows": int(original_rows - len(data)),
        "invalid_dates": invalid_date,
        "invalid_numeric_rows": invalid_numeric,
        "cancellation_or_return_lines": int(data["is_cancellation"].sum()),
        "missing_customer_ids": int(data["Customer ID"].isna().sum()),
        "missing_descriptions_after_fill": 0,
        "date_min": data["InvoiceDate"].min().isoformat() if len(data) else None,
        "date_max": data["InvoiceDate"].max().isoformat() if len(data) else None,
        "currency": "GBP",
        "notes": [
            "Negative quantities and cancellation invoice identifiers are retained as reversals.",
            "Rows with invalid dates, invalid numeric values, zero quantity, or non-positive unit price are excluded.",
            "Missing customer identifiers are preserved as unknown; they are not imputed.",
        ],
    }
    return data, quality


def aggregate_outputs(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    monthly = data.groupby("month", as_index=False).agg(
        net_sales=("line_value", "sum"),
        gross_sales=("gross_sales", "sum"),
        refunds=("refund_value", "sum"),
        invoice_lines=("Invoice", "size"),
        invoices=("Invoice", "nunique"),
        customers=("Customer ID", "nunique"),
    )
    monthly["net_sales"] = monthly["net_sales"].round(2)
    monthly["gross_sales"] = monthly["gross_sales"].round(2)
    monthly["refunds"] = monthly["refunds"].round(2)
    monthly = monthly.sort_values("month").reset_index(drop=True)

    country = data.groupby("Country", as_index=False).agg(
        net_sales=("line_value", "sum"),
        gross_sales=("gross_sales", "sum"),
        refunds=("refund_value", "sum"),
        invoice_lines=("Invoice", "size"),
        invoices=("Invoice", "nunique"),
        customers=("Customer ID", "nunique"),
    ).sort_values("net_sales", ascending=False)
    country[["net_sales", "gross_sales", "refunds"]] = country[["net_sales", "gross_sales", "refunds"]].round(2)

    invoice = data.groupby(["Invoice", "InvoiceDate", "Country"], as_index=False).agg(
        net_sales=("line_value", "sum"),
        line_count=("StockCode", "size"),
        distinct_products=("StockCode", "nunique"),
        customer_id=("Customer ID", "first"),
    )
    invoice["net_sales"] = invoice["net_sales"].round(2)
    return monthly, country, invoice


def _forecast_one(train: np.ndarray, horizon: int, method: str) -> np.ndarray:
    if method == "last_value":
        return np.repeat(train[-1], horizon)
    if method == "moving_average_3":
        return np.repeat(float(np.mean(train[-3:])), horizon)
    if method == "seasonal_naive_12":
        return np.asarray([train[-12 + (i % 12)] for i in range(horizon)], dtype=float)
    if method == "linear_trend":
        x = np.arange(len(train)).reshape(-1, 1)
        model = LinearRegression().fit(x, train)
        future = np.arange(len(train), len(train) + horizon).reshape(-1, 1)
        return np.maximum(0, model.predict(future))
    raise ValueError(f"Unknown forecast method: {method}")


def forecast_backtest(monthly: pd.DataFrame, min_train: int = 12, max_horizon: int = 3) -> dict[str, Any]:
    values = monthly["net_sales"].to_numpy(dtype=float)
    methods = ["last_value", "moving_average_3", "linear_trend"]
    if len(values) >= 24:
        methods.append("seasonal_naive_12")
    errors: dict[str, list[float]] = {method: [] for method in methods}
    wape_parts: dict[str, list[tuple[float, float]]] = {method: [] for method in methods}
    origins = 0
    # Rolling-origin evaluation: each origin sees only earlier months.
    for cutoff in range(min_train, len(values)):
        horizon = min(max_horizon, len(values) - cutoff)
        if horizon <= 0:
            continue
        actual = values[cutoff:cutoff + horizon]
        origins += 1
        for method in methods:
            if method == "seasonal_naive_12" and cutoff < 12:
                continue
            predicted = _forecast_one(values[:cutoff], horizon, method)
            errors[method].extend(np.abs(actual - predicted).tolist())
            wape_parts[method].append((float(np.abs(actual - predicted).sum()), float(np.abs(actual).sum())))
    scores = {}
    for method in methods:
        absolute = errors[method]
        denominator = sum(pair[1] for pair in wape_parts[method])
        scores[method] = {
            "mae": round(float(np.mean(absolute)), 2) if absolute else None,
            "wape_pct": round(100 * sum(pair[0] for pair in wape_parts[method]) / denominator, 2) if denominator else None,
            "evaluated_predictions": len(absolute),
            "evaluation_origins": len(wape_parts[method]),
        }
    ranked = sorted(
        ((name, score["wape_pct"]) for name, score in scores.items() if score["wape_pct"] is not None),
        key=lambda item: item[1],
    )
    return {
        "methodology": "Expanding-window rolling-origin backtest; maximum 3-month horizon; no future rows used in training.",
        "minimum_training_months": min_train,
        "maximum_horizon_months": max_horizon,
        "rolling_origins": origins,
        "scores": scores,
        "best_by_wape": ranked[0][0] if ranked else None,
        "caveat": "This is one retailer and a historical period; results are not a universal forecast guarantee.",
    }


def build_report(frame: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cleaned, quality = clean_transactions(frame)
    monthly, country, invoice = aggregate_outputs(cleaned)
    forecast = forecast_backtest(monthly)
    report = {
        "dataset": "UCI Online Retail II",
        "citation": CITATION,
        "license": LICENSE,
        "quality": quality,
        "summary": {
            "months": int(len(monthly)),
            "countries": int(country["Country"].nunique()),
            "invoices": int(invoice["Invoice"].nunique()),
            "customers_with_ids": int(cleaned["Customer ID"].nunique(dropna=True)),
            "net_sales_gbp": round(float(cleaned["line_value"].sum()), 2),
            "gross_sales_gbp": round(float(cleaned["gross_sales"].sum()), 2),
            "refunds_gbp": round(float(cleaned["refund_value"].sum()), 2),
            "top_countries_by_net_sales": country.head(10).to_dict(orient="records"),
        },
        "forecast_backtest": forecast,
        "interpretation_limits": [
            "Sales-only data: no supplier expense, payroll, bank balance, or operating cost fields.",
            "No ground-truth fraud or anomaly labels are provided.",
            "Country is a customer geography field, not a company branch identifier.",
            "Historical data is from 2009–2011 and should not be treated as current market behavior.",
        ],
    }
    return report, monthly, country, invoice


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a reproducible UCI Online Retail II benchmark for LeakLens.")
    parser.add_argument("--input", type=Path, help="Path to the UCI online_retail_II.xlsx workbook.")
    parser.add_argument("--download", action="store_true", help="Download the official UCI workbook ZIP first.")
    parser.add_argument("--output", type=Path, default=Path("artifacts/uci_online_retail_ii"))
    args = parser.parse_args()
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    workbook = args.input
    if args.download:
        archive = download_dataset(raw_dir / "online_retail_ii.zip")
        with zipfile.ZipFile(archive) as zipped:
            candidates = [name for name in zipped.namelist() if name.lower().endswith((".xlsx", ".xls"))]
            if not candidates:
                raise ValueError("No Excel workbook found in the downloaded UCI archive.")
            zipped.extract(candidates[0], raw_dir)
            workbook = raw_dir / candidates[0]
    if workbook is None:
        parser.error("Provide --input or use --download.")
    frame = load_workbook(workbook)
    report, monthly, country, invoice = build_report(frame)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "benchmark.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    monthly.to_csv(args.output / "monthly_sales.csv", index=False)
    country.to_csv(args.output / "country_sales.csv", index=False)
    invoice.to_csv(args.output / "invoice_features.csv", index=False)
    print(json.dumps({"output": str(args.output), "summary": report["summary"], "forecast_backtest": report["forecast_backtest"]}, indent=2))


if __name__ == "__main__":
    main()
