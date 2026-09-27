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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import finance
import scheduler


class FinanceTests(unittest.TestCase):
    def test_requested_run_does_not_follow_latest_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "2026-09-25-nightly.json").write_text('{"run_id":"2026-09-25-nightly","status":"review_required","issues":[]}')
            (root / "2026-09-26-daily.json").write_text('{"run_id":"2026-09-26-daily","status":"review_required","issues":[]}')
            with patch.object(finance, "RUNS", root):
                report = finance.execute("finance_latest_run", {"run_id": "2026-09-25-nightly"})
                self.assertEqual(report["run_id"], "2026-09-25-nightly")
                with self.assertRaisesRegex(ValueError, "does not exist"):
                    finance.latest_run("2026-09-24-nightly")
                with self.assertRaisesRegex(ValueError, "exact dated"):
                    finance.latest_run("../private")

    def test_tool_exposes_same_acceptance_rule_as_review(self):
        report = finance.calculate("2026-09-25", "nightly")
        report["model_status"] = "completed"
        response = finance.work_item_response(report)
        self.assertNotIn("model_status", response)
        self.assertNotIn("model_analysis", response)
        context = response["review_context"]
        self.assertTrue(context["acceptance_blocked_by_sources"])
        self.assertFalse(context["source_exception_available"])
        self.assertEqual(context["required_research_actions"][0]["research_id"], "R-MER")
        self.assertEqual(context["required_research_actions"][0]["position_id"], "FIC-MER")
        self.assertIn("Open limit or research issue", response["source_review_requirements"][0])
        self.assertFalse(finance.acceptance_requirements(report)["can_accept_analysis"])
        report["issues"] = []
        clear = finance.work_item_response(report)["review_context"]
        self.assertFalse(clear["acceptance_blocked_by_sources"])
        self.assertEqual(clear["required_research_actions"], [])
        self.assertTrue(finance.acceptance_requirements(report)["can_accept_analysis"])
        report["model_status"] = "failed"
        self.assertFalse(finance.acceptance_requirements(report)["can_accept_analysis"])

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
            (root / "2026-09-25-daily.json").write_text('{"run_id":"2026-09-25-daily","status":"review_required","issues":[]}')
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
            with patch.object(scheduler, "RUNS", base / "runs"):
                result = scheduler.tick(datetime(2026, 9, 25, 9, tzinfo=ZoneInfo("America/New_York")), dry_run=True)
            self.assertEqual(result, [{"cadence": "daily", "status": "already_recorded"}])

    def test_schedule_waits_for_model_then_runs_without_losing_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            now = datetime(2026, 9, 25, 9, tzinfo=ZoneInfo("America/New_York"))
            with patch.object(scheduler, "RUNS", Path(tmp) / "runs"), patch.object(scheduler, "model_ready", side_effect=[False, True]), patch.object(scheduler.subprocess, "run") as run:
                run.return_value = subprocess.CompletedProcess([], 0, "saved", "")
                self.assertEqual(scheduler.tick(now)[0]["status"], "waiting_for_model")
                run.assert_not_called()
                self.assertFalse((Path(tmp) / "runs/2026-09-25-daily.json").exists())
                self.assertEqual(scheduler.tick(now)[0]["status"], "recorded")
                run.assert_called_once()

    def test_failed_schedule_retries_twice_then_preserves_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            report = finance.calculate("2026-09-25", "daily")
            report["model_status"] = "failed"
            (run_dir / "2026-09-25-daily.json").write_text(json.dumps(report))
            now = datetime(2026, 9, 25, 9, tzinfo=ZoneInfo("America/New_York"))
            with patch.object(scheduler, "RUNS", run_dir), patch.object(scheduler, "model_ready", return_value=True), patch.object(scheduler.subprocess, "run") as worker:
                worker.return_value = subprocess.CompletedProcess([], 1, "", "failed")
                self.assertEqual(scheduler.tick(now, profile="isolated-recovery")[0]["status"], "failed")
                self.assertEqual(worker.call_args.args[0][-3:-1], ["--profile", "isolated-recovery"])
                self.assertIn("--retry-model", worker.call_args.args[0])
                attempts = run_dir / "attempts"
                attempts.mkdir()
                for number in range(2):
                    (attempts / f"2026-09-25-daily-{number}.json").write_text("{}")
                worker.reset_mock()
                self.assertEqual(scheduler.tick(now)[0]["status"], "retry_limit_reached")
                worker.assert_not_called()
                self.assertEqual(json.loads((run_dir / "2026-09-25-daily.json").read_text()), report)

    def test_failed_schedule_does_not_retry_changed_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            report = finance.calculate("2026-09-25", "daily")
            report.update(model_status="failed", source_sha256={"old": "hash"})
            (run_dir / "2026-09-25-daily.json").write_text(json.dumps(report))
            now = datetime(2026, 9, 25, 9, tzinfo=ZoneInfo("America/New_York"))
            with patch.object(scheduler, "RUNS", run_dir), patch.object(scheduler, "model_ready", return_value=True), patch.object(scheduler.subprocess, "run") as worker:
                self.assertEqual(scheduler.tick(now)[0]["status"], "source_changed")
                worker.assert_not_called()

    def test_stale_data_is_recorded_even_without_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            now = datetime(2026, 9, 26, 9, tzinfo=ZoneInfo("America/New_York"))
            with patch.object(scheduler, "RUNS", Path(tmp) / "runs"), patch.object(scheduler, "model_ready") as ready, patch.object(scheduler.subprocess, "run") as run:
                run.return_value = subprocess.CompletedProcess([], 0, "blocked", "")
                self.assertEqual(scheduler.tick(now)[0]["status"], "recorded")
                ready.assert_not_called()
                run.assert_called_once()

    def test_scheduler_and_worker_share_external_run_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "external-queue"
            now = datetime(2026, 9, 26, 9, tzinfo=ZoneInfo("America/New_York"))
            with patch.dict(os.environ, {"AMBIENT_FINANCE_RUNS": str(run_dir)}), patch.object(scheduler, "RUNS", run_dir):
                first = scheduler.tick(now)
                self.assertEqual(first[0]["status"], "recorded")
                saved = run_dir / "2026-09-26-daily.json"
                self.assertEqual(json.loads(saved.read_text())["model_status"], "skipped_data_gate")
                before = saved.read_bytes()
                self.assertEqual(scheduler.tick(now)[0]["status"], "already_recorded")
                self.assertEqual(saved.read_bytes(), before)

    def test_profile_and_launch_agent_preserve_external_run_directory(self):
        import install_launch_agent
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = str(Path(tmp) / "queue")
            profile = Path(tmp) / "profile"
            with patch.dict(os.environ, {"AMBIENT_FINANCE_RUNS": run_dir}):
                subprocess.run([sys.executable, str(ROOT / "setup.py"), "--out", str(profile)], check=True, capture_output=True)
                saved = json.loads((profile / "config.yaml").read_text())
                self.assertEqual(saved["mcp_servers"]["ambient_finance"]["env"]["AMBIENT_FINANCE_RUNS"], run_dir)
                with patch.object(install_launch_agent.shutil, "which", return_value="/usr/local/bin/hermes"):
                    agent = install_launch_agent.config(Path(sys.executable))
                self.assertEqual(agent["EnvironmentVariables"]["AMBIENT_FINANCE_RUNS"], run_dir)

    def test_retry_does_not_feed_prior_draft_to_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            run = finance.calculate("2026-09-25", "daily")
            run.update(run_id="2026-09-25-daily", model_status="failed",
                       model_analysis="obsolete timeout claim", model_error="TimeoutExpired")
            (base / "2026-09-25-daily.json").write_text(json.dumps(run))
            binary = base / "hermes"
            binary.write_text("#!/usr/bin/env python3\n"
                              "import json,os,pathlib,sys\n"
                              "p=pathlib.Path(os.environ['AMBIENT_FINANCE_RUNS'])/'2026-09-25-daily.json'\n"
                              "r=json.loads(p.read_text())\n"
                              "if r.get('model_analysis') is not None or r['model_status']!='pending': sys.exit(7)\n"
                              "print('Fresh fictional draft')\n")
            binary.chmod(0o755)
            env = {**os.environ, "AMBIENT_FINANCE_RUNS": tmp,
                   "PATH": str(base) + os.pathsep + os.environ["PATH"]}
            proc = subprocess.run([sys.executable, str(ROOT / "run_schedule.py"), "--cadence", "daily",
                                   "--as-of", "2026-09-25", "--retry-model", "--with-hermes", "--session-db", str(base / "hermes-state.db")],
                                  capture_output=True, text=True, env=env)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            after = json.loads((base / "2026-09-25-daily.json").read_text())
            self.assertEqual(after["model_status"], "failed")
            self.assertIsNone(after["model_analysis"])
            self.assertIn("Hermes", after["model_error"])
            archived = list((base / "attempts").glob("*.json"))
            self.assertEqual(len(archived), 1)
            self.assertEqual(json.loads(archived[0].read_text())["model_analysis"], "obsolete timeout claim")

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


