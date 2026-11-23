from fastapi.testclient import TestClient
from app import store
from app.main import app

def setup_workspace(tmp_path):
    store.DB_PATH = tmp_path / "test.sqlite3"
    store.init_db()
    store.clear_transactions()
    store.seed_if_empty(force=True)

def test_core_endpoints(tmp_path):
    setup_workspace(tmp_path)
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        overview = client.get("/api/v1/overview").json()
        assert overview["transaction_count"] >= 50
        assert overview["revenue"] > 0
        assert overview["expenses"] > 0
        for endpoint in ["/api/v1/expenses", "/api/v1/leaks", "/api/v1/anomalies",
                         "/api/v1/health-score", "/api/v1/recommendations",
                         "/api/v1/vendors", "/api/v1/subscriptions", "/api/v1/alerts"]:
            assert client.get(endpoint).status_code == 200
        anomaly = client.get("/api/v1/anomalies").json()
        assert "Local Outlier Factor" in anomaly["models"]
        health = client.get("/api/v1/health-score").json()
        assert health["available"] is True
        assert len(health["history"]) == 1
        alerts = client.get("/api/v1/alerts").json()["alerts"]
        if alerts:
            alert_id = alerts[0]["id"]
            assert client.patch(f"/api/v1/alerts/{alert_id}", json={"status": "reviewed"}).status_code == 200
            history = client.get(f"/api/v1/alerts/{alert_id}/history").json()["history"]
            assert history[-1]["status"] == "reviewed"
            assert client.patch(f"/api/v1/alerts/{alert_id}", json={"status": "open"}).status_code == 200
            reopened = client.get(f"/api/v1/alerts/{alert_id}/history").json()["history"]
            assert reopened[-1]["status"] == "open"
        assert client.patch("/api/v1/alerts/not-a-real-alert", json={"status": "reviewed"}).status_code == 404
        assert client.get("/api/v1/forecast").json()["available"] is True

def test_import_validates_and_deduplicates(tmp_path):
    setup_workspace(tmp_path)
    with TestClient(app) as client:
        csv = b"date,description,vendor,category,amount,type,currency\n2026-11-01,Invoice,Example Co,Sales,1200,income,USD\nnot-a-date,Bad row,Example Co,Sales,100,income,USD\n"
        response = client.post("/api/v1/import", files={"file": ("ledger.csv", csv, "text/csv")})
        assert response.status_code == 200
        assert response.json()["inserted"] == 1
        assert len(response.json()["errors"]) == 1
        again = client.post("/api/v1/import", files={"file": ("ledger.csv", csv, "text/csv")})
        assert again.json()["duplicates_already_in_workspace"] == 1

def test_simulator_and_assistant(tmp_path):
    setup_workspace(tmp_path)
    with TestClient(app) as client:
        result = client.post("/api/v1/simulate", json={"revenue_change_pct": 10, "expense_change_pct": -5})
        assert result.status_code == 200 and result.json()["net_change"] > 0
        answer = client.post("/api/v1/assistant", json={"question": "Which vendor costs the most?"})
        assert answer.status_code == 200 and answer.json()["evidence"]

def test_report_download(tmp_path):
    setup_workspace(tmp_path)
    with TestClient(app) as client:
        csv = client.get("/api/v1/reports?format=csv")
        assert csv.status_code == 200 and "text/csv" in csv.headers["content-type"]
        pdf = client.get("/api/v1/reports?format=pdf")
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

def test_revenue_quality_budgets_and_period_comparison(tmp_path):
    setup_workspace(tmp_path)
    with TestClient(app) as client:
        assert client.get("/api/v1/revenue").json()["total"] > 0
        assert client.get("/api/v1/comparison").json()["available"] is True
        quality = client.get("/api/v1/data-quality").json()
        assert quality["transaction_count"] >= 50
        saved = client.put("/api/v1/budgets", json={"category": "Marketing", "monthly_amount": 1500, "currency": "USD"})
        assert saved.status_code == 200
        assert any(x["category"] == "Marketing" for x in saved.json()["budgets"])
        recs = client.get("/api/v1/recommendations").json()["recommendations"]
        assert any("budget exceeded" in r["title"].lower() for r in recs)


