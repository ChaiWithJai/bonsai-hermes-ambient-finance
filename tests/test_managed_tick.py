import json
import fcntl
import os
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
import managed_tick as managed
import scheduler
import finance
import install_launch_agent


class ManagedTickTests(unittest.TestCase):
    def setUp(self):
        self.args = Namespace(profile='test', runtime=Path('/runtime'), model=Path('/model'), queue_module=None)

    def test_data_block_skips_model_start(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(managed, 'RUNS', Path(tmp)), patch.object(managed, 'needs_model', return_value=False), patch.object(scheduler, 'tick', return_value=[]), patch.object(managed.subprocess, 'Popen') as start:
            self.assertEqual(managed.run(self.args)['status'], 'no_inference_needed')
            start.assert_not_called()

    def test_existing_listener_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(managed, 'RUNS', Path(tmp)), patch.object(managed, 'needs_model', return_value=True), patch.object(managed, 'port_open', return_value=True), patch.object(managed.subprocess, 'Popen') as start:
            self.assertEqual(managed.run(self.args)['status'], 'waiting_for_existing_service')
            start.assert_not_called()

    def test_owned_services_stop_after_worker_exception(self):
        processes = [Mock(), Mock()]
        for p in processes:
            p.poll.return_value = None
        with tempfile.TemporaryDirectory() as tmp, patch.object(managed, 'RUNS', Path(tmp)), patch.object(managed, 'needs_model', return_value=True), patch.object(managed, 'port_open', return_value=False), patch.object(managed.subprocess, 'Popen', side_effect=processes), patch.object(scheduler, 'model_ready', return_value=True), patch.object(scheduler, 'tick', side_effect=RuntimeError('worker failed')):
            with self.assertRaisesRegex(RuntimeError, 'worker failed'):
                managed.run(self.args)
            for p in processes:
                p.terminate.assert_called_once()
                p.wait.assert_called_once()

    def test_shared_queue_refuses_without_startup(self):
        queue = Mock();queue.probe.return_value = (False, 'occupied')
        self.args.queue_module = Path('/queue.py')
        with tempfile.TemporaryDirectory() as tmp, patch.object(managed, 'RUNS', Path(tmp)), patch.object(managed, 'needs_model', return_value=True), patch.object(managed, 'port_open', return_value=False), patch.object(managed, 'load_queue', return_value=queue), patch.object(managed.subprocess, 'Popen') as start:
            self.assertEqual(managed.run(self.args)['status'], 'waiting_for_gpu')
            start.assert_not_called();queue.claim.assert_not_called()

    def test_pending_decision_respects_source_gate_and_completed_work(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(managed, 'RUNS', Path(tmp)):
            self.assertFalse(managed.needs_model(datetime(2026,9,26,9,tzinfo=scheduler.TZ)))
            current = datetime(2026,9,25,9,tzinfo=scheduler.TZ)
            self.assertTrue(managed.needs_model(current))
            (Path(tmp)/'2026-09-25-daily.json').write_text(json.dumps({'model_status':'completed'}))
            self.assertFalse(managed.needs_model(current))
            interrupted = finance.calculate('2026-09-25', 'daily')
            interrupted['model_status'] = 'running'
            (Path(tmp)/'2026-09-25-daily.json').write_text(json.dumps(interrupted))
            self.assertTrue(managed.needs_model(current))

    def test_installer_keeps_custom_profile_and_managed_command(self):
        with patch.object(install_launch_agent.shutil, 'which', return_value='/bin/hermes'):
            config = install_launch_agent.config(Path('/python'), ['--model','/model','--runtime','/runtime','--dedicated-host'], 'custom')
        self.assertTrue(config['ProgramArguments'][1].endswith('managed_tick.py'))
        self.assertEqual(config['ProgramArguments'][2:4], ['--profile','custom'])
        self.assertEqual(config['StartInterval'], 300)

    def test_worker_refuses_concurrent_owner_without_changing_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with (directory / '.2026-09-26-daily.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                result = subprocess.run([sys.executable, str(managed.ROOT / 'run_schedule.py'), '--cadence', 'daily', '--as-of', '2026-09-26'], env={**os.environ, 'AMBIENT_FINANCE_RUNS': tmp}, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('already owns', result.stderr)
                self.assertFalse((directory / '2026-09-26-daily.json').exists())

    def test_data_directory_propagates_to_profile_and_launch_agent(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'AMBIENT_FINANCE_DATA': tmp}):
            profile = Path(tmp) / 'profile'
            subprocess.run([sys.executable, str(managed.ROOT / 'setup.py'), '--out', str(profile)], check=True, capture_output=True)
            config = json.loads((profile / 'config.yaml').read_text())
            self.assertEqual(config['mcp_servers']['ambient_finance']['env']['AMBIENT_FINANCE_DATA'], tmp)
            self.assertEqual(finance.data_root(), Path(tmp))
            with patch.object(install_launch_agent.shutil, 'which', return_value='/bin/hermes'):
                agent = install_launch_agent.config(Path('/python'))
            self.assertEqual(agent['EnvironmentVariables']['AMBIENT_FINANCE_DATA'], tmp)

    def test_queue_scan_ignores_only_wrapper_pid(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = Path(tmp) / 'queue.py'
            module.write_text('def blocking_processes(text): return text.splitlines()\n')
            adapter = managed.load_queue(module)
            current = f'{os.getpid()} python managed_tick.py --runtime /bin/llama-server'
            other = '999999 /bin/llama-server --model /weights'
            self.assertEqual(adapter.blocking_processes(current + '\n' + other), [other])
