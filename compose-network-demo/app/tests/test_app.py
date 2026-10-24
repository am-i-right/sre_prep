import pytest

from app import app, redis_client
from redis.exceptions import ConnectionError as RedisConnectionError


@pytest.fixture
def client():
    app.config.update(
        TESTING=True,
        LAB_MODE=True,
    )

    with app.test_client() as test_client:
        yield test_client


def test_index(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json["service"] == "sre-compose-demo"


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "alive"


def test_ready_success(client, monkeypatch):
    monkeypatch.setattr(
        redis_client,
        "ping",
        lambda: True,
    )

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json["status"] == "ready"


def test_ready_failure(client, monkeypatch):
    def broken_ping():
        raise RedisConnectionError("Redis unavailable")

    monkeypatch.setattr(
        redis_client,
        "ping",
        broken_ping,
    )

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json["status"] == "not_ready"


def test_simulated_error(client):
    response = client.get("/lab/error")

    assert response.status_code == 503


def test_metrics(client):
    client.get("/")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert b"app_http_requests_total" in response.data
    assert b"app_http_request_duration_seconds" in response.data
    assert b"app_http_errors_total" in response.data

