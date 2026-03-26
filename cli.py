#!/usr/bin/env python3
"""
Trading Bot CLI – Binance Futures Testnet
==========================================
Entry point for placing orders via the command line.

Usage examples:
  python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
  python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 95000
  python cli.py place --symbol ETHUSDT --side BUY --type STOP_MARKET --qty 0.01 --stop-price 3000
  python cli.py account
  python cli.py open-orders --symbol BTCUSDT
"""

from __future__ import annotations

import argparse
import os
import sys

from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.logging_config import setup_logging, get_logger
from bot.orders import place_order, print_order_summary
from bot.validators import ValidationError

import requests

# ── Bootstrap logging before anything else ──────────────────────────────────
setup_logging()
logger = get_logger("cli")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_client() -> BinanceFuturesClient:
    """Build client from environment variables or prompt the user."""
    api_key = os.environ.get("BINANCE_TESTNET_API_KEY", "").strip()
    api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET", "").strip()

    if not api_key:
        api_key = input("Enter your Binance Testnet API Key: ").strip()
    if not api_secret:
        api_secret = input("Enter your Binance Testnet API Secret: ").strip()

    if not api_key or not api_secret:
        print("ERROR: API key and secret are required.", file=sys.stderr)
        sys.exit(1)

    return BinanceFuturesClient(api_key=api_key, api_secret=api_secret)


def _handle_place(args: argparse.Namespace) -> None:
    """Handle the 'place' sub-command."""
    client = _get_client()

    # Pre-validate early to give friendly errors before any API call
    try:
        from bot.validators import validate_all
        params = validate_all(
            symbol=args.symbol,
            side=args.side,
            order_type=args.type,
            quantity=args.qty,
            price=args.price,
            stop_price=args.stop_price,
        )
    except (ValueError, ValidationError) as exc:
        print(f"\n✗  Validation error: {exc}\n", file=sys.stderr)
        logger.warning("Input validation failed: %s", exc)
        sys.exit(2)

    # Show request summary
    print_order_summary(
        symbol=params["symbol"],
        side=params["side"],
        order_type=params["order_type"],
        quantity=params["quantity"],
        price=params["price"],
        stop_price=params["stop_price"],
    )

    # Confirm before submitting (skip with --yes)
    if not args.yes:
        confirm = input("Submit this order? [y/N]: ").strip().lower()
        if confirm not in ("y", "yes"):
            print("Order cancelled by user.")
            logger.info("Order cancelled by user before submission.")
            sys.exit(0)

    # Place the order
    try:
        result = place_order(
            client=client,
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params["price"],
            stop_price=params["stop_price"],
        )
        print(result)
        print("\n✓  Order placed successfully!\n")
        logger.info("CLI: order placed successfully | orderId=%s", result.order_id)

    except (ValueError, ValidationError) as exc:
        print(f"\n✗  Validation error: {exc}\n", file=sys.stderr)
        logger.error("Validation error: %s", exc)
        sys.exit(2)

    except BinanceAPIError as exc:
        print(f"\n✗  Binance API error [{exc.code}]: {exc.msg}\n", file=sys.stderr)
        logger.error("BinanceAPIError: code=%s msg=%s", exc.code, exc.msg)
        sys.exit(3)

    except requests.exceptions.ConnectionError:
        print("\n✗  Network error: Could not reach Binance Testnet. Check your internet connection.\n", file=sys.stderr)
        logger.error("Network connection error")
        sys.exit(4)

    except requests.exceptions.Timeout:
        print("\n✗  Request timed out. The Binance Testnet may be slow – try again.\n", file=sys.stderr)
        logger.error("Request timeout")
        sys.exit(4)

    except Exception as exc:
        print(f"\n✗  Unexpected error: {exc}\n", file=sys.stderr)
        logger.exception("Unexpected error in CLI place handler")
        sys.exit(5)


def _handle_account(args: argparse.Namespace) -> None:
    """Print account balance summary."""
    client = _get_client()
    try:
        account = client.get_account()
        assets = [a for a in account.get("assets", []) if float(a.get("walletBalance", 0)) > 0]
        print("\n" + "═" * 52)
        print("  ACCOUNT BALANCES")
        print("═" * 52)
        for a in assets:
            print(f"  {a['asset']:10s}  wallet={a['walletBalance']:>16s}  unrealised PNL={a.get('unrealizedProfit', '0'):>12s}")
        if not assets:
            print("  No assets with positive balance found.")
        print("═" * 52 + "\n")
    except BinanceAPIError as exc:
        print(f"\n✗  API error [{exc.code}]: {exc.msg}\n", file=sys.stderr)
        sys.exit(3)


def _handle_open_orders(args: argparse.Namespace) -> None:
    """Print open orders for a symbol (or all)."""
    client = _get_client()
    try:
        orders = client.get_open_orders(symbol=args.symbol or None)
        if not orders:
            print("\nNo open orders found.\n")
            return
        print(f"\n{'ID':>12}  {'Symbol':>10}  {'Side':>5}  {'Type':>12}  {'Qty':>10}  {'Price':>12}  Status")
        print("─" * 80)
        for o in orders:
            print(
                f"{o.get('orderId'):>12}  {o.get('symbol'):>10}  {o.get('side'):>5}  "
                f"{o.get('type'):>12}  {o.get('origQty'):>10}  {o.get('price'):>12}  {o.get('status')}"
            )
        print()
    except BinanceAPIError as exc:
        print(f"\n✗  API error [{exc.code}]: {exc.msg}\n", file=sys.stderr)
        sys.exit(3)


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001 --yes
  python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 95000
  python cli.py place --symbol ETHUSDT --side BUY --type STOP_MARKET --qty 0.01 --stop-price 3000
  python cli.py account
  python cli.py open-orders --symbol BTCUSDT
        """,
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    # -- place --
    place_p = subparsers.add_parser("place", help="Place a new futures order")
    place_p.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    place_p.add_argument("--side", required=True, choices=["BUY", "SELL"], help="Order side")
    place_p.add_argument(
        "--type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET"],
        help="Order type",
    )
    place_p.add_argument("--qty", required=True, type=float, metavar="QUANTITY", help="Order quantity")
    place_p.add_argument("--price", type=float, default=None, help="Limit price (required for LIMIT)")
    place_p.add_argument("--stop-price", type=float, default=None, dest="stop_price", help="Stop price (required for STOP_MARKET)")
    place_p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    place_p.set_defaults(func=_handle_place)

    # -- account --
    acct_p = subparsers.add_parser("account", help="Show account balances")
    acct_p.set_defaults(func=_handle_account)

    # -- open-orders --
    oo_p = subparsers.add_parser("open-orders", help="List open orders")
    oo_p.add_argument("--symbol", default=None, help="Filter by symbol")
    oo_p.set_defaults(func=_handle_open_orders)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
