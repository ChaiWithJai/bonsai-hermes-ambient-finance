"""Install the local ambient-finance scheduler as a per-user macOS LaunchAgent."""

from __future__ import annotations

import argparse
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path


LABEL = "com.prismml.bonsai-ambient-finance"
ROOT = Path(__file__).resolve().parent
AGENT = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
LOGS = Path.home() / "Library" / "Logs" / "PrismML"


def config(python: Path) -> dict:
    hermes = shutil.which("hermes")
    if not hermes:
        raise SystemExit("Hermes CLI is not on PATH")
    path = ":".join(dict.fromkeys([
        str(Path(hermes).parent), str(python.parent),
        "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin",
    ]))
    return {
        "Label": LABEL,
        "ProgramArguments": [str(python), str(ROOT / "scheduler.py"), "--once"],
        "WorkingDirectory": str(ROOT),
        "RunAtLoad": True,
        "StartInterval": 300,
        "EnvironmentVariables": {"PATH": path, "MLFLOW_DISABLE_AGENT_HINT": "1"},
        "StandardOutPath": str(LOGS / "ambient-finance.out.log"),
        "StandardErrorPath": str(LOGS / "ambient-finance.err.log"),
    }


def main():
    if sys.platform != "darwin":
        raise SystemExit("This installer is for macOS launchd")
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--replace", action="store_true", help="Replace this demo's existing LaunchAgent")
    args = parser.parse_args()
    python = args.python.expanduser()
    if not python.is_file():
        raise SystemExit(f"Python does not exist: {python}")
    AGENT.parent.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    data = plistlib.dumps(config(python), sort_keys=True)
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
