"""Deterministic analytics and read-only MCP tools for a fictional portfolio."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from lib.source_documents import read_document

ROOT = Path(__file__).resolve().parent
RUNS = Path(os.environ.get("AMBIENT_FINANCE_RUNS", str(ROOT / "runs")))


def D(value: object) -> Decimal:
    return Decimal(str(value))


def money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def pct(value: Decimal) -> str:
    return str((value * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def data_root() -> Path:
    return Path(os.environ.get("AMBIENT_FINANCE_DATA", str(ROOT))).expanduser().absolute()


def load_fixture() -> tuple[dict, dict]:
    portfolio = json.loads((data_root() / "fixtures/portfolio.json").read_text())
    research = json.loads((data_root() / "fixtures/research.json").read_text())
    assert portfolio["fictional"] and research["fictional"]
    return portfolio, research


def calculate(as_of: str, cadence: str) -> dict:
    """Use decimal arithmetic. Values and shocks come only from the fixture."""
    day = date.fromisoformat(as_of)
    if cadence not in {"nightly", "daily", "weekly", "quarterly"}:
        raise ValueError("cadence must be nightly, daily, weekly or quarterly")
    p, research = load_fixture()
    positions = p["positions"]
    ids = [row["id"] for row in positions]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate position ID")
    report_by_id = {r["id"]: r for r in research["reports"]}
    if len(report_by_id) != len(research["reports"]):
        raise ValueError("duplicate research ID")
    if any(D(row["shares"]) < 0 or D(row["close"]) <= 0 or D(row["prior_close"]) <= 0 for row in positions):
        raise ValueError("shares and prices must be valid positive numbers")
    if D(p["cash"]) < 0:
        raise ValueError("negative cash is unsupported")
    values = {row["id"]: D(row["shares"]) * D(row["close"]) for row in positions}
    total = sum(values.values(), D(p["cash"]))
    if total <= 0:
        raise ValueError("portfolio value must be positive")
    limits = p["limits"]
    issues: list[dict] = []
    output_positions: list[dict] = []
    sectors: dict[str, Decimal] = {}
    daily_pnl = D(0)
    for row in positions:
        pid = row["id"]
        price_day = date.fromisoformat(row["price_date"])
        if price_day != day:
            issues.append({"code": "price_not_current", "position_id": pid, "price_date": str(price_day), "severity": "block"})
        report = report_by_id.get(row["research_id"])
        if not report or report["issuer_id"] != pid:
            issues.append({"code": "research_missing", "position_id": pid, "severity": "block"})
        else:
            age = (day - date.fromisoformat(report["date"])).days
            if age < 0:
                issues.append({"code": "research_future_dated", "position_id": pid, "severity": "block"})
            elif age > int(limits["max_research_age_days"]):
                issues.append({"code": "research_stale", "position_id": pid, "research_id": report["id"], "age_days": age, "severity": "review"})
            if not (data_root() / report["source"]).is_file():
                issues.append({"code": "research_file_missing", "position_id": pid, "research_id": report["id"], "severity": "block"})
        value = values[pid]
        weight = value / total
        if weight > D(limits["max_issuer_weight"]):
            issues.append({"code": "issuer_limit", "position_id": pid, "weight_pct": pct(weight), "severity": "review"})
        sectors[row["sector"]] = sectors.get(row["sector"], D(0)) + value
        change = D(row["shares"]) * (D(row["close"]) - D(row["prior_close"]))
        daily_pnl += change
        output_positions.append({"id": pid, "issuer": row["issuer"], "sector": row["sector"], "value_usd": money(value), "weight_pct": pct(weight), "change_from_prior_close_usd": money(change), "research_id": row["research_id"], "price_date": row["price_date"]})
    cash_weight = D(p["cash"]) / total
    if cash_weight < D(limits["min_cash_weight"]):
        issues.append({"code": "cash_limit", "weight_pct": pct(cash_weight), "severity": "review"})
    output_sectors = []
    for sector, value in sorted(sectors.items()):
        weight = value / total
        output_sectors.append({"sector": sector, "value_usd": money(value), "weight_pct": pct(weight)})
        if weight > D(limits["max_sector_weight"]):
            issues.append({"code": "sector_limit", "sector": sector, "weight_pct": pct(weight), "severity": "review"})
    scenarios = []
    for scenario in p["scenarios"]:
        if set(scenario["shocks"]) != set(ids):
            raise ValueError(f"scenario {scenario['id']} must include each position exactly once")
        delta = sum((values[pid] * D(shock) for pid, shock in scenario["shocks"].items()), D(0))
        scenarios.append({"id": scenario["id"], "name": scenario["name"], "assumption": scenario["description"], "change_usd": money(delta), "change_pct": pct(delta / total), "ending_value_usd": money(total + delta)})
    file_hashes = {}
    source_paths = [data_root() / "fixtures/portfolio.json", data_root() / "fixtures/research.json"]
    source_paths.extend(data_root() / report["source"] for report in research["reports"] if (data_root() / report["source"]).is_file())
    for path in source_paths:
        file_hashes[str(path.relative_to(data_root()))] = hashlib.sha256(path.read_bytes()).hexdigest()
    status = "blocked" if any(i["severity"] == "block" for i in issues) else "review_required"
    return {"schema_version": 1, "fictional": True, "as_of": as_of, "cadence": cadence, "methodology": p["methodology"], "status": status, "total_value_usd": money(total), "cash_usd": money(D(p["cash"])), "cash_weight_pct": pct(cash_weight), "daily_change_from_prior_close_usd": money(daily_pnl), "positions": output_positions, "sectors": output_sectors, "scenarios": scenarios, "issues": issues, "source_sha256": file_hashes, "model_analysis": None, "trade_execution_available": False}


def source_review_requirements(run: dict) -> list[str]:
    reasons = []
    if run["status"] == "blocked":
        reasons.append("Source data are blocked. Refresh them before accepting analysis.")
    if any(issue["severity"] == "review" for issue in run["issues"]):
        reasons.append("Open limit or research issue. Resolve it before accepting analysis.")
    return reasons


def acceptance_requirements(run: dict) -> dict:
    reasons = source_review_requirements(run)
    if run.get("model_status") != "completed":
        reasons.append("No completed Hermes analysis is available for review.")
    return {"can_accept_analysis": not reasons, "reasons": reasons,
            "trade_authorized": False}


def work_item_response(run: dict) -> dict:
    # Draft generation needs portfolio facts, not its own changing execution state.
    facts = {key: value for key, value in run.items()
             if not key.startswith("model_") and key != "review_decision"}
    requirements = source_review_requirements(run)
    research_actions = [
        {"action": "refresh_research", "position_id": issue["position_id"],
         "research_id": issue["research_id"],
         "reason": "The research exceeds the review age limit. Obtain a current report before acceptance."}
        for issue in run["issues"] if issue["code"] == "research_stale"
    ]
    return {**facts, "source_review_requirements": requirements,
            "review_context": {
                "acceptance_blocked_by_sources": bool(requirements),
                "source_requirements": requirements,
                "required_research_actions": research_actions,
                "source_exception_available": False,
                "next_decision": (
                    "Determine who will obtain the required source updates. Acceptance is unavailable until the source issues are resolved."
                    if requirements else
                    "Review the completed draft for accuracy before recording an acceptance decision."),
            }}


def latest_run(run_id=None) -> dict:
    if run_id is not None:
        if not isinstance(run_id, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}-(?:nightly|daily|weekly|quarterly)", run_id):
            raise ValueError("Use an exact dated run ID")
        path = RUNS / (run_id + ".json")
        if not path.exists():
            raise ValueError("Requested work item does not exist")
        return work_item_response(json.loads(path.read_text()))
    paths = sorted((path for path in RUNS.glob("*.json") if re.fullmatch(r"\d{4}-\d{2}-\d{2}-(?:nightly|daily|weekly|quarterly)\.json", path.name)), key=lambda x: x.stat().st_mtime, reverse=True)
    if not paths:
        return {"status": "no_run", "message": "Run the local schedule first."}
    return work_item_response(json.loads(paths[0].read_text()))


def execute(name: str, args: dict) -> dict:
    if name == "finance_latest_run":
        return latest_run(args.get("run_id"))
    if name == "finance_position":
        pid = args.get("position_id")
        p, r = load_fixture()
        row = next((x for x in p["positions"] if x["id"] == pid), None)
        if not row:
            raise ValueError("Use an exact position ID from finance_latest_run")
        research = next((x for x in r["reports"] if x["id"] == row["research_id"]), None)
        document = read_document(data_root(), research["source"]) if research else None
        return {"fictional": True, "position": row, "research": research,
                "research_index_scope": "Catalog metadata and summary; compare with source_document for the actual file contents.",
                "source_document": document}
    raise ValueError("Unknown tool")


def tool(name: str, description: str, props: dict | None = None, required: list[str] | None = None) -> dict:
    return {"name": name, "description": description, "inputSchema": {"type": "object", "properties": props or {}, "required": required or [], "additionalProperties": False}, "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}}


TOOLS = [
    tool("finance_latest_run", "Read a scheduled portfolio work item. Supply run_id for a specific task; omit it only to browse the latest work item.", {"run_id": {"type": "string"}}),
    tool("finance_position", "Read a fictional position and its analyst source without changing either.", {"position_id": {"type": "string"}}, ["position_id"]),
]


def main() -> None:
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if "id" not in request:
                continue
            method = request["method"]
            if method == "initialize":
                result = {"protocolVersion": request.get("params", {}).get("protocolVersion", "2024-11-05"), "capabilities": {"tools": {}}, "serverInfo": {"name": "ambient-finance", "version": "1.0.0"}}
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                params = request["params"]
                try:
                    result = {"content": [{"type": "text", "text": json.dumps(execute(params["name"], params.get("arguments", {})))}]}
                except Exception as exc:
                    result = {"isError": True, "content": [{"type": "text", "text": str(exc)}]}
            else:
                result = {}
            print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)
        except Exception as exc:
            print(str(exc), file=sys.stderr)


if __name__ == "__main__":
    main()
