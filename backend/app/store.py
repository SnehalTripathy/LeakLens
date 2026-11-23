from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.getenv("LEAKLENS_DB_PATH", str(ROOT / ".data" / "leaklens.sqlite3")))


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def fingerprint(row: dict[str, Any]) -> str:
    parts = [
        str(row.get("date", "")),
        str(row.get("vendor", "")).strip().casefold(),
        f"{float(row.get('amount', 0)):.2f}",
        str(row.get("type", "")).strip().casefold(),
        str(row.get("currency", "USD")).upper(),
    ]
    # Preserve historical fingerprints for legacy transactions without branch metadata.
    if str(row.get("branch", "")).strip():
        parts.append(str(row.get("branch", "")).strip().casefold())
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def init_db() -> None:
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL UNIQUE,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                vendor TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                type TEXT NOT NULL CHECK(type IN ('income','expense')),
                currency TEXT NOT NULL DEFAULT 'USD',
                source TEXT NOT NULL DEFAULT 'manual',
                created_at TEXT NOT NULL
            )
        """)
        columns = {row["name"] for row in db.execute("PRAGMA table_info(transactions)").fetchall()}
        for name, definition in {
            "branch": "TEXT NOT NULL DEFAULT ''",
            "account_code": "TEXT NOT NULL DEFAULT ''",
            "account_name": "TEXT NOT NULL DEFAULT ''",
            "service_date": "TEXT NOT NULL DEFAULT ''",
        }.items():
            if name not in columns:
                db.execute(f"ALTER TABLE transactions ADD COLUMN {name} {definition}")
        db.execute("""
            CREATE TABLE IF NOT EXISTS account_mappings (
                category TEXT PRIMARY KEY,
                account_code TEXT NOT NULL,
                account_name TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS workspace_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS alert_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT NOT NULL,
                classification TEXT NOT NULL CHECK(classification IN ('confirmed_leak','false_positive','needs_more_evidence')),
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_alert_feedback_id ON alert_feedback(alert_id)")
        db.execute("""
            CREATE TABLE IF NOT EXISTS subscription_contracts (
                id TEXT PRIMARY KEY,
                vendor TEXT NOT NULL,
                expected_amount REAL NOT NULL CHECK(expected_amount > 0),
                currency TEXT NOT NULL,
                cadence TEXT NOT NULL CHECK(cadence IN ('weekly','monthly','quarterly','annual')),
                start_date TEXT NOT NULL DEFAULT '',
                end_date TEXT NOT NULL DEFAULT '',
                reference TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS alert_states (
                alert_id TEXT PRIMARY KEY,
                status TEXT NOT NULL CHECK(status IN ('open','reviewed','dismissed','resolved')),
                updated_at TEXT NOT NULL
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_transactions_vendor ON transactions(vendor)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category)")
        db.execute("""
            CREATE TABLE IF NOT EXISTS health_score_history (
                snapshot_date TEXT PRIMARY KEY,
                score INTEGER NOT NULL,
                label TEXT NOT NULL,
                components_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS alert_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT NOT NULL,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_alert_history_id ON alert_status_history(alert_id, updated_at)")
        db.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                category TEXT NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD',
                monthly_amount REAL NOT NULL CHECK(monthly_amount >= 0),
                updated_at TEXT NOT NULL,
                PRIMARY KEY(category, currency)
            )
        """)


def _seed_rows() -> list[dict[str, Any]]:
    today = date.today()
    rows: list[dict[str, Any]] = []
    recurring = [("WorkSuite Pro", "Software", 189.0), ("CloudSphere", "Technology", 640.0),
                 ("LedgerFlow", "Software", 79.0), ("Office Hub", "Operations", 145.0)]
    for month_back in range(5, -1, -1):
        month_index = today.month - 1 - month_back
        year = today.year + month_index // 12
        month = month_index % 12 + 1
        last_day = (date(year + (month == 12), (month % 12) + 1, 1) - timedelta(days=1)).day
        def day(n: int) -> str:
            return date(year, month, min(n, last_day)).isoformat()
        # Income streams: the business has a modest upward trend.
        trend = 1 + (5 - month_back) * 0.045
        for i, (vendor, amount) in enumerate([
            ("Northstar Co.", 9200), ("Verity Labs", 7100), ("Morrow Retail", 5400)
        ]):
            rows.append({"date": day(5 + i * 9), "description": f"Client payment — {vendor}",
                         "vendor": vendor, "category": "Sales", "amount": round(amount * trend, 2),
                         "type": "income", "currency": "USD", "source": "demo"})
        for vendor, category, amount in recurring:
            # An intentionally unusual duplicate-like payment occurs once for review.
            actual = amount * (1.35 if vendor == "WorkSuite Pro" and month_back == 0 else 1.0)
            rows.append({"date": day(12), "description": f"Recurring payment — {vendor}",
                         "vendor": vendor, "category": category, "amount": actual,
                         "type": "expense", "currency": "USD", "source": "demo"})
        expense_items = [
            ("AdCurrent", "Marketing", 980 + month_back * 22),
            ("People & Co.", "People", 4700 + month_back * 35),
            ("Paper & Co.", "Operations", 210 + month_back * 4),
            ("Morrow Consulting", "Professional services", 680),
            ("CloudSphere", "Technology", 420),
        ]
        for i, (vendor, category, amount) in enumerate(expense_items):
            if vendor == "AdCurrent" and month_back == 0:
                amount *= 1.85
            rows.append({"date": day(16 + i % 10), "description": f"{category} expense — {vendor}",
                         "vendor": vendor, "category": category, "amount": round(amount, 2),
                         "type": "expense", "currency": "USD", "source": "demo"})
    return rows


def seed_if_empty(force: bool = False) -> None:
    with connect() as db:
        marker = db.execute("SELECT value FROM app_meta WHERE key='demo_seeded'").fetchone()
        count = db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        if marker and not force:
            return
        if count and not force:
            # Existing workspaces with transactions predate the seed marker; do not overwrite them.
            db.execute("INSERT OR REPLACE INTO app_meta(key,value,updated_at) VALUES(?,?,?)",
                       ("demo_seeded", "existing_workspace", datetime.now(timezone.utc).isoformat()))
            return
    insert_transactions(_seed_rows())
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO app_meta(key,value,updated_at) VALUES(?,?,?)",
                   ("demo_seeded", "true", datetime.now(timezone.utc).isoformat()))


def insert_transactions(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    inserted = 0
    duplicates = 0
    with connect() as db:
        for row in rows:
            clean = dict(row)
            clean.setdefault("currency", "USD")
            clean.setdefault("source", "import")
            if not clean.get("account_code") or not clean.get("account_name"):
                mapping = get_account_mapping(clean.get("category", ""))
                if mapping:
                    clean["account_code"] = clean.get("account_code") or mapping["account_code"]
                    clean["account_name"] = clean.get("account_name") or mapping["account_name"]
            clean["id"] = clean.get("id") or fingerprint(clean)[:16]
            fp = fingerprint(clean)
            try:
                db.execute("""
                    INSERT INTO transactions
                    (id,fingerprint,date,description,vendor,category,amount,type,currency,source,
                     branch,account_code,account_name,service_date,created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (clean["id"], fp, clean["date"], clean["description"], clean["vendor"],
                      clean["category"], float(clean["amount"]), clean["type"], clean["currency"],
                      clean["source"], clean.get("branch", ""), clean.get("account_code", ""),
                      clean.get("account_name", ""), clean.get("service_date", ""),
                      datetime.now(timezone.utc).isoformat()))
                inserted += 1
            except sqlite3.IntegrityError:
                duplicates += 1
    return {"inserted": inserted, "duplicates": duplicates}


def get_transaction(transaction_id: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("""
            SELECT id,date,description,vendor,category,amount,type,currency,source,
                   branch,account_code,account_name,service_date
            FROM transactions WHERE id=?
        """, (transaction_id,)).fetchone()
    return dict(row) if row else None


def list_transactions() -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("""
            SELECT id,date,description,vendor,category,amount,type,currency,source,
                   branch,account_code,account_name,service_date
            FROM transactions ORDER BY date DESC, rowid DESC
        """).fetchall()
    return [dict(row) for row in rows]


def clear_transactions() -> None:
    with connect() as db:
        db.execute("DELETE FROM transactions")


def update_alert_status(alert_id: str, status: str) -> None:
    with connect() as db:
        timestamp = datetime.now(timezone.utc).isoformat()
        db.execute("""
            INSERT INTO alert_states(alert_id,status,updated_at) VALUES(?,?,?)
            ON CONFLICT(alert_id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at
        """, (alert_id, status, timestamp))
        db.execute("INSERT INTO alert_status_history(alert_id,status,updated_at) VALUES(?,?,?)",
                   (alert_id, status, timestamp))


def get_alert_states() -> dict[str, str]:
    with connect() as db:
        rows = db.execute("SELECT alert_id,status FROM alert_states").fetchall()
    return {row["alert_id"]: row["status"] for row in rows}

def delete_transaction(transaction_id: str) -> bool:
    with connect() as db:
        result = db.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
    return result.rowcount > 0


def update_transaction(transaction_id: str, row: dict[str, Any]) -> bool:
    clean = dict(row)
    clean.setdefault("currency", "USD")
    clean.setdefault("source", "manual")
    fp = fingerprint(clean)
    with connect() as db:
        try:
            result = db.execute("""
                UPDATE transactions SET fingerprint=?,date=?,description=?,vendor=?,category=?,
                    amount=?,type=?,currency=?,source=?,branch=?,account_code=?,account_name=?,service_date=? WHERE id=?
            """, (fp, clean["date"], clean["description"], clean["vendor"], clean["category"],
                  float(clean["amount"]), clean["type"], clean["currency"], clean["source"],
                  clean.get("branch", ""), clean.get("account_code", ""), clean.get("account_name", ""),
                  clean.get("service_date", ""), transaction_id))
        except sqlite3.IntegrityError:
            return False
    return result.rowcount > 0


def get_budgets() -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT category,currency,monthly_amount,updated_at FROM budgets ORDER BY category").fetchall()
    return [dict(row) for row in rows]


def set_budget(category: str, currency: str, monthly_amount: float) -> None:
    with connect() as db:
        db.execute("""
            INSERT INTO budgets(category,currency,monthly_amount,updated_at) VALUES(?,?,?,?)
            ON CONFLICT(category,currency) DO UPDATE SET monthly_amount=excluded.monthly_amount,updated_at=excluded.updated_at
        """, (category, currency, monthly_amount, datetime.now().astimezone().isoformat()))


def record_health_snapshot(snapshot: dict[str, Any]) -> None:
    snapshot_day = date.today().isoformat()
    with connect() as db:
        db.execute("""
            INSERT INTO health_score_history(snapshot_date,score,label,components_json,created_at)
            VALUES(?,?,?,?,?)
            ON CONFLICT(snapshot_date) DO UPDATE SET score=excluded.score,label=excluded.label,
                components_json=excluded.components_json,created_at=excluded.created_at
        """, (snapshot_day, int(snapshot["score"]), str(snapshot["label"]),
              json.dumps(snapshot.get("components", [])), datetime.now(timezone.utc).isoformat()))


def get_health_history(limit: int = 90) -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("""
            SELECT snapshot_date,score,label,components_json FROM health_score_history
            ORDER BY snapshot_date DESC LIMIT ?
        """, (max(1, min(limit, 365)),)).fetchall()
    return [{"date": row["snapshot_date"], "score": row["score"], "label": row["label"],
             "components": json.loads(row["components_json"])} for row in reversed(rows)]


def get_alert_history(alert_id: str) -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("""
            SELECT status,updated_at FROM alert_status_history
            WHERE alert_id=? ORDER BY updated_at DESC, id DESC LIMIT 100
        """, (alert_id,)).fetchall()
    return [{"status": row["status"], "updated_at": row["updated_at"]} for row in reversed(rows)]


def existing_fingerprints() -> set[str]:
    with connect() as db:
        rows = db.execute("SELECT fingerprint FROM transactions").fetchall()
    return {row["fingerprint"] for row in rows}


DEFAULT_SETTINGS = {"accounting_basis": "cash", "fiscal_year_start_month": 1, "default_currency": "USD",
                    "retention_days": 0, "timezone": "UTC"}


def get_workspace_settings() -> dict[str, Any]:
    with connect() as db:
        rows = db.execute("SELECT key,value FROM workspace_settings").fetchall()
    settings = dict(DEFAULT_SETTINGS)
    for row in rows:
        try:
            settings[row["key"]] = json.loads(row["value"])
        except (TypeError, json.JSONDecodeError):
            continue
    return settings


def set_workspace_settings(values: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        for key, value in values.items():
            db.execute("""INSERT INTO workspace_settings(key,value,updated_at) VALUES(?,?,?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",
                (key, json.dumps(value), now))
    return get_workspace_settings()


def get_branch_summary() -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("""SELECT branch,currency,
            SUM(CASE WHEN type='income' THEN amount ELSE 0 END) AS revenue,
            SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) AS expenses,
            COUNT(*) AS transaction_count
            FROM transactions WHERE TRIM(branch)<>'' GROUP BY branch,currency
            ORDER BY branch,currency""").fetchall()
    return [dict(row) | {"net": round(row["revenue"] - row["expenses"], 2)} for row in rows]


def record_alert_feedback(alert_id: str, classification: str, notes: str = "") -> None:
    with connect() as db:
        db.execute("INSERT INTO alert_feedback(alert_id,classification,notes,created_at) VALUES(?,?,?,?)",
                   (alert_id, classification, notes[:1000], datetime.now(timezone.utc).isoformat()))


def get_alert_feedback_metrics() -> dict[str, Any]:
    with connect() as db:
        rows = db.execute("SELECT classification,COUNT(*) AS count FROM alert_feedback GROUP BY classification").fetchall()
        latest = db.execute("SELECT alert_id,classification,notes,created_at FROM alert_feedback ORDER BY id DESC LIMIT 100").fetchall()
    counts = {row["classification"]: row["count"] for row in rows}
    confirmed = counts.get("confirmed_leak", 0)
    false_positive = counts.get("false_positive", 0)
    adjudicated = confirmed + false_positive
    return {"counts": counts, "adjudicated_reviews": adjudicated,
            "observed_precision_pct": round(confirmed / adjudicated * 100, 2) if adjudicated else None,
            "recall_pct": None,
            "recall_note": "Recall cannot be calculated from alert feedback alone because unflagged transactions have not been independently labelled.",
            "recent_feedback": [dict(row) for row in latest]}


def upsert_subscription_contract(contract: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        db.execute("""INSERT INTO subscription_contracts
            (id,vendor,expected_amount,currency,cadence,start_date,end_date,reference,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET vendor=excluded.vendor,expected_amount=excluded.expected_amount,
            currency=excluded.currency,cadence=excluded.cadence,start_date=excluded.start_date,
            end_date=excluded.end_date,reference=excluded.reference""",
            (contract["id"], contract["vendor"], contract["expected_amount"], contract["currency"],
             contract["cadence"], contract.get("start_date", ""), contract.get("end_date", ""),
             contract.get("reference", ""), now))
    return next(item for item in list_subscription_contracts() if item["id"] == contract["id"])


def list_subscription_contracts() -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT id,vendor,expected_amount,currency,cadence,start_date,end_date,reference,created_at FROM subscription_contracts ORDER BY vendor").fetchall()
    return [dict(row) for row in rows]


def delete_financial_data() -> dict[str, int]:
    tables = ["transactions", "budgets", "alert_states", "alert_status_history", "health_score_history",
              "alert_feedback", "subscription_contracts"]
    counts = {}
    with connect() as db:
        for table in tables:
            counts[table] = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            db.execute(f"DELETE FROM {table}")
        db.execute("INSERT OR REPLACE INTO app_meta(key,value,updated_at) VALUES(?,?,?)",
                   ("demo_seeded", "user_data_deleted", datetime.now(timezone.utc).isoformat()))
    return counts


def get_account_mappings() -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT category,account_code,account_name,updated_at FROM account_mappings ORDER BY category").fetchall()
    return [dict(row) for row in rows]


def get_account_mapping(category: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute("SELECT category,account_code,account_name,updated_at FROM account_mappings WHERE category=? COLLATE NOCASE", (category.strip(),)).fetchone()
    return dict(row) if row else None


def set_account_mapping(category: str, account_code: str, account_name: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        db.execute("""INSERT INTO account_mappings(category,account_code,account_name,updated_at)
            VALUES(?,?,?,?) ON CONFLICT(category) DO UPDATE SET account_code=excluded.account_code,
            account_name=excluded.account_name,updated_at=excluded.updated_at""",
            (category.strip(), account_code.strip(), account_name.strip(), now))
        db.execute("""UPDATE transactions SET account_code=?,account_name=?
            WHERE category=? COLLATE NOCASE""", (account_code.strip(), account_name.strip(), category.strip()))
    return get_account_mapping(category) or {}
