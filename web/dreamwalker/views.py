"""Blueprints for Dreamwalker."""
from __future__ import annotations

import json
from typing import Any, Dict

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    jsonify,
    render_template,
    request,
    stream_with_context,
)
import requests

ui_bp = Blueprint("dreamwalker_ui", __name__)
api_bp = Blueprint("dreamwalker_api", __name__)
stream_bp = Blueprint("dreamwalker_stream", __name__)


def _safe_call(func):
    try:
        return func(), None
    except requests.RequestException as exc:  # pragma: no cover - network errors are logged
        return None, str(exc)


@ui_bp.app_context_processor
def inject_globals() -> Dict[str, Any]:
    return {
        "orchestrators": current_app.config.get("ORCHESTRATORS", {}),
        "mcp_url": current_app.config.get("MCP_BASE_URL"),
        "base_path": current_app.config.get("BASE_PATH", ""),
    }


@ui_bp.route("/health")
def health() -> Response:
    client = current_app.mcp_client
    health, error = _safe_call(client.get_health)
    status = "ok"
    if error:
        status = "error"
    elif health:
        status = health.get("status", "ok")
    return jsonify({"status": status, "upstream": health, "error": error})


@ui_bp.route("/")
def dashboard() -> str:
    client = current_app.mcp_client
    health, health_error = _safe_call(client.get_health)
    tools, tools_error = _safe_call(client.list_tools)
    resources, resources_error = _safe_call(client.list_resources)
    patterns, patterns_error = _safe_call(client.list_patterns)
    return render_template(
        "dashboard.html",
        health=health,
        health_error=health_error,
        tools=tools,
        tools_error=tools_error,
        resources=resources,
        resources_error=resources_error,
        patterns=patterns,
        patterns_error=patterns_error,
    )


@ui_bp.route("/orchestrators/<name>")
def orchestrator_detail(name: str) -> str:
    orchestrator = current_app.config["ORCHESTRATORS"].get(name)
    if not orchestrator:
        abort(404)
    client = current_app.mcp_client
    patterns, _ = _safe_call(client.list_patterns)
    pattern = None
    if patterns and isinstance(patterns, dict):
        for candidate in patterns.get("patterns", []):
            if candidate.get("name", "").lower() == orchestrator["label"].lower():
                pattern = candidate
                break
    return render_template("orchestrator.html", orchestrator=orchestrator, pattern=pattern)


@ui_bp.route("/settings", methods=["GET"])
def settings_form() -> str:
    return render_template("settings.html")


@api_bp.route("/orchestrations", methods=["POST"])
def start_orchestration() -> Response:
    data = request.get_json(silent=True) or {}
    orchestrator = (data.get("orchestrator") or "hive").lower()
    payload = data.get("payload") or {}
    client = current_app.mcp_client
    try:
        result = client.start_orchestration(orchestrator, payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except requests.RequestException as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify(result)


@api_bp.route("/status/<task_id>", methods=["GET"])
def orchestration_status(task_id: str) -> Response:
    client = current_app.mcp_client
    try:
        result = client.get_status(task_id)
    except requests.RequestException as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify(result)


@stream_bp.route("/stream/<task_id>")
def proxy_stream(task_id: str) -> Response:
    client = current_app.mcp_client

    def _event_stream() -> Any:
        try:
            for line in client.stream_events(task_id):
                if not line:
                    yield b": keep-alive\n\n"
                else:
                    yield line + b"\n"
        except requests.RequestException as exc:  # pragma: no cover - network
            payload = json.dumps({"error": str(exc), "task_id": task_id})
            yield f"event: error\ndata: {payload}\n\n".encode()

    return Response(stream_with_context(_event_stream()), mimetype="text/event-stream")
