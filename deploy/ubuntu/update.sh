#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${APP_NAME:-tv-polymarket-bot}"
APP_USER="${APP_USER:-botuser}"
APP_GROUP="${APP_GROUP:-$APP_USER}"
APP_DIR="${APP_DIR:-/opt/tradingview-polymarket-bot}"
BRANCH="${BRANCH:-main}"
REMOTE_NAME="${REMOTE_NAME:-origin}"
RELOAD_NGINX="${RELOAD_NGINX:-true}"

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this script as root or with sudo." >&2
    exit 1
  fi
}

require_repo() {
  if [[ ! -d "$APP_DIR/.git" ]]; then
    echo "Expected a git repository at $APP_DIR" >&2
    exit 1
  fi
}

ensure_clean_worktree() {
  if [[ -n "$(git -C "$APP_DIR" status --porcelain)" ]]; then
    echo "Working tree is not clean. Commit or discard local changes before redeploy." >&2
    exit 1
  fi
}

update_code() {
  git -C "$APP_DIR" fetch "$REMOTE_NAME"
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" pull --ff-only "$REMOTE_NAME" "$BRANCH"
}

install_dependencies() {
  "$APP_DIR/.venv/bin/pip" install --upgrade pip
  "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
}

fix_permissions() {
  chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"
}

restart_service() {
  systemctl daemon-reload
  systemctl restart "$APP_NAME"
  systemctl status "$APP_NAME" --no-pager
}

reload_nginx_if_requested() {
  if [[ "$RELOAD_NGINX" != "true" ]]; then
    return
  fi

  if command -v nginx >/dev/null 2>&1; then
    nginx -t
    systemctl reload nginx
  fi
}

print_summary() {
  echo
  echo "Redeploy complete."
  echo "App dir: $APP_DIR"
  echo "Branch: $BRANCH"
  echo "Service: $APP_NAME"
}

require_root
require_repo
ensure_clean_worktree
update_code
install_dependencies
fix_permissions
restart_service
reload_nginx_if_requested
print_summary
