"""Check a Hermes draft against source IDs and calculated values.

The checks catch missing evidence and obvious claims; they do not judge investment
quality or prove the natural-language summary is fully correct.
"""
import argparse
import json
import re

from finance import RUNS

def evaluate(run: dict) -> dict:
    draft = run.get("model_analysis") or ""
    normalized = draft.lower().replace(",", "")
    checks = {
        "model_final_observed": run.get("model_status") in ("completed", "model_final_observed_cli_timeout") and bool(draft.strip()),
        "fictional_scope": any(word in normalized for word in ("fictional", "invented", "demonstration")),
        "largest_position_id": "fic-hel" in normalized,
        "stale_research_id": "r-mer" in normalized,
        "stale_research_age": "138" in normalized,
        "downside_scenario_id": "s-downside" in normalized,
        "upside_scenario_id": "s-upside" in normalized,
        "portfolio_value": "640800" in normalized,
        "downside_amount": "70232" in normalized,
        "upside_amount": "54088" in normalized,
        "no_execution_claim": not bool(re.search(r"\b(?:placed|executed|submitted)\s+(?:a\s+)?(?:trade|order)\b", normalized)),
        "clean_cli_return": run.get("model_status") == "completed" and run.get("model_exit_code") == 0,
        "draft_under_250_words": len(draft.split()) <= 250,
        "no_obsolete_timeout_claim": "model_final_observed_cli_timeout" not in normalized and "cli timed out" not in normalized,
    }
    return {"run_id": run["run_id"], "checks": checks, "passed": all(checks.values()), "scope": "Draft coverage and simple false-claim checks only. Human investment review remains required."}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    args = parser.parse_args()
    run = json.loads((RUNS / f"{args.run_id}.json").read_text())
    result = evaluate(run)
    target = RUNS / f"{args.run_id}.eval.json"
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
