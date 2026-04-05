# Nginx Reverse Proxy

Use the sample config in `deploy/nginx/tv-polymarket-bot.conf` as the production reverse proxy template.

## Expected Topology

- `nginx` listens on `80/443`
- the bot listens on `127.0.0.1:8000`
- TradingView sends webhooks to:

```text
https://your-domain.com/webhooks/tradingview/<WEBHOOK_SECRET>
```

## Deploy Steps

1. Copy `deploy/nginx/tv-polymarket-bot.conf` to `/etc/nginx/sites-available/tv-polymarket-bot.conf`
2. Replace:
   - `your-domain.com`
   - certificate paths if needed
3. Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/tv-polymarket-bot.conf /etc/nginx/sites-enabled/tv-polymarket-bot.conf
```

4. Test configuration:

```bash
sudo nginx -t
```

5. Reload nginx:

```bash
sudo systemctl reload nginx
```

## Notes

- Keep the bot bound to localhost and let nginx handle public access.
- If you use Cloudflare or another proxy, make sure HTTPS termination and forwarded headers match your setup.
- The webhook path does not need any special nginx rewrite rules; it is proxied as-is.
