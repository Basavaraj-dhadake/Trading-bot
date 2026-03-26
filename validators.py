"""
Input validation for trading bot CLI arguments.
All functions raise ValidationError with descriptive messages on invalid input.
"""

from __future__ import annotations

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}


class ValidationError(ValueError):
    """Raised when user-supplied trading parameters fail validation."""
    pass


def validate_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if not s:
        raise ValidationError("Symbol must not be empty.")
    if not s.isalnum():
        raise ValidationError(f"Symbol '{s}' contains invalid characters. Use alphanumeric only (e.g. BTCUSDT).")
    return s


def validate_side(side: str) -> str:
    s = side.strip().upper()
    if s not in VALID_SIDES:
        raise ValidationError(f"Side must be one of {sorted(VALID_SIDES)}, got '{side}'.")
    return s


def validate_order_type(order_type: str) -> str:
    t = order_type.strip().upper()
    if t not in VALID_ORDER_TYPES:
        raise ValidationError(f"Order type must be one of {sorted(VALID_ORDER_TYPES)}, got '{order_type}'.")
    return t


def validate_quantity(quantity) -> float:
    try:
        q = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be a valid number, got '{quantity}'.")
    if q <= 0:
        raise ValidationError(f"Quantity must be greater than 0, got {q}.")
    return q


def validate_price(price, order_type: str):
    """Price is required only for LIMIT orders; ignored for others."""
    if order_type != "LIMIT":
        return None
    if price is None:
        raise ValidationError(f"Price is required for {order_type} orders.")
    try:
        p = float(price)
    except (TypeError, ValueError):
        raise ValidationError(f"Price must be a valid number, got '{price}'.")
    if p <= 0:
        raise ValidationError(f"Price must be greater than 0, got {p}.")
    return p


def validate_stop_price(stop_price, order_type: str):
    """Stop price is required only for STOP_MARKET orders."""
    if order_type != "STOP_MARKET":
        return None
    if stop_price is None:
        raise ValidationError("Stop price is required for STOP_MARKET orders.")
    try:
        sp = float(stop_price)
    except (TypeError, ValueError):
        raise ValidationError(f"Stop price must be a valid number, got '{stop_price}'.")
    if sp <= 0:
        raise ValidationError(f"Stop price must be greater than 0, got {sp}.")
    return sp


def validate_all(symbol, side, order_type, quantity, price=None, stop_price=None) -> dict:
    """Run all validations and return a clean params dict."""
    clean_symbol = validate_symbol(symbol)
    clean_side = validate_side(side)
    clean_type = validate_order_type(order_type)
    clean_qty = validate_quantity(quantity)
    clean_price = validate_price(price, clean_type)
    clean_stop = validate_stop_price(stop_price, clean_type)

    return {
        "symbol": clean_symbol,
        "side": clean_side,
        "order_type": clean_type,
        "quantity": clean_qty,
        "price": clean_price,
        "stop_price": clean_stop,
    }
