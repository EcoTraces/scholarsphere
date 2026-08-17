from fastapi.testclient import TestClient

from app.main import app


def test_responses_carry_baseline_security_headers() -> None:
    response = TestClient(app).get("/health/live")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "max-age=" in response.headers["Strict-Transport-Security"]
    assert response.headers["Cache-Control"] == "no-store"
