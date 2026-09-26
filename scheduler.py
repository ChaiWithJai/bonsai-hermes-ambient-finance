"""Local schedule driver. Run under launchd or another process supervisor."""
from __future__ import annotations

import argparse
import json
import urllib.request

from finance import RUNS, calculate
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
TZ = ZoneInfo("America/New_York")


def first_business_day_of_quarter(day) -> bool:
    if day.month not in (1, 4, 7, 10):
        return False
    first = day.replace(day=1)
    while first.weekday() >= 5:
        first += timedelta(days=1)
    return day == first


def due(now: datetime) -> list[str]:
    local = now.astimezone(TZ)
    day = local.date()
    hour = local.hour
    # Each cadence can run once per day. run_schedule enforces idempotency.
    result = []
    if hour >= 22:
        result.append("nightly")
    if hour >= 7:
        result.append("daily")
    if day.weekday() == 0 and hour >= 8:
        result.append("weekly")
    if first_business_day_of_quarter(day) and hour >= 9:
        result.append("quarterly")
    return result


def model_ready() -> bool:
    """Check the configured proxy and model without issuing an inference request."""
    config = json.loads((ROOT / "config/hermes-config.json").read_text())["model"]
    try:
        with urllib.request.urlopen(config["base_url"].rstrip("/") + "/models", timeout=5) as response:
            models = json.load(response).get("data", [])
        return any(item.get("id") == config["default"] for item in models)
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def tick(now: datetime, dry_run: bool = False) -> list[dict]:
    local = now.astimezone(TZ)
    output = []
    for cadence in due(now):
        run_id = f"{local.date().isoformat()}-{cadence}"
        path = RUNS / f"{run_id}.json"
        if path.exists():
            output.append({"cadence": cadence, "status": "already_recorded"})
            continue
        if dry_run:
            output.append({"cadence": cadence, "status": "would_run"})
            continue
        report = calculate(local.date().isoformat(), cadence)
        if report["status"] == "review_required" and not model_ready():
            output.append({"cadence": cadence, "status": "waiting_for_model"})
            continue
        result = subprocess.run([sys.executable, str(ROOT / "run_schedule.py"), "--cadence", cadence, "--as-of", local.date().isoformat(), "--with-hermes"], capture_output=True, text=True)
        output.append({"cadence": cadence, "status": "recorded" if result.returncode == 0 else "failed", "detail": result.stdout.strip() if result.returncode == 0 else result.stderr.strip()})
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--now", help="ISO timestamp, for testing only")
    args = parser.parse_args()
    if args.now and not args.dry_run:
        raise SystemExit("--now requires --dry-run, so a historical test cannot create a scheduled run.")
    while True:
        now = datetime.fromisoformat(args.now) if args.now else datetime.now(TZ)
        for item in tick(now, args.dry_run):
            print(item, flush=True)
        if args.once:
            break
        time.sleep(60)
