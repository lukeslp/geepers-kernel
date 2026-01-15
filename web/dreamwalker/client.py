"""Client helper for talking to the MCP HTTP API."""
from __future__ import annotations

import json
import logging
import os
from copy import deepcopy
from typing import Any, Dict, Iterable, Optional

import requests
from requests import Response

LOGGER = logging.getLogger(__name__)

DEFAULT_ORCHESTRATOR_ENDPOINTS: Dict[str, Dict[str, Any]] = {
    "hive": {"endpoint": "/tools/orchestrate_research", "method": "POST"},
    "swarm": {"endpoint": "/tools/orchestrate_search", "method": "POST"},
}


class MCPClient:
    """Lightweight wrapper around the MCP HTTP endpoints."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        *,
        api_key: Optional[str] = None,
        timeout: int = 20,
        orchestrators: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("MCP_BASE_URL", "http://localhost:5060")).rstrip("/")
        self.api_key = api_key or os.getenv("DREAMWALKER_API_KEY")
        self.timeout = timeout
        self.session = requests.Session()
        self.orchestrators: Dict[str, Dict[str, Any]] = (
            deepcopy(orchestrators) if orchestrators else deepcopy(DEFAULT_ORCHESTRATOR_ENDPOINTS)
        )

    def _headers(self, *, json_body: bool = True) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if json_body:
            headers["Content-Type"] = "application/json"
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _handle(self, response: Response) -> Dict[str, Any]:
        try:
            response.raise_for_status()
        except requests.HTTPError:
            LOGGER.exception("MCP request failed: %s", response.text[:200])
            raise
        if not response.text:
            return {}
        try:
            return response.json()
        except json.JSONDecodeError:
            LOGGER.warning("Unexpected non-JSON response from MCP: %s", response.text[:200])
            return {"raw": response.text}

    def get_health(self) -> Dict[str, Any]:
        response = self.session.get(
            f"{self.base_url}/health", headers=self._headers(json_body=False), timeout=self.timeout
        )
        return self._handle(response)

    def list_tools(self) -> Dict[str, Any]:
        response = self.session.get(
            f"{self.base_url}/tools", headers=self._headers(json_body=False), timeout=self.timeout
        )
        return self._handle(response)

    def list_resources(self) -> Dict[str, Any]:
        response = self.session.get(
            f"{self.base_url}/resources", headers=self._headers(json_body=False), timeout=self.timeout
        )
        return self._handle(response)

    def start_orchestration(self, orchestrator: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        meta = self.orchestrators.get(orchestrator)
        if not meta:
            raise ValueError(f"Unknown orchestrator '{orchestrator}'")
        endpoint = meta["endpoint"]
        method = meta.get("method", "POST").upper()
        url = f"{self.base_url}{endpoint}"
        if method == "GET":
            response = self.session.get(
                url,
                headers=self._headers(json_body=False),
                params=payload,
                timeout=self.timeout,
            )
        else:
            response = self.session.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
        return self._handle(response)

    def get_status(self, task_id: str) -> Dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/tools/get_orchestration_status",
            headers=self._headers(),
            json={"task_id": task_id},
            timeout=self.timeout,
        )
        return self._handle(response)

    def list_patterns(self) -> Dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/tools/list_orchestrator_patterns",
            headers=self._headers(),
            json={},
            timeout=self.timeout,
        )
        return self._handle(response)

    def stream_events(self, task_id: str) -> Iterable[bytes]:
        response = self.session.get(
            f"{self.base_url}/stream/{task_id}",
            headers=self._headers(json_body=False),
            timeout=self.timeout,
            stream=True,
        )
        response.raise_for_status()
        return response.iter_lines()
