"""
Tool module for Federal Election Commission API access.
"""

from __future__ import annotations
from typing import Any, Dict, List
from .data_tool_base import DataToolModuleBase


class FECTools(DataToolModuleBase):
    """Expose FEC campaign finance data through the tool registry."""

    name = "fec_data"
    display_name = "FEC Data"
    description = "Access Federal Election Commission campaign finance data"
    version = "1.0.0"
    source_name = "fec"
    api_key_name = "fec"
    max_records = 100

    def build_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "fec_search_candidates",
                    "description": "Search for political candidates in FEC database.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Candidate name (partial match)."},
                            "state": {"type": "string", "description": "Two-letter state code."},
                            "party": {"type": "string", "description": "Party (DEM, REP, IND)."},
                            "office": {"type": "string", "description": "Office (H=House, S=Senate, P=President)."},
                            "cycle": {"type": "integer", "description": "Election cycle year."},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "fec_get_candidate_finances",
                    "description": "Get financial summary for a candidate.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "candidate_id": {"type": "string", "description": "FEC candidate ID."},
                            "cycle": {"type": "integer", "description": "Election cycle year."},
                        },
                        "required": ["candidate_id", "cycle"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "fec_search_committees",
                    "description": "Search for PACs and committees.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Committee name."},
                            "committee_type": {"type": "string", "description": "Type (H, S, P, O)."},
                        },
                    },
                },
            },
        ]

    def fec_search_candidates(self, name: str = None, state: str = None, party: str = None, 
                             office: str = None, cycle: int = None) -> Dict[str, Any]:
        """Search for candidates."""
        return self.data_client.search_candidates(name, state, party, office, cycle)

    def fec_get_candidate_finances(self, candidate_id: str, cycle: int) -> Dict[str, Any]:
        """Get candidate finances."""
        return self.data_client.get_candidate_finances(candidate_id, cycle)

    def fec_search_committees(self, name: str = None, committee_type: str = None) -> Dict[str, Any]:
        """Search committees."""
        return self.data_client.search_committees(name, committee_type)
