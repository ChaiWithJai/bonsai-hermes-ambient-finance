"""Create a separate Hermes profile that points to this demo's read-only MCP server."""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--out", required=True)
args = parser.parse_args()
out = Path(args.out).expanduser().resolve()
if out.exists():
    raise SystemExit(f"Refusing to overwrite {out}")
out.mkdir(parents=True)
config = json.loads((ROOT / "hermes-config.json").read_text())
config["mcp_servers"]["ambient_finance"]["command"] = sys.executable
config["mcp_servers"]["ambient_finance"]["args"] = [str(ROOT / "finance.py")]
(out / "config.yaml").write_text(json.dumps(config, indent=2) + "\n")
shutil.copy2(ROOT / "SOUL.md", out / "SOUL.md")
print(out)
