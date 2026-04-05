# TradingView -> Polymarket Bot

This project receives TradingView webhook alerts and turns them into Polymarket trades. It includes:

- TradingView webhook ingestion with FastAPI
- Polymarket CLOB integration via the official Python SDK
- A 3x progression system with a maximum of 4 steps
- SQLite-backed state for current step, estimated balance, and the active trade
- One-trade-at-a-time locking
- File logging for entries, exits, and errors
- Dry-run mode for safe testing without live orders

## Important Behavior

- Base trade size comes from `BASE_TRADE_AMOUNT`
- After each loss, the next trade size becomes `previous_size * 3`
- Maximum sequence length is `MAX_STEPS=4`, so the default sequence is `50 -> 150 -> 450 -> 1350`
- A win resets the step back to `0`
- A loss on the final allowed step also resets back to `0` and logs that the progression was exhausted
- The bot will not open a second trade while one is already active

## Strategy Assumption

This MVP assumes TradingView sends two kinds of alerts:

- `ENTER`: buy the specified Polymarket token
- `EXIT`: sell the same token to close the open trade

The progression advances only after an `EXIT` alert, because that is when the bot can calculate whether the trade won or lost based on realized PnL.

## Quick Start

1. Create and activate a virtual environment:

   ```powershell
   cd D:\tradingview-polymarket-bot
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Copy the environment template:

   ```powershell
   Copy-Item .env.example .env
   ```

4. Set at least:
   - `WEBHOOK_SECRET`
   - `BASE_TRADE_AMOUNT`
   - `INITIAL_BALANCE`

5. For safe testing, keep `DRY_RUN=true`
6. Start the API server:

   ```powershell
   python main.py
   ```

7. TradingView webhook URL:

   ```text
   https://your-domain.com/webhooks/tradingview/<WEBHOOK_SECRET>
   ```

TradingView expects a regular `POST` webhook endpoint. Its webhook help center documents JSON bodies, authentication considerations, retry behavior, and the platform constraints around destination ports and delivery behavior. Source: [TradingView webhook docs](https://www.tradingview.com/support/folders/43000560150/).

## Live Trading Setup

For live Polymarket trading, set:

- `DRY_RUN=false`
- `POLYMARKET_PRIVATE_KEY`
- `POLYMARKET_FUNDER`

This project uses Polymarket’s official Python CLOB client. Polymarket’s current quickstart shows:

- Python SDK package: `py-clob-client`
- CLOB host: `https://clob.polymarket.com`
- Polygon chain id: `137`
- API credentials derived via `create_or_derive_api_creds()`

Sources:
- [Polymarket quickstart](https://docs.polymarket.com/quickstart)
- [Polymarket orders overview](https://docs.polymarket.com/developers/CLOB/orders/get-order)

## Webhook Payload Example

```json
{
  "action": "ENTER",
  "alert_id": "btc-ema-cross-2026-04-04T22:10:00Z",
  "market_slug": "will-bitcoin-be-above-100k-on-june-30",
  "tv_symbol": "BTCUSD",
  "condition_id": "0x_condition_id_here",
  "token_id": "0x_yes_or_no_token_id_here",
  "outcome": "YES",
  "max_price": 0.63,
  "note": "EMA cross long"
}
```

Exit example:

```json
{
  "action": "EXIT",
  "alert_id": "btc-ema-cross-exit-2026-04-04T23:05:00Z",
  "token_id": "0x_yes_or_no_token_id_here",
  "min_price": 0.58,
  "note": "strategy exit"
}
```

## Operational Notes

- The bot uses a single in-process lock, so one application instance should own the webhook endpoint and database.
- Prices are treated as “marketable limit orders” by adding or subtracting `MAX_SLIPPAGE`.
- Polymarket expresses all orders as limit orders; “market” execution is achieved by sending marketable limit prices. Source: [Polymarket orders overview](https://docs.polymarket.com/developers/CLOB/orders/get-order)
- In dry-run mode, the bot generates deterministic fake fills so you can test the progression logic without touching capital.

## API Endpoints

- `GET /health`
- `GET /status`
- `POST /webhooks/tradingview/{secret}`
- `POST /webhooks/tradingview/{secret}/close-loss` for dry-run helper testing
- `POST /webhooks/tradingview/{secret}/close-win` for dry-run helper testing

## Deployment Files

- `Dockerfile`
- `docker-compose.yml`
- `deploy/systemd/tv-polymarket-bot.service`
- `deploy/supervisor/tv-polymarket-bot.conf`
- `deploy/windows/start-dry-run.ps1`
- `deploy/windows/start-live.ps1`
- `deploy/windows/start-dry-run.bat`
- `deploy/windows/start-live.bat`
- `deploy/nginx/tv-polymarket-bot.conf`
- `deploy/ubuntu/install_ubuntu_vps.sh`
- `deploy/ubuntu/update.sh`
- `docs/RUNBOOK.md`
- `.env.production.example`
- `docs/VPS_DEPLOYMENT_CHECKLIST.md`
- `docs/NGINX_DEPLOYMENT.md`
- `docs/UBUNTU_QUICKSTART.md`
- `scripts/dry_run_smoke_test.py`

## Ready Test Payloads

- `examples/enter.json`
- `examples/exit.json`
- `examples/win-enter.json`
- `examples/win-exit.json`
