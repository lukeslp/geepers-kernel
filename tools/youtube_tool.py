"""
Tool module for YouTube Data API v3.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .data_tool_base import DataToolModuleBase


class YouTubeTools(DataToolModuleBase):
    """Expose YouTube search, channel stats, and playlist access."""

    name = "youtube_data"
    display_name = "YouTube Data API"
    description = "Search videos, fetch channel statistics, and list playlists"
    version = "1.0.0"
    source_name = "youtube"
    api_key_name = "youtube"
    max_records = 25

    def build_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "youtube_search_videos",
                    "description": "Search for videos on YouTube.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query."},
                            "max_results": {
                                "type": "integer",
                                "default": 10,
                                "description": "Maximum number of results (<=25).",
                            },
                            "order": {
                                "type": "string",
                                "default": "relevance",
                                "description": "Sort order (date, rating, relevance, title, viewCount).",
                            },
                            "safe_search": {
                                "type": "string",
                                "default": "moderate",
                                "description": "Safe search setting (none, moderate, strict).",
                            },
                            "video_duration": {
                                "type": "string",
                                "description": "Filter by duration (any, short, medium, long).",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "youtube_channel_statistics",
                    "description": "Fetch channel statistics for a channel ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "channel_id": {"type": "string", "description": "YouTube channel ID."}
                        },
                        "required": ["channel_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "youtube_playlist_items",
                    "description": "List items in a playlist.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "playlist_id": {"type": "string", "description": "YouTube playlist ID."},
                            "max_results": {
                                "type": "integer",
                                "default": 25,
                                "description": "Maximum number of items (<=25).",
                            },
                        },
                        "required": ["playlist_id"],
                    },
                },
            },
        ]

    def youtube_search_videos(
        self,
        query: str,
        max_results: int = 10,
        order: str = "relevance",
        safe_search: str = "moderate",
        video_duration: str | None = None,
    ) -> Dict[str, Any]:
        """Search for videos with optional filters."""
        client = self._get_client()
        max_results = min(max_results, self.max_records or max_results)
        result = client.search_videos(
            query=query,
            max_results=max_results,
            order=order,
            safe_search=safe_search,
            video_duration=video_duration,
        )
        result["videos"] = self._apply_record_limit(result.get("videos", []))
        result["query"] = query
        return result

    def youtube_channel_statistics(self, channel_id: str) -> Dict[str, Any]:
        """Retrieve statistics and metadata for a YouTube channel."""
        client = self._get_client()
        return client.get_channel_statistics(channel_id=channel_id)

    def youtube_playlist_items(self, playlist_id: str, max_results: int = 25) -> Dict[str, Any]:
        """List items from the specified playlist."""
        client = self._get_client()
        max_results = min(max_results, self.max_records or max_results)
        result = client.get_playlist_items(playlist_id=playlist_id, max_results=max_results)
        result["items"] = self._apply_record_limit(result.get("items", []))
        return result


if __name__ == "__main__":
    YouTubeTools.main()

