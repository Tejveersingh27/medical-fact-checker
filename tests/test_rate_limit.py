"""Tests for the web server's spending limits and the /api/check endpoint."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import server


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    """Fresh counters, default settings and a clock the test controls."""
    server.hits_by_visitor.clear()
    server.hits_today.clear()
    monkeypatch.setattr(server, "TRUSTED_PROXY_HOPS", 0)
    monkeypatch.setattr(server, "PER_VISITOR_LIMIT", 10)
    monkeypatch.setattr(server, "DAILY_LIMIT", 25)
    monkeypatch.setattr(server, "MAX_TRACKED_VISITORS", 10_000)
    clock = SimpleNamespace(now=1_000_000.0)
    monkeypatch.setattr(server, "time", SimpleNamespace(time=lambda: clock.now))
    return clock


def request(ip="1.1.1.1", forwarded=None):
    headers = {"x-forwarded-for": forwarded} if forwarded else {}
    return SimpleNamespace(headers=headers, client=SimpleNamespace(host=ip))


def allowed(req):
    """True if the request is let through, False if it gets a 429."""
    try:
        server.enforce_limits(req)
        return True
    except HTTPException as error:
        assert error.status_code == 429
        return False


# --- per-visitor hourly limit --------------------------------------------------

def test_visitor_is_blocked_after_ten_checks_in_an_hour():
    assert [allowed(request()) for _ in range(11)] == [True] * 10 + [False]


def test_one_visitors_limit_does_not_affect_another():
    for _ in range(10):
        allowed(request("1.1.1.1"))
    assert allowed(request("2.2.2.2"))


def test_visitor_can_check_again_after_an_hour(clean_state):
    for _ in range(10):
        allowed(request())
    assert not allowed(request())
    clean_state.now += 3601
    assert allowed(request())


# --- daily limit ---------------------------------------------------------------

def test_whole_site_is_blocked_after_25_checks_a_day(clean_state):
    assert all(allowed(request(f"10.0.0.{i}")) for i in range(25))
    assert not allowed(request("10.0.1.1"))
    clean_state.now += 86401
    assert allowed(request("10.0.1.1"))


# --- who counts as the visitor ---------------------------------------------------

def test_forged_forwarded_header_is_ignored_by_default():
    # Same real address, a new fake X-Forwarded-For every time: still one visitor.
    results = [allowed(request("1.1.1.1", forwarded=f"6.6.6.{i}")) for i in range(11)]
    assert results == [True] * 10 + [False]


def test_behind_one_proxy_the_rightmost_entry_is_the_visitor(monkeypatch):
    monkeypatch.setattr(server, "TRUSTED_PROXY_HOPS", 1)
    assert server.client_ip(request("proxy", forwarded="fake, 9.9.9.9")) == "9.9.9.9"
    results = [allowed(request("proxy", forwarded=f"{i}.{i}.{i}.{i}, 9.9.9.9")) for i in range(11)]
    assert results == [True] * 10 + [False]


def test_behind_two_proxies_the_second_from_right_is_the_visitor(monkeypatch):
    monkeypatch.setattr(server, "TRUSTED_PROXY_HOPS", 2)
    assert server.client_ip(request("proxy", forwarded="fake, 9.9.9.9, 10.0.0.1")) == "9.9.9.9"


def test_missing_forwarded_header_falls_back_to_the_connecting_address(monkeypatch):
    monkeypatch.setattr(server, "TRUSTED_PROXY_HOPS", 1)
    assert server.client_ip(request("3.3.3.3")) == "3.3.3.3"


# --- visitor table cap -----------------------------------------------------------

def test_new_visitors_are_refused_when_the_table_is_full(monkeypatch):
    monkeypatch.setattr(server, "MAX_TRACKED_VISITORS", 3)
    assert all(allowed(request(f"1.1.1.{i}")) for i in range(3))
    assert not allowed(request("1.1.1.99"))
    assert allowed(request("1.1.1.0"))  # someone already tracked is still served


def test_idle_visitors_are_forgotten_to_make_room(monkeypatch, clean_state):
    monkeypatch.setattr(server, "MAX_TRACKED_VISITORS", 3)
    for i in range(3):
        allowed(request(f"1.1.1.{i}"))
    clean_state.now += 3601
    assert allowed(request("1.1.1.99"))
    assert len(server.hits_by_visitor) == 1


# --- the endpoint itself -----------------------------------------------------------

@pytest.fixture
def client(monkeypatch):
    answer = {"verdict": "TRUE", "explanation": "x", "sources": []}
    monkeypatch.setattr(server, "check_claim", lambda *args: answer)
    return TestClient(server.app)


def test_endpoint_returns_the_fact_check(client):
    response = client.post("/api/check", json={"claim": "Hantavirus spreads by rodents."})
    assert response.status_code == 200
    assert response.json()["verdict"] == "TRUE"


@pytest.mark.parametrize("claim", ["", "ab", "x" * 501])
def test_endpoint_rejects_claims_that_are_too_short_or_too_long(client, claim):
    assert client.post("/api/check", json={"claim": claim}).status_code == 422


def test_endpoint_returns_429_when_limited(client, monkeypatch):
    monkeypatch.setattr(server, "PER_VISITOR_LIMIT", 1)
    body = {"claim": "Hantavirus spreads by rodents."}
    assert client.post("/api/check", json=body).status_code == 200
    assert client.post("/api/check", json=body).status_code == 429


def test_endpoint_hides_internal_errors(client, monkeypatch):
    def explode(*args):
        raise TimeoutError("OpenAI timed out")
    monkeypatch.setattr(server, "check_claim", explode)
    response = client.post("/api/check", json={"claim": "Hantavirus spreads by rodents."})
    assert response.status_code == 502
    assert "OpenAI" not in response.text
