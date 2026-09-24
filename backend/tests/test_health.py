from fastapi.testclient import TestClient

from app.main import app


def test_application_loads() -> None:
    assert app.title == "Nowshera Digital AI ATS API"


def test_health_check_returns_expected_payload() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "nowshera-digital-ai-ats-api",
    }
