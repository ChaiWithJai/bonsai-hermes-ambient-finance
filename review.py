"""Record human review of a draft. Never authorizes a trade."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from finance import RUNS, acceptance_requirements

parser = argparse.ArgumentParser()
parser.add_argument("run_id")
parser.add_argument("--reviewer", required=True)
parser.add_argument("--decision", choices=["accept_analysis", "reject_analysis"], required=True)
parser.add_argument("--note", required=True)
args = parser.parse_args()
if not args.reviewer.strip() or not args.note.strip():
    raise SystemExit("Reviewer and note must contain text.")
path = RUNS / f"{args.run_id}.json"
if not path.is_file():
    raise SystemExit("Unknown run ID")
run = json.loads(path.read_text())
requirements = acceptance_requirements(run)
if args.decision == "accept_analysis" and not requirements["can_accept_analysis"]:
    raise SystemExit(" ".join(requirements["reasons"]))
review_file = RUNS / f"{args.run_id}.reviews.jsonl"
record = {"run_id": args.run_id, "reviewer_entered_name": args.reviewer.strip(), "decision": args.decision, "note": args.note.strip(), "at_utc": datetime.now(timezone.utc).isoformat(), "trade_authorized": False, "identity_verified": False}
with review_file.open("a") as file:
    file.write(json.dumps(record) + "\n")
print(json.dumps(record))
