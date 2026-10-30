"""Tests for the small utility routes of the web server."""

from fastapi.testclient import TestClient

import server


def test_health_reports_ok():
    response = TestClient(server.app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_does_not_use_up_any_rate_limit():
    before = len(server.hits_today)
    client = TestClient(server.app)
    for _ in range(50):
        assert client.get("/health").status_code == 200
    assert len(server.hits_today) == before


def test_home_page_is_served():
    response = TestClient(server.app).get("/")
    assert response.status_code == 200
    assert "Hantavirus Fact-Checker" in response.text
