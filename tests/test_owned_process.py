import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from lib.owned_process import run

ROOT = Path(__file__).resolve().parents[1]


class OwnedProcessTests(unittest.TestCase):
    def test_preserves_output_exit_and_signal_handler(self):
        previous = signal.getsignal(signal.SIGTERM)
        result = run([sys.executable, '-c', 'import sys; print("saved"); sys.exit(3)'])
        self.assertEqual((result.returncode, result.stdout.strip()), (3, 'saved'))
        self.assertEqual(signal.getsignal(signal.SIGTERM), previous)

    def test_timeout_cleans_process_group(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            run([sys.executable, '-c', 'import time; time.sleep(30)'], timeout=.1)

    def test_sigterm_releases_child_listener_before_worker_exits(self):
        self.check_interruption(False)

    def test_sigterm_cleans_nested_worker_process_groups(self):
        self.check_interruption(True)

    def check_interruption(self, nested):
        with tempfile.TemporaryDirectory() as tmp:
            ready = Path(tmp) / 'port'
            child = Path(tmp) / 'child.py'
            child.write_text('import socket,time\nfrom pathlib import Path\ns=socket.socket();s.bind(("127.0.0.1",0));s.listen()\nPath('+repr(str(ready))+').write_text(str(s.getsockname()[1]))\ntime.sleep(60)\n')
            command = [sys.executable, str(child)]
            if nested:
                command = [sys.executable, '-c', 'from lib.owned_process import run; run('+repr(command)+')']
            worker = subprocess.Popen([sys.executable, '-c',
                'from lib.owned_process import run; run('+repr(command)+')'],
                cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                deadline = time.monotonic() + 10
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(ready.exists(), 'Child did not become ready')
                port = int(ready.read_text())
                worker.terminate()
                worker.wait(timeout=10)
                with socket.socket() as probe:
                    self.assertNotEqual(probe.connect_ex(('127.0.0.1', port)), 0)
            finally:
                if worker.poll() is None:
                    worker.kill();worker.wait()
