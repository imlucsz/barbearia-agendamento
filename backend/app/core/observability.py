"""Low-cardinality, per-process request metrics and safe request logs."""
from __future__ import annotations

from collections import Counter, defaultdict, deque
import json
import logging
import math
import re
import threading
import time

from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger("app.request")
_LOCK = threading.Lock()
_REQUEST_COUNTS: Counter[tuple[str, str, int]] = Counter()
_LATENCIES: dict[tuple[str, str], deque[float]] = defaultdict(lambda: deque(maxlen=2048))
_TOTAL_REQUESTS = 0
_TOTAL_5XX = 0
_METHOD = re.compile(r"[A-Z]{1,16}\Z")


def _route_template(scope) -> str:
    route = scope.get("route")
    template = getattr(route, "path", None)
    return template if isinstance(template, str) and template.startswith("/") else "unmatched"


def _method(scope) -> str:
    method = str(scope.get("method", "OTHER")).upper()
    return method if _METHOD.fullmatch(method) else "OTHER"


def _label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def record_request(route: str, method: str, status: int, duration_seconds: float) -> None:
    global _TOTAL_REQUESTS, _TOTAL_5XX
    with _LOCK:
        _REQUEST_COUNTS[(route, method, status)] += 1
        _LATENCIES[(route, method)].append(max(0.0, duration_seconds * 1000.0))
        _TOTAL_REQUESTS += 1
        if status >= 500:
            _TOTAL_5XX += 1


def metrics_text() -> str:
    """Return Prometheus exposition with no user, resource ID, or URL labels."""
    with _LOCK:
        counts = sorted(_REQUEST_COUNTS.items())
        latencies = {key: tuple(values) for key, values in _LATENCIES.items()}
        total, failures = _TOTAL_REQUESTS, _TOTAL_5XX

    lines = [
        "# HELP http_requests_total Total HTTP requests handled by this process.",
        "# TYPE http_requests_total counter",
    ]
    for (route, method, status), value in counts:
        lines.append(
            f'http_requests_total{{route="{_label(route)}",method="{_label(method)}",status="{status}"}} {value}'
        )
    lines.extend((
        "# HELP http_requests_5xx_ratio Fraction of requests with a 5xx status.",
        "# TYPE http_requests_5xx_ratio gauge",
        f"http_requests_5xx_ratio {failures / total if total else 0.0:.6f}",
        "# HELP http_request_duration_ms Approximate request latency quantiles over the last 2048 observations per route and method.",
        "# TYPE http_request_duration_ms gauge",
    ))
    for (route, method), observations in sorted(latencies.items()):
        ordered = sorted(observations)
        for quantile in (0.50, 0.95):
            index = min(len(ordered) - 1, max(0, math.ceil(quantile * len(ordered)) - 1))
            lines.append(
                f'http_request_duration_ms{{route="{_label(route)}",method="{_label(method)}",quantile="{quantile:.2f}"}} {ordered[index]:.3f}'
            )
    return "\n".join(lines) + "\n"


def reset_metrics_for_tests() -> None:
    global _TOTAL_REQUESTS, _TOTAL_5XX
    with _LOCK:
        _REQUEST_COUNTS.clear()
        _LATENCIES.clear()
        _TOTAL_REQUESTS = 0
        _TOTAL_5XX = 0


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started = time.perf_counter()
        route = "unmatched"
        method = _method(request.scope)
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            route = _route_template(request.scope)
            return response
        finally:
            duration = time.perf_counter() - started
            request_id = getattr(getattr(request, "state", None), "request_id", "unknown")
            record_request(route, method, status, duration)
            logger.log(logging.INFO, json.dumps({
                "event": "http_request",
                "request_id": request_id,
                "route": route,
                "method": method,
                "status": status,
                "duration_ms": round(duration * 1000.0, 3),
            }, separators=(",", ":"), ensure_ascii=True))
