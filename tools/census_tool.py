"""
Tool module exposing Census Bureau datasets through the ToolRegistry.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .data_tool_base import DataToolModuleBase


class CensusTools(DataToolModuleBase):
    """Tools for interacting with U.S. Census Bureau datasets."""

    name = "census_data"
    display_name = "U.S. Census Data"
    description = "Access ACS and population datasets from the U.S. Census Bureau"
    version = "1.0.0"
    source_name = "census"
    api_key_name = "census"
    max_records = 500

    def build_schemas(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "census_fetch_acs",
                    "description": "Fetch ACS data for specified variables and geography.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "year": {"type": "integer", "default": 2022},
                            "variables": {
                                "type": "object",
                                "description": "Mapping of Census variable codes to friendly column names.",
                            },
                            "geography": {
                                "type": "string",
                                "default": "county:*",
                                "description": "Geography filter (e.g., county:*, state:41).",
                            },
                            "dataset": {
                                "type": "string",
                                "default": "acs5",
                                "description": "ACS dataset (acs5, acs1).",
                            },
                            "state": {
                                "type": "string",
                                "description": "Optional state FIPS code to constrain results.",
                            },
                            "limit": {
                                "type": "integer",
                                "default": 200,
                                "description": "Maximum number of records to return.",
                            },
                        },
                        "required": ["year", "variables"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "census_fetch_population",
                    "description": "Fetch population estimates for counties or states.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "year": {"type": "integer", "default": 2023},
                            "geography": {
                                "type": "string",
                                "default": "county",
                                "description": "Geography level (county or state).",
                            },
                            "state": {
                                "type": "string",
                                "description": "Optional state FIPS code.",
                            },
                            "limit": {
                                "type": "integer",
                                "default": 200,
                                "description": "Maximum number of records to return.",
                            },
                        },
                        "required": ["year"],
                    },
                },
            },
        ]

    def census_fetch_acs(
        self,
        year: int,
        variables: Dict[str, str],
        geography: str = "county:*",
        dataset: str = "acs5",
        state: Optional[str] = None,
        limit: int = 200,
    ) -> Dict[str, Any]:
        """
        Fetch data from the American Community Survey.
        """
        client = self._get_client()
        dataframe = client.fetch_acs(
            year=year,
            variables=variables,
            geography=geography,
            dataset=dataset,
            state=state,
        )
        normalized = self._normalize_dataframe(dataframe)
        records = self._apply_record_limit(normalized, limit=min(limit, self.max_records or limit))
        metadata = client.get_metadata()
        return {
            "records": records,
            "metadata": metadata,
            "variables": variables,
            "year": year,
            "geography": geography,
        }

    def census_fetch_population(
        self,
        year: int,
        geography: str = "county",
        state: Optional[str] = None,
        limit: int = 200,
    ) -> Dict[str, Any]:
        """
        Fetch population estimates from Census datasets.
        """
        client = self._get_client()
        dataframe = client.fetch_population(year=year, geography=geography, state=state)
        normalized = self._normalize_dataframe(dataframe)
        records = self._apply_record_limit(normalized, limit=min(limit, self.max_records or limit))
        return {
            "records": records,
            "year": year,
            "geography": geography,
            "state": state,
        }


if __name__ == "__main__":
    CensusTools.main()

