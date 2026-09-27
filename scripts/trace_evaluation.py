"""Record a real MLflow trace of the deterministic review of a captured model draft."""
import sys
import argparse
import json
import os
from pathlib import Path

import mlflow
from mlflow.entities import SpanType

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluate_analysis import evaluate
from finance import RUNS

parser = argparse.ArgumentParser()
parser.add_argument("run_id")
args = parser.parse_args()
mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5210"))
mlflow.set_experiment("ambient-finance-demo")


@mlflow.trace(name="evaluate_captured_finance_draft", span_type=SpanType.CHAIN)
def traced_review(run_id: str) -> dict:
    run = json.loads((RUNS / f"{run_id}.json").read_text())
    return evaluate(run)


result = traced_review(args.run_id)
trace_id = mlflow.get_last_active_trace_id()
observed = mlflow.get_trace(trace_id, flush=True)
record = {"run_id": args.run_id, "trace_id": trace_id, "experiment_id": observed.info.experiment_id, "trace_status": observed.info.status.value, "passed": result["passed"], "check_count": len(result["checks"]), "scope": "Offline checks on the captured model draft and recorded CLI exit. This trace is not an online model trace or investment-quality evaluation."}
(RUNS / f"{args.run_id}.mlflow.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record))
