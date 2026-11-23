from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import store
from .engines import (anomaly_detection, assistant_answer, expense_intelligence, forecast,
                      health_score, leak_signals, overview, parse_upload, recommendations, simulate,
                      revenue_intelligence, budget_performance, period_comparison, data_quality)

@asynccontextmanager
async def lifespan(_: FastAPI):
    store.init_db()
    store.seed_if_empty()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="LeakLens API",
    version="0.2.0",
    description="Local-first financial intelligence, anomaly review and forecasting API.",
)
origins = [x.strip() for x in os.getenv("LEAKLENS_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["*"],
)


class TransactionInput(BaseModel):
    date: str
    description: str = Field(min_length=1, max_length=240)
    vendor: str = Field(min_length=1, max_length=120)
    category: str = Field(default="Uncategorised", max_length=100)
    amount: float = Field(gt=0, allow_inf_nan=False)
    type: Literal["income", "expense"]
    currency: str = Field(default="USD", pattern=r"^[A-Za-z]{3}$")
    branch: str = Field(default="", max_length=120)
    account_code: str = Field(default="", max_length=40)
    account_name: str = Field(default="", max_length=120)
    service_date: str = Field(default="", max_length=10)


class BudgetInput(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    monthly_amount: float = Field(ge=0, allow_inf_nan=False)
    currency: str = Field(default="USD", pattern=r"^[A-Za-z]{3}$")


class AlertStatusInput(BaseModel):
    status: Literal["open", "reviewed", "dismissed", "resolved"]


class SimulationInput(BaseModel):
    revenue_change_pct: float = Field(default=0, ge=-100, le=300)
    expense_change_pct: float = Field(default=0, ge=-100, le=300)
    one_off_cost: float = Field(default=0, ge=0, le=1_000_000_000)


class AssistantInput(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class WorkspaceSettingsInput(BaseModel):
    accounting_basis: Literal["cash", "accrual"] = "cash"
    fiscal_year_start_month: int = Field(default=1, ge=1, le=12)
    default_currency: str = Field(default="USD", pattern=r"^[A-Za-z]{3}$")
    retention_days: int = Field(default=0, ge=0, le=3650)
    timezone: str = Field(default="UTC", min_length=1, max_length=80)


class AlertFeedbackInput(BaseModel):
    classification: Literal["confirmed_leak", "false_positive", "needs_more_evidence"]
    notes: str = Field(default="", max_length=1000)


class SubscriptionContractInput(BaseModel):
    vendor: str = Field(min_length=1, max_length=120)
    expected_amount: float = Field(gt=0, allow_inf_nan=False)
    currency: str = Field(default="USD", pattern=r"^[A-Za-z]{3}$")
    cadence: Literal["weekly", "monthly", "quarterly", "annual"] = "monthly"
    start_date: str = Field(default="", max_length=10)
    end_date: str = Field(default="", max_length=10)
    reference: str = Field(default="", max_length=160)


def _rows():
    return store.list_transactions()


def _analysis_rows():
    rows = _rows()
    if store.get_workspace_settings().get("accounting_basis") == "accrual":
        return [{**row, "date": row.get("service_date") or row["date"]} for row in rows]
    return rows


def _require_local_admin(request: Request):
    if os.getenv("LEAKLENS_ENABLE_LOCAL_ADMIN", "").casefold() != "true":
        raise HTTPException(status_code=403, detail="Local admin endpoints are disabled. Enable LEAKLENS_ENABLE_LOCAL_ADMIN only for trusted local development.")
    host = request.client.host if request.client else ""
    if host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(status_code=403, detail="Local admin endpoints are restricted to loopback clients.")


def _signals(rows=None):
    return leak_signals(rows if rows is not None else _rows())


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "leaklens-api", "version": app.version, "database": "sqlite-local", "authentication": "disabled", "public_deployment_safe": False}


@app.get("/api/v1", tags=["system"])
def api_root():
    return {
        "name": "LeakLens",
        "version": app.version,
        "modules": ["transactions", "import-preview", "import", "overview", "revenue", "expenses",
                    "period-comparison", "budgets", "data-quality", "leaks", "anomalies",
                    "forecast", "health-score-history", "recommendations", "simulation", "vendors",
                    "subscriptions", "alerts", "alert-history", "assistant", "reports"],
        "authentication": "disabled by product decision; intended for a single local workspace in v1.0",
    }


@app.get("/api/v1/transactions", tags=["transactions"])
def get_transactions(q: str | None = None, kind: Literal["income", "expense"] | None = None,
                     category: str | None = None, vendor: str | None = None):
    rows = _rows()
    if q:
        needle = q.casefold()
        rows = [r for r in rows if needle in " ".join(str(r.get(k, "")) for k in ("id", "description", "vendor", "category", "branch", "account_code", "account_name")).casefold()]
    if kind:
        rows = [r for r in rows if r["type"] == kind]
    if category:
        rows = [r for r in rows if r["category"].casefold() == category.casefold()]
    if vendor:
        rows = [r for r in rows if r["vendor"].casefold() == vendor.casefold()]
    return {"count": len(rows), "transactions": rows}


@app.post("/api/v1/transactions", tags=["transactions"])
def create_transaction(payload: TransactionInput):
    try:
        parsed = datetime.fromisoformat(payload.date).date().isoformat()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Date must use ISO format YYYY-MM-DD.") from exc
    row = payload.model_dump()
    row["date"] = parsed
    row["currency"] = payload.currency.upper()
    if row.get("service_date"):
        try:
            row["service_date"] = datetime.fromisoformat(row["service_date"]).date().isoformat()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Service date must use ISO format YYYY-MM-DD.") from exc
    row["id"] = store.fingerprint(row)[:16]
    result = store.insert_transactions([row])
    if result["duplicates"]:
        raise HTTPException(status_code=409, detail="A matching transaction already exists.")
    return {"created": True, "transaction": store.get_transaction(row["id"])}


@app.put("/api/v1/transactions/{transaction_id}", tags=["transactions"])
def edit_transaction(transaction_id: str, payload: TransactionInput):
    try:
        parsed = datetime.fromisoformat(payload.date).date().isoformat()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Date must use ISO format YYYY-MM-DD.") from exc
    if not any(r["id"] == transaction_id for r in _rows()):
        raise HTTPException(status_code=404, detail="Transaction not found.")
    row = payload.model_dump()
    row["date"] = parsed
    row["currency"] = payload.currency.upper()
    if row.get("service_date"):
        try:
            row["service_date"] = datetime.fromisoformat(row["service_date"]).date().isoformat()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Service date must use ISO format YYYY-MM-DD.") from exc
    row["source"] = "manual"
    if not store.update_transaction(transaction_id, row):
        raise HTTPException(status_code=409, detail="The edited transaction duplicates another ledger row.")
    return {"updated": True, "id": transaction_id}


@app.delete("/api/v1/transactions/{transaction_id}", tags=["transactions"])
def delete_transaction(transaction_id: str):
    if not store.delete_transaction(transaction_id):
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return {"deleted": True, "id": transaction_id}


@app.post("/api/v1/import/preview", tags=["data"])
async def preview_import(file: UploadFile = File(...)):
    filename = file.filename or "upload.csv"
    content = await file.read(10 * 1024 * 1024 + 1)
    try:
        parsed = parse_upload(filename, content)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    existing = store.existing_fingerprints()
    already_present = sum(1 for row in parsed["rows"] if store.fingerprint(row) in existing)
    return {
        "filename": filename, "total_rows": parsed["total_rows"],
        "valid_rows": len(parsed["rows"]), "estimated_new_rows": max(0, len(parsed["rows"]) - already_present),
        "duplicates_already_in_workspace": already_present,
        "duplicates_within_file": len(parsed["duplicate_rows"]),
        "duplicate_row_numbers": parsed["duplicate_rows"],
        "errors": parsed["errors"][:100], "mapped_columns": parsed["mapped_columns"],
        "preview": parsed["rows"][:10],
        "note": "Preview only. No records are written until the import is confirmed."
    }


@app.post("/api/v1/import", tags=["data"])
async def import_transactions(file: UploadFile = File(...)):
    filename = file.filename or "upload.csv"
    content = await file.read(10 * 1024 * 1024 + 1)
    try:
        parsed = parse_upload(filename, content)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = store.insert_transactions(parsed["rows"])
    return {
        "filename": filename, "total_rows": parsed["total_rows"],
        "valid_rows": len(parsed["rows"]), "inserted": result["inserted"],
        "duplicates_already_in_workspace": result["duplicates"],
        "duplicates_within_file": len(parsed["duplicate_rows"]),
        "duplicate_row_numbers": parsed["duplicate_rows"],
        "errors": parsed["errors"][:100], "mapped_columns": parsed["mapped_columns"],
    }


@app.get("/api/v1/overview", tags=["analytics"])
def get_overview():
    return overview(_analysis_rows())


@app.get("/api/v1/expenses", tags=["analytics"])
def get_expenses():
    return expense_intelligence(_analysis_rows())


@app.get("/api/v1/revenue", tags=["analytics"])
def get_revenue():
    return revenue_intelligence(_analysis_rows())


@app.get("/api/v1/comparison", tags=["analytics"])
def get_period_comparison():
    return period_comparison(_analysis_rows())


@app.get("/api/v1/data-quality", tags=["data"])
def get_data_quality():
    return data_quality(_analysis_rows())


@app.get("/api/v1/budgets", tags=["analytics"])
def get_budgets():
    return budget_performance(_rows(), store.get_budgets())


@app.put("/api/v1/budgets", tags=["analytics"])
def put_budget(payload: BudgetInput):
    store.set_budget(payload.category.strip(), payload.currency.upper(), payload.monthly_amount)
    return get_budgets()


@app.get("/api/v1/leaks", tags=["intelligence"])
def get_leaks():
    signals = _signals(_analysis_rows())
    return {"count": len(signals), "signals": signals,
            "disclaimer": "These are rule-based indicators for human review, not confirmed losses or fraud."}


@app.get("/api/v1/anomalies", tags=["intelligence"])
def get_anomalies():
    return anomaly_detection(_analysis_rows())


@app.get("/api/v1/forecast", tags=["intelligence"])
def get_forecast(horizon: int = 3):
    if horizon < 1 or horizon > 3:
        raise HTTPException(status_code=422, detail="Forecast horizon must be between 1 and 3 months.")
    return forecast(_analysis_rows(), horizon)


@app.get("/api/v1/health-score", tags=["intelligence"])
def get_health_score():
    rows = _analysis_rows()
    result = health_score(rows, _signals(rows))
    if result.get("available"):
        store.record_health_snapshot(result)
    result["history"] = store.get_health_history()
    return result


@app.get("/api/v1/recommendations", tags=["intelligence"])
def get_recommendations():
    rows = _analysis_rows()
    items = recommendations(rows, _signals(rows), store.get_budgets())
    return {"count": len(items), "recommendations": items}


@app.post("/api/v1/simulate", tags=["intelligence"])
def run_simulation(payload: SimulationInput):
    try:
        return simulate(_analysis_rows(), payload.revenue_change_pct, payload.expense_change_pct, payload.one_off_cost)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/vendors", tags=["analytics"])
def get_vendors():
    data = expense_intelligence(_analysis_rows())
    return {"count": len(data["vendors"]), "vendors": data["vendors"]}


@app.get("/api/v1/subscriptions", tags=["analytics"])
def get_subscriptions():
    data = expense_intelligence(_analysis_rows())
    return {"count": len(data["recurring"]), "subscriptions": data["recurring"],
            "note": "Recurring payment patterns are inferred from transaction history; usage/contract data is not available."}


@app.get("/api/v1/alerts", tags=["intelligence"])
def get_alerts():
    rows = _analysis_rows()
    signals = _signals(rows)
    anomaly = anomaly_detection(rows)
    states = store.get_alert_states()
    alerts = []
    for signal in signals:
        alerts.append({**signal, "status": states.get(signal["id"], "open"), "source": "rule",
                       "history": store.get_alert_history(signal["id"])})
    for result in anomaly.get("results", []):
        tx = result["transaction"]
        alert_id = f"ml-{tx['id']}"
        alerts.append({"id": alert_id, "title": "Unusual transaction pattern", "detail": result["explanation"],
                       "severity": result["severity"], "estimated_exposure": 0,
                       "amount_under_review": tx["amount"], "evidence": [tx], "evidence_count": 1, "status": states.get(alert_id, "open"),
                       "source": "ml-ensemble", "score": result["score"],
                       "history": store.get_alert_history(alert_id)})
    return {"count": len(alerts), "alerts": alerts}


@app.get("/api/v1/alerts/{alert_id}/history", tags=["intelligence"])
def alert_history(alert_id: str):
    return {"id": alert_id, "history": store.get_alert_history(alert_id)}


@app.patch("/api/v1/alerts/{alert_id}", tags=["intelligence"])
def set_alert_status(alert_id: str, payload: AlertStatusInput):
    rows = _rows()
    valid_rule_ids = {s["id"] for s in _signals(rows)}
    anomaly = anomaly_detection(rows)
    valid_ml_ids = {f"ml-{item['transaction']['id']}" for item in anomaly.get("results", [])}
    if alert_id not in valid_rule_ids and alert_id not in valid_ml_ids:
        raise HTTPException(status_code=404, detail="Alert not found.")
    store.update_alert_status(alert_id, payload.status)
    return {"id": alert_id, "status": payload.status}


@app.post("/api/v1/assistant", tags=["assistant"])
def ask_assistant(payload: AssistantInput):
    rows = _analysis_rows()
    return assistant_answer(payload.question, rows, _signals(rows))



@app.get("/api/v1/settings", tags=["settings"])
def get_settings():
    return store.get_workspace_settings()


@app.put("/api/v1/settings", tags=["settings"])
def put_settings(payload: WorkspaceSettingsInput):
    values = payload.model_dump()
    values["default_currency"] = payload.default_currency.upper()
    return store.set_workspace_settings(values)


@app.get("/api/v1/fiscal-year", tags=["analytics"])
def get_fiscal_year():
    settings = store.get_workspace_settings()
    start_month = int(settings.get("fiscal_year_start_month", 1))
    today = datetime.now().date()
    start_year = today.year if today.month >= start_month else today.year - 1
    start = datetime(start_year, start_month, 1).date()
    end = datetime(start_year + 1, start_month, 1).date()
    rows = [row for row in _analysis_rows() if start.isoformat() <= row["date"] < end.isoformat()]
    return {"start_date": start.isoformat(), "end_date_exclusive": end.isoformat(),
            "accounting_basis": settings.get("accounting_basis", "cash"), "summary": overview(rows)}


@app.get("/api/v1/branches", tags=["analytics"])
def get_branches():
    return {"branches": store.get_branch_summary(),
            "note": "Only transactions with explicit branch/location values are included; unassigned transactions are excluded."}


@app.get("/api/v1/chart-of-accounts", tags=["analytics"])
def get_chart_of_accounts():
    grouped = {}
    for row in _analysis_rows():
        key = (row.get("account_code") or "UNMAPPED", row.get("account_name") or row.get("category") or "Unmapped", row["currency"])
        item = grouped.setdefault(key, {"account_code": key[0], "account_name": key[1], "currency": key[2],
                                        "income": 0.0, "expenses": 0.0, "transaction_count": 0})
        item["income" if row["type"] == "income" else "expenses"] += row["amount"]
        item["transaction_count"] += 1
    accounts = []
    for item in grouped.values():
        item["net"] = round(item["income"] - item["expenses"], 2)
        item["income"] = round(item["income"], 2)
        item["expenses"] = round(item["expenses"], 2)
        accounts.append(item)
    return {"accounts": sorted(accounts, key=lambda item: (item["account_code"], item["currency"])),
            "note": "Unmapped rows remain visible. Account codes/names are supplied by the ledger and are not independently certified classifications."}


@app.post("/api/v1/alerts/{alert_id}/feedback", tags=["intelligence"])
def submit_alert_feedback(alert_id: str, payload: AlertFeedbackInput):
    valid_rule_ids = {item["id"] for item in _signals(_analysis_rows())}
    anomaly = anomaly_detection(_analysis_rows())
    valid_ml_ids = {f"ml-{item['transaction']['id']}" for item in anomaly.get("results", [])}
    if alert_id not in valid_rule_ids and alert_id not in valid_ml_ids:
        raise HTTPException(status_code=404, detail="Alert not found.")
    store.record_alert_feedback(alert_id, payload.classification, payload.notes)
    return {"saved": True, "metrics": store.get_alert_feedback_metrics()}


@app.get("/api/v1/alert-feedback/metrics", tags=["intelligence"])
def alert_feedback_metrics():
    return store.get_alert_feedback_metrics()


@app.get("/api/v1/subscription-contracts", tags=["subscriptions"])
def get_subscription_contracts():
    return {"contracts": store.list_subscription_contracts()}


@app.post("/api/v1/subscription-contracts", tags=["subscriptions"])
def save_subscription_contract(payload: SubscriptionContractInput):
    values = payload.model_dump()
    values["currency"] = payload.currency.upper()
    for field in ("start_date", "end_date"):
        if values[field]:
            try:
                values[field] = datetime.fromisoformat(values[field]).date().isoformat()
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=f"{field} must use ISO format YYYY-MM-DD.") from exc
    if values["start_date"] and values["end_date"] and values["end_date"] < values["start_date"]:
        raise HTTPException(status_code=422, detail="Contract end date must not precede its start date.")
    values["id"] = store.fingerprint({"date": values.get("start_date", ""), "vendor": values["vendor"],
                                      "amount": values["expected_amount"], "type": "contract",
                                      "currency": values["currency"]})[:20]
    return {"contract": store.upsert_subscription_contract(values)}


@app.get("/api/v1/subscription-contracts/comparison", tags=["subscriptions"])
def compare_subscription_contracts():
    contracts = store.list_subscription_contracts()
    recurring = expense_intelligence(_analysis_rows()).get("recurring", [])
    comparisons = []
    for contract in contracts:
        factor = {"weekly": 52 / 12, "monthly": 1, "quarterly": 1 / 3, "annual": 1 / 12}[contract["cadence"]]
        expected_monthly = contract["expected_amount"] * factor
        matches = [item for item in recurring if item.get("vendor", "").casefold() == contract["vendor"].casefold()
                   and item.get("currency", contract["currency"]) == contract["currency"]]
        observed = max((float(item.get("average_amount", item.get("average", 0))) for item in matches), default=None)
        comparisons.append({**contract, "expected_monthly": round(expected_monthly, 2),
                            "observed_recurring_amount": round(observed, 2) if observed is not None else None,
                            "variance": round(observed - expected_monthly, 2) if observed is not None else None,
                            "status": "matched_for_review" if observed is not None else "no_matching_recurring_pattern"})
    return {"comparisons": comparisons,
            "note": "This compares ledger-inferred recurring amounts with user-entered contract terms. It does not verify usage, invoice authenticity, contract authenticity or entitlement."}


@app.get("/api/v1/privacy", tags=["privacy"])
def privacy_summary():
    return {"authentication": "disabled", "deployment_safe": False, "database": "SQLite local-development store",
            "retention_days": store.get_workspace_settings().get("retention_days", 0),
            "retention_note": "0 means no automatic deletion. A non-zero retention value is a policy record only; automated deletion is not enabled.",
            "backup": "Backup/restore routes require LEAKLENS_ENABLE_LOCAL_ADMIN=true and a loopback client.",
            "deletion": "Data deletion requires the same local-only gate and an exact confirmation phrase.",
            "warning": "Do not expose this unauthenticated single-workspace API to the public internet or deploy with persistent financial uploads."}


@app.get("/api/v1/admin/backup", tags=["privacy"])
def create_local_backup(request: Request):
    _require_local_admin(request)
    if not store.DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Workspace database does not exist yet.")
    with sqlite3.connect(store.DB_PATH) as db:
        content = db.serialize()
    return StreamingResponse(io.BytesIO(content), media_type="application/vnd.sqlite3",
                             headers={"Content-Disposition": "attachment; filename=leaklens-backup.sqlite3"})


@app.post("/api/v1/admin/restore", tags=["privacy"])
async def restore_local_backup(request: Request, confirmation: str, file: UploadFile = File(...)):
    _require_local_admin(request)
    if confirmation != "RESTORE LEAKLENS DATABASE":
        raise HTTPException(status_code=400, detail="Restore confirmation phrase did not match.")
    content = await file.read(100 * 1024 * 1024 + 1)
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Backup exceeds the 100 MB restore limit.")
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    try:
        with sqlite3.connect(temp_path) as source:
            check = source.execute("PRAGMA quick_check").fetchone()
            tables = {row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            required = {"transactions", "app_meta", "budgets", "alert_states"}
            if not check or check[0] != "ok" or not required.issubset(tables):
                raise HTTPException(status_code=400, detail="Uploaded file is not a valid LeakLens SQLite backup.")
            with sqlite3.connect(store.DB_PATH) as target:
                source.backup(target)
    finally:
        temp_path.unlink(missing_ok=True)
    return {"restored": True, "transaction_count": len(_rows())}


@app.delete("/api/v1/admin/financial-data", tags=["privacy"])
def delete_local_financial_data(request: Request, confirmation: str):
    _require_local_admin(request)
    if confirmation != "DELETE MY LEAKLENS DATA":
        raise HTTPException(status_code=400, detail="Deletion confirmation phrase did not match.")
    return {"deleted": store.delete_financial_data(),
            "note": "Workspace preferences are retained. Demo data will not be reseeded automatically."}


@app.get("/api/v1/reports", tags=["reports"])
def download_report(format: Literal["csv", "pdf"] = "csv"):
    rows = _analysis_rows()
    summary = overview(rows)
    if format == "csv":
        buffer = io.StringIO()
        columns = ["date", "service_date", "description", "vendor", "category", "account_code", "account_name", "branch", "amount", "type", "currency", "source"]
        writer = csv.DictWriter(buffer, fieldnames=columns)
        writer.writeheader()
        def safe_cell(value):
            if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\\t", "\\r")):
                return "'" + value
            return value
        writer.writerows([{k: safe_cell(row.get(k, "")) for k in columns} for row in rows])
        output = io.BytesIO(buffer.getvalue().encode("utf-8"))
        return StreamingResponse(output, media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=leaklens-transactions.csv"})
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="PDF export dependency is not installed.") from exc
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, title="LeakLens Financial Summary")
    styles = getSampleStyleSheet()
    story = [Paragraph("LeakLens — Financial Summary", styles["Title"]),
             Paragraph("Generated from the current workspace ledger. Indicative analysis, not audited accounts.", styles["BodyText"]),
             Spacer(1, 16)]
    data = [["Metric", "Recorded value"],
            ["Revenue", f'{summary["revenue"]:,.2f} {summary["currency"]}'],
            ["Expenses", f'{summary["expenses"]:,.2f} {summary["currency"]}'],
            ["Net movement", f'{summary["net"]:,.2f} {summary["currency"]}'],
            ["Profit margin", f'{summary["profit_margin"]:.1f}%'],
            ["Transactions", str(summary["transaction_count"])]]
    table = Table(data, colWidths=[220, 240])
    table.setStyle(TableStyle([("BACKGROUND", (0,0),(-1,0), colors.HexColor("#C6F432")),
                               ("TEXTCOLOR", (0,0),(-1,0), colors.HexColor("#0B0B0C")),
                               ("GRID", (0,0),(-1,-1), .4, colors.HexColor("#CCCCCC")),
                               ("PADDING", (0,0),(-1,-1), 8)]))
    story.append(table)
    story.append(Spacer(1, 18))
    story.append(Paragraph("Monthly trends", styles["Heading2"]))
    monthly_data = [["Month", "Revenue", "Expenses", "Net"]]
    monthly_data += [[m["month"], f'{m["income"]:,.2f}', f'{m["expenses"]:,.2f}', f'{m["income"]-m["expenses"]:,.2f}'] for m in summary["monthly"]]
    monthly_table = Table(monthly_data, repeatRows=1)
    monthly_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#202124")),
                                       ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                                       ("GRID",(0,0),(-1,-1),.4,colors.HexColor("#CCCCCC")),
                                       ("PADDING",(0,0),(-1,-1),6)]))
    story.append(monthly_table)
    doc.build(story)
    output.seek(0)
    return StreamingResponse(output, media_type="application/pdf",
                             headers={"Content-Disposition": "attachment; filename=leaklens-financial-summary.pdf"})
