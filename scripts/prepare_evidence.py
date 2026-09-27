"""Create a small publishable evidence bundle from a local fictional run."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
import json

from finance import ROOT, RUNS

parser = argparse.ArgumentParser()
parser.add_argument("run_id")
args = parser.parse_args()
run_id = args.run_id
run = json.loads((RUNS / f"{run_id}.json").read_text())
evaluation = json.loads((RUNS / f"{run_id}.eval.json").read_text())
trace = json.loads((RUNS / f"{run_id}.mlflow.json").read_text())
out = ROOT / "evidence"
out.mkdir(exist_ok=True)
public_run = {key: value for key, value in run.items() if key not in ("model_exchange_path", "model_analysis")}
prefix = run_id.rsplit("-", 1)[-1]
(out / f"{prefix}-run.json").write_text(json.dumps(public_run, indent=2) + "\n")
status = ("Hermes exited with code zero after the model response."
          if run.get("model_status") == "completed" and run.get("model_exit_code") == 0
          else "The model response was captured, but Hermes did not exit successfully.")
(out / f"{prefix}-model-draft.md").write_text("# Captured Bonsai draft\n\nThe model returned this text through the local proxy after Hermes called its finance tools. " + status + " The inputs are fictional and human portfolio review remains required.\n\n" + run["model_analysis"].strip() + "\n")
(out / f"{prefix}-evaluation.json").write_text(json.dumps(evaluation, indent=2) + "\n")
(out / f"{prefix}-mlflow-trace.json").write_text(json.dumps(trace, indent=2) + "\n")
print(out)
