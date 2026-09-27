import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, Mock

import finance
import managed_tick
import scheduler

ROOT = Path(__file__).resolve().parents[1]


class SourceRefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / 'inputs'
        self.runs = self.root / 'runs'
        for folder in ('fixtures', 'mock-drive', 'mock-sheets'):
            shutil.copytree(ROOT / folder, self.data / folder)
        self.env = {**os.environ, 'AMBIENT_FINANCE_DATA': str(self.data), 'AMBIENT_FINANCE_RUNS': str(self.runs)}
        self.path = self.runs / '2026-09-26-daily.json'
        self.now = datetime(2026, 9, 26, 9, tzinfo=scheduler.TZ)

    def tearDown(self):
        self.temp.cleanup()

    def run_item(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'run_schedule.py'), '--cadence', 'daily', '--as-of', '2026-09-26', *args], env=self.env, capture_output=True, text=True)

    def refresh_inputs(self):
        path = self.data / 'fixtures/portfolio.json'
        source = json.loads(path.read_text())
        for position in source['positions']:
            position['price_date'] = '2026-09-26'
        path.write_text(json.dumps(source))

    def test_worker_archives_blocked_bytes_and_uses_new_sources(self):
        self.assertEqual(self.run_item('--with-hermes').returncode, 0)
        previous = self.path.read_bytes()
        self.assertEqual(json.loads(previous)['model_status'], 'skipped_data_gate')
        self.refresh_inputs()
        result = self.run_item('--refresh-blocked')
        self.assertEqual(result.returncode, 0, result.stderr)
        current = json.loads(self.path.read_text())
        self.assertEqual(current['status'], 'review_required')
        self.assertEqual(current['source_revision'], 1)
        self.assertNotEqual(current['source_sha256'], json.loads(previous)['source_sha256'])
        archives = list((self.runs / 'revisions').glob('*.json'))
        self.assertEqual(len(archives), 1)
        self.assertEqual(archives[0].read_bytes(), previous)
        # The same valid source cannot repeatedly create new revisions.
        self.assertNotEqual(self.run_item('--refresh-blocked').returncode, 0)
        self.assertEqual(len(list((self.runs / 'revisions').glob('*.json'))), 1)

    def test_invalid_or_reviewed_refresh_preserves_saved_work(self):
        self.assertEqual(self.run_item('--with-hermes').returncode, 0)
        previous = self.path.read_bytes()
        self.assertNotEqual(self.run_item('--refresh-blocked').returncode, 0)
        self.assertEqual(self.path.read_bytes(), previous)
        self.refresh_inputs()
        (self.runs / '2026-09-26-daily.reviews.jsonl').write_text('{"decision":"reject_analysis"}\n')
        self.assertNotEqual(self.run_item('--refresh-blocked').returncode, 0)
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertFalse((self.runs / 'revisions').exists())

    def test_scheduler_and_managed_worker_reconsider_changed_sources(self):
        self.assertEqual(self.run_item('--with-hermes').returncode, 0)
        with patch.dict(os.environ, self.env), patch.object(scheduler, 'RUNS', self.runs), patch.object(managed_tick, 'RUNS', self.runs):
            self.assertFalse(managed_tick.needs_model(self.now))
            self.refresh_inputs()
            self.assertTrue(managed_tick.needs_model(self.now))
            with patch.object(scheduler, 'model_ready', return_value=False):
                self.assertEqual(scheduler.tick(self.now)[0]['status'], 'waiting_for_model')
            with patch.object(scheduler, 'model_ready', return_value=True), patch.object(scheduler, 'run_owned', return_value=Mock(returncode=0, stdout='recorded', stderr='')) as launch:
                self.assertEqual(scheduler.tick(self.now)[0]['status'], 'recorded')
                self.assertIn('--refresh-blocked', launch.call_args.args[0])
                self.assertIn('--with-hermes', launch.call_args.args[0])
            saved = json.loads(self.path.read_text())
            saved.update(status='review_required', model_status='completed')
            self.path.write_text(json.dumps(saved))
            self.assertFalse(managed_tick.needs_model(self.now))
            with patch.object(scheduler, 'run_owned') as launch:
                self.assertEqual(scheduler.tick(self.now)[0]['status'], 'already_recorded')
                launch.assert_not_called()
