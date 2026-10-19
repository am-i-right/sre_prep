import os

from flask import Flask, jsonify
from redis import Redis
from redis.exceptions import RedisError


app = Flask(__name__)

redis_client = Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


@app.get("/")
def index():
    return jsonify({
        "service": "sre-compose-demo",
        "message": "Hello from Python!",
    })


@app.get("/health")
def health():
    try:
        redis_client.ping()
        return jsonify({
            "status": "ok",
            "redis": "connected",
        })
    except RedisError:
        return jsonify({
            "status": "unhealthy",
            "redis": "unavailable",
        }), 503


@app.get("/counter")
def counter():
    try:
        value = redis_client.get("counter")
        return jsonify({
            "counter": int(value or 0),
        })
    except RedisError:
        return jsonify({
            "error": "Redis unavailable",
        }), 503


@app.post("/increment")
def increment():
    try:
        value = redis_client.incr("counter")
        return jsonify({
            "counter": value,
        })
    except RedisError:
        return jsonify({
            "error": "Redis unavailable",
        }), 503

