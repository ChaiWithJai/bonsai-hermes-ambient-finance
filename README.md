# Scheduled portfolio review

Prepare the position, scenario and research checks before the portfolio team meets. The saved draft identifies the exposure and unresolved research for the reviewer.

## How it works

Python checks source freshness and calculates the portfolio results. When a review is due, the scheduler starts local Bonsai and Hermes to explain the findings, saves the draft and stops its model services. See the [architecture](docs/architecture.md) for data flow, persistence and failure handling.

The [recorded scheduled run](evidence/managed-launchd-20260927/README.md) saved a draft asking who would obtain updated research and by when.

## Get started

The example uses sample holdings, prices and analyst assumptions. The prices are dated September 25, 2026; a live schedule requires current inputs. Python 3.10 or newer runs the sample calculation. It saves `runs/2026-09-25-nightly.json` with portfolio value $640,800 and status `review_required` because Meridian research is stale. [Setup](docs/setup.md) adds model analysis; [scheduling](docs/managed-service.md) adds automatic runs.

```sh
git clone https://github.com/ChaiWithJai/bonsai-hermes-ambient-finance.git
cd bonsai-hermes-ambient-finance
python3 scripts/make_mock_sources.py
python3 run_schedule.py --cadence nightly --as-of 2026-09-25
```

## Resources

| Resource | Use it to |
| --- | --- |
| [Setup](docs/setup.md) | Run the agent and connect its inputs. |
| [Model parameters](docs/parameter-guide.md) | Understand the settings, evidence and tuning tradeoffs. |
| [Configuration capture](docs/recorded-configuration.md) | Inspect the recorded model and Hermes settings. |
| [Source reading](docs/source-reading.md) | Inspect PDF citations and CSV inputs. |
| [Development](docs/development.md) | Find the implementation and run its tests. |
