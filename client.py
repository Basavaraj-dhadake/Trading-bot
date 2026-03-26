"""
Binance Futures Testnet client.
Handles authentication (HMAC-SHA256 signatures) and raw HTTP communication.
Uses the requests library with no third-party Binance SDK dependency.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlencode

import requests

from bot.logging_config import get_logger

logger = get_logger("client")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT = 10  # seconds


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx response or an error payload."""

    def __init__(self, code: int, msg: str, http_status: int | None = None):
        self.code = code
        self.msg = msg
        self.http_status = http_status
        super().__init__(f"Binance API error {code}: {msg}")


class BinanceFuturesClient:
    """
    Lightweight Binance USDT-M Futures Testnet client.

    Responsibilities:
      - Sign requests with HMAC-SHA256
      - Send HTTP requests and handle low-level errors
      - Log every outbound request and inbound response at DEBUG level
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str = TESTNET_BASE_URL):
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")
        self._api_key = api_key
        self._api_secret = api_secret.encode()
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({"X-MBX-APIKEY": self._api_key})
        logger.debug("BinanceFuturesClient initialised (base_url=%s)", self._base_url)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _timestamp(self) -> int:
        return int(time.time() * 1000)

    def _sign(self, params: dict) -> dict:
        """Append a valid HMAC-SHA256 signature to *params* (in-place) and return it."""
        query = urlencode(params)
        sig = hmac.new(self._api_secret, query.encode(), hashlib.sha256).hexdigest()
        params["signature"] = sig
        return params

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        signed: bool = True,
    ) -> Any:
        """
        Core HTTP dispatch method.

        Args:
            method:   HTTP method ("GET", "POST", "DELETE").
            endpoint: API path, e.g. "/fapi/v1/order".
            params:   Query/body parameters.
            signed:   Whether to add timestamp + signature.

        Returns:
            Parsed JSON response (dict or list).

        Raises:
            BinanceAPIError: On API-level errors.
            requests.RequestException: On network-level errors.
        """
        params = params or {}

        if signed:
            params["timestamp"] = self._timestamp()
            self._sign(params)

        url = f"{self._base_url}{endpoint}"

        logger.debug("→ %s %s | params=%s", method.upper(), url, {k: v for k, v in params.items() if k != "signature"})

        try:
            if method.upper() in ("GET", "DELETE"):
                resp = self._session.request(method, url, params=params, timeout=DEFAULT_TIMEOUT)
            else:
                resp = self._session.request(method, url, data=params, timeout=DEFAULT_TIMEOUT)
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network connection error: %s", exc)
            raise
        except requests.exceptions.Timeout:
            logger.error("Request timed out after %ss: %s %s", DEFAULT_TIMEOUT, method, url)
            raise
        except requests.exceptions.RequestException as exc:
            logger.error("Unexpected request error: %s", exc)
            raise

        logger.debug("← HTTP %s | %s", resp.status_code, resp.text[:500])

        try:
            data = resp.json()
        except ValueError:
            resp.raise_for_status()
            return resp.text

        # Binance error payload pattern
        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            raise BinanceAPIError(
                code=data.get("code", -1),
                msg=data.get("msg", "Unknown error"),
                http_status=resp.status_code,
            )

        resp.raise_for_status()
        return data

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def get_server_time(self) -> dict:
        """Ping the testnet and return server time (useful for connectivity checks)."""
        return self._request("GET", "/fapi/v1/time", signed=False)

    def get_exchange_info(self) -> dict:
        """Fetch exchange info (symbols, precision rules, etc.)."""
        return self._request("GET", "/fapi/v1/exchangeInfo", signed=False)

    def get_account(self) -> dict:
        """Return account details including balance."""
        return self._request("GET", "/fapi/v2/account")

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        stop_price: float | None = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
    ) -> dict:
        """
        Place a new futures order.

        Args:
            symbol:        e.g. "BTCUSDT"
            side:          "BUY" or "SELL"
            order_type:    "MARKET", "LIMIT", or "STOP_MARKET"
            quantity:      Order quantity (base asset).
            price:         Required for LIMIT orders.
            stop_price:    Required for STOP_MARKET orders.
            time_in_force: "GTC" | "IOC" | "FOK" (LIMIT only).
            reduce_only:   If True, the order can only reduce an existing position.

        Returns:
            Binance order response dict.
        """
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }

        if order_type == "LIMIT":
            params["price"] = price
            params["timeInForce"] = time_in_force

        if order_type == "STOP_MARKET":
            params["stopPrice"] = stop_price

        if reduce_only:
            params["reduceOnly"] = "true"

        logger.info(
            "Placing %s %s order | symbol=%s qty=%s price=%s",
            side,
            order_type,
            symbol,
            quantity,
            price or stop_price or "N/A",
        )

        response = self._request("POST", "/fapi/v1/order", params=params)
        logger.info("Order placed successfully | orderId=%s status=%s", response.get("orderId"), response.get("status"))
        return response

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel an open order."""
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("DELETE", "/fapi/v1/order", params=params)

    def get_order(self, symbol: str, order_id: int) -> dict:
        """Query a single order by ID."""
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("GET", "/fapi/v1/order", params=params)

    def get_open_orders(self, symbol: str | None = None) -> list:
        """Return all open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params)
