# Binance Futures Testnet Trading Bot

A clean, structured Python CLI application for placing orders on the **Binance USDT-M Futures Testnet**.

---

## Features

- Place **MARKET**, **LIMIT**, and **STOP_MARKET** orders (bonus third type)
- Supports **BUY** and **SELL** sides
- Full **input validation** with helpful error messages
- Structured logging to `logs/trading_bot_YYYYMMDD.log`
- Layered architecture: client → orders → CLI
- No Binance SDK required — uses direct REST calls via `requests`

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance REST client (auth, signing, HTTP)
│   ├── orders.py          # Order placement logic & OrderResult value object
│   ├── validators.py      # Input validation (raises ValidationError)
│   └── logging_config.py  # Dual file+console logging setup
├── cli.py                 # CLI entry point (argparse)
├── logs/
│   └── trading_bot_YYYYMMDD.log
├── README.md
└── requirements.txt
```

---

## Setup

### 1. Register a Binance Futures Testnet Account

1. Visit [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Click **"Start Trading"** and log in with your GitHub or Google account
3. Navigate to **API Management** → **Create API**
4. Copy your **API Key** and **API Secret**

### 2. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/trading-bot.git
cd trading-bot

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Set API Credentials

**Recommended — environment variables:**

```bash
export BINANCE_TESTNET_API_KEY="your_api_key_here"
export BINANCE_TESTNET_API_SECRET="your_api_secret_here"
```

**Windows PowerShell:**

```powershell
$env:BINANCE_TESTNET_API_KEY="your_api_key_here"
$env:BINANCE_TESTNET_API_SECRET="your_api_secret_here"
```

If environment variables are not set, the CLI will prompt you to enter them interactively.

---

## Usage

### Place a MARKET order

```bash
# BUY 0.001 BTC at market price (auto-confirms with --yes)
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001 --yes

# SELL 0.01 ETH at market price (will prompt for confirmation)
python cli.py place --symbol ETHUSDT --side SELL --type MARKET --qty 0.01
```

### Place a LIMIT order

```bash
# SELL 0.001 BTC with a limit price of 90,000 USDT
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 90000

# BUY 0.01 ETH with a limit price of 2,000 USDT
python cli.py place --symbol ETHUSDT --side BUY --type LIMIT --qty 0.01 --price 2000
```

### Place a STOP_MARKET order (bonus)

```bash
# BUY ETHUSDT when price rises to 2,100 (stop-loss / breakout entry)
python cli.py place --symbol ETHUSDT --side BUY --type STOP_MARKET --qty 0.01 --stop-price 2100

# SELL BTCUSDT if price drops to 80,000
python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --qty 0.001 --stop-price 80000
```

### View account balances

```bash
python cli.py account
```

### List open orders

```bash
python cli.py open-orders --symbol BTCUSDT
python cli.py open-orders                  # all symbols
```

---

## Example Output

```
════════════════════════════════════════════════════
  ORDER REQUEST SUMMARY
════════════════════════════════════════════════════
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.001
════════════════════════════════════════════════════

Submit this order? [y/N]: y

────────────────────────────────────────────────────
  ORDER RESULT
────────────────────────────────────────────────────
  Order ID      : 4036591847
  Symbol        : BTCUSDT
  Side          : BUY
  Type          : MARKET
  Status        : FILLED
  Orig Qty      : 0.001
  Executed Qty  : 0.001
  Avg Price     : 87342.50000
  Limit Price   : 0
  Time In Force : GTC
────────────────────────────────────────────────────

✓  Order placed successfully!
```

---

## Logging

Logs are written to `logs/trading_bot_YYYYMMDD.log`.

- **File handler**: captures `DEBUG` and above (full API request/response detail)
- **Console handler**: displays `INFO` and above (clean user-facing output)

Example log lines:

```
2026-03-26 10:12:03 | DEBUG    | trading_bot.client | → POST .../fapi/v1/order | params={...}
2026-03-26 10:12:04 | INFO     | trading_bot.client | Order placed successfully | orderId=4036591847 status=FILLED
2026-03-26 10:22:05 | WARNING  | trading_bot.cli    | Input validation failed: Price is required for LIMIT orders.
2026-03-26 10:27:50 | ERROR    | trading_bot.client | API error placing order: code=-1121 msg=Invalid symbol.
```

---

## Validation & Error Handling

| Scenario | Behaviour |
|---|---|
| Missing required price for LIMIT | `ValidationError` with clear message, exit code 2 |
| Invalid symbol characters | `ValidationError` before any API call |
| Quantity ≤ 0 | `ValidationError` before any API call |
| Binance API rejects the order | `BinanceAPIError` with Binance error code + message, exit code 3 |
| Network / timeout | Friendly message + exit code 4 |
| Unexpected exception | Logged with full traceback, exit code 5 |

---

## Assumptions

1. **USDT-M Futures only** — all orders target `/fapi/v1/order` (not COIN-M or Spot).
2. **Testnet only** — the base URL is hardcoded to `https://testnet.binancefuture.com`. To use mainnet, set `BINANCE_BASE_URL` or edit `client.py`.
3. **GTC time-in-force** used by default for LIMIT orders.
4. **No leverage management** — leverage is left at the testnet default. Use the Binance UI to adjust it before trading.
5. **Quantity precision** — the bot sends raw float quantities. If Binance rejects with `-1111` (precision error), adjust your quantity to match the symbol's `stepSize` from exchange info.

---

## Requirements

- Python 3.9+
- `requests>=2.31.0`