class SourceDocumentTests(unittest.TestCase):
    def test_pdf_content_is_extracted_with_page_and_hash(self):
        result = finance.execute("finance_position", {"position_id": "FIC-AST"})
        source = result["source_document"]
        self.assertEqual(source["pages"][0]["page"], 1)
        self.assertIn("Customer concentration", source["pages"][0]["text"])
        self.assertEqual(len(source["sha256"]), 64)

    def test_changed_csv_is_read_even_when_catalog_summary_is_unchanged(self):
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("fixtures", "mock-drive", "mock-sheets"):
                shutil.copytree(ROOT / name, root / name)
            with patch.object(finance, "ROOT", root):
                before = finance.calculate("2026-09-25", "nightly")
                path = root / "mock-sheets/cirrus-grid-model.csv"
                path.write_text(path.read_text().replace("Capital spending could reduce free cash flow.",
                                                        "A major renewal has been delayed."))
                result = finance.execute("finance_position", {"position_id": "FIC-CIR"})
                self.assertIn("Capital spending", result["research"]["risk"])
                self.assertIn("A major renewal has been delayed.", str(result["source_document"]["rows"]))
                after = finance.calculate("2026-09-25", "nightly")
                key = "mock-sheets/cirrus-grid-model.csv"
                self.assertNotEqual(before["source_sha256"][key], after["source_sha256"][key])


if __name__ == "__main__":
    unittest.main()
