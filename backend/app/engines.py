from __future__ import annotations

import calendar
import io
import math
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

ALIASES = {
    "date": ["date", "transaction_date", "posted_date", "time"],
    "description": ["description", "memo", "details", "narration", "name", "reference"],
    "vendor": ["vendor", "merchant", "payee", "counterparty", "supplier"],
    "category": ["category", "account", "expense_category", "type_category"],
    "amount": ["amount", "value", "total", "transaction_amount"],
    "debit": ["debit", "withdrawal", "money_out"],
    "credit": ["credit", "deposit", "money_in"],
    "type": ["type", "direction", "transaction_type", "income_expense", "kind"],
    "currency": ["currency", "ccy"],
}


def _column(columns: list[str], aliases: list[str]) -> str | None:
    normalized = {str(c).strip().casefold(): str(c) for c in columns}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    return None


def parse_upload(filename: str, content: bytes) -> dict[str, Any]:
    if len(content) > 10 * 1024 * 1024:
        raise ValueError("File exceeds the 10 MB import limit.")
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "csv":
        frame = pd.read_csv(io.BytesIO(content), dtype=str)
    elif ext in {"xlsx", "xls"}:
        frame = pd.read_excel(io.BytesIO(content), dtype=str)
    else:
        raise ValueError("Unsupported file type. Upload a CSV or Excel workbook.")
    if frame.empty:
        raise ValueError("The uploaded file contains no transaction rows.")
    frame.columns = [str(c).strip() for c in frame.columns]
    cols = list(frame.columns)
    mapped = {key: _column(cols, values) for key, values in ALIASES.items()}
    if not (mapped["amount"] or (mapped["debit"] or mapped["credit"])):
        raise ValueError("Could not find an amount column or debit/credit columns.")
    if not mapped["date"]:
        raise ValueError("Could not find a transaction date column.")
    # Positive-only amount columns are directionally ambiguous unless a type or debit/credit field exists.
    if mapped["amount"] and not mapped["type"] and not (mapped["debit"] or mapped["credit"]):
        signed_amounts = [_number(v) for v in frame[mapped["amount"]].tolist() if _text(v)]
        if signed_amounts and all(value >= 0 for value in signed_amounts):
            raise ValueError("A positive-only Amount column does not identify income versus expense. Add a Type/Direction column, Debit/Credit columns, or use signed amounts with expenses as negative values.")
    accepted: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    duplicate_rows: list[int] = []
    for index, raw in frame.iterrows():
        row_no = int(index) + 2
        try:
            raw_date = raw.get(mapped["date"])
            parsed_date = pd.to_datetime(raw_date, errors="raise", dayfirst=False).date().isoformat()
            if mapped["debit"] or mapped["credit"]:
                debit = _number(raw.get(mapped["debit"])) if mapped["debit"] else 0.0
                credit = _number(raw.get(mapped["credit"])) if mapped["credit"] else 0.0
                if debit > 0 and credit > 0:
                    raise ValueError("Both debit and credit are populated.")
                amount = debit or credit
                kind = "income" if credit > 0 else "expense"
            else:
                source_amount = _number(raw.get(mapped["amount"]))
                amount = abs(source_amount)
                type_value = str(raw.get(mapped["type"], "") if mapped["type"] else "").strip().casefold()
                if type_value in {"income", "credit", "deposit", "inflow"}:
                    kind = "income"
                elif type_value in {"expense", "debit", "withdrawal", "outflow"}:
                    kind = "expense"
                else:
                    kind = "expense" if source_amount < 0 else "income" if source_amount > 0 else ""
            if not math.isfinite(amount) or amount <= 0:
                raise ValueError("Amount must be a finite positive number.")
            description = _text(raw.get(mapped["description"]) if mapped["description"] else "") or "Imported transaction"
            vendor = _text(raw.get(mapped["vendor"]) if mapped["vendor"] else "") or description
            category = _text(raw.get(mapped["category"]) if mapped["category"] else "") or "Uncategorised"
            currency = (_text(raw.get(mapped["currency"]) if mapped["currency"] else "") or "USD").upper()
            if not re.fullmatch(r"[A-Z]{3}", currency):
                raise ValueError("Currency must be a three-letter ISO code.")
            row = {"date": parsed_date, "description": description[:240], "vendor": vendor[:120],
                   "category": category[:100], "amount": round(amount, 2), "type": kind,
                   "currency": currency, "source": "upload"}
            key = (row["date"], row["vendor"].casefold(), row["amount"], row["type"], currency)
            if key in seen:
                duplicate_rows.append(row_no)
                continue
            seen.add(key)
            accepted.append(row)
        except Exception as exc:
            errors.append({"row": row_no, "reason": str(exc)})
    return {"rows": accepted, "errors": errors, "duplicate_rows": duplicate_rows,
            "total_rows": len(frame), "mapped_columns": {k: v for k, v in mapped.items() if v}}


