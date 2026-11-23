from __future__ import annotations

import pandas as pd
import pytest

from app.public_dataset import aggregate_outputs, build_report, clean_transactions, forecast_backtest


@pytest.fixture
def retail_frame():
    return pd.DataFrame([
        {"Invoice": "10001", "StockCode": "A", "Description": "Item A", "Quantity": 2, "InvoiceDate": "01/01/2010 10:00", "Price": 5.0, "Customer ID": "C1", "Country": "United Kingdom"},
        {"Invoice": "10001", "StockCode": "B", "Description": "Item B", "Quantity": 1, "InvoiceDate": "01/01/2010 10:00", "Price": 10.0, "Customer ID": "C1", "Country": "United Kingdom"},
        {"Invoice": "C10002", "StockCode": "A", "Description": "Item A", "Quantity": -1, "InvoiceDate": "02/01/2010 11:00", "Price": 5.0, "Customer ID": "C1", "Country": "United Kingdom"},
        {"Invoice": "10003", "StockCode": "C", "Description": "Item C", "Quantity": 3, "InvoiceDate": "01/02/2010 09:00", "Price": 2.0, "Customer ID": None, "Country": "France"},
        {"Invoice": "10004", "StockCode": "D", "Description": "Bad row", "Quantity": 1, "InvoiceDate": "not-a-date", "Price": 8.0, "Customer ID": "C2", "Country": "France"},
    ])


def test_cleaning_keeps_refunds_and_reports_invalid_rows(retail_frame):
    cleaned, quality = clean_transactions(retail_frame)
    assert len(cleaned) == 3
    assert quality["source_rows"] == 5
    assert quality["invalid_dates"] == 1
    assert quality["cancellation_or_return_lines"] == 1
    assert quality["missing_customer_ids"] == 1
    assert cleaned["line_value"].sum() == 21


def test_aggregations_separate_gross_refunds_and_net(retail_frame):
    cleaned, _ = clean_transactions(retail_frame)
    monthly, country, invoices = aggregate_outputs(cleaned)
    assert monthly["gross_sales"].sum() == 26
    assert monthly["refunds"].sum() == 5
    assert monthly["net_sales"].sum() == 21
    assert set(country["Country"]) == {"United Kingdom", "France"}
    assert invoices["Invoice"].nunique() == 3


def test_forecast_backtest_uses_rolling_origins_and_returns_baselines():
    monthly = pd.DataFrame({"month": [f"2010-{m:02d}" for m in range(1, 13)] + [f"2011-{m:02d}" for m in range(1, 7)],
                            "net_sales": [100 + 10 * i for i in range(18)]})
    result = forecast_backtest(monthly)
    assert result["rolling_origins"] > 0
    assert result["scores"]["last_value"]["evaluated_predictions"] > 0
    assert result["scores"]["moving_average_3"]["mae"] is not None
    assert result["scores"]["linear_trend"]["mae"] is not None
    assert "seasonal_naive_12" not in result["scores"]


def test_full_report_discloses_dataset_boundaries(retail_frame):
    report, monthly, country, invoice = build_report(retail_frame)
    assert report["dataset"] == "UCI Online Retail II"
    assert report["license"] == "CC BY 4.0"
    assert any("Sales-only" in item for item in report["interpretation_limits"])
    assert len(monthly) == 2
    assert len(country) == 2
    assert len(invoice) == 3


def test_missing_required_columns_fails_clearly(retail_frame):
    with pytest.raises(ValueError, match="Missing expected UCI columns"):
        clean_transactions(retail_frame.drop(columns=["Country"]))
