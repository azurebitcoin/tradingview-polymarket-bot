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
  "ORIGIN_BASE_URL": "https://azurebitcoin.info"
}
```

Set the two secrets with Wrangler:

```bash
cd cloudflare-worker
wrangler secret put EDGE_WEBHOOK_SECRET
wrangler secret put ORIGIN_WEBHOOK_SECRET
```

Ready commands with placeholders:

```bash
cd cloudflare-worker
printf '%s' 'replace-with-public-edge-secret' | wrangler secret put EDGE_WEBHOOK_SECRET
printf '%s' 'replace-with-private-origin-secret' | wrangler secret put ORIGIN_WEBHOOK_SECRET
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

Configured origin URL in this repo:

```text
https://azurebitcoin.info
```

Then the Worker forwards:

```text
Public:
https://grant-browser-online.grant-browser-hub-a80397.workers.dev/webhooks/tradingview/<EDGE_WEBHOOK_SECRET>

Origin:
https://azurebitcoin.info/webhooks/tradingview/<ORIGIN_WEBHOOK_SECRET>
```

## Notes

- `workers.dev` is suitable as the public edge endpoint
- for direct VPS TLS termination, keep a separate custom origin domain on the server
- the Worker streams the incoming request body directly to the origin instead of buffering it into memory
- make sure `https://azurebitcoin.info` resolves to your VPS backend and does not route back into the same Worker, otherwise you will create a proxy loop

## End-to-End Launch Checklist

1. Confirm the backend is reachable directly:

```bash
curl https://azurebitcoin.info/health
curl https://azurebitcoin.info/status
```

2. Make sure the bot `.env` on the VPS contains the private origin webhook secret in the backend route you plan to protect.

3. Install Worker dependencies:

```bash
cd cloudflare-worker
npm install
```

4. Set Worker secrets:

```bash
printf '%s' 'replace-with-public-edge-secret' | wrangler secret put EDGE_WEBHOOK_SECRET
printf '%s' 'replace-with-private-origin-secret' | wrangler secret put ORIGIN_WEBHOOK_SECRET
```

5. Deploy the Worker:

```bash
npm run deploy
```

6. Check the public edge URL:

```bash
curl https://grant-browser-online.grant-browser-hub-a80397.workers.dev/health
curl https://grant-browser-online.grant-browser-hub-a80397.workers.dev/status
```

7. Build the TradingView webhook URL:

```text
https://grant-browser-online.grant-browser-hub-a80397.workers.dev/webhooks/tradingview/<EDGE_WEBHOOK_SECRET>
```

8. In dry-run mode, send a manual test payload through the Worker:

```bash
curl -X POST \
  "https://grant-browser-online.grant-browser-hub-a80397.workers.dev/webhooks/tradingview/<EDGE_WEBHOOK_SECRET>" \
  -H "Content-Type: application/json" \
  --data @../examples/enter.json
```

9. If you want to force-close a dry-run trade for testing:

```bash
curl -X POST \
  "https://grant-browser-online.grant-browser-hub-a80397.workers.dev/webhooks/tradingview/<EDGE_WEBHOOK_SECRET>/close-loss"
```

```bash
curl -X POST \
  "https://grant-browser-online.grant-browser-hub-a80397.workers.dev/webhooks/tradingview/<EDGE_WEBHOOK_SECRET>/close-win"
```

10. Only after webhook delivery, bot logging, and dry-run state transitions are correct, switch the backend from `DRY_RUN=true` to `DRY_RUN=false`.
