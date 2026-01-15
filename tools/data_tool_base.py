"""
Base utilities for data source tool modules.

Data tool modules wrap data-fetching clients and expose them through the
ToolRegistry with consistent schemas and error handling.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from config import ConfigManager
from data_fetching.factory import DataFetchingFactory

from .module_base import ToolModuleBase


class DataToolModuleBase(ToolModuleBase):
    """Base class for data source tool modules."""

    source_name: str = ""
    api_key_name: Optional[str] = None
    max_records: Optional[int] = 1000  # safeguard to avoid enormous payloads

    def initialize(self) -> None:
        if not self.source_name:
            raise ValueError("DataToolModuleBase subclasses must define source_name")
        self._client = None
        self.tool_schemas = self.build_schemas()

    def build_schemas(self) -> List[Dict[str, Any]]:
        """Subclasses must provide tool schemas."""
        raise NotImplementedError("Subclasses must implement build_schemas()")

    def _get_client(self):
        """Instantiate and memoize the underlying data client."""
        if self._client is not None:
            return self._client

        kwargs: Dict[str, Any] = {}

        if self.api_key_name:
            api_key = self.config.get("api_key")
            if not api_key:
                config = ConfigManager()
                api_key = config.get_api_key(self.api_key_name)
            if api_key:
                kwargs["api_key"] = api_key

        try:
            self._client = DataFetchingFactory.create_client(self.source_name, **kwargs)
        except Exception as exc:  # noqa: BLE001 - surface friendly error message
            raise RuntimeError(
                f"Could not initialize data client for '{self.source_name}': {exc}"
            ) from exc

        return self._client

    @staticmethod
    def _normalize_dataframe(data: Any, limit: Optional[int] = None) -> Any:
        """Convert pandas DataFrame to records if applicable."""
        if hasattr(data, "to_dict"):
            records = data.to_dict(orient="records")
            if limit is not None:
                return records[:limit]
            return records
        return data

    def _apply_record_limit(
        self,
        records: List[Dict[str, Any]],
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Limit record count to avoid huge responses.

        Args:
            records: List of records to trim.
            limit: Optional explicit limit. Defaults to self.max_records.

        Returns:
            Possibly trimmed record list.
        """
        max_items = limit if limit is not None else self.max_records
        if max_items is None:
            return records
        return records[:max_items]


__all__ = ["DataToolModuleBase"]

