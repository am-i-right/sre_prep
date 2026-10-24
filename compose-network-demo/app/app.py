import os
import time
import uuid

from flask import Flask, Response, abort, g, jsonify, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from redis import Redis
from redis.exceptions import RedisError
from werkzeug.exceptions import HTTPException

from logging_config import setup_logger


app = Flask(__name__)
logger = setup_logger()

app.config["LAB_MODE"] = (
    os.getenv("ENABLE_LAB_ENDPOINTS", "false").lower()
    == "true"
)

redis_client = Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


# 1. Total HTTP requests
HTTP_REQUESTS = Counter(
    "app_http_requests_total",
    "Total number of HTTP requests",
    ["method", "route", "status"],
)


# 2. HTTP 5xx errors
HTTP_ERRORS = Counter(
    "app_http_errors_total",
    "Total number of HTTP 5xx responses",
    ["method", "route", "status"],
)


# 3. HTTP request duration
REQUEST_DURATION = Histogram(
    "app_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
    buckets=(
        0.005, 0.01, 0.025, 0.05,
        0.1, 0.25, 0.5, 1.0,
        2.5, 5.0, 10.0,
    ),
)


# 4. Current active requests
IN_PROGRESS = Gauge(
    "app_http_requests_in_progress",
    "Current active HTTP requests",
)


# 5. Latest Redis readiness result
REDIS_AVAILABLE = Gauge(
    "app_redis_available",
    "Last Redis readiness check: 1=success, 0=failure",
)


def get_request_id():
    supplied = request.headers.get("X-Request-ID", "")

    if (
        1 <= len(supplied) <= 64
        and all(
            char.isascii()
            and (char.isalnum() or char in "-_")
            for char in supplied
        )
    ):
        return supplied

    return str(uuid.uuid4())


@app.before_request
def start_request():
    # Do not instrument Prometheus scrapes.
    if request.path == "/metrics":
        return

    g.started_at = time.perf_counter()
    g.request_id = get_request_id()
    g.instrumented = True

    IN_PROGRESS.inc()


@app.after_request
def finish_request(response):
    if not getattr(g, "instrumented", False):
        return response

    duration = time.perf_counter() - g.started_at

    route = (
        request.url_rule.rule
        if request.url_rule
        else "unmatched"
    )

    status = response.status_code
    method = request.method

    HTTP_REQUESTS.labels(
        method=method,
        route=route,
        status=str(status),
    ).inc()

    if status >= 500:
        HTTP_ERRORS.labels(
            method=method,
            route=route,
            status=str(status),
        ).inc()

    REQUEST_DURATION.labels(
        method=method,
        route=route,
    ).observe(duration)

    fields = {
        "request_id": g.request_id,
        "method": method,
        "route": route,
        "status": status,
        "duration_ms": round(duration * 1000, 2),
    }

    if status >= 500:
        logger.warning(
            "http_request",
            extra={"fields": fields},
        )
    else:
        logger.info(
            "http_request",
            extra={"fields": fields},
        )

    response.headers["X-Request-ID"] = g.request_id

    return response


@app.teardown_request
def end_request(error):
    if getattr(g, "instrumented", False):
        IN_PROGRESS.dec()


@app.errorhandler(Exception)
def handle_exception(error):
    if isinstance(error, HTTPException):
        return error

    logger.exception(
        "unhandled_exception",
        extra={
            "fields": {
                "request_id": getattr(
                    g, "request_id", None
                ),
                "route": request.path,
            }
        },
    )

    return jsonify({
        "error": "Internal server error"
    }), 500


# --------- Health and readiness ---------

@app.get("/health")
def health():
    return jsonify({
        "status": "alive",
        "service": "sre-compose-demo",
    }), 200


@app.get("/ready")
def ready():
    try:
        redis_client.ping()

        REDIS_AVAILABLE.set(1)

        return jsonify({
            "status": "ready",
            "redis": "connected",
        }), 200

    except RedisError:
        REDIS_AVAILABLE.set(0)

        return jsonify({
            "status": "not_ready",
            "redis": "unavailable",
        }), 503


# --------- Main application ---------

@app.get("/")
def index():
    return jsonify({
        "service": "sre-compose-demo",
        "message": "Hello from Python!",
    })


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


# --------- Prometheus metrics ---------

@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        content_type=CONTENT_TYPE_LATEST,
    )


# --------- Training endpoints ---------

@app.get("/slow")
def slow():
    if not app.config["LAB_MODE"]:
        abort(404)

    try:
        seconds = float(
            request.args.get("seconds", "1")
        )
    except ValueError:
        return jsonify({
            "error": "Invalid seconds"
        }), 400

    if not 0 <= seconds <= 10:
        return jsonify({
            "error": "Seconds must be between 0 and 10"
        }), 400

    time.sleep(seconds)

    return jsonify({
        "status": "ok",
        "duration_requested": seconds,
    })


@app.get("/lab/error")
def simulated_error():
    if not app.config["LAB_MODE"]:
        abort(404)

    return jsonify({
        "error": "Simulated service failure",
    }), 503

