# Scheduled portfolio review

Prepare the position, scenario and research checks before the portfolio team meets. The saved draft identifies the exposure and unresolved research for the reviewer.

## How it works

Python checks source dates and calculates the portfolio results. On schedule, Hermes and local Bonsai prepare a review draft, then the worker stops its model services.

The [recorded scheduled run](evidence/managed-launchd-20260927/README.md) saved a draft asking who would obtain updated research and by when.

## Get started

With Python 3.10 or newer, review the sample portfolio as of September 25, 2026. Expect `runs/2026-09-25-nightly.json` with a $640,800 portfolio value and `review_required` status because Meridian research is stale. A live schedule requires current inputs.

```sh
git clone https://github.com/ChaiWithJai/bonsai-hermes-ambient-finance.git
cd bonsai-hermes-ambient-finance
python3 scripts/make_mock_sources.py
python3 run_schedule.py --cadence nightly --as-of 2026-09-25
```

## Resources

| Resource | Use it to |
| --- | --- |
| [Setup](docs/setup.md) | Configure Bonsai and Hermes. |
| [Scheduling](docs/managed-service.md) | Install and operate the scheduled worker. |
| [Architecture](docs/architecture.md) | Follow the tools, records and failure handling. |
| [Model parameters](docs/parameter-guide.md) | Choose settings and inspect the supporting measurements. |
| [Configuration capture](docs/recorded-configuration.md) | See the model and Hermes settings used in the recorded run. |
| [Source reading](docs/source-reading.md) | Inspect PDF citations and CSV inputs. |
| [Development](docs/development.md) | Find the implementation and run its tests. |
