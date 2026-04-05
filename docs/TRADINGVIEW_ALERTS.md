# TradingView Alert Format

## URL

```text
https://your-domain.com/webhooks/tradingview/<WEBHOOK_SECRET>
```

## ENTER Alert Example

```json
{
  "action": "ENTER",
  "alert_id": "signal-enter-001",
  "market_slug": "will-bitcoin-be-above-100k-on-june-30",
  "tv_symbol": "BTCUSD",
  "condition_id": "0x_condition_id_here",
  "token_id": "0x_token_id_here",
  "outcome": "YES",
  "max_price": 0.63,
  "note": "Breakout entry"
}
```

## EXIT Alert Example

```json
{
  "action": "EXIT",
  "alert_id": "signal-exit-001",
  "token_id": "0x_token_id_here",
  "min_price": 0.58,
  "note": "Target or stop exit"
}
```

## Required Fields

- `action`
- `token_id`

## Strongly Recommended For Live Mode

- `condition_id`
- `alert_id`
- `market_slug`
- `outcome`

`condition_id` matters because the Polymarket SDK quickstart fetches `minimum_tick_size` and `neg_risk` from the market before posting orders.

## Practical Notes

- TradingView webhooks should target port `80` or `443`
- Do not put wallet secrets or private keys inside the alert body
- If your endpoint is too slow, TradingView may drop the request

Reference:
- https://www.tradingview.com/support/folders/43000560150/
