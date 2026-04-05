# Cloudflare Worker Proxy

This Worker gives you a public Cloudflare endpoint for TradingView and forwards requests to your VPS-hosted bot.

## What It Does

- exposes a public `workers.dev` webhook URL
- keeps the public edge secret different from the private origin secret
- forwards `POST /webhooks/tradingview/<EDGE_WEBHOOK_SECRET>` to your backend as `POST /webhooks/tradingview/<ORIGIN_WEBHOOK_SECRET>`
- also proxies `GET /health` and `GET /status`
- logs structured request metadata through Cloudflare observability

## Files

- `cloudflare-worker/src/index.js`
- `cloudflare-worker/wrangler.jsonc`
- `cloudflare-worker/.dev.vars.example`
- `cloudflare-worker/package.json`

## Required Configuration

Set the origin URL in `cloudflare-worker/wrangler.jsonc`:

```json
"vars": {
  "ORIGIN_BASE_URL": "https://your-vps-domain.example.com"
}
```

Set the two secrets with Wrangler:

```bash
cd cloudflare-worker
wrangler secret put EDGE_WEBHOOK_SECRET
wrangler secret put ORIGIN_WEBHOOK_SECRET
```

Recommended secret split:

- `EDGE_WEBHOOK_SECRET`: the secret visible in the public TradingView webhook URL
- `ORIGIN_WEBHOOK_SECRET`: the secret used only on your VPS backend

## Local Development

```bash
cd cloudflare-worker
cp .dev.vars.example .dev.vars
npm install
npm run dev
```

## Deploy

```bash
cd cloudflare-worker
npm install
npm run deploy
```

## Example Public Webhook URL

```text
https://grant-browser-online.grant-browser-hub-a80397.workers.dev/webhooks/tradingview/<EDGE_WEBHOOK_SECRET>
```

## Recommended Origin URL

Use a VPS URL that is not your public TradingView URL, for example:

```text
https://bot-origin.yourdomain.com
```

Then the Worker forwards:

```text
Public:
https://grant-browser-online.grant-browser-hub-a80397.workers.dev/webhooks/tradingview/<EDGE_WEBHOOK_SECRET>

Origin:
https://bot-origin.yourdomain.com/webhooks/tradingview/<ORIGIN_WEBHOOK_SECRET>
```

## Notes

- `workers.dev` is suitable as the public edge endpoint
- for direct VPS TLS termination, keep a separate custom origin domain on the server
- the Worker streams the incoming request body directly to the origin instead of buffering it into memory
