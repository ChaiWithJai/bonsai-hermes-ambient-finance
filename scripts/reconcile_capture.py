"""Preserve a model final answer when Hermes timed out after its model call.

This records an observed model response, not a successful Hermes CLI return.
"""
import sys
import argparse
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finance import ROOT, RUNS

parser = argparse.ArgumentParser()
parser.add_argument("run_id")
args = parser.parse_args()
path = RUNS / f"{args.run_id}.json"
run = json.loads(path.read_text())
if run.get("model_status") != "failed" or run.get("model_error") != "TimeoutExpired":
    raise SystemExit("Only a CLI timeout can be reconciled from captured model output")
matches = []
for exchange in (ROOT / "exchanges").glob("*.json"):
    record = json.loads(exchange.read_text())
    if args.run_id not in json.dumps(record.get("request", {})):
        continue
    if record.get("http_status") != 200:
        continue
    choice = record.get("response", {}).get("choices", [{}])[0]
    message = choice.get("message", {})
    content = message.get("content") or ""
    if choice.get("finish_reason") != "stop" or not content.strip() or message.get("tool_calls"):
        continue
    matches.append((exchange.stat().st_mtime, exchange, content))
if not matches:
    raise SystemExit("No completed final model response found in raw exchanges")
matches.sort()
_, exchange, content = matches[-1]
if args.run_id not in content:
    raise SystemExit("Final model response did not identify the requested run")
run["model_analysis"] = content
run["model_status"] = "model_final_observed_cli_timeout"
run["model_exchange_path"] = str(exchange.relative_to(ROOT))
path.write_text(json.dumps(run, indent=2) + "\n")
print(json.dumps({"run_id": args.run_id, "model_status": run["model_status"], "exchange": run["model_exchange_path"]}))
