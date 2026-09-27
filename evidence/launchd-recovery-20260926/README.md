# Scheduled source check and restart

On September 26, a separate per-user launchd job invoked the current scheduler with an empty external work directory. The scheduler recorded the daily review as blocked because the September 25 prices were stale, and it skipped Hermes. Restarting the job preserved the exact work item bytes and reported `already_recorded`. The temporary job was unloaded after verification. The existing five-minute demo job was left installed.

`result.json` records the work item hash, and `scheduler.log` contains both invocations. The adjacent work item contains the blocked source checks. No inference request was made, so the run verifies scheduling and persistence only.

The accompanying code change retries a failed model draft on later checks, with at most two automatic retries and an archive of each earlier attempt. Tests cover the retry limit, unchanged source requirement and nonzero exit when Hermes has no saved final answer. A live model failure followed by a scheduled successful retry remains unverified.
