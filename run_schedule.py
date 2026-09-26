"""Create an immutable local work item for a nightly, daily, weekly or quarterly review."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from finance import ROOT, RUNS, calculate

parser = argparse.ArgumentParser()
parser.add_argument("--cadence", choices=["nightly", "daily", "weekly", "quarterly"], required=True)
parser.add_argument("--as-of", default=date.today().isoformat())
parser.add_argument("--with-hermes", action="store_true")
parser.add_argument("--retry-model", action="store_true", help="Retry model generation for an existing unchanged work item")
parser.add_argument("--profile", default="ambient-finance-demo")
args = parser.parse_args()

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
else:
    result = calculate(args.as_of, args.cadence)
    result["run_id"] = run_id
    result["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    result["review_decision"] = "pending"
    result["model_status"] = "not_requested"
if args.with_hermes and result["status"] == "review_required":
    prompt = (f"Review the latest {args.cadence} fictional finance run {run_id}. "
              "Call finance_latest_run and finance_position for any issuer you discuss. "
              "Describe the largest exposure, both assumed scenarios and the stale research item. "
              "Cite exact IDs. Prepare a draft for a human portfolio manager. Do not propose an order or claim a trade was placed.")
    command = ["hermes", "--profile", args.profile, "chat", "--oneshot", "-Q", "--run-budget", "300", "-q", prompt]
    # Save the deterministic report first, so the tool can read it during the agent run.
    out.write_text(json.dumps(result, indent=2) + "\n")
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=360, env=os.environ.copy())
        result["model_status"] = "completed" if proc.returncode == 0 else "failed"
        result["model_analysis"] = proc.stdout.strip() if proc.returncode == 0 else None
        result["model_exit_code"] = proc.returncode
        result.pop("model_error", None)
        # Store diagnostics locally. Do not present a failed response as a verified analysis.
        (RUNS / f"{run_id}.hermes.log").write_text(proc.stderr)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        result["model_status"] = "failed"
        result["model_error"] = type(exc).__name__
else:
    result["model_status"] = "skipped_data_gate" if args.with_hermes else "not_requested"
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"run_id": run_id, "status": result["status"], "model_status": result["model_status"], "issues": result["issues"], "path": str(out)}))
