"""Create a small publishable evidence bundle from the local fictional run."""
import json
from pathlib import Path

from finance import ROOT, RUNS

run_id = "2026-09-25-daily"
run = json.loads((RUNS / f"{run_id}.json").read_text())
evaluation = json.loads((RUNS / f"{run_id}.eval.json").read_text())
trace = json.loads((RUNS / f"{run_id}.mlflow.json").read_text())
out = ROOT / "evidence"
out.mkdir(exist_ok=True)
public_run = {key: value for key, value in run.items() if key not in ("model_exchange_path", "model_analysis")}
(out / "daily-run.json").write_text(json.dumps(public_run, indent=2) + "\n")
(out / "captured-model-draft.md").write_text("# Captured Bonsai draft\n\nThe model returned this text through the local proxy after Hermes called its finance tools. The Hermes CLI later timed out, so this file is evidence of a model final response, not a successful CLI return.\n\n" + run["model_analysis"].strip() + "\n")
(out / "evaluation.json").write_text(json.dumps(evaluation, indent=2) + "\n")
(out / "mlflow-trace.json").write_text(json.dumps(trace, indent=2) + "\n")
print(out)
