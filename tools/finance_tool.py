"""
Tool module for Alpha Vantage financial data.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .data_tool_base import DataToolModuleBase


class FinanceTools(DataToolModuleBase):
    """Expose Alpha Vantage endpoints for equities, FX, and crypto."""

    name = "finance_data"
    display_name = "Alpha Vantage Finance"
    description = "Fetch equity time series, FX rates, and crypto quotes"
    version = "1.0.0"
    source_name = "finance"
    api_key_name = "alphavantage"
    max_records = 100

    def build_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "finance_daily_time_series",
                    "description": "Get daily adjusted time series for an equity.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "Ticker symbol (e.g., AAPL)."},
                            "output_size": {
                                "type": "string",
                                "default": "compact",
                                "description": "compact (100 data points) or full.",
                            },
                        },
                        "required": ["symbol"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "finance_fx_rate",
                    "description": "Get realtime foreign exchange rate.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "from_currency": {"type": "string", "description": "Base currency code (e.g., USD)."},
                            "to_currency": {"type": "string", "description": "Quote currency code (e.g., EUR)."},
                        },
                        "required": ["from_currency", "to_currency"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "finance_crypto_quote",
                    "description": "Get digital currency daily quote.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "Crypto symbol (e.g., BTC)."},
                            "market": {
                                "type": "string",
                                "default": "USD",
                                "description": "Market currency (e.g., USD).",
                            },
                        },
                        "required": ["symbol"],
                    },
                },
            },
        ]

    def finance_daily_time_series(
        self,
        symbol: str,
        output_size: str = "compact",
    ) -> Dict[str, Any]:
        """Return daily adjusted time series for an equity symbol."""
        client = self._get_client()
        data = client.get_daily_time_series(symbol=symbol, output_size=output_size)
        prices = data.get("prices", [])
        data["prices"] = self._apply_record_limit(prices)
        data["symbol"] = symbol
        return data

    def finance_fx_rate(self, from_currency: str, to_currency: str) -> Dict[str, Any]:
        """Return an FX rate quote."""
        client = self._get_client()
        return client.get_fx_rate(from_currency=from_currency, to_currency=to_currency)

    def finance_crypto_quote(self, symbol: str, market: str = "USD") -> Dict[str, Any]:
        """Return a digital currency quote."""
        client = self._get_client()
        data = client.get_crypto_quote(symbol=symbol, market=market)
        quotes = data.get("quotes", [])
        data["quotes"] = self._apply_record_limit(quotes)
        data["symbol"] = symbol
        data["market"] = market
        return data


if __name__ == "__main__":
    FinanceTools.main()

