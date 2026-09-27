"""Create an immutable local work item for a nightly, daily, weekly or quarterly review."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import sqlite3
import time
from datetime import date, datetime, timezone
from pathlib import Path

from finance import ROOT, RUNS, calculate
from lib.hermes_result import cursor, final_answer

parser = argparse.ArgumentParser()
parser.add_argument("--cadence", choices=["nightly", "daily", "weekly", "quarterly"], required=True)
parser.add_argument("--as-of", default=date.today().isoformat())
parser.add_argument("--with-hermes", action="store_true")
parser.add_argument("--retry-model", action="store_true", help="Retry model generation for an existing unchanged work item")
parser.add_argument("--profile", default="ambient-finance-demo")
parser.add_argument("--session-db", type=Path, help="Hermes state.db path when using a nonstandard profile location")
parser.add_argument("--model-timeout", type=int, default=660, help="Whole Hermes process timeout, including startup (seconds)")
args = parser.parse_args()
if args.model_timeout < 60:
    parser.error("--model-timeout must be at least 60 seconds")

RUNS.mkdir(parents=True, exist_ok=True)
run_id = f"{args.as_of}-{args.cadence}"
out = RUNS / f"{run_id}.json"
if out.exists() and not args.retry_model:
    raise SystemExit(f"Run already exists: {out}. A scheduled retry will not overwrite its evidence.")
if args.retry_model:
    if not out.exists() or not args.with_hermes:
        raise SystemExit("Retry requires an existing run and --with-hermes")
    result = json.loads(out.read_text())
    current = calculate(args.as_of, args.cadence)
    if current["source_sha256"] != result["source_sha256"] or current["total_value_usd"] != result["total_value_usd"]:
        raise SystemExit("Source inputs changed. Create a new dated work item instead of changing this run.")
    if result["model_status"] == "completed":
        raise SystemExit("Model analysis already completed for this work item")
    attempts = RUNS / "attempts"
    attempts.mkdir(exist_ok=True)
    snapshot = attempts / f"{run_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json"
    snapshot.write_text(json.dumps(result, indent=2) + "\n")
    # A retry must not let the model read its previous draft or obsolete status.
    for key in ("model_analysis", "model_error", "model_exit_code", "model_elapsed_seconds", "model_exchange_path"):
        result.pop(key, None)
    result["model_analysis"] = None
    result["model_status"] = "pending"
else:
    result = calculate(args.as_of, args.cadence)
    result["run_id"] = run_id
    result["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    result["review_decision"] = "pending"
    result["model_status"] = "not_requested"
if args.with_hermes and result["status"] == "review_required":
    prompt = (f"Review finance work item {run_id}. "
              f"Call finance_latest_run with run_id={run_id}, then finance_position for the largest exposure and the stale-research position. "
              "Explain those two positions, both assumed scenarios, and the research the team needs before it can finish the review. "
              "When the tool says source issues prevent acceptance, ask who will obtain the named research updates and when. Keep acceptance unavailable until those issues are resolved. "
              "Write for the portfolio manager: describe the decision in ordinary sentences without quoting JSON keys or boolean values. "
              "Cite exact IDs. Write a draft of at most 250 words for a human portfolio manager. "
              "Do not discuss prior model attempts, propose an order, or claim a trade was placed.")
    run_budget = max(30, args.model_timeout - 60)
    command = ["hermes", "--profile", args.profile, "chat", "--oneshot", "-Q", "--run-budget", str(run_budget), "-q", prompt]
    # Save the deterministic report first, so the tool can read it during the agent run.
    out.write_text(json.dumps(result, indent=2) + "\n")
    session_db = args.session_db or Path.home() / ".hermes" / "profiles" / args.profile / "state.db"
    before_message = cursor(session_db)
    started = time.monotonic()
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=args.model_timeout, env=os.environ.copy())
        result["model_status"] = "completed" if proc.returncode == 0 else "failed"
        result["model_analysis"] = None
        result["model_exit_code"] = proc.returncode
        result.pop("model_error", None)
        (RUNS / f"{run_id}.hermes.stdout.log").write_text(proc.stdout)
        if proc.returncode == 0:
            try:
                session_id, answer = final_answer(session_db, before_message, prompt)
                result["model_session_id"] = session_id
                result["model_analysis"] = answer
            except (ValueError, sqlite3.Error) as error:
                result["model_status"] = "failed"
                result["model_error"] = str(error)
        # Store diagnostics locally. Do not present a failed response as a verified analysis.
        (RUNS / f"{run_id}.hermes.log").write_text(proc.stderr)
    except subprocess.TimeoutExpired as exc:
        result["model_status"] = "failed"
        result["model_error"] = type(exc).__name__
        (RUNS / f"{run_id}.hermes.log").write_bytes(exc.stderr or b"")
    except FileNotFoundError as exc:
        result["model_status"] = "failed"
        result["model_error"] = type(exc).__name__
    result["model_elapsed_seconds"] = round(time.monotonic() - started, 1)
else:
    result["model_status"] = "skipped_data_gate" if args.with_hermes else "not_requested"
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"run_id": run_id, "status": result["status"], "model_status": result["model_status"], "issues": result["issues"], "path": str(out)}))
