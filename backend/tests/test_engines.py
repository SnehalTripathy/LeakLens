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
    assert result["backtest_observations"] == 4
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
