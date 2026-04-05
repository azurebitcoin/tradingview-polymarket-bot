# Runbook

## Local Dry Run

1. Copy `.env.example` to `.env`
2. Keep `DRY_RUN=true`
3. Set `WEBHOOK_SECRET`
4. Start the server:

```powershell
python main.py
```

5. Health check:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/health
```

6. Status check:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/status
```

7. Send an entry alert:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/webhooks/tradingview/<WEBHOOK_SECRET> `
  -ContentType "application/json" `
  -InFile .\examples\enter.json
```

8. Send an exit alert:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/webhooks/tradingview/<WEBHOOK_SECRET> `
  -ContentType "application/json" `
  -InFile .\examples\exit.json
```

Optional dry-run helper to force a loss after opening a trade:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/webhooks/tradingview/<WEBHOOK_SECRET>/close-loss
```

Optional dry-run helper to force a win after opening a trade:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/webhooks/tradingview/<WEBHOOK_SECRET>/close-win
```

Optional winning dry-run pair:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/webhooks/tradingview/<WEBHOOK_SECRET> `
  -ContentType "application/json" `
  -InFile .\examples\win-enter.json
```

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/webhooks/tradingview/<WEBHOOK_SECRET> `
  -ContentType "application/json" `
  -InFile .\examples\win-exit.json
```

If you want to validate the API flow without keeping a local server running, use:

```powershell
python .\scripts\dry_run_smoke_test.py
```

## Docker

```powershell
docker compose up --build -d
```

## Windows Launch Scripts

PowerShell:

```powershell
.\deploy\windows\start-dry-run.ps1
.\deploy\windows\start-live.ps1
```

Batch:

```bat
.\deploy\windows\start-dry-run.bat
.\deploy\windows\start-live.bat
```

## systemd

1. Copy the repo to `/opt/tradingview-polymarket-bot`
2. Create the virtualenv and install requirements
3. Copy `deploy/systemd/tv-polymarket-bot.service` to `/etc/systemd/system/`
4. Run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tv-polymarket-bot
sudo systemctl start tv-polymarket-bot
```

## Supervisor

1. Copy `deploy/supervisor/tv-polymarket-bot.conf` to `/etc/supervisor/conf.d/`
2. Run:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl status tv-polymarket-bot
```

## Production Environment Template

Use `.env.production.example` as the base for VPS deployment.

## Nginx Reverse Proxy

Use `deploy/nginx/tv-polymarket-bot.conf` as the production nginx template.

## Ubuntu One-Command Install

Use `deploy/ubuntu/install_ubuntu_vps.sh` for the VPS bootstrap path.
See `docs/UBUNTU_QUICKSTART.md` for the copy-paste sequence.

## Safe VPS Update

For a fast redeploy on Ubuntu after new code is pushed:

```bash
cd /opt/tradingview-polymarket-bot
sudo bash deploy/ubuntu/update.sh
```

Behavior:

- aborts if the working tree is dirty
- fetches and fast-forwards from `origin/main`
- refreshes Python dependencies inside `.venv`
- restarts `tv-polymarket-bot`
- validates and reloads nginx
