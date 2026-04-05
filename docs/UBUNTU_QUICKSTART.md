# Ubuntu VPS Quickstart

These steps assume:

- Ubuntu 22.04+ or 24.04
- a DNS record already points to your VPS
- you have this project locally and can upload or clone it onto the server

## Copy-Paste Deployment Steps

```bash
sudo apt-get update && sudo apt-get install -y git
sudo mkdir -p /opt
cd /opt
sudo git clone https://github.com/azurebitcoin/tradingview-polymarket-bot tradingview-polymarket-bot
cd /opt/tradingview-polymarket-bot
sudo cp .env.production.example .env
sudo nano .env
sudo DOMAIN=your-domain.com CERTBOT_EMAIL=you@example.com bash deploy/ubuntu/install_ubuntu_vps.sh
```

## After The Script Finishes

Check service status:

```bash
sudo systemctl status tv-polymarket-bot --no-pager
```

Check nginx:

```bash
sudo nginx -t
```

Check health:

```bash
curl https://your-domain.com/health
```

Webhook URL:

```text
https://your-domain.com/webhooks/tradingview/<WEBHOOK_SECRET>
```

## Safe Go-Live Sequence

1. keep `DRY_RUN=true` in `.env`
2. test `/health`
3. test `/status`
4. send a dry-run `ENTER`
5. send `close-loss`
6. send another `ENTER`
7. send `close-win`
8. only after that change to `DRY_RUN=false`

## Notes

- the install script creates `.venv`, installs requirements, registers `systemd`, enables nginx, and attempts HTTPS if `DOMAIN` and `CERTBOT_EMAIL` are provided
- if you rerun the script after editing code locally, it resyncs the repository into `/opt/tradingview-polymarket-bot`

## Safe Redeploy After New Pushes

```bash
cd /opt/tradingview-polymarket-bot
sudo bash deploy/ubuntu/update.sh
```

This script:

- requires a clean git worktree
- runs `git pull --ff-only`
- refreshes dependencies
- restarts the bot service
- tests and reloads nginx
