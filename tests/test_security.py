from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.security import RateLimiter

client = TestClient(app)

PRODUCT = {
    "name": "Secured Plan",
    "description": "Behind an API key",
    "price": 99,
    "quantity": 10,
}


def test_rate_limiter_allows_then_blocks():
    limiter = RateLimiter()
    decisions = [limiter.check("caller", limit=2, window=60)[0] for _ in range(3)]
    assert decisions == [True, True, False]

    _, retry_after = limiter.check("caller", limit=2, window=60)
    assert retry_after >= 1


def test_rate_limiter_disabled_when_limit_non_positive():
    limiter = RateLimiter()
    assert all(limiter.check("caller", limit=0)[0] for _ in range(100))


def test_open_access_when_no_keys_configured():
    # Default settings configure no API keys, so requests pass without a header.
    assert client.get("/products").status_code == 200


def test_requires_valid_api_key_when_configured(monkeypatch):
    monkeypatch.setenv("API_KEYS", "top-secret, second-key")
    get_settings.cache_clear()

    missing = client.get("/products")
    assert missing.status_code == 401
    assert missing.json()["detail"]["error"] == "unauthenticated"
    assert missing.headers["WWW-Authenticate"] == "ApiKey"

    wrong = client.get("/products", headers={"X-API-Key": "nope"})
    assert wrong.status_code == 401

    ok = client.get("/products", headers={"X-API-Key": "top-secret"})
    assert ok.status_code == 200

    second = client.post(
        "/products", json=PRODUCT, headers={"X-API-Key": "second-key"}
    )
    assert second.status_code == 201


def test_rate_limit_returns_429_with_retry_after(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    get_settings.cache_clear()

    assert client.get("/products").status_code == 200
    assert client.get("/products").status_code == 200

    limited = client.get("/products")
    assert limited.status_code == 429
    body = limited.json()["detail"]
    assert body["error"] == "rate_limited"
    assert body["limit_per_minute"] == 2
    assert int(limited.headers["Retry-After"]) >= 1
