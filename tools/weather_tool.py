"""
Tool module for NOAA / National Weather Service data.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .data_tool_base import DataToolModuleBase


class WeatherTools(DataToolModuleBase):
    """Expose weather and alert data via the shared tool registry."""

    name = "weather_data"
    display_name = "Weather (NOAA)"
    description = "Retrieve current weather, forecasts, and alerts from NOAA"
    version = "1.0.0"
    source_name = "weather"
    api_key_name = None
    max_records = 50

    def build_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "weather_get_current",
                    "description": "Get current weather for coordinates.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "latitude": {"type": "number", "description": "Latitude in decimal degrees."},
                            "longitude": {
                                "type": "number",
                                "description": "Longitude in decimal degrees.",
                            },
                        },
                        "required": ["latitude", "longitude"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "weather_get_forecast",
                    "description": "Get multi-day weather forecast for coordinates.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "latitude": {"type": "number"},
                            "longitude": {"type": "number"},
                            "periods": {
                                "type": "integer",
                                "default": 7,
                                "description": "Number of forecast periods to return (<=14).",
                            },
                        },
                        "required": ["latitude", "longitude"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "weather_get_alerts",
                    "description": "Get weather alerts for a state.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "state": {
                                "type": "string",
                                "description": "Two-letter state code (e.g., OR, WA).",
                            }
                        },
                        "required": ["state"],
                    },
                },
            },
        ]

    def weather_get_current(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Return current weather observations."""
        client = self._get_client()
        return client.get_current_weather(latitude=latitude, longitude=longitude)

    def weather_get_forecast(
        self,
        latitude: float,
        longitude: float,
        periods: int = 7,
    ) -> Dict[str, Any]:
        """Return forecast data for the provided coordinates."""
        client = self._get_client()
        periods = max(1, min(periods, 14))
        result = client.get_forecast(latitude=latitude, longitude=longitude, periods=periods)
        periods_data = result.get("periods", [])
        result["periods"] = self._apply_record_limit(periods_data, limit=periods)
        return result

    def weather_get_alerts(self, state: str) -> Dict[str, Any]:
        """Return current weather alerts for the state."""
        client = self._get_client()
        return client.get_alerts(state=state)


if __name__ == "__main__":
    WeatherTools.main()

