# Architecture

## Flow

1. TradingView sends a JSON webhook to `/webhooks/tradingview/{secret}`.
2. FastAPI validates the payload with `TradingViewAlert`.
3. `TradingEngine` acquires a global lock so only one alert is processed at a time.
4. The engine reads the current step and active trade state from SQLite.
5. On `ENTER`, it calculates the progression amount and opens one Polymarket position.
6. On `EXIT`, it closes the active position, computes realized PnL, updates balance, and moves the progression step.
7. The new state is persisted and logged.

## Modules

- `bot/config.py` loads environment configuration.
- `bot/storage/` creates the SQLite schema and persists both singleton state and trade history.
- `bot/core/progression.py` keeps progression math separate from exchange logic.
- `bot/integrations/polymarket_client.py` wraps the official Polymarket SDK for live mode and simulates fills in dry-run mode.
- `bot/services/trading_engine.py` implements the entry/exit rules and “one trade at a time” behavior.
- `bot/api/app.py` exposes the webhook and status endpoints.

## Persistence Model

`bot_state` stores:

- current step
- estimated balance
- progression parameters
- active trade id
- last outcome

`trades` stores:

- entry and exit order metadata
- token / market references
- requested notional
- filled size and prices
- realized PnL and result

## Why A Single Active Trade

The requested progression system depends on sequence state. If two trades are open at the same time, the bot cannot know which one should advance or reset the progression first. This implementation therefore enforces one active trade maximum.
