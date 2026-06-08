from fastapi.testclient import TestClient

from app.main import app
from app.observability import Counters

client = TestClient(app)


def test_counters_increment_and_reset():
    counters = Counters()
    counters.increment("widgets")
    counters.increment("widgets", 4)
    assert counters.snapshot()["widgets"] == 5

    counters.reset()
    assert counters.snapshot() == {}


def test_metrics_endpoint_reports_request_counts():
    client.get("/health")
    client.get("/products")

    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["uptime_seconds"] >= 0
    assert body["counters"]["http.requests.total"] >= 3
    assert body["counters"]["http.responses.200"] >= 2


def test_request_id_header_is_returned_and_echoed():
    generated = client.get("/health")
    assert generated.headers["X-Request-ID"]

    echoed = client.get("/health", headers={"X-Request-ID": "trace-123"})
    assert echoed.headers["X-Request-ID"] == "trace-123"
