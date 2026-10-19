import pytest

from redis.exceptions import ConnectionError as RedisConnectionError
from app import app, redis_client


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client


def test_index(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json["service"] == "sre-compose-demo"


def test_health_success(client, monkeypatch):
    monkeypatch.setattr(
        redis_client,
        "ping",
        lambda: True,
    )

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_health_redis_failure(client, monkeypatch):
    def broken_ping():
        raise RedisConnectionError("Redis unavailable")

    monkeypatch.setattr(
        redis_client,
        "ping",
        broken_ping,
    )

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json["status"] == "unhealthy"


def test_increment(client, monkeypatch):
    monkeypatch.setattr(
        redis_client,
        "incr",
        lambda key: 7,
    )

    response = client.post("/increment")

    assert response.status_code == 200
    assert response.json["counter"] == 7

