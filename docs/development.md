# Development

| Location | What to change |
| --- | --- |
| `finance.py` | Portfolio arithmetic, source checks and read-only model tools. |
| `run_schedule.py`, `scheduler.py` | Work-item persistence, cadence and retry behavior. |
| `managed_tick.py` | Model startup, readiness checks and cleanup. |
| `review.py` | Human decisions and acceptance checks. |
| `fixtures/`, `mock-drive/`, `mock-sheets/` | Sample inputs and generated report files. |
| `config/`, `scripts/` | Agent settings, service helpers and sample generation. |
| `tests/` | Source, persistence and scheduling regression checks. |
| `docs/`, `evidence/` | Operating guides and recorded runs. |

Run `python3 -m unittest discover -s tests -v` after changing the workflow. Keep generated drafts and runtime state in their configured data directories; the source checkout contains the implementation and sample inputs.
