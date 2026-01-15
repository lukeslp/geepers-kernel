"""
Tool module for NASA open APIs.
"""

from __future__ import annotations

from typing import Dict, Optional

from .data_tool_base import DataToolModuleBase


class NASATools(DataToolModuleBase):
    """Expose NASA astronomy and earth observation APIs as tools."""

    name = "nasa_data"
    display_name = "NASA Open APIs"
    description = "Access APOD, Mars Rover photos, Earth imagery, and NEO data"
    version = "1.0.0"
    source_name = "nasa"
    api_key_name = "nasa"
    max_records = 50

    def build_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "nasa_get_apod",
                    "description": "Get Astronomy Picture of the Day (APOD).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "Optional date (YYYY-MM-DD).",
                            },
                            "count": {
                                "type": "integer",
                                "description": "Retrieve a random set of APOD entries (<=10).",
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "nasa_get_mars_photos",
                    "description": "Get Mars Rover photos for a given sol or Earth date.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "rover": {
                                "type": "string",
                                "description": "Rover name (curiosity, opportunity, spirit).",
                                "default": "curiosity",
                            },
                            "sol": {"type": "integer", "description": "Martian solar day."},
                            "earth_date": {"type": "string", "description": "Earth date (YYYY-MM-DD)."},
                            "camera": {"type": "string", "description": "Optional camera filter."},
                            "page": {"type": "integer", "default": 1},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "nasa_get_earth_imagery",
                    "description": "Retrieve Earth imagery for coordinates.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "latitude": {"type": "number"},
                            "longitude": {"type": "number"},
                            "date": {"type": "string", "description": "Date of imagery (YYYY-MM-DD)."},
                            "dim": {
                                "type": "number",
                                "description": "Width/height of image in degrees (default 0.025).",
                            },
                        },
                        "required": ["latitude", "longitude"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "nasa_get_neo_feed",
                    "description": "Get near-Earth object (NEO) feed for a date range.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)."},
                            "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)."},
                        },
                    },
                },
            },
        ]

    def nasa_get_apod(
        self,
        date: Optional[str] = None,
        count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Return Astronomy Picture of the Day metadata."""
        client = self._get_client()
        if count is not None:
            count = max(1, min(count, 10))
        return client.get_apod(date=date, count=count)

    def nasa_get_mars_photos(
        self,
        rover: str = "curiosity",
        sol: Optional[int] = None,
        earth_date: Optional[str] = None,
        camera: Optional[str] = None,
        page: int = 1,
    ) -> Dict[str, Any]:
        """Return Mars rover photos."""
        client = self._get_client()
        result = client.get_mars_photos(
            rover=rover,
            sol=sol,
            earth_date=earth_date,
            camera=camera,
            page=page,
        )
        photos = result.get("photos", [])
        result["photos"] = self._apply_record_limit(photos)
        return result

    def nasa_get_earth_imagery(
        self,
        latitude: float,
        longitude: float,
        date: Optional[str] = None,
        dim: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Return Earth imagery metadata for coordinates."""
        client = self._get_client()
        return client.get_earth_imagery(
            latitude=latitude,
            longitude=longitude,
            date=date,
            dim=dim,
        )

    def nasa_get_neo_feed(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return near-Earth object feed."""
        client = self._get_client()
        return client.get_neo(start_date=start_date, end_date=end_date)


if __name__ == "__main__":
    NASATools.main()

