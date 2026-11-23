from fastapi.testclient import TestClient
from app import store
from app.main import app

def setup_workspace(tmp_path):
    store.DB_PATH = tmp_path / "test.sqlite3"
    store.init_db()
    store.clear_transactions()
    store.seed_if_empty()

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
