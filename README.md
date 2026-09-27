# Run the ambient finance workstation demo

The local job reviews a fictional investment portfolio while the team is away. It calculates position and sector weights, applies two stated scenario shocks, checks research age and saves a draft for human review. Hermes can use Ternary Bonsai 2 27B to explain the work item through two read-only tools. The supplied tools cannot place trades or update the portfolio.

The [architecture](docs/architecture.md) explains the source data, calculation, model tools, persistence and service dependencies.

The [public reproduction guide](https://gist.github.com/ChaiWithJai/e53e6e13fcecb0946643c02497419b81) gives the short command sequence, including the retry needed to request a model draft after the deterministic nightly run.

The included prices, issuers, analyst notes and methodology are invented. The sample date is September 25, 2026, and a run for a later date will be blocked until the price data are refreshed. Scenario outcomes are arithmetic results under assumed price changes. They are not forecasts, backtests or evidence of investment returns.

## Review the source data

First, run `python3 make_mock_sources.py` to generate two fictional PDF analyst notes and two fictional CSV models. The portfolio positions, prices, scenario shocks and risk limits are in `fixtures/portfolio.json`. The report index in `fixtures/research.json` supplies the summaries read by the tools and points to the generated files. The position tool reads PDF text by page and CSV cells by row, alongside the catalog summary. The nightly job records SHA-256 hashes of the JSON fixtures and referenced report files, and stops approval if a report file is missing. Install Poppler for PDF extraction (`brew install poppler` on macOS or `apt-get install poppler-utils` on Ubuntu). Scanned PDFs without extractable text require OCR, which is not implemented.

The sample methodology requires each issuer to stay below 35% of portfolio value, each sector below 60%, cash above 5%, and research to be no older than 90 days. The Meridian Payments note is 138 days old on the sample date, so it remains an open issue for a human reviewer. The work item does not resolve the issue by guessing what the analyst would say.

The [source-reading guide](docs/source-reading.md) shows the recorded page and row citations, a catalog conflict case and the remaining snapshot limitations.

## Generate a deterministic work item

Run the sample nightly calculation from this directory:

```sh
python3 run_schedule.py --cadence nightly --as-of 2026-09-25
```

The command writes `runs/2026-09-25-nightly.json`. It refuses to overwrite the file on a scheduled retry, which keeps the original source hashes and calculation intact. A failed model draft can be retried with `--retry-model --with-hermes` when the source hashes are unchanged. The wrapper archives the prior attempt and removes its draft from the tool-readable work item before asking Hermes again. The expected portfolio value is $640,800, with a $300 change from the listed prior closes. The downside scenario is a $70,232 loss under its assumed shocks. The report status is `review_required` because the Meridian note is stale.

A failed Hermes attempt exits with a nonzero status. On the next scheduled check, the scheduler retries a failed draft if the sources are unchanged and the model is available. It allows two automatic retries, preserving each prior attempt, then leaves the failure for investigation. Completed drafts and data-blocked reports are not retried.

The scheduler supports nightly, daily, weekly and quarterly checks. It uses the America/New_York clock. The following dry run prints the periods that would be due at a chosen time without creating a report:

```sh
python3 scheduler.py --once --dry-run --now 2026-10-01T09:00:00-04:00
```

Run `python3 scheduler.py --once` from a local process supervisor to process all periods due now. Run `python3 scheduler.py` under launchd or another supervisor to check each minute. A Mac that is powered off does no work, and the scheduler does not backfill a missed date. Source refresh is an integration task. With the supplied September 25 prices, runs after that date are recorded as blocked.

On macOS, `python3 install_launch_agent.py` installs a per-user LaunchAgent that runs the one-shot scheduler at login and every five minutes. It discovers the current Python and Hermes paths; inspect an existing job before using `--replace`. Check it with `launchctl print gui/$(id -u)/com.prismml.bonsai-ambient-finance`. To stop it, run `launchctl bootout gui/$(id -u)/com.prismml.bonsai-ambient-finance`. The installer supervises the scheduler only. Keep the model server and sampling proxy available separately before expecting an unattended model draft.

## Add the local model and Hermes

Follow the [official Prism runtime instructions](https://github.com/PrismML-Eng/Bonsai-demo) and download [Ternary Bonsai 2 27B GGUF](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf). The matching Prism runtime is required for the ternary model. The example uses a 65,536-token context, one server slot, GPU offload, the native tool template and a 512-token reasoning budget. The sampling values in `config/sampling.json` follow the model card's thinking guidance. The context and response limits are choices for this task.

Start the model in one terminal, using the real paths on your computer:

```sh
export LLAMA_SERVER=/absolute/path/to/llama-server
export BONSAI_MODEL=/absolute/path/to/Ternary-Bonsai-2-27B-PQ2_0.gguf
sh start_model.sh
```

Start the request proxy in another terminal with `python3 settings_proxy.py`. It listens on loopback port 5264, forwards to the model on port 62737, applies `config/sampling.json`, and saves each complete request and response in `exchanges/`. The proxy keeps the entire payload on the local machine and does not redact sensitive input, so choose the input data and retention policy accordingly.

Create a separate Hermes profile under the installed Hermes home. The setup command refuses to overwrite an existing profile:

```sh
python3 setup.py --out "$HOME/.hermes/profiles/ambient-finance-demo"
hermes --profile ambient-finance-demo chat --oneshot -Q --run-budget 150 -q "Read the latest fictional portfolio run and explain the open review issue."
```

To generate a scheduled work item and request an analyst draft in one command, run `python3 run_schedule.py --cadence nightly --as-of 2026-09-25 --with-hermes`. If you followed the deterministic calculation above, use `python3 run_schedule.py --cadence nightly --as-of 2026-09-25 --retry-model --with-hermes` to add the model draft to that same work item. The wrapper preserves the earlier record in `runs/attempts/`. A completed model draft cannot be retried with this command. Do not advance the sample date to bypass an existing file, because the supplied prices are valid only for September 25. The script saves the deterministic calculation before calling Hermes so that the agent can read it. The final answer is saved as `model_analysis` only when Hermes exits successfully and the matching new session contains a saved final assistant answer. CLI stdout alone is insufficient. The exit code by itself does not establish that the prose is factually correct, so the human review remains necessary.

## Review a work item

The reviewer can reject an item with a note:

```sh
python3 review.py 2026-09-25-nightly --reviewer "Demo reviewer" --decision reject_analysis --note "Refresh R-MER before using this analysis."
```

The review is appended to `runs/2026-09-25-nightly.reviews.jsonl`. The reviewer name is entered text, not a verified identity. An acceptance attempt fails while price data are blocked, research is stale or a limit issue remains open. Even an accepted analyst note would not authorize a trade. The only MCP tools are `finance_latest_run` and `finance_position`, and both are read only.

## Verify the demonstration

Run `python3 -m unittest discover -s tests -v`. The tests check scenario arithmetic, current-price blocking, missing research, incomplete scenario inputs, the schedule, retry behavior, the tool surface and the review gate. The publishable evidence in `evidence/` contains an earlier timed-out daily attempt, a nightly run that completed with a clean Hermes exit, and the first LaunchAgent-triggered daily run that blocked on stale prices without calling Hermes. The nightly session called the two read-only tools, returned a 182-word draft, and passed 14 narrow offline MLflow checks. Read `EVIDENCE.md` before describing these runs; the evaluation is not a live model trace or investment-quality review.
