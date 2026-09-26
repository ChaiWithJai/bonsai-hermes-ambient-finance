# How a portfolio review is prepared

The workstation prepares a dated work item for a portfolio manager. Python calculates exposures and stated scenarios, while Hermes asks the local Bonsai model to explain the positions and unresolved research. The manager receives a draft with the source identifiers needed to investigate it.

## Data and calculation

`fixtures/portfolio.json` supplies positions, prices, limits and scenario shocks. `fixtures/research.json` supplies research dates and summaries. Linked PDFs and CSV files are checked for existence; the current tools do not extract their contents. Replacing the fixtures with a governed source is an integration step.

`finance.calculate` checks prices and research before returning the calculation. Stale prices block model generation. Stale research permits a draft that identifies the issue, but prevents acceptance. Each work item records the input hashes and its effective date.

## Model and tools

`run_schedule.py` writes the work item before invoking Hermes. The prompt names its exact run ID. `finance_latest_run` accepts that ID, and `finance_position` returns a position with its research summary. Omitting the run ID selects the most recently modified work-item file, which is useful for browsing but unsuitable for identifying a particular scheduled task.

Hermes calls the loopback proxy on port 5264. The proxy applies `sampling.json`, forwards the request to Bonsai on port 62737 and saves the full request and response locally. Both tools are read only. The model cannot place a trade or modify the portfolio through them.

The position tool reads the current fixtures rather than an immutable per-run source snapshot. Keep the fixtures unchanged during a run. Versioned snapshots are still needed before supporting concurrent source refresh and analysis.

## Review and persistence

Work items are stored under `runs/`. An ordinary retry refuses to overwrite an existing item. A model retry archives the previous attempt and removes its obsolete draft before requesting another analysis. Completed model drafts are not eligible for that retry path.

The work-item response exposes `source_review_requirements`, sharing its source and limit rules with `review.py`. Draft-generation status and previous model text remain in the stored record, outside the model's fact response. The review command separately checks whether a completed draft exists. Acceptance requires usable source data, no unresolved research or limit issue, and a completed model draft. A rejected draft can carry a reviewer note. Reviewer names are entered text; the demonstration does not authenticate reviewers. No review decision authorizes trading.

## Scheduling and operation

The scheduler checks daily, nightly, weekly and quarterly periods in America/New_York. The macOS installer starts that scheduler at login and every five minutes. It does not start or supervise Bonsai or the request proxy, and missed dates are not backfilled. Continuous operation therefore requires service supervision and a fresh source feed beyond the current installer.

Full model exchanges remain on disk and can contain the supplied portfolio data. Keep access to the workstation and its evidence directories consistent with the data's permissions. MLflow's current evaluator records checks of captured results; it is separate from online model tracing.