def test_transaction_update_and_delete(tmp_path):
    setup_workspace(tmp_path)
    with TestClient(app) as client:
        tx = client.get("/api/v1/transactions").json()["transactions"][0]
        payload = {k: tx[k] for k in ["date","description","vendor","category","amount","type","currency"]}
        payload["description"] = "Edited from API test"
        updated = client.put(f"/api/v1/transactions/{tx['id']}", json=payload)
        assert updated.status_code == 200
        fetched = client.get("/api/v1/transactions", params={"q": "Edited from API test"})
        assert fetched.json()["count"] == 1
        deleted = client.delete(f"/api/v1/transactions/{tx['id']}")
        assert deleted.status_code == 200
        assert client.delete(f"/api/v1/transactions/{tx['id']}").status_code == 404

def test_import_preview_does_not_write_until_confirmed(tmp_path):
    setup_workspace(tmp_path)
    with TestClient(app) as client:
        before = client.get("/api/v1/transactions").json()["count"]
        csv = b"date,description,vendor,category,amount,type,currency\n2026-11-03,Preview only,Preview Vendor,Operations,75,expense,USD\n"
        preview = client.post("/api/v1/import/preview", files={"file": ("preview.csv", csv, "text/csv")})
        assert preview.status_code == 200
        assert preview.json()["estimated_new_rows"] == 1
        assert "Preview only" in preview.json()["preview"][0]["description"]
        after_preview = client.get("/api/v1/transactions").json()["count"]
        assert after_preview == before
        imported = client.post("/api/v1/import", files={"file": ("preview.csv", csv, "text/csv")})
        assert imported.json()["inserted"] == 1

def test_positive_only_import_requires_transaction_direction(tmp_path):
    setup_workspace(tmp_path)
    with TestClient(app) as client:
        csv = b"date,description,vendor,category,amount\n2026-11-05,Office supplies,Paper Co,Operations,75\n"
        response = client.post("/api/v1/import/preview", files={"file": ("ambiguous.csv", csv, "text/csv")})
        assert response.status_code == 400
        assert "does not identify income versus expense" in response.json()["detail"]

def test_import_detect_review_and_report_end_to_end(tmp_path):
    setup_workspace(tmp_path)
    with TestClient(app) as client:
        csv = (
            "date,description,vendor,category,amount,type,currency\n"
            "2026-06-12,Recurring infrastructure,Cloud Test Vendor,Technology,100,expense,USD\n"
            "2026-07-12,Recurring infrastructure,Cloud Test Vendor,Technology,100,expense,USD\n"
            "2026-08-12,Recurring infrastructure,Cloud Test Vendor,Technology,100,expense,USD\n"
            "2026-09-12,Recurring infrastructure,Cloud Test Vendor,Technology,100,expense,USD\n"
            "2026-10-12,Recurring infrastructure,Cloud Test Vendor,Technology,100,expense,USD\n"
            "2026-11-12,Unusual infrastructure charge,Cloud Test Vendor,Technology,250,expense,USD\n"
        ).encode()
        preview = client.post("/api/v1/import/preview", files={"file": ("e2e.csv", csv, "text/csv")})
        assert preview.status_code == 200
        assert preview.json()["estimated_new_rows"] == 6
        imported = client.post("/api/v1/import", files={"file": ("e2e.csv", csv, "text/csv")})
        assert imported.status_code == 200
        assert imported.json()["inserted"] == 6

        leaks = client.get("/api/v1/leaks").json()["signals"]
        signal = next(item for item in leaks if item["kind"] == "vendor-spike" and item["subject"] == "Cloud Test Vendor")
        assert signal["estimated_exposure"] == 150

        reviewed = client.patch(f"/api/v1/alerts/{signal['id']}", json={"status": "reviewed"})
        assert reviewed.status_code == 200
        history = client.get(f"/api/v1/alerts/{signal['id']}/history").json()["history"]
        assert history[-1]["status"] == "reviewed"

        report = client.get("/api/v1/reports?format=csv")
        assert report.status_code == 200
        assert b"Cloud Test Vendor" in report.content


def test_demo_data_is_not_reseeded_after_workspace_is_cleared(tmp_path):
    setup_workspace(tmp_path)
    for row in store.list_transactions():
        assert store.delete_transaction(row["id"]) is True
    assert store.list_transactions() == []
    store.seed_if_empty()
    assert store.list_transactions() == []


def test_create_transaction_returns_created_row_when_backdated(tmp_path):
    setup_workspace(tmp_path)
    with TestClient(app) as client:
        payload = {
            "date": "2026-01-01",
            "description": "Backdated opening balance",
            "vendor": "Opening Ledger",
            "category": "Equity",
            "amount": 500,
            "type": "income",
            "currency": "USD",
        }
        result = client.post("/api/v1/transactions", json=payload)
        assert result.status_code == 200
        assert result.json()["transaction"]["description"] == "Backdated opening balance"
        assert result.json()["transaction"]["date"] == "2026-01-01"


