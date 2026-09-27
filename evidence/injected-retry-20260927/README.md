# Injected failure and scheduled retry

The scheduler retried the September 25 daily work item after an injected HTTP 400 response. The isolated local endpoint reported the model available during readiness, then rejected the actual Hermes completion request. The next direct scheduler tick used the local Bonsai model and the same source hashes.

The retry made local inference requests, but Hermes exited with code 0 without saving a final assistant answer. The worker correctly returned failure and kept `model_analysis` empty. Successful recovery is not established. The first failure remains in the attempt archive, and the retry remains available for investigation.

Both ticks used an explicit historical date to match the supplied prices. They were invoked through `scheduler.tick`, not through a live launchd clock. The separate launchd test verifies current-date blocking and persistence. The experiment owned its model and proxy processes, stopped both after the failed retry, and released the Mac queue. No production work items were modified.
