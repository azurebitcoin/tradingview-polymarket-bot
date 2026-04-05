# VPS Deployment Checklist

## Before Uploading The Bot

- provision a VPS with a static public IP or stable DNS name
- ensure ports `80` and `443` are available for TradingView webhooks
- install Python 3.11+
- install `git`
- install `nginx` or another reverse proxy
- install either `systemd` or `supervisor`
- decide whether you will run directly on the host or through Docker

## Secrets And Wallet Safety

- never store production secrets inside the repository
- create `.env` from `.env.production.example`
- generate a long random `WEBHOOK_SECRET`
- fund the Polymarket wallet with the required assets for your strategy
- confirm `POLYMARKET_PRIVATE_KEY` and `POLYMARKET_FUNDER` match the same wallet
- restrict shell access to the VPS
- back up the private key outside the server

## First Boot In Safe Mode

- start with `DRY_RUN=true`
- verify `/health` and `/status`
- test the main webhook endpoint using `examples/enter.json`
- test `POST /webhooks/tradingview/{secret}/close-loss`
- test `POST /webhooks/tradingview/{secret}/close-win`
- confirm state updates in SQLite and logs

## Before Enabling Live Trading

- switch to `DRY_RUN=false`
- recheck all production `.env` values
- verify the wallet has enough balance for the full progression worst case
- verify your alert payloads include the correct `token_id`
- verify `condition_id` is present for live order posting
- confirm reverse proxy TLS is working and TradingView can reach the webhook URL
- make sure only one instance of the bot is running

## Operational Controls

- enable auto-restart with `systemd` or `supervisor`
- monitor disk usage for logs
- rotate logs or keep the included rotating file logger enabled
- back up `bot_state.db`
- monitor VPS clock drift and keep NTP enabled
- document a manual stop procedure before touching the wallet or upgrading the server

## Recommended Go-Live Sequence

1. run dry-run tests on the VPS
2. send a single very small live trade
3. confirm entry and exit behavior
4. confirm progression reset after a win
5. confirm progression advance after a loss
6. only then raise the base trade amount
