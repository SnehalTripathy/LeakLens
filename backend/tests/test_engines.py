from __future__ import annotations

import pytest

from app.engines import (
    forecast,
    leak_signals,
    overview,
    parse_upload,
    simulate,
)


def tx(day: str, vendor: str, amount: float, kind: str = "expense",
       category: str = "Operations", currency: str = "USD") -> dict:
    return {
        "id": f"{day}-{vendor}-{amount}",
        "date": day,
        "description": f"{vendor} transaction",
        "vendor": vendor,
        "category": category,
        "amount": amount,
        "type": kind,
        "currency": currency,
        "source": "test",
    }


def test_overview_reconciles_income_expense_net_and_margin():
    rows = [
        tx("2026-11-01", "Client A", 1000, "income", "Sales"),
        tx("2026-11-02", "Client B", 500, "income", "Sales"),
        tx("2026-11-03", "Office", 200, "expense", "Operations"),
        tx("2026-11-04", "Cloud", 100, "expense", "Technology"),
    ]
    result = overview(rows)
    assert result["revenue"] == 1500
    assert result["expenses"] == 300
    assert result["net"] == 1200
    assert result["profit_margin"] == 80
    assert result["transaction_count"] == 4


def test_overview_does_not_sum_mixed_currencies():
    rows = [
        tx("2026-11-01", "Client USD", 1000, "income", "Sales", "USD"),
        tx("2026-11-02", "Office USD", 250, "expense", "Operations", "USD"),
        tx("2026-11-03", "Client GBP", 9999, "income", "Sales", "GBP"),
    ]
    result = overview(rows)
    assert result["currency"] == "USD"
    assert result["revenue"] == 1000
    assert result["expenses"] == 250
    assert result["net"] == 750
    assert result["other_currencies"] == {"USD": 2, "GBP": 1}


def test_signed_amount_import_uses_negative_as_expense():
    csv = (
        "date,description,vendor,category,amount\n"
        "2026-11-01,Client payment,Client A,Sales,250\n"
        "2026-11-02,Office payment,Office Co,Operations,-75\n"
    ).encode()
    parsed = parse_upload("signed.csv", csv)
    assert len(parsed["rows"]) == 2
    assert parsed["rows"][0]["type"] == "income"
    assert parsed["rows"][0]["amount"] == 250
    assert parsed["rows"][1]["type"] == "expense"
    assert parsed["rows"][1]["amount"] == 75


def test_positive_only_amount_without_direction_is_rejected():
    csv = (
        "date,description,vendor,amount\n"
        "2026-11-01,Unknown flow,Unknown vendor,250\n"
    ).encode()
    with pytest.raises(ValueError, match="does not identify income versus expense"):
        parse_upload("ambiguous.csv", csv)


def test_vendor_spike_signal_has_evidence_and_is_not_confirmed_loss():
    rows = [tx(f"2026-{month:02d}-12", "Cloud Vendor", 100) for month in range(6, 11)]
    rows.append(tx("2026-11-12", "Cloud Vendor", 250))
    signals = leak_signals(rows)
    spike = next(s for s in signals if s["kind"] == "vendor-spike")
    assert spike["estimated_exposure"] == 150
    assert spike["severity"] in {"medium", "high"}
    assert spike["evidence_count"] >= 1
    assert "human review" in spike["classification"]


def test_forecast_requires_four_months_and_returns_three_steps():
    sparse = [
        tx("2026-09-05", "Client", 1000, "income", "Sales"),
        tx("2026-10-05", "Client", 1100, "income", "Sales"),
        tx("2026-11-05", "Client", 1200, "income", "Sales"),
    ]
    assert forecast(sparse)["available"] is False

    history = []
    for month in range(6, 12):
        history.extend([
            tx(f"2026-{month:02d}-05", "Client", 1000 + month * 10, "income", "Sales"),
            tx(f"2026-{month:02d}-15", "Office", 300 + month * 5, "expense", "Operations"),
        ])
    result = forecast(history, horizon=3)
    assert result["available"] is True
    assert len(result["forecast"]) == 3
    assert all(item["income"] >= 0 and item["expenses"] >= 0 for item in result["forecast"])
    assert result["backtest_mae"] is not None
    assert result["backtest_naive_mae"] is not None
    assert result["backtest_periods"] == 2
    assert result["backtest_observations"] == 6
    assert set(result["backtest_by_metric"]) == {"income", "expenses"}


def test_simulator_uses_last_three_month_baseline_and_assumptions():
    rows = []
    for month, income, expense in [(9, 1000, 500), (10, 1100, 550), (11, 1200, 600)]:
        rows.extend([
            tx(f"2026-{month:02d}-05", "Client", income, "income", "Sales"),
            tx(f"2026-{month:02d}-15", "Office", expense, "expense", "Operations"),
        ])
    result = simulate(rows, revenue_change_pct=10, expense_change_pct=-10, one_off_cost=50)
    assert result["baseline"]["revenue"] == 1100
    assert result["baseline"]["expenses"] == 550
    assert result["scenario"]["revenue"] == 1210
    assert result["scenario"]["expenses"] == 545
    assert result["net_change"] == 115


def test_possible_duplicate_vendor_payment_is_flagged_for_human_review():
    rows = [
        tx("2026-11-01", "Payment Vendor", 350),
        tx("2026-11-03", "Payment Vendor", 350),
        tx("2026-11-18", "Payment Vendor", 350),
    ]
    signals = leak_signals(rows)
    duplicate = next(s for s in signals if s["kind"] == "possible-duplicate-payment")
    assert duplicate["estimated_exposure"] == 350
    assert duplicate["evidence_count"] == 2
    assert "human review" in duplicate["classification"]


def test_forecast_enables_seasonal_baseline_with_24_months():
    rows = []
    # Repeating 12-month pattern makes seasonal naive the strongest held-out baseline.
    for month_index in range(25):
        year = 2025 + (month_index // 12)
        month = month_index % 12 + 1
        seasonal_income = [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2400, 2600][month - 1]
        seasonal_expense = [400, 420, 440, 460, 480, 500, 520, 540, 560, 580, 700, 750][month - 1]
        rows.extend([
            tx(f"{year}-{month:02d}-05", "Seasonal Client", seasonal_income, "income", "Sales"),
            tx(f"{year}-{month:02d}-15", "Seasonal Office", seasonal_expense, "expense", "Operations"),
        ])
    result = forecast(rows, horizon=3)
    assert result["available"] is True
    assert result["selected_model_by_metric"]["income"] == "seasonal_naive_12"
    assert result["selected_model_by_metric"]["expenses"] == "seasonal_naive_12"
    assert result["model"] == "Seasonal naive (12-month)"
    assert result["forecast"][0]["income"] == 1100
    assert result["forecast"][0]["expenses"] == 420


def test_forecast_does_not_enable_seasonality_with_short_history():
    rows = []
    for month in range(1, 13):
        rows.extend([
            tx(f"2026-{month:02d}-05", "Client", 1000 + month * 20, "income", "Sales"),
            tx(f"2026-{month:02d}-15", "Office", 300 + month * 10, "expense", "Operations"),
        ])
    result = forecast(rows)
    assert result["available"] is True
    assert "seasonal_naive_12" not in result["selected_model_by_metric"].values()
