"""Dreamwalker Flask application factory."""
from __future__ import annotations

import json
import logging
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

from flask import Flask

from .client import MCPClient
from .views import api_bp, stream_bp, ui_bp

TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

LOGGER = logging.getLogger(__name__)

DEFAULT_ORCHESTRATORS: Dict[str, Dict[str, Any]] = {
    "hive": {
        "slug": "hive",
        "label": "Hive",
        "description": "Hierarchical research orchestration (Beltalowda).",
        "endpoint": "/tools/orchestrate_research",
        "method": "POST",
    },
    "swarm": {
        "slug": "swarm",
        "label": "Swarm",
        "description": "Multi-agent domain search across text, news, technical, and more.",
        "endpoint": "/tools/orchestrate_search",
        "method": "POST",
    },
}


def load_orchestrators() -> Dict[str, Dict[str, Any]]:
    """Load orchestrator metadata from defaults and optional JSON overrides."""
    orchestrators: Dict[str, Dict[str, Any]] = deepcopy(DEFAULT_ORCHESTRATORS)
    raw = os.getenv("DREAMWALKER_ORCHESTRATORS")
    if not raw:
        return orchestrators
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        LOGGER.warning("Invalid DREAMWALKER_ORCHESTRATORS JSON; using defaults")
        return orchestrators
    overrides = _parse_orchestrator_payload(payload)
    if overrides:
        orchestrators.update(overrides)
    return orchestrators


def _parse_orchestrator_payload(payload: Any) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    if isinstance(payload, dict):
        items = payload.items()
    elif isinstance(payload, list):
        items = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            slug = entry.get("slug") or entry.get("name") or entry.get("label")
            if not slug:
                continue
            normalized_entry = dict(entry)
            normalized_entry.pop("slug", None)
            items.append((_slugify(str(slug)), normalized_entry))
    else:
        return result

    for slug, metadata in items:
        normalized = _normalize_orchestrator(slug, metadata)
        if normalized:
            result[slug] = normalized
    return result


def _normalize_orchestrator(slug: str, metadata: Any) -> Dict[str, Any] | None:
    if not isinstance(metadata, dict):
        return None
    endpoint = metadata.get("endpoint")
    if not endpoint:
        return None
    normalized = dict(metadata)
    normalized["slug"] = _slugify(slug)
    normalized["endpoint"] = endpoint
    normalized["label"] = metadata.get("label") or metadata.get("name") or slug.title()
    normalized["description"] = metadata.get("description", "")
    normalized["method"] = metadata.get("method", "POST").upper()
    return normalized


def _slugify(value: str) -> str:
    slug = value.strip().lower().replace(" ", "-")
    return slug or "orchestrator"


def _normalize_base_path(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.strip()
    if not normalized or normalized == "/":
        return ""
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized.rstrip("/")


def create_app(config: Dict[str, Any] | None = None) -> Flask:
    """Create the Dreamwalker Flask app."""
    app = Flask(
        __name__,
        template_folder=str(TEMPLATE_DIR),
        static_folder=str(STATIC_DIR),
    )
    orchestrators = load_orchestrators()
    base_path = _normalize_base_path(os.getenv("DREAMWALKER_BASE_PATH"))
    app.config.update(
        MCP_BASE_URL=os.getenv("MCP_BASE_URL", "http://localhost:5060"),
        DREAMWALKER_API_KEY=os.getenv("DREAMWALKER_API_KEY"),
        JSON_SORT_KEYS=False,
        ORCHESTRATORS=orchestrators,
        BASE_PATH=base_path,
    )
    if config:
        app.config.update(config)

    active_orchestrators = dict(app.config.get("ORCHESTRATORS", {}))

    app.mcp_client = MCPClient(
        base_url=app.config["MCP_BASE_URL"],
        api_key=app.config.get("DREAMWALKER_API_KEY"),
        orchestrators=active_orchestrators,
    )

    app.register_blueprint(ui_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(stream_bp)

    return app


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    create_app().run(host="127.0.0.1", port=5000, debug=True)
