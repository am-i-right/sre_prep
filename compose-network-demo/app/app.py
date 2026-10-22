
import os
import time

from flask import Flask, Response, g, jsonify, request
from redis import Redis
from redis.exceptions import RedisError

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)


app = Flask(__name__)

redis_client = Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


# 1. Counter: total number of HTTP requests
HTTP_REQUESTS = Counter(
    "app_http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"],
)


# 2. Gauge: current number of requests
IN_PROGRESS = Gauge(
    "app_http_requests_in_progress",
    "HTTP requests currently in progress",
)


# 3. Histogram: HTTP request duration in seconds
REQUEST_DURATION = Histogram(
    "app_http_request_duration_seconds",
    "Duration of HTTP requests in seconds",
    ["method", "route"],
    buckets=(
        0.005, 0.01, 0.025, 0.05,
        0.1, 0.25, 0.5, 1.0,
        2.5, 5.0, 10.0,
    ),
)


# 4. Gauge: result of the latest Redis healthcheck
REDIS_AVAILABLE = Gauge(
    "app_redis_available",
    "Last Redis healthcheck result: 1=success, 0=failure",
)


@app.before_request
def before_request():
    # Do not count Prometheus scrape requests.
    if request.path == "/metrics":
        return

    g.started_at = time.perf_counter()
    IN_PROGRESS.inc()
    g.instrumented = True


@app.after_request
def after_request(response):
    if not getattr(g, "instrumented", False):
        return response

    # Use route template, not raw URL.
    route = (
        request.url_rule.rule
        if request.url_rule
        else "unmatched"
    )

    HTTP_REQUESTS.labels(
        method=request.method,
        route=route,
        status=str(response.status_code),
    ).inc()

    elapsed = time.perf_counter() - g.started_at

    REQUEST_DURATION.labels(
        method=request.method,
        route=route,
    ).observe(elapsed)

    return response


@app.teardown_request
def teardown_request(error):
    if getattr(g, "instrumented", False):
        IN_PROGRESS.dec()


@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        content_type=CONTENT_TYPE_LATEST,
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
        REDIS_AVAILABLE.set(1)

        return jsonify({
            "status": "ok",
            "redis": "connected",
        })
    except RedisError:
        REDIS_AVAILABLE.set(0)

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


# Diagnostic endpoint for practicing latency monitoring.
@app.get("/slow")
def slow():
    try:
        seconds = float(request.args.get("seconds", "2"))
    except ValueError:
        return jsonify({"error": "Invalid seconds"}), 400

    if not 0 <= seconds <= 10:
        return jsonify({"error": "Out of range"}), 400

    time.sleep(seconds)

    return jsonify({
        "message": "Slow request completed",
        "seconds": seconds,
    })

