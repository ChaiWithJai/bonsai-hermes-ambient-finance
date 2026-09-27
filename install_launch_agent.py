"""Install the local ambient-finance scheduler as a per-user macOS LaunchAgent."""

from __future__ import annotations

import argparse
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path


LABEL = "com.prismml.bonsai-ambient-finance"
ROOT = Path(__file__).resolve().parent
AGENT = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
LOGS = Path.home() / "Library" / "Logs" / "PrismML"


def config(python: Path, managed_args: list[str] | None = None, profile: str = "ambient-finance-demo") -> dict:
    hermes = shutil.which("hermes")
    if not hermes:
        raise SystemExit("Hermes CLI is not on PATH")
    path = ":".join(dict.fromkeys([
        str(Path(hermes).parent), str(python.parent),
        "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin",
    ]))
    environment = {"PATH": path, "MLFLOW_DISABLE_AGENT_HINT": "1"}
    for name in ("AMBIENT_FINANCE_RUNS", "AMBIENT_FINANCE_DATA"):
        if os.environ.get(name):
            environment[name] = str(Path(os.environ[name]).expanduser().absolute())
    command = [str(python), str(ROOT / "scheduler.py"), "--once", "--profile", profile]
    if managed_args is not None:
        command = [str(python), str(ROOT / "managed_tick.py"), "--profile", profile, *managed_args]
    return {
        "Label": LABEL,
        "ProgramArguments": command,
        "WorkingDirectory": str(ROOT),
        "RunAtLoad": True,
        "StartInterval": 300,
        "ExitTimeOut": 60,
        "EnvironmentVariables": environment,
        "StandardOutPath": str(LOGS / "ambient-finance.out.log"),
        "StandardErrorPath": str(LOGS / "ambient-finance.err.log"),
    }


def main():
    if sys.platform != "darwin":
        raise SystemExit("This installer is for macOS launchd")
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--profile", default="ambient-finance-demo")
    parser.add_argument("--managed-model", type=Path)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--queue-module", type=Path)
    parser.add_argument("--dedicated-host", action="store_true")
    parser.add_argument("--replace", action="store_true", help="Replace this demo's existing LaunchAgent")
    args = parser.parse_args()
    python = args.python.expanduser()
    if not python.is_file():
        raise SystemExit(f"Python does not exist: {python}")
    AGENT.parent.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    managed = None
    if args.managed_model:
        if not args.runtime or bool(args.queue_module) == args.dedicated_host:
            parser.error("--managed-model requires --runtime and exactly one of --queue-module or --dedicated-host")
        for value in (args.managed_model, args.runtime, args.queue_module):
            if value and not value.expanduser().is_file():
                parser.error(f"File does not exist: {value}")
        managed = ["--model", str(args.managed_model.expanduser().absolute()),
                   "--runtime", str(args.runtime.expanduser().absolute())]
        if args.queue_module:
            managed += ["--queue-module", str(args.queue_module.expanduser().absolute())]
        else:
            managed += ["--dedicated-host"]
    elif args.runtime or args.queue_module or args.dedicated_host:
        parser.error("Model lifecycle options require --managed-model")
    data = plistlib.dumps(config(python.absolute(), managed, args.profile), sort_keys=True)
    uid = subprocess.check_output(["id", "-u"], text=True).strip()
    target = f"gui/{uid}/{LABEL}"
    present = subprocess.run(["launchctl", "print", target], capture_output=True).returncode == 0
    if AGENT.exists() and AGENT.read_bytes() != data:
        if not args.replace:
            raise SystemExit(f"LaunchAgent differs; inspect it, then use --replace: {AGENT}")
        if present:
            subprocess.run(["launchctl", "bootout", target], check=True)
            present = False
    AGENT.write_bytes(data)
    if not present:
        subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(AGENT)], check=True)
    print(f"Installed {target} from {AGENT}; first check runs at load, then every 300 seconds")


if __name__ == "__main__":
    main()