def test_accounting_settings_branch_and_chart_of_accounts(tmp_path):
    setup_workspace(tmp_path)
    with TestClient(app) as client:
        payload = {
            "date": "2026-11-15", "service_date": "2026-10-31",
            "description": "East branch consulting", "vendor": "East Client",
            "category": "Sales", "amount": 1250, "type": "income", "currency": "USD",
            "branch": "East", "account_code": "4000", "account_name": "Consulting Revenue"
        }
        created = client.post("/api/v1/transactions", json=payload)
        assert created.status_code == 200
        row = created.json()["transaction"]
        assert row["branch"] == "East"
        assert row["account_code"] == "4000"
        assert row["service_date"] == "2026-10-31"

        saved = client.put("/api/v1/settings", json={
            "accounting_basis": "accrual", "fiscal_year_start_month": 4,
            "default_currency": "INR", "retention_days": 365, "timezone": "Asia/Kolkata"
        })
        assert saved.status_code == 200
        assert saved.json()["accounting_basis"] == "accrual"
        assert saved.json()["fiscal_year_start_month"] == 4

        branches = client.get("/api/v1/branches").json()["branches"]
        assert any(item["branch"] == "East" and item["revenue"] == 1250 for item in branches)
        accounts = client.get("/api/v1/chart-of-accounts").json()["accounts"]
        assert any(item["account_code"] == "4000" and item["income"] == 1250 for item in accounts)
        fiscal = client.get("/api/v1/fiscal-year").json()
        assert fiscal["start_date"] == "2026-04-01"
        assert fiscal["summary"]["revenue"] >= 1250


def test_alert_feedback_metrics_are_not_misrepresented_as_recall(tmp_path):
    setup_workspace(tmp_path)
    with TestClient(app) as client:
        signals = client.get("/api/v1/leaks").json()["signals"]
        assert signals
        alert_id = signals[0]["id"]
        saved = client.post(f"/api/v1/alerts/{alert_id}/feedback",
                            json={"classification": "false_positive", "notes": "Verified against invoice."})
        assert saved.status_code == 200
        metrics = client.get("/api/v1/alert-feedback/metrics").json()
        assert metrics["counts"]["false_positive"] == 1
        assert metrics["observed_precision_pct"] == 0
        assert metrics["recall_pct"] is None
        assert "unflagged transactions" in metrics["recall_note"]


def test_subscription_contract_comparison_is_evidence_qualified(tmp_path):
    setup_workspace(tmp_path)
    with TestClient(app) as client:
        saved = client.post("/api/v1/subscription-contracts", json={
            "vendor": "WorkSuite Pro", "expected_amount": 189, "currency": "USD",
            "cadence": "monthly", "reference": "SYNTHETIC-CONTRACT-REF"
        })
        assert saved.status_code == 200
        comparison = client.get("/api/v1/subscription-contracts/comparison").json()
        item = next(x for x in comparison["comparisons"] if x["vendor"] == "WorkSuite Pro")
        assert item["expected_monthly"] == 189
        assert item["observed_recurring_amount"] is not None
        assert "does not verify usage" in comparison["note"]


def test_privacy_admin_endpoints_are_disabled_by_default(tmp_path):
    setup_workspace(tmp_path)
    with TestClient(app) as client:
        assert client.get("/api/v1/privacy").json()["deployment_safe"] is False
        assert client.get("/api/v1/admin/backup").status_code == 403
        assert client.delete("/api/v1/admin/financial-data",
                             params={"confirmation": "DELETE MY LEAKLENS DATA"}).status_code == 403


def test_local_backup_and_confirmed_delete_are_loopback_gated(tmp_path, monkeypatch):
    setup_workspace(tmp_path)
    monkeypatch.setenv("LEAKLENS_ENABLE_LOCAL_ADMIN", "true")
    with TestClient(app) as client:
        backup = client.get("/api/v1/admin/backup")
        assert backup.status_code == 200
        assert backup.content[:16] == b"SQLite format 3\x00"
        deleted = client.delete("/api/v1/admin/financial-data",
                                params={"confirmation": "DELETE MY LEAKLENS DATA"})
        assert deleted.status_code == 200
        assert client.get("/api/v1/transactions").json()["count"] == 0
