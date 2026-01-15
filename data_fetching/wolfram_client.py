"""
Wolfram Alpha API Client
Provides programmatic access to Wolfram Alpha for computational knowledge.

Author: Luke Steuber
"""

import os
import logging
import urllib.parse
import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# API URLs
WOLFRAM_SIMPLE_URL = "http://api.wolframalpha.com/v1/simple"
WOLFRAM_SHORT_URL = "http://api.wolframalpha.com/v1/result"
WOLFRAM_FULL_URL = "http://api.wolframalpha.com/v2/query"
WOLFRAM_SPOKEN_URL = "http://api.wolframalpha.com/v1/spoken"


@dataclass
class WolframResult:
    """Result from Wolfram Alpha query"""
    success: bool
    query: str
    result: Optional[str] = None
    result_type: str = "text"  # text, image, spoken, full
    pods: Optional[List[Dict]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'success': self.success,
            'query': self.query,
            'result': self.result,
            'result_type': self.result_type,
            'pods': self.pods,
            'error': self.error
        }


class WolframAlphaClient:
    """Client for interacting with Wolfram Alpha API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Wolfram Alpha client.

        Args:
            api_key: Wolfram Alpha App ID. If not provided, uses
                     WOLFRAMALPHA_APP_ID environment variable.
        """
        self.api_key = api_key or os.environ.get('WOLFRAMALPHA_APP_ID', '')
        self.session = requests.Session()

        if not self.api_key:
            logger.warning("No Wolfram Alpha API key provided")

    def _check_api_key(self) -> None:
        """Raise error if no API key"""
        if not self.api_key:
            raise ValueError(
                "Wolfram Alpha API key required. "
                "Set WOLFRAMALPHA_APP_ID environment variable or pass api_key parameter."
            )

    def query(self, query: str, timeout: int = 30) -> WolframResult:
        """
        Query Wolfram Alpha and get a short text answer.

        Args:
            query: Question or problem to solve
            timeout: Request timeout in seconds

        Returns:
            WolframResult with the answer
        """
        self._check_api_key()

        try:
            logger.info(f"Wolfram Alpha query: {query}")

            params = {
                "i": query,
                "appid": self.api_key,
                "format": "plaintext"
            }

            response = self.session.get(
                WOLFRAM_SHORT_URL,
                params=params,
                timeout=timeout
            )

            if response.status_code == 501:
                return WolframResult(
                    success=False,
                    query=query,
                    error="Wolfram Alpha couldn't understand the query"
                )

            response.raise_for_status()

            return WolframResult(
                success=True,
                query=query,
                result=response.text,
                result_type="text"
            )

        except requests.RequestException as e:
            logger.error(f"Wolfram Alpha query error: {e}")
            return WolframResult(
                success=False,
                query=query,
                error=str(e)
            )

    def query_spoken(self, query: str, timeout: int = 30) -> WolframResult:
        """
        Query Wolfram Alpha and get a spoken-style answer.

        Args:
            query: Question or problem to solve
            timeout: Request timeout in seconds

        Returns:
            WolframResult with spoken answer
        """
        self._check_api_key()

        try:
            logger.info(f"Wolfram Alpha spoken query: {query}")

            params = {
                "i": query,
                "appid": self.api_key
            }

            response = self.session.get(
                WOLFRAM_SPOKEN_URL,
                params=params,
                timeout=timeout
            )
            response.raise_for_status()

            return WolframResult(
                success=True,
                query=query,
                result=response.text,
                result_type="spoken"
            )

        except requests.RequestException as e:
            logger.error(f"Wolfram Alpha spoken query error: {e}")
            return WolframResult(
                success=False,
                query=query,
                error=str(e)
            )

    def query_image_url(self, query: str) -> WolframResult:
        """
        Get URL for Wolfram Alpha image result.

        Args:
            query: Question or problem to solve

        Returns:
            WolframResult with image URL
        """
        self._check_api_key()

        params = {"i": query, "appid": self.api_key}
        image_url = f"{WOLFRAM_SIMPLE_URL}?{urllib.parse.urlencode(params)}"

        return WolframResult(
            success=True,
            query=query,
            result=image_url,
            result_type="image"
        )

    def query_full(self, query: str, timeout: int = 30) -> WolframResult:
        """
        Query Wolfram Alpha with full results (all pods).

        Args:
            query: Question or problem to solve
            timeout: Request timeout in seconds

        Returns:
            WolframResult with all pods
        """
        self._check_api_key()

        try:
            logger.info(f"Wolfram Alpha full query: {query}")

            params = {
                "input": query,
                "appid": self.api_key,
                "output": "json",
                "format": "plaintext"
            }

            response = self.session.get(
                WOLFRAM_FULL_URL,
                params=params,
                timeout=timeout
            )
            response.raise_for_status()

            data = response.json()
            query_result = data.get("queryresult", {})

            if not query_result.get("success"):
                return WolframResult(
                    success=False,
                    query=query,
                    error=query_result.get("error", {}).get("msg", "Query failed")
                )

            # Extract pods
            pods = []
            for pod in query_result.get("pods", []):
                pod_data = {
                    "title": pod.get("title"),
                    "id": pod.get("id"),
                    "position": pod.get("position"),
                    "subpods": []
                }

                for subpod in pod.get("subpods", []):
                    pod_data["subpods"].append({
                        "title": subpod.get("title", ""),
                        "plaintext": subpod.get("plaintext", "")
                    })

                pods.append(pod_data)

            # Get primary result
            primary_result = None
            for pod in pods:
                if pod["id"] == "Result" or pod["title"] == "Result":
                    if pod["subpods"]:
                        primary_result = pod["subpods"][0].get("plaintext")
                    break

            return WolframResult(
                success=True,
                query=query,
                result=primary_result,
                result_type="full",
                pods=pods
            )

        except requests.RequestException as e:
            logger.error(f"Wolfram Alpha full query error: {e}")
            return WolframResult(
                success=False,
                query=query,
                error=str(e)
            )

    def calculate(self, expression: str) -> WolframResult:
        """
        Calculate a mathematical expression.

        Args:
            expression: Math expression (e.g., "2+2", "integrate x^2")

        Returns:
            WolframResult with calculation
        """
        return self.query(expression)

    def convert(self, value: str, from_unit: str, to_unit: str) -> WolframResult:
        """
        Convert units.

        Args:
            value: Numeric value
            from_unit: Source unit
            to_unit: Target unit

        Returns:
            WolframResult with conversion
        """
        query = f"convert {value} {from_unit} to {to_unit}"
        return self.query(query)

    def define(self, word: str) -> WolframResult:
        """
        Get definition of a word.

        Args:
            word: Word to define

        Returns:
            WolframResult with definition
        """
        query = f"define {word}"
        return self.query(query)


# Convenience functions
def wolfram_query(query: str, api_key: Optional[str] = None) -> str:
    """
    Quick query to Wolfram Alpha.

    Args:
        query: Question or problem
        api_key: Optional API key

    Returns:
        Answer string or error message
    """
    client = WolframAlphaClient(api_key=api_key)
    result = client.query(query)

    if result.success:
        return result.result
    return f"Error: {result.error}"


def wolfram_calculate(expression: str, api_key: Optional[str] = None) -> str:
    """
    Calculate a math expression.

    Args:
        expression: Math expression
        api_key: Optional API key

    Returns:
        Result string
    """
    client = WolframAlphaClient(api_key=api_key)
    result = client.calculate(expression)

    if result.success:
        return result.result
    return f"Error: {result.error}"