def _text(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def _number(value: Any) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0.0
    text = str(value).strip().replace(",", "").replace("$", "").replace("£", "").replace("€", "").replace("₹", "")
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    if text in {"", "-", "—"}:
        return 0.0
    return float(text)


def _month_key(value: str) -> str:
    return pd.to_datetime(value).strftime("%Y-%m")


def _fmt_month(key: str) -> str:
    return pd.Period(key, freq="M").strftime("%b %Y")


def _primary_currency(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return rows
    counts = Counter(r.get("currency", "USD") for r in rows)
    primary = counts.most_common(1)[0][0]
    return [r for r in rows if r.get("currency", "USD") == primary]


def overview(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"currency": "USD", "revenue": 0, "expenses": 0, "net": 0, "profit_margin": 0,
                "transaction_count": 0, "monthly": [], "categories": [], "vendors": [], "recent": []}
    currencies = Counter(r.get("currency", "USD") for r in rows)
    currency = currencies.most_common(1)[0][0]
    scoped = [r for r in rows if r.get("currency", "USD") == currency]
    income = sum(r["amount"] for r in scoped if r["type"] == "income")
    expenses = sum(r["amount"] for r in scoped if r["type"] == "expense")
    net = income - expenses
    monthly_map: dict[str, dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})
    category_map: dict[str, float] = defaultdict(float)
    vendor_map: dict[str, float] = defaultdict(float)
    for r in scoped:
        key = _month_key(r["date"])
        monthly_map[key]["income" if r["type"] == "income" else "expenses"] += r["amount"]
        if r["type"] == "expense":
            category_map[r["category"]] += r["amount"]
            vendor_map[r["vendor"]] += r["amount"]
    monthly = [{"month": _fmt_month(k), "period": k, "income": round(v["income"], 2),
                "expenses": round(v["expenses"], 2), "net": round(v["income"] - v["expenses"], 2)}
               for k, v in sorted(monthly_map.items())[-12:]]
    categories = [{"name": k, "value": round(v, 2), "share": round(v / expenses * 100, 1) if expenses else 0}
                  for k, v in sorted(category_map.items(), key=lambda x: x[1], reverse=True)]
    vendors = [{"name": k, "spend": round(v, 2), "share": round(v / expenses * 100, 1) if expenses else 0}
               for k, v in sorted(vendor_map.items(), key=lambda x: x[1], reverse=True)[:10]]
    return {"currency": currency, "other_currencies": dict(currencies), "revenue": round(income, 2),
            "expenses": round(expenses, 2), "net": round(net, 2),
            "profit_margin": round(net / income * 100, 1) if income else 0,
            "transaction_count": len(scoped), "monthly": monthly, "categories": categories,
            "vendors": vendors, "recent": scoped[:10]}


def expense_intelligence(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = _primary_currency(rows)
    expenses = [r for r in rows if r["type"] == "expense"]
    if not expenses:
        return {"total": 0, "fixed_estimate": 0, "variable_estimate": 0, "categories": [], "vendors": [], "recurring": []}
    category_totals: dict[str, float] = defaultdict(float)
    vendor_totals: dict[str, float] = defaultdict(float)
    for r in expenses:
        category_totals[r["category"]] += r["amount"]
        vendor_totals[r["vendor"]] += r["amount"]
    recurring = []
    for vendor, group in _group(expenses, "vendor").items():
        if len(group) >= 3:
            amounts = [g["amount"] for g in group]
            if max(amounts) <= max(min(amounts) * 1.35, np.median(amounts) * 1.25):
                recurring.append({"vendor": vendor, "occurrences": len(group), "median_amount": round(float(np.median(amounts)), 2),
                                  "estimated_monthly": round(float(np.median(amounts)), 2)})
    recurring_vendors = {x["vendor"] for x in recurring}
    fixed = sum(r["amount"] for r in expenses if r["vendor"] in recurring_vendors)
    total = sum(r["amount"] for r in expenses)
    return {"total": round(total, 2), "fixed_estimate": round(fixed, 2),
            "variable_estimate": round(total - fixed, 2),
            "categories": [{"name": k, "spend": round(v, 2), "share": round(v / total * 100, 1)}
                           for k, v in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)],
            "vendors": [{"name": k, "spend": round(v, 2), "share": round(v / total * 100, 1)}
                        for k, v in sorted(vendor_totals.items(), key=lambda x: x[1], reverse=True)],
            "recurring": recurring}


def _group(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        result[str(row[key])].append(row)
    return result


def leak_signals(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = _primary_currency(rows)
    expenses = [r for r in rows if r["type"] == "expense"]
    signals: list[dict[str, Any]] = []
    # Large individual transaction compared with the same vendor's past activity.
    for vendor, group in _group(expenses, "vendor").items():
        ordered = sorted(group, key=lambda r: r["date"])
        if len(ordered) < 5:
            continue
        amounts = np.array([r["amount"] for r in ordered], dtype=float)
        median = float(np.median(amounts[:-1]))
        latest = ordered[-1]
        if median > 0 and latest["amount"] > median * 1.7 and latest["amount"] - median >= 100:
            exposure = latest["amount"] - median
            signals.append(_signal("vendor-spike", vendor, "Vendor payment above its usual level",
                                   f"{vendor} latest payment is {latest['amount']:.2f}, versus a historical median of {median:.2f}.",
                                   exposure, "high" if exposure > 1000 else "medium", [latest], "Rule-based baseline comparison"))
    # Same vendor and near-identical monthly charges can be subscriptions; price increase is a review signal.
    for vendor, group in _group(expenses, "vendor").items():
        monthly: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in group:
            monthly[_month_key(r["date"])].append(r)
        if len(monthly) >= 3:
            medians = [(m, float(np.median([x["amount"] for x in vals]))) for m, vals in sorted(monthly.items())]
            old = [v for _, v in medians[:-1]]
            baseline = float(np.median(old))
            latest = medians[-1][1]
            if baseline > 0 and latest > baseline * 1.2 and latest - baseline >= 10:
                signals.append(_signal("subscription-price-change", vendor, "Recurring vendor charge increased",
                                       f"Latest monthly charge is {latest:.2f}; prior recurring median was {baseline:.2f}.",
                                       latest - baseline, "medium", monthly[medians[-1][0]], "Monthly recurrence comparison"))
    # Category growth from latest month against the previous 3-month mean.
    months = sorted({_month_key(r["date"]) for r in expenses})
    if len(months) >= 4:
        latest_month = months[-1]
        prior_months = months[-4:-1]
        categories = {r["category"] for r in expenses}
        for category in categories:
            current = sum(r["amount"] for r in expenses if r["category"] == category and _month_key(r["date"]) == latest_month)
            baseline = np.mean([sum(r["amount"] for r in expenses if r["category"] == category and _month_key(r["date"]) == m)
                                for m in prior_months])
            if baseline >= 100 and current > baseline * 1.3:
                evidence = [r for r in expenses if r["category"] == category and _month_key(r["date"]) == latest_month]
                signals.append(_signal("category-spend-spike", category, "Category spending is rising",
                                       f"{category} spending this month is {current:.2f}, above its recent monthly average of {baseline:.2f}.",
                                       max(0, current - baseline), "high" if current > baseline * 1.6 else "medium",
                                       evidence, "Latest month compared with prior three-month average"))
    # Concentration: vendor contributes unusually high proportion of spend.
    total = sum(r["amount"] for r in expenses)
    if total:
        for vendor, group in _group(expenses, "vendor").items():
            value = sum(r["amount"] for r in group)
            share = value / total
            if share >= 0.35 and value >= 1000:
                signals.append(_signal("vendor-concentration", vendor, "Spending concentrated with one vendor",
                                       f"{vendor} represents {share:.0%} of recorded expenses. Concentration is a dependency risk, not proof of overpayment.",
                                       0, "medium", group[-5:], "Share of total recorded expense spend"))
    # Repeated small payments in the last 30 days.
    cutoff = date.today() - timedelta(days=30)
    for vendor, group in _group(expenses, "vendor").items():
        recent = [r for r in group if pd.to_datetime(r["date"]).date() >= cutoff and r["amount"] <= 100]
        if len(recent) >= 5:
            signals.append(_signal("repeated-small-charges", vendor, "Repeated small charges",
                                   f"{len(recent)} charges of 100 or less appear for {vendor} in the last 30 days.",
                                   sum(r["amount"] for r in recent), "low", recent, "Count and sum of small recent charges"))
    # Stable ids make workflow states sticky between refreshes.
    unique = {}
    for signal in signals:
        unique[signal["id"]] = signal
    return sorted(unique.values(), key=lambda s: ({"high": 0, "medium": 1, "low": 2}[s["severity"]], -s["estimated_exposure"]))


def _signal(kind: str, subject: str, title: str, detail: str, exposure: float,
            severity: str, evidence: list[dict[str, Any]], method: str) -> dict[str, Any]:
    import hashlib
    identifier = hashlib.sha1(f"{kind}|{subject}".encode()).hexdigest()[:12]
    return {"id": identifier, "kind": kind, "subject": subject, "title": title, "detail": detail,
            "estimated_exposure": round(float(exposure), 2), "severity": severity,
            "evidence": evidence[:8], "evidence_count": len(evidence), "method": method,
            "classification": "potential issue — human review required"}


def anomaly_detection(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = _primary_currency(rows)
    expenses = [r for r in rows if r["type"] == "expense"]
    if len(expenses) < 12:
        return {"available": False, "reason": "At least 12 expense transactions are required for anomaly modelling.",
                "model": "Isolation Forest", "results": []}
    try:
        from sklearn.ensemble import IsolationForest
        from sklearn.neighbors import LocalOutlierFactor
        vendors = Counter(r["vendor"] for r in expenses)
        categories = Counter(r["category"] for r in expenses)
        x = np.array([[math.log1p(r["amount"]), pd.to_datetime(r["date"]).day,
                       pd.to_datetime(r["date"]).dayofweek,
                       math.log1p(vendors[r["vendor"]]), math.log1p(categories[r["category"]])]
                      for r in expenses], dtype=float)
        isolation = IsolationForest(n_estimators=250, contamination="auto", random_state=42)
        isolation.fit(x)
        isolation_raw = -isolation.score_samples(x)
        isolation_ranks = pd.Series(isolation_raw).rank(pct=True).to_numpy()
        lof_neighbors = min(20, max(2, len(expenses) - 1))
        lof = LocalOutlierFactor(n_neighbors=lof_neighbors, contamination="auto")
        lof.fit_predict(x)
        lof_raw = -lof.negative_outlier_factor_
        lof_ranks = pd.Series(lof_raw).rank(pct=True).to_numpy()
        combined = np.maximum(isolation_ranks, lof_ranks)
        results = []
        amount_values = np.array([r["amount"] for r in expenses], dtype=float)
        amount_median = float(np.median(amount_values))
        day_counts = Counter(pd.to_datetime(r["date"]).day for r in expenses)
        for index, (row, score) in enumerate(zip(expenses, combined)):
            if score >= 0.88:
                severity = "high" if score >= 0.97 else "medium"
                factors = []
                if amount_median > 0 and row["amount"] >= amount_median * 1.8:
                    factors.append(f"Amount is {row['amount'] / amount_median:.1f}× the median expense amount.")
                if vendors[row["vendor"]] <= 2:
                    factors.append("Vendor has very few observations in the current ledger.")
                if categories[row["category"]] <= 3:
                    factors.append("Category has a relatively small sample in the modelled ledger.")
                day = pd.to_datetime(row["date"]).day
                if day_counts[day] <= max(1, len(expenses) * 0.03):
                    factors.append("Transaction day-of-month is uncommon in this dataset.")
                explanation = " ".join(factors) or "The combination of amount, timing and vendor/category frequency differs from the modelled transaction pattern."
                results.append({"transaction": row, "score": round(float(score * 100), 1), "severity": severity,
                                "explanation": explanation, "contextual_checks": factors,
                                "model_scores": {"isolation_forest_percentile": round(float(isolation_ranks[index] * 100), 1),
                                                 "local_outlier_factor_percentile": round(float(lof_ranks[index] * 100), 1)},
                                "score_interpretation": "Maximum percentile rank from two unsupervised models within this workspace's current expense sample; not a probability of fraud.",
                                "model": "Isolation Forest + Local Outlier Factor"})
        return {"available": True, "model": "Isolation Forest + Local Outlier Factor", "sample_size": len(expenses),
                "flagged_count": len(results), "models": ["Isolation Forest", "Local Outlier Factor"],
                "results": sorted(results, key=lambda x: x["score"], reverse=True)[:30],
                "note": "Unsupervised anomaly scores indicate unusual patterns, not fraud or confirmed loss. Percentiles are relative to this workspace sample and are not calibrated probabilities."}
    except Exception as exc:
        return {"available": False, "reason": f"Anomaly model could not run: {exc}",
                "model": "Isolation Forest", "results": []}


def forecast(rows: list[dict[str, Any]], horizon: int = 3) -> dict[str, Any]:
    rows = _primary_currency(rows)
    monthly: dict[str, dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})
    for r in rows:
        monthly[_month_key(r["date"])][r["type"] if r["type"] == "income" else "expenses"] += r["amount"]
    months = sorted(monthly)
    if len(months) < 4:
        return {"available": False, "reason": "At least four distinct months of transactions are required.",
                "history": [], "forecast": [], "model": "Linear trend baseline"}
    # Fill missing months with zeros to preserve a continuous monthly series.
    start, end = pd.Period(months[0], "M"), pd.Period(months[-1], "M")
    periods = [str(p) for p in pd.period_range(start, end, freq="M")]
    series = {metric: np.array([monthly.get(p, {}).get(metric, 0.0) for p in periods], dtype=float)
              for metric in ("income", "expenses")}
    x = np.arange(len(periods), dtype=float)
    history = [{"month": _fmt_month(p), "period": p, "income": round(float(series["income"][i]), 2),
                "expenses": round(float(series["expenses"][i]), 2)}
               for i, p in enumerate(periods)]
    forecast_rows = []
    errors = []
    naive_errors = []
    backtest_by_metric = {}
    backtest_period_count = 0
    for metric in ("income", "expenses"):
        y = series[metric]
        if len(y) >= 6:
            split = len(y) - 2
            coef = np.polyfit(x[:split], y[:split], 1)
            validation = np.maximum(0.0, np.polyval(coef, x[split:]))
            actual = y[split:]
            naive = np.repeat(y[split - 1], len(actual))
            trend_err = np.abs(validation - actual)
            naive_err = np.abs(naive - actual)
            errors.extend(trend_err.tolist())
            naive_errors.extend(naive_err.tolist())
            backtest_period_count = max(backtest_period_count, len(actual))
            trend_mae = float(np.mean(trend_err))
            naive_mae = float(np.mean(naive_err))
            backtest_by_metric[metric] = {
                "trend_mae": round(trend_mae, 2),
                "naive_mae": round(naive_mae, 2),
                "improvement_pct": round((naive_mae - trend_mae) / naive_mae * 100, 1) if naive_mae else None,
            }
    for step in range(1, max(1, min(int(horizon), 3)) + 1):
        target_index = len(periods) - 1 + step
        future: dict[str, Any] = {"step": step}
        for metric in ("income", "expenses"):
            y = series[metric]
            coef = np.polyfit(x, y, 1)
            prediction = max(0.0, float(np.polyval(coef, target_index)))
            residual = y - np.polyval(coef, x)
            spread = float(np.std(residual, ddof=1)) if len(residual) > 1 else 0.0
            band = spread * (1.0 + 0.25 * step)
            future[metric] = round(prediction, 2)
            future[f"{metric}_lower"] = round(max(0.0, prediction - band), 2)
            future[f"{metric}_upper"] = round(prediction + band, 2)
        future["net"] = round(future["income"] - future["expenses"], 2)
        period = pd.Period(periods[-1], "M") + step
        future["month"] = period.strftime("%b %Y")
        forecast_rows.append(future)
    mae = float(np.mean(errors)) if errors else None
    naive_mae = float(np.mean(naive_errors)) if naive_errors else None
    return {"available": True, "model": "Linear trend baseline", "history": history, "forecast": forecast_rows,
            "backtest_mae": round(mae, 2) if mae is not None else None,
            "backtest_naive_mae": round(naive_mae, 2) if naive_mae is not None else None,
            "backtest_improvement_pct": round((naive_mae - mae) / naive_mae * 100, 1) if naive_mae and mae is not None else None,
            "backtest_periods": backtest_period_count,
            "backtest_observations": len(errors),
            "backtest_by_metric": backtest_by_metric,
            "backtest_method": "The final two observed months are held out; a linear trend is compared with a last-observation naive forecast, separately for revenue and expenses.",
            "uncertainty": "Bands use historical residual dispersion and widen with horizon; they are indicative, not calibrated confidence intervals.",
            "minimum_data": "Four distinct months for forecasting; at least six contiguous months for held-out two-step backtesting."}


def health_score(rows: list[dict[str, Any]], signals: list[dict[str, Any]]) -> dict[str, Any]:
    rows = _primary_currency(rows)
    o = overview(rows)
    if not rows:
        return {"available": False, "reason": "Upload transactions to calculate a health score."}
    income, expenses = o["revenue"], o["expenses"]
    margin = o["profit_margin"]
    profitability = float(np.clip(50 + margin * 1.8, 0, 100)) if income else 0
    cashflow = 80 if o["net"] > 0 else float(np.clip(50 + (o["net"] / max(expenses, 1)) * 50, 0, 100))
    efficiency = float(np.clip(100 - (expenses / income * 100 if income else 100), 0, 100))
    monthly_income = [x["income"] for x in o["monthly"] if x["income"] > 0]
    volatility = float(np.std(monthly_income) / np.mean(monthly_income)) if len(monthly_income) > 1 and np.mean(monthly_income) else 1
    stability = float(np.clip(100 - volatility * 100, 0, 100))
    high_exposure = sum(s["estimated_exposure"] for s in signals if s["severity"] == "high")
    risk = float(np.clip(100 - high_exposure / max(expenses, 1) * 100 - len(signals) * 2, 0, 100))
    coverage = float(np.clip(len(rows) / 60 * 100, 0, 100))
    parts = [
        {"name": "Profitability", "score": round(profitability), "weight": 25, "basis": "Net margin relative to recorded revenue"},
        {"name": "Cash-flow balance", "score": round(cashflow), "weight": 20, "basis": "Recorded income less recorded expenses"},
        {"name": "Expense efficiency", "score": round(efficiency), "weight": 15, "basis": "Expense-to-revenue ratio"},
        {"name": "Revenue stability", "score": round(stability), "weight": 15, "basis": "Monthly revenue coefficient of variation"},
        {"name": "Risk exposure", "score": round(risk), "weight": 15, "basis": "Rule-based potential exposure and signal count"},
        {"name": "Data coverage", "score": round(coverage), "weight": 10, "basis": "Transaction count proxy; not a measure of bookkeeping quality"},
    ]
    score = round(sum(p["score"] * p["weight"] for p in parts) / 100)
    label = "Strong" if score >= 80 else "Stable" if score >= 65 else "Needs attention" if score >= 45 else "At risk"
    return {"available": True, "score": score, "label": label, "components": parts,
            "methodology": "Weighted transparent index. Scores are directional indicators, not credit ratings or audited financial advice."}


def recommendations(rows: list[dict[str, Any]], signals: list[dict[str, Any]], budgets: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = _primary_currency(rows)
    out = []
    for signal in signals[:10]:
        exposure = signal["estimated_exposure"]
        out.append({"id": f"rec-{signal['id']}", "priority": signal["severity"], "title": f"Review: {signal['title']}",
                    "action": f"Check the source transactions for {signal['subject']}; verify the invoice, service period and approval before changing spend.",
                    "evidence": signal["detail"], "potential_savings": round(exposure, 2),
                    "savings_type": "estimated exposure; not guaranteed savings", "source_signal_id": signal["id"]})
    current_period = date.today().strftime("%Y-%m")
    for budget in budgets or []:
        if budget.get("currency", "USD") != (rows[0].get("currency", "USD") if rows else "USD"):
            continue
        actual = sum(r["amount"] for r in rows if r["type"] == "expense" and r["category"] == budget["category"] and _month_key(r["date"]) == current_period)
        limit = float(budget["monthly_amount"])
        if limit > 0 and actual > limit:
            over = actual - limit
            out.append({"id": f"rec-budget-{budget['category']}", "priority": "high", "title": f"{budget['category']} budget exceeded",
                        "action": "Review recent transactions in this category, confirm one-off costs and agree a corrective spend plan.",
                        "evidence": f"Month-to-date actual is {actual:.2f}, exceeding the {limit:.2f} monthly budget by {over:.2f}.",
                        "potential_savings": round(over, 2), "savings_type": "budget overrun; not guaranteed savings"})
    exp = [r for r in rows if r["type"] == "expense"]
    if exp:
        by_vendor = _group(exp, "vendor")
        biggest = max(by_vendor.items(), key=lambda item: sum(r["amount"] for r in item[1]))
        total = sum(r["amount"] for r in exp)
        share = sum(r["amount"] for r in biggest[1]) / total if total else 0
        if share > 0.25:
            out.append({"id": "rec-vendor-diversification", "priority": "low", "title": "Review vendor dependency",
                        "action": f"Review renewal terms and backup options for {biggest[0]}; avoid changing providers without a service comparison.",
                        "evidence": f"This vendor represents {share:.0%} of recorded expense spend.",
                        "potential_savings": 0, "savings_type": "no savings estimate; concentration review"})
    return out


def simulate(rows: list[dict[str, Any]], revenue_change_pct: float, expense_change_pct: float,
             one_off_cost: float = 0.0) -> dict[str, Any]:
    if not rows:
        raise ValueError("At least one transaction is required before running a scenario.")
    if not -100 <= revenue_change_pct <= 300 or not -100 <= expense_change_pct <= 300:
        raise ValueError("Scenario percentage changes must be between -100% and +300%.")
    if not 0 <= one_off_cost <= 1_000_000_000:
        raise ValueError("One-off cost must be between 0 and 1,000,000,000.")
    o = overview(rows)
    months = o["monthly"][-3:]
    base_revenue = float(np.mean([m["income"] for m in months])) if months else o["revenue"]
    base_expenses = float(np.mean([m["expenses"] for m in months])) if months else o["expenses"]
    scenario_revenue = base_revenue * (1 + revenue_change_pct / 100)
    scenario_expenses = base_expenses * (1 + expense_change_pct / 100) + one_off_cost
    return {"currency": o["currency"], "baseline": {"revenue": round(base_revenue, 2), "expenses": round(base_expenses, 2),
            "net": round(base_revenue - base_expenses, 2)},
            "scenario": {"revenue": round(scenario_revenue, 2), "expenses": round(scenario_expenses, 2),
            "net": round(scenario_revenue - scenario_expenses, 2)},
            "net_change": round((scenario_revenue - scenario_expenses) - (base_revenue - base_expenses), 2),
            "assumptions": {"revenue_change_pct": revenue_change_pct, "expense_change_pct": expense_change_pct, "one_off_cost": one_off_cost},
            "basis": "Average of the last three recorded calendar months; not a cash forecast."}


def assistant_answer(question: str, rows: list[dict[str, Any]], signals: list[dict[str, Any]]) -> dict[str, Any]:
    q = question.casefold()
    o = overview(rows)
    if not rows:
        return {"answer": "Upload transactions first. I can then answer questions using the workspace ledger.", "evidence": []}
    if any(k in q for k in ["highest vendor", "top vendor", "vendor costs", "vendor spend"]):
        top = o["vendors"][0] if o["vendors"] else None
        answer = f"{top['name']} is the largest recorded expense vendor at {top['spend']:,.2f} {o['currency']} ({top['share']:.1f}% of expense spend)." if top else "There is no vendor expense data yet."
        return {"answer": answer, "evidence": [top] if top else []}
    if any(k in q for k in ["expense", "spent", "spend"]):
        return {"answer": f"Recorded expenses total {o['expenses']:,.2f} {o['currency']} across {o['transaction_count']} transactions. The largest categories are " + ", ".join(f"{x['name']} ({x['share']}%)" for x in o["categories"][:3]) + ".", "evidence": o["categories"][:3]}
    if any(k in q for k in ["revenue", "income", "sales"]):
        return {"answer": f"Recorded revenue is {o['revenue']:,.2f} {o['currency']}. Net operating movement is {o['net']:,.2f} {o['currency']}, with a recorded margin of {o['profit_margin']:.1f}%.", "evidence": [{"revenue": o["revenue"], "net": o["net"], "margin": o["profit_margin"]}]}
    if any(k in q for k in ["risk", "leak", "loss", "problem", "unusual"]):
        answer = f"I found {len(signals)} rule-based signals for review. They indicate patterns to investigate, not confirmed losses or fraud."
        return {"answer": answer, "evidence": signals[:5]}
    if any(k in q for k in ["save", "reduce", "cut", "recommend"]):
        recs = recommendations(rows, signals)[:5]
        return {"answer": f"There are {len(recs)} evidence-linked actions to review. Start with the highest-priority vendor or category signals; verify source invoices before acting.", "evidence": recs}
    if any(k in q for k in ["profit", "margin", "cash flow"]):
        return {"answer": f"Recorded revenue is {o['revenue']:,.2f} {o['currency']}; expenses are {o['expenses']:,.2f}; net is {o['net']:,.2f}; margin is {o['profit_margin']:.1f}%.", "evidence": [{"revenue": o["revenue"], "expenses": o["expenses"], "net": o["net"], "margin": o["profit_margin"]}]}
    return {"answer": "I can answer questions about recorded revenue, expenses, profit, vendors, categories, and detected review signals. Try: “Which vendor costs the most?” or “Where are unusual expenses appearing?”", "evidence": [], "scope": "This assistant is deterministic and grounded in the current workspace data; it does not call an external LLM."}


def revenue_intelligence(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = _primary_currency(rows)
    income = [r for r in rows if r["type"] == "income"]
    total = sum(r["amount"] for r in income)
    counterparties: dict[str, float] = defaultdict(float)
    categories: dict[str, float] = defaultdict(float)
    monthly: dict[str, float] = defaultdict(float)
    for row in income:
        counterparties[row["vendor"]] += row["amount"]
        categories[row["category"]] += row["amount"]
        monthly[_month_key(row["date"])] += row["amount"]
    return {
        "total": round(total, 2),
        "counterparties": [{"name": k, "revenue": round(v, 2), "share": round(v / total * 100, 1) if total else 0}
                           for k, v in sorted(counterparties.items(), key=lambda x: x[1], reverse=True)],
        "sources": [{"name": k, "revenue": round(v, 2), "share": round(v / total * 100, 1) if total else 0}
                    for k, v in sorted(categories.items(), key=lambda x: x[1], reverse=True)],
        "monthly": [{"month": _fmt_month(k), "period": k, "revenue": round(v, 2)}
                    for k, v in sorted(monthly.items())[-12:]],
        "note": "Counterparty names are taken from the vendor/payee field; customer identity is only as accurate as the uploaded ledger."
    }


def budget_performance(rows: list[dict[str, Any]], budgets: list[dict[str, Any]]) -> dict[str, Any]:
    rows = _primary_currency(rows)
    currency = rows[0].get("currency", "USD") if rows else "USD"
    selected = [b for b in budgets if b["currency"] == currency]
    current_month = date.today().strftime("%Y-%m")
    actuals: dict[str, float] = defaultdict(float)
    for row in rows:
        if row["type"] == "expense" and _month_key(row["date"]) == current_month:
            actuals[row["category"]] += row["amount"]
    day_no = date.today().day
    month_days = calendar.monthrange(date.today().year, date.today().month)[1]
    result = []
    for budget in selected:
        actual = actuals.get(budget["category"], 0.0)
        limit = budget["monthly_amount"]
        projected = actual / max(day_no, 1) * month_days
        result.append({"category": budget["category"], "currency": currency, "budget": round(limit, 2),
                       "actual_mtd": round(actual, 2), "remaining": round(limit - actual, 2),
                       "projected_month_end": round(projected, 2),
                       "variance_pct": round((actual - limit) / limit * 100, 1) if limit else None,
                       "status": "over budget" if actual > limit else "watch" if projected > limit else "on track"})
    return {"month": current_month, "currency": currency, "days_elapsed": day_no, "days_in_month": month_days,
            "budgets": result, "note": "Budgets are user-entered. Projection assumes the current month-to-date daily spend rate continues."}


def period_comparison(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = _primary_currency(rows)
    periods = sorted({_month_key(r["date"]) for r in rows})
    if len(periods) < 2:
        return {"available": False, "reason": "At least two distinct months are required."}
    latest, prior = periods[-1], periods[-2]
    def totals(period: str) -> dict[str, float]:
        group = [r for r in rows if _month_key(r["date"]) == period]
        income = sum(r["amount"] for r in group if r["type"] == "income")
        expenses = sum(r["amount"] for r in group if r["type"] == "expense")
        return {"revenue": round(income, 2), "expenses": round(expenses, 2), "net": round(income - expenses, 2)}
    current, previous = totals(latest), totals(prior)
    changes = {key: round((current[key] - previous[key]) / abs(previous[key]) * 100, 1) if previous[key] else None
               for key in current}
    return {"available": True, "current_period": latest, "previous_period": prior,
            "current": current, "previous": previous, "change_pct": changes,
            "note": "Compares the two latest months represented in the ledger; a partially recorded month is not adjusted for days elapsed."}


def data_quality(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"transaction_count": 0, "currency_count": 0, "source_counts": {}, "issues": [],
                "quality_score": 0, "note": "Import a ledger to run data-quality checks."}
    issues = []
    for field in ("date", "description", "vendor", "category", "currency"):
        missing = sum(1 for r in rows if not str(r.get(field, "")).strip())
        if missing:
            issues.append({"field": field, "count": missing, "severity": "medium", "message": f"{missing} rows have missing {field} values."})
    invalid = sum(1 for r in rows if not math.isfinite(float(r.get("amount", 0))) or float(r.get("amount", 0)) <= 0)
    if invalid:
        issues.append({"field": "amount", "count": invalid, "severity": "high", "message": f"{invalid} rows have invalid amounts."})
    currencies = Counter(r.get("currency", "USD") for r in rows)
    sources = Counter(r.get("source", "unknown") for r in rows)
    quality = max(0, round(100 - sum(x["count"] for x in issues) / len(rows) * 100))
    return {"transaction_count": len(rows), "currency_count": len(currencies), "currencies": dict(currencies),
            "source_counts": dict(sources), "issues": issues, "quality_score": quality,
            "duplicate_policy": "Exact date/vendor/amount/type/currency fingerprints are blocked at import time; duplicate rows are reported in import results.",
            "note": "Quality score is a completeness/validity heuristic, not an audit or assurance rating."}

