from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_api_root_lists_modules():
    response = client.get("/api/v1")
    assert response.status_code == 200
    assert "modules" in response.json()
    assert "transactions" in response.json()["modules"]
