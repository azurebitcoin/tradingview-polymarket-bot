"""Run an in-process dry-run smoke test against the FastAPI app."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def main() -> None:
    """Boot the app in dry-run mode and exercise health/status/entry/exit."""

    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))
    os.environ["WEBHOOK_SECRET"] = "local-test-secret"
    os.environ["DRY_RUN"] = "true"
    os.environ["INITIAL_BALANCE"] = "1000"
    os.environ["BASE_TRADE_AMOUNT"] = "50"
    os.environ["DATABASE_PATH"] = ":memory:"
    os.environ["LOG_FILE_PATH"] = ""

    from main import build_app

    app = build_app()
    client = TestClient(app)

    enter_payload = json.loads((project_root / "examples" / "enter.json").read_text())
    exit_payload = json.loads((project_root / "examples" / "exit.json").read_text())

    health = client.get("/health")
    status_before = client.get("/status")
    enter = client.post("/webhooks/tradingview/local-test-secret", json=enter_payload)
    status_open = client.get("/status")
    exit_trade = client.post("/webhooks/tradingview/local-test-secret", json=exit_payload)
    status_after = client.get("/status")

    summary = {
        "health": health.json(),
        "status_before": status_before.json(),
        "enter": enter.json(),
        "status_open": status_open.json(),
        "exit": exit_trade.json(),
        "status_after": status_after.json(),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
