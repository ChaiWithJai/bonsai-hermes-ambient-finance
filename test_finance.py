import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import finance
import scheduler

ROOT = Path(__file__).resolve().parent


class FinanceTests(unittest.TestCase):
    def test_reference_calculation(self):
        report = finance.calculate("2026-09-25", "nightly")
        self.assertEqual(report["total_value_usd"], "640800.00")
        self.assertEqual(report["daily_change_from_prior_close_usd"], "300.00")
        self.assertEqual(report["cash_weight_pct"], "13.26")
        self.assertEqual(report["scenarios"][0]["change_usd"], "-70232.00")
        self.assertEqual(report["scenarios"][1]["ending_value_usd"], "694888.00")
        self.assertEqual(report["status"], "review_required")
        self.assertEqual([x["code"] for x in report["issues"]], ["research_stale"])
        self.assertEqual(report["issues"][0]["age_days"], 138)
        self.assertFalse(report["trade_execution_available"])

    def test_stale_prices_block_current_schedule(self):
        report = finance.calculate("2026-09-26", "daily")
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(sum(x["code"] == "price_not_current" for x in report["issues"]), 4)

    def test_missing_research_blocks(self):
        p, r = finance.load_fixture()
        p = copy.deepcopy(p)
        p["positions"][0]["research_id"] = "R-NOPE"
        with patch.object(finance, "load_fixture", return_value=(p, r)):
            report = finance.calculate("2026-09-25", "nightly")
        self.assertIn("research_missing", [x["code"] for x in report["issues"]])
        self.assertEqual(report["status"], "blocked")

    def test_scenario_requires_all_positions(self):
        p, r = finance.load_fixture()
        p = copy.deepcopy(p)
        del p["scenarios"][0]["shocks"]["FIC-AST"]
        with patch.object(finance, "load_fixture", return_value=(p, r)):
            with self.assertRaises(ValueError):
                finance.calculate("2026-09-25", "nightly")

    def test_mcp_lists_only_read_tools(self):
        proc = subprocess.run([sys.executable, str(ROOT / "finance.py")], input=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n", text=True, capture_output=True, check=True)
        tools = json.loads(proc.stdout)["result"]["tools"]
        self.assertEqual({t["name"] for t in tools}, {"finance_latest_run", "finance_position"})
        self.assertTrue(all(t["annotations"]["readOnlyHint"] for t in tools))

    def test_latest_run_ignores_evaluation_sidecars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "2026-09-25-daily.json").write_text('{"run_id":"2026-09-25-daily"}')
            (root / "2026-09-25-daily.eval.json").write_text('{"run_id":"wrong-sidecar"}')
            with patch.object(finance, "RUNS", root):
                self.assertEqual(finance.latest_run()["run_id"], "2026-09-25-daily")

    def test_schedule_cadences(self):
        tz = ZoneInfo("America/New_York")
        self.assertEqual(scheduler.due(datetime(2026, 9, 25, 22, 0, tzinfo=tz)), ["nightly", "daily"])
        self.assertEqual(scheduler.due(datetime(2026, 9, 28, 8, 0, tzinfo=tz)), ["daily", "weekly"])
        self.assertEqual(scheduler.due(datetime(2026, 10, 1, 9, 0, tzinfo=tz)), ["daily", "quarterly"])

    def test_schedule_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "runs").mkdir()
            (base / "runs/2026-09-25-daily.json").write_text("{}")
            with patch.object(scheduler, "ROOT", base):
                result = scheduler.tick(datetime(2026, 9, 25, 9, tzinfo=ZoneInfo("America/New_York")), dry_run=True)
            self.assertEqual(result, [{"cadence": "daily", "status": "already_recorded"}])

    def test_review_gate_rejects_stale_research_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2026-09-25-nightly.json"
            report = finance.calculate("2026-09-25", "nightly")
            report.update(run_id="2026-09-25-nightly", model_status="completed")
            path.write_text(json.dumps(report))
            env = dict(os.environ, AMBIENT_FINANCE_RUNS=tmp)
            cmd = [sys.executable, str(ROOT / "review.py"), "2026-09-25-nightly", "--reviewer", "Demo reviewer", "--note", "Research must be refreshed"]
            accepted = subprocess.run(cmd + ["--decision", "accept_analysis"], capture_output=True, text=True, env=env)
            self.assertNotEqual(accepted.returncode, 0)
            self.assertIn("Open limit or research issue", accepted.stderr)
            rejected = subprocess.run(cmd + ["--decision", "reject_analysis"], capture_output=True, text=True, env=env)
            self.assertEqual(rejected.returncode, 0)
            record = json.loads((Path(tmp) / "2026-09-25-nightly.reviews.jsonl").read_text())
            self.assertFalse(record["trade_authorized"])
            self.assertFalse(record["identity_verified"])


if __name__ == "__main__":
    unittest.main()
