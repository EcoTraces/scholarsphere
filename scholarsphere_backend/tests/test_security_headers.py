from fastapi.testclient import TestClient

from app.main import app


def test_responses_carry_baseline_security_headers() -> None:
    response = TestClient(app).get("/health/live")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "max-age=" in response.headers["Strict-Transport-Security"]
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Content-Security-Policy"] == (
        "default-src 'none'; frame-ancestors 'none'"
    )
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"


def test_docs_routes_are_exempt_from_the_strict_csp() -> None:
    # /docs is mounted here since tests run with app_env != "production"
    # (app.main _expose_docs) - Swagger UI's CDN script/inline styles
    # would be blocked by the strict default-src 'none' CSP applied
    # everywhere else, so this path must not carry it.
    response = TestClient(app).get("/docs")
    assert response.status_code == 200
    assert "Content-Security-Policy" not in response.headers
