from __future__ import annotations

import csv
import io
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
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


def _rows():
    return store.list_transactions()


def _signals(rows=None):
    return leak_signals(rows if rows is not None else _rows())


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "leaklens-api", "version": app.version}


@app.get("/api/v1", tags=["system"])
def api_root():
    return {
        "name": "LeakLens",
        "version": app.version,
        "modules": ["transactions", "import", "overview", "expenses", "leaks", "anomalies",
                    "forecast", "health-score", "recommendations", "simulation", "vendors",
                    "subscriptions", "alerts", "assistant", "reports"],
        "authentication": "disabled by product decision; intended for a single local workspace in v1.0",
    }


@app.get("/api/v1/transactions", tags=["transactions"])
def get_transactions(q: str | None = None, kind: Literal["income", "expense"] | None = None,
                     category: str | None = None, vendor: str | None = None):
    rows = _rows()
    if q:
        needle = q.casefold()
        rows = [r for r in rows if needle in " ".join(str(r.get(k, "")) for k in ("id", "description", "vendor", "category")).casefold()]
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
    result = store.insert_transactions([row])
    if result["duplicates"]:
        raise HTTPException(status_code=409, detail="A matching transaction already exists.")
    return {"created": True, "transaction": store.list_transactions()[0]}


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
    row["source"] = "manual"
    if not store.update_transaction(transaction_id, row):
        raise HTTPException(status_code=409, detail="The edited transaction duplicates another ledger row.")
    return {"updated": True, "id": transaction_id}


@app.delete("/api/v1/transactions/{transaction_id}", tags=["transactions"])
def delete_transaction(transaction_id: str):
    if not store.delete_transaction(transaction_id):
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return {"deleted": True, "id": transaction_id}


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
    return overview(_rows())


@app.get("/api/v1/expenses", tags=["analytics"])
def get_expenses():
    return expense_intelligence(_rows())


@app.get("/api/v1/revenue", tags=["analytics"])
def get_revenue():
    return revenue_intelligence(_rows())


@app.get("/api/v1/comparison", tags=["analytics"])
def get_period_comparison():
    return period_comparison(_rows())


@app.get("/api/v1/data-quality", tags=["data"])
def get_data_quality():
    return data_quality(_rows())


@app.get("/api/v1/budgets", tags=["analytics"])
def get_budgets():
    return budget_performance(_rows(), store.get_budgets())


@app.put("/api/v1/budgets", tags=["analytics"])
def put_budget(payload: BudgetInput):
    store.set_budget(payload.category.strip(), payload.currency.upper(), payload.monthly_amount)
    return get_budgets()


@app.get("/api/v1/leaks", tags=["intelligence"])
def get_leaks():
    signals = _signals()
    return {"count": len(signals), "signals": signals,
            "disclaimer": "These are rule-based indicators for human review, not confirmed losses or fraud."}


@app.get("/api/v1/anomalies", tags=["intelligence"])
def get_anomalies():
    return anomaly_detection(_rows())


@app.get("/api/v1/forecast", tags=["intelligence"])
def get_forecast(horizon: int = 3):
    if horizon < 1 or horizon > 3:
        raise HTTPException(status_code=422, detail="Forecast horizon must be between 1 and 3 months.")
    return forecast(_rows(), horizon)


@app.get("/api/v1/health-score", tags=["intelligence"])
def get_health_score():
    rows = _rows()
    result = health_score(rows, _signals(rows))
    if result.get("available"):
        store.record_health_snapshot(result)
    result["history"] = store.get_health_history()
    return result


@app.get("/api/v1/recommendations", tags=["intelligence"])
def get_recommendations():
    rows = _rows()
    items = recommendations(rows, _signals(rows), store.get_budgets())
    return {"count": len(items), "recommendations": items}


@app.post("/api/v1/simulate", tags=["intelligence"])
def run_simulation(payload: SimulationInput):
    try:
        return simulate(_rows(), payload.revenue_change_pct, payload.expense_change_pct, payload.one_off_cost)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/vendors", tags=["analytics"])
def get_vendors():
    data = expense_intelligence(_rows())
    return {"count": len(data["vendors"]), "vendors": data["vendors"]}


@app.get("/api/v1/subscriptions", tags=["analytics"])
def get_subscriptions():
    data = expense_intelligence(_rows())
    return {"count": len(data["recurring"]), "subscriptions": data["recurring"],
            "note": "Recurring payment patterns are inferred from transaction history; usage/contract data is not available."}


@app.get("/api/v1/alerts", tags=["intelligence"])
def get_alerts():
    rows = _rows()
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
                       "severity": result["severity"], "estimated_exposure": tx["amount"],
                       "evidence": [tx], "evidence_count": 1, "status": states.get(alert_id, "open"),
                       "source": "ml-ensemble", "score": result["score"],
                       "history": store.get_alert_history(alert_id)})
    return {"count": len(alerts), "alerts": alerts}


@app.get("/api/v1/alerts/{alert_id}/history", tags=["intelligence"])
def alert_history(alert_id: str):
    return {"id": alert_id, "history": store.get_alert_history(alert_id)}


@app.patch("/api/v1/alerts/{alert_id}", tags=["intelligence"])
def set_alert_status(alert_id: str, payload: AlertStatusInput):
    valid_ids = {s["id"] for s in _signals()}
    if not (alert_id in valid_ids or alert_id.startswith("ml-")):
        raise HTTPException(status_code=404, detail="Alert not found.")
    store.update_alert_status(alert_id, payload.status)
    return {"id": alert_id, "status": payload.status}


@app.post("/api/v1/assistant", tags=["assistant"])
def ask_assistant(payload: AssistantInput):
    rows = _rows()
    return assistant_answer(payload.question, rows, _signals(rows))


@app.get("/api/v1/reports", tags=["reports"])
def download_report(format: Literal["csv", "pdf"] = "csv"):
    rows = _rows()
    summary = overview(rows)
    if format == "csv":
        buffer = io.StringIO()
        columns = ["date", "description", "vendor", "category", "amount", "type", "currency", "source"]
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
