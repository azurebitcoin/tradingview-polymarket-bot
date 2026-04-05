#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${APP_NAME:-tv-polymarket-bot}"
APP_USER="${APP_USER:-botuser}"
APP_GROUP="${APP_GROUP:-$APP_USER}"
APP_DIR="${APP_DIR:-/opt/tradingview-polymarket-bot}"
DOMAIN="${DOMAIN:-}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this script as root or with sudo." >&2
    exit 1
  fi
}

install_packages() {
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y \
    git \
    rsync \
    nginx \
    certbot \
    python3-certbot-nginx \
    python3 \
    python3-venv
}

ensure_user() {
  if ! id -u "$APP_USER" >/dev/null 2>&1; then
    useradd --system --create-home --home-dir "/home/$APP_USER" --shell /bin/bash "$APP_USER"
  fi
}

sync_project() {
  mkdir -p "$APP_DIR"
  rsync -a --delete \
    --exclude ".git" \
    --exclude ".venv" \
    --exclude "__pycache__" \
    --exclude "*.pyc" \
    --exclude "logs" \
    --exclude "bot_state.db" \
    "$REPO_ROOT"/ "$APP_DIR"/
  mkdir -p "$APP_DIR/logs"
}

setup_python() {
  "$PYTHON_BIN" -m venv "$APP_DIR/.venv"
  "$APP_DIR/.venv/bin/pip" install --upgrade pip
  "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
}

prepare_env() {
  if [[ ! -f "$APP_DIR/.env" ]]; then
    cp "$APP_DIR/.env.production.example" "$APP_DIR/.env"
    echo "Created $APP_DIR/.env from .env.production.example"
    echo "Edit it before enabling live trading." >&2
  fi
}

install_systemd_unit() {
  sed \
    -e "s|/opt/tradingview-polymarket-bot|$APP_DIR|g" \
    -e "s|User=botuser|User=$APP_USER|g" \
    -e "s|Group=botuser|Group=$APP_GROUP|g" \
    "$APP_DIR/deploy/systemd/tv-polymarket-bot.service" \
    > "/etc/systemd/system/$APP_NAME.service"

  systemctl daemon-reload
  systemctl enable "$APP_NAME"
}

write_nginx_http_config() {
  if [[ -z "$DOMAIN" ]]; then
    return
  fi

  cat > "/etc/nginx/sites-available/$APP_NAME.conf" <<EOF
upstream ${APP_NAME}_upstream {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    client_max_body_size 256k;

    access_log /var/log/nginx/$APP_NAME.access.log;
    error_log /var/log/nginx/$APP_NAME.error.log warn;

    location / {
        proxy_pass http://${APP_NAME}_upstream;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_read_timeout 15s;
        proxy_connect_timeout 5s;
        proxy_send_timeout 15s;
    }
}
EOF

  ln -sf "/etc/nginx/sites-available/$APP_NAME.conf" "/etc/nginx/sites-enabled/$APP_NAME.conf"
  rm -f /etc/nginx/sites-enabled/default
  nginx -t
  systemctl reload nginx
}

enable_https() {
  if [[ -z "$DOMAIN" || -z "$CERTBOT_EMAIL" ]]; then
    echo "Skipping certbot because DOMAIN or CERTBOT_EMAIL is empty."
    return
  fi

  certbot --nginx \
    --non-interactive \
    --agree-tos \
    --redirect \
    -m "$CERTBOT_EMAIL" \
    -d "$DOMAIN"
}

finalize_permissions() {
  chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"
}

start_services() {
  systemctl restart "$APP_NAME"
  systemctl status "$APP_NAME" --no-pager || true
  systemctl enable nginx
  systemctl restart nginx
}

print_summary() {
  echo
  echo "Install complete."
  echo "App dir: $APP_DIR"
  echo "Systemd service: $APP_NAME.service"
  if [[ -n "$DOMAIN" ]]; then
    echo "Health URL: https://$DOMAIN/health"
    echo "Webhook URL: https://$DOMAIN/webhooks/tradingview/<WEBHOOK_SECRET>"
  else
    echo "Health URL: http://<server-ip>/health"
    echo "Webhook URL: http://<server-ip>/webhooks/tradingview/<WEBHOOK_SECRET>"
  fi
  echo "Edit $APP_DIR/.env before using live trading."
}

require_root
install_packages
ensure_user
sync_project
setup_python
prepare_env
install_systemd_unit
write_nginx_http_config
enable_https
finalize_permissions
start_services
print_summary
