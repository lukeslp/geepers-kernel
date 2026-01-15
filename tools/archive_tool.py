"""
Tool module for interacting with the Internet Archive Wayback Machine.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .data_tool_base import DataToolModuleBase


class ArchiveTools(DataToolModuleBase):
    """Expose Internet Archive snapshot utilities as MCP-compatible tools."""

    name = "archive_data"
    display_name = "Internet Archive (Wayback)"
    description = "Query archived web snapshots and trigger new captures"
    version = "1.0.0"
    source_name = "archive"
    api_key_name = None
    max_records = 100

    def build_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "archive_get_latest_snapshot",
                    "description": "Get the most recent archived snapshot for a URL.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to inspect"}
                        },
                        "required": ["url"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "archive_list_snapshots",
                    "description": "List archived snapshots for a URL.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to inspect"},
                            "limit": {
                                "type": "integer",
                                "default": 25,
                                "description": "Maximum number of snapshots to return.",
                            },
                        },
                        "required": ["url"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "archive_url",
                    "description": "Request archiving of a URL in the Wayback Machine.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to archive"},
                            "wait_for_completion": {
                                "type": "boolean",
                                "default": True,
                                "description": "Whether to wait for the snapshot to become available.",
                            },
                            "retry_delay": {
                                "type": "integer",
                                "default": 5,
                                "description": "Seconds to wait before checking status again.",
                            },
                        },
                        "required": ["url"],
                    },
                },
            },
        ]

    @staticmethod
    def _snapshot_to_dict(snapshot) -> Dict[str, Any]:
        """Convert ArchivedSnapshot dataclass to a serializable dictionary."""
        if snapshot is None:
            return {}

        return {
            "url": snapshot.url,
            "archive_url": snapshot.archive_url,
            "timestamp": snapshot.timestamp.isoformat() if snapshot.timestamp else None,
            "status_code": snapshot.status_code,
            "original_url": snapshot.original_url,
        }

    def archive_get_latest_snapshot(self, url: str) -> Dict[str, Any]:
        """Return the latest archived snapshot for the provided URL."""
        client = self._get_client()
        snapshot = client.get_latest_snapshot(url)
        if snapshot is None:
            return {"url": url, "snapshot": None, "message": "No snapshots found"}
        return {"url": url, "snapshot": self._snapshot_to_dict(snapshot)}

    def archive_list_snapshots(self, url: str, limit: int = 25) -> Dict[str, Any]:
        """List archived snapshots for a URL, capped for safety."""
        client = self._get_client()
        snapshots = client.get_all_snapshots(url=url, limit=limit)
        serialised = [
            self._snapshot_to_dict(snapshot)
            for snapshot in snapshots[: limit or self.max_records]
        ]
        return {"url": url, "snapshots": serialised, "count": len(serialised)}

    def archive_url(
        self,
        url: str,
        wait_for_completion: bool = True,
        retry_delay: int = 5,
    ) -> Dict[str, Any]:
        """Request archiving a URL and optionally wait for completion."""
        client = self._get_client()
        result = client.archive_url(
            url=url,
            wait_for_completion=wait_for_completion,
            retry_delay=retry_delay,
        )

        payload: Dict[str, Any] = {
            "success": result.success,
            "archive_url": result.archive_url,
            "error": result.error,
        }

        if result.snapshot:
            payload["snapshot"] = self._snapshot_to_dict(result.snapshot)

        return payload


if __name__ == "__main__":
    ArchiveTools.main()

