"""Start owned local inference only when a scheduled review needs it."""
from __future__ import annotations
import argparse
import fcntl
import importlib.util
import json
import os
import signal
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
import scheduler
from finance import RUNS, calculate
from lib.work_item import can_refresh

ROOT = Path(__file__).resolve().parent


def needs_model(now):
    day = now.astimezone(scheduler.TZ).date().isoformat()
    for cadence in scheduler.due(now):
        path = RUNS / f"{day}-{cadence}.json"
        report = calculate(day, cadence)
        if report['status'] != 'review_required':
            continue
        if not path.exists():
            return True
        saved = json.loads(path.read_text())
        if can_refresh(saved, report) and not (RUNS / f'{day}-{cadence}.reviews.jsonl').exists():
            return True
        attempts = list((RUNS / 'attempts').glob(f'{day}-{cadence}-*.json'))
        if (saved.get('model_status') in ('failed', 'running') and len(attempts) < 2
                and saved.get('source_sha256') == report['source_sha256']):
            return True
    return False


def port_open(port):
    with socket.socket() as client:
        client.settimeout(.2)
        return client.connect_ex(('127.0.0.1', port)) == 0


def load_queue(path):
    spec = importlib.util.spec_from_file_location('ambient_gpu_queue', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # The queue scans command arguments, so our --runtime llama-server path can
    # look like a running server. Exclude only this wrapper PID, never its children.
    scanner = module.blocking_processes
    module.blocking_processes = lambda text: [line for line in scanner(text)
        if line.split(maxsplit=1)[0] != str(os.getpid())]
    return module


def run(args):
    RUNS.mkdir(parents=True, exist_ok=True)
    with (RUNS / '.managed.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'status': 'already_running'}
        now = datetime.now(scheduler.TZ)
        if not needs_model(now):
            return {'status': 'no_inference_needed', 'checks': scheduler.tick(now, profile=args.profile)}
        if any(port_open(port) for port in (62737, 5264)):
            return {'status': 'waiting_for_existing_service', 'detail': 'Owned startup will not replace another listener.'}
        queue = load_queue(args.queue_module) if args.queue_module else None
        job = 'ambient-scheduled-' + uuid.uuid4().hex
        if queue:
            for index in range(3):
                clear, reason = queue.probe('mac')
                if not clear:
                    return {'status': 'waiting_for_gpu', 'detail': reason}
                if index < 2:
                    time.sleep(30)
            queue.put(job, 'mac', {'kind': 'manual-integration', 'scope': 'Scheduled ambient finance model lifecycle'})
            if not queue.claim('mac', job):
                queue.update(job, 'cancelled', 'Another job owns the Mac lane; next tick can retry')
                return {'status': 'waiting_for_gpu'}
        services = []
        state = 'failed'
        try:
            env = {**os.environ, 'LLAMA_SERVER': str(args.runtime), 'BONSAI_MODEL': str(args.model)}
            for name, command in [('model', ['sh', str(ROOT / 'start_model.sh')]),
                                  ('proxy', [sys.executable, str(ROOT / 'settings_proxy.py')])]:
                with (RUNS / f'{job}-{name}.log').open('w') as log:
                    services.append(subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT))
            for _ in range(120):
                if any(process.poll() is not None for process in services):
                    raise RuntimeError('An owned model service exited before readiness')
                if scheduler.model_ready():
                    break
                time.sleep(1)
            else:
                raise RuntimeError('Owned model did not become ready within 120 seconds')
            checks = scheduler.tick(now, profile=args.profile)
            state = 'failed' if any(item['status'] == 'failed' for item in checks) else 'completed'
            return {'status': state, 'queue_job': job if queue else None, 'checks': checks}
        finally:
            clean = True
            for process in reversed(services):
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            clean = False
            if queue:
                queue.update(job, state if clean else 'needs_review', 'Owned services stopped' if clean else 'Owned cleanup could not be verified')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--profile', default='ambient-finance-demo')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--queue-module', type=Path, help='Shared gpu_queue.py module on a shared Mac')
    mode.add_argument('--dedicated-host', action='store_true', help='Use only on a workstation dedicated to this service')
    args = parser.parse_args()
    for name in ('runtime', 'model', 'queue_module'):
        value = getattr(args, name)
        if value and not value.expanduser().absolute().is_file():
            parser.error(f'{name} does not name a file')
        if value:
            setattr(args, name, value.expanduser().absolute())
    def stop(signum, frame):
        raise KeyboardInterrupt('Service interrupted')
    signal.signal(signal.SIGTERM, stop)
    print(json.dumps(run(args)), flush=True)


if __name__ == '__main__':
    main()
