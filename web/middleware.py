"""
Common middleware registration utilities for Flask apps.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from flask import Flask, g, request

__all__ = ["register_request_logging", "register_error_handlers", "add_correlation_id"]


def register_request_logging(app: Flask, *, logger: Optional[logging.Logger] = None) -> None:
    """
    Register before/after request hooks that log request metadata and latency.
    """
    log = logger or logging.getLogger("shared.web.request")

    @app.before_request
    def _start_timer():
        g._request_started_at = time.time()

    @app.after_request
    def _log_request(response):
        started = getattr(g, "_request_started_at", time.time())
        duration = time.time() - started
        log.info(
            "%s %s %s %0.3fs",
            request.method,
            request.path,
            response.status_code,
            duration,
        )
        response.headers.setdefault("X-Response-Time", f"{duration:.3f}s")
        return response


def register_error_handlers(app: Flask, *, logger: Optional[logging.Logger] = None) -> None:
    """
    Register simple JSON error handlers for common status codes.
    """
    log = logger or logging.getLogger("shared.web.errors")

    @app.errorhandler(400)
    def bad_request(error):  # pragma: no cover - flask handles wiring
        log.warning("400 Bad Request: %s", error)
        return {"error": "bad_request", "message": str(error)}, 400

    @app.errorhandler(404)
    def not_found(error):  # pragma: no cover
        log.warning("404 Not Found: %s", request.path)
        return {"error": "not_found", "path": request.path}, 404

    @app.errorhandler(Exception)
    def internal_error(error):  # pragma: no cover
        log.exception("500 Internal Server Error: %s", error)
        return {"error": "internal_server_error"}, 500


def add_correlation_id(app: Flask, header: str = "X-Correlation-Id") -> None:
    """
    Inject a correlation ID into request context and response headers.
    """

    @app.before_request
    def _inject_correlation_id():
        correlation_id = request.headers.get(header, str(uuid.uuid4()))
        g.correlation_id = correlation_id  # type: ignore[attr-defined]

    @app.after_request
    def _add_header(response):
        response.headers.setdefault(header, getattr(g, "correlation_id", str(uuid.uuid4())))
        return response

