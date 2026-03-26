"""
Order placement and reporting logic.
Acts as the service layer between the CLI and the raw Binance client.
"""

from __future__ import annotations

from typing import Any

from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.logging_config import get_logger
from bot.validators import validate_all

logger = get_logger("orders")


class OrderResult:
    """Simple value object holding the parsed Binance order response."""

    def __init__(self, raw: dict):
        self.raw = raw
        self.order_id: int = raw.get("orderId", 0)
        self.symbol: str = raw.get("symbol", "")
        self.side: str = raw.get("side", "")
        self.order_type: str = raw.get("type", "")
        self.status: str = raw.get("status", "")
        self.orig_qty: str = raw.get("origQty", "0")
        self.executed_qty: str = raw.get("executedQty", "0")
        self.avg_price: str = raw.get("avgPrice", "0")
        self.price: str = raw.get("price", "0")
        self.time_in_force: str = raw.get("timeInForce", "")
        self.client_order_id: str = raw.get("clientOrderId", "")

    def __str__(self) -> str:
        lines = [
            "─" * 52,
            "  ORDER RESULT",
            "─" * 52,
            f"  Order ID      : {self.order_id}",
            f"  Symbol        : {self.symbol}",
            f"  Side          : {self.side}",
            f"  Type          : {self.order_type}",
            f"  Status        : {self.status}",
            f"  Orig Qty      : {self.orig_qty}",
            f"  Executed Qty  : {self.executed_qty}",
            f"  Avg Price     : {self.avg_price}",
            f"  Limit Price   : {self.price}",
            f"  Time In Force : {self.time_in_force}",
            "─" * 52,
        ]
        return "\n".join(lines)


def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Any,
    price: Any = None,
    stop_price: Any = None,
) -> OrderResult:
    """
    Validate inputs, place an order via the client, and return an OrderResult.

    Args:
        client:      Authenticated BinanceFuturesClient instance.
        symbol:      Trading pair, e.g. "BTCUSDT".
        side:        "BUY" or "SELL".
        order_type:  "MARKET", "LIMIT", or "STOP_MARKET".
        quantity:    Order quantity.
        price:       Limit price (required for LIMIT).
        stop_price:  Stop trigger price (required for STOP_MARKET).

    Returns:
        OrderResult wrapping the API response.

    Raises:
        ValueError:      On invalid input.
        BinanceAPIError: On API-level failures.
        requests.RequestException: On network failures.
    """
    # --- Validate all inputs first ---
    params = validate_all(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
    )

    logger.info(
        "Order request validated | %s %s %s qty=%s price=%s",
        params["side"],
        params["order_type"],
        params["symbol"],
        params["quantity"],
        params["price"] or params["stop_price"] or "N/A",
    )

    # --- Dispatch to client ---
    try:
        raw = client.place_order(
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params["price"],
            stop_price=params["stop_price"],
        )
    except BinanceAPIError as exc:
        logger.error("API error placing order: code=%s msg=%s", exc.code, exc.msg)
        raise
    except Exception as exc:
        logger.error("Unexpected error placing order: %s", exc)
        raise

    result = OrderResult(raw)
    logger.debug("Full order response: %s", raw)
    return result


def print_order_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None,
    stop_price: float | None,
) -> None:
    """Print a pre-submission order summary to stdout."""
    print("\n" + "═" * 52)
    print("  ORDER REQUEST SUMMARY")
    print("═" * 52)
    print(f"  Symbol     : {symbol}")
    print(f"  Side       : {side}")
    print(f"  Type       : {order_type}")
    print(f"  Quantity   : {quantity}")
    if price:
        print(f"  Price      : {price}")
    if stop_price:
        print(f"  Stop Price : {stop_price}")
    print("═" * 52 + "\n")
