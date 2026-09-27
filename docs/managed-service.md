# Run reviews without keeping model terminals open

The managed scheduler starts local inference when a due review has usable source data. It waits for the model and proxy, runs the review, and stops both processes afterward. A blocked source check or completed review does not load the model. The service runs while the Mac is awake and the user remains logged in; it does not change power settings or wake a shut-down machine.

First, create the Hermes profile with the same source and work directories that the scheduled job will use. `AMBIENT_FINANCE_DATA` must contain `fixtures/portfolio.json`, `fixtures/research.json`, and the source documents named in the research records. The supplied prices describe September 25, so later checks will block until a source provider supplies current data. Changing the date on old prices is not a source refresh.

```sh
export AMBIENT_FINANCE_DATA="/absolute/path/to/portfolio-inputs"
export AMBIENT_FINANCE_RUNS="$HOME/.local/state/bonsai-ambient-finance/runs"
python3 setup.py --out "$HOME/.hermes/profiles/ambient-finance-demo"
```

For a lifecycle demonstration using sample data, create a separate dated input directory before setup. Choose the date explicitly; the generator copies the sample values and records that they are mocked prices. It does not run as part of the scheduler or update the date automatically.

```sh
python3 scripts/create_sample_inputs.py --out "$HOME/.local/state/bonsai-ambient-finance/sample-inputs" --as-of YYYY-MM-DD
```

Set `AMBIENT_FINANCE_DATA` to that directory before creating the profile. On the next date, the same sample prices will be stale and inference will be skipped.

Second, install the managed scheduler on a workstation dedicated to the demo. Use the downloaded model and matching Prism runtime paths.

```sh
python3 install_launch_agent.py \
  --managed-model "$BONSAI_MODEL" \
  --runtime "$LLAMA_SERVER" \
  --dedicated-host
```

On a shared lab Mac, replace `--dedicated-host` with `--queue-module /absolute/path/to/gpu_queue.py`. The adapter uses the lab queue's `probe`, `put`, `claim`, and `update` functions. It requires three clear probes thirty seconds apart before claiming the Mac lane. Another reservation or recognized model process leaves the review waiting for a later tick. The repository does not include the lab queue; a dedicated workstation does not need that adapter.

The installer refuses to change a differing existing job without `--replace`. Inspect its model paths, profile, source directory and work directory before replacing it. The managed wrapper preserves existing listeners on its model and proxy ports and starts only processes it owns. A local lock prevents overlapping managed checks, and a work-item lock prevents concurrent workers from overwriting the same report.

A failed or interrupted draft can be retried twice on later checks if its source hashes remain unchanged. Each attempt is archived before retry, and work-item writes use an atomic rename. A completed draft remains unchanged. When refreshed sources clear an unreviewed blocked item, the next check starts inference and preserves the earlier record in `revisions/`. The service records failures separately from completed drafts, and it still requires a saved Hermes final answer.

Inspect the installed job and its logs with:

```sh
launchctl print gui/$(id -u)/com.prismml.bonsai-ambient-finance
tail -n 20 "$HOME/Library/Logs/PrismML/ambient-finance.out.log"
tail -n 20 "$HOME/Library/Logs/PrismML/ambient-finance.err.log"
```

Stop the job with `launchctl bootout gui/$(id -u)/com.prismml.bonsai-ambient-finance`. The scheduler does not refresh source data or backfill missed dates. The default installer mode still expects an independently managed model; pass the managed model options to enable owned startup and cleanup.
