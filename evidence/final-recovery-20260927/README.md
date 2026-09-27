# Completed retry of a failed portfolio review

The scheduler retried a copy of the earlier failed September 25 daily work item in a separate local queue. Hermes saved a 201-word final answer, and the worker verified the exact answer in the session database before marking the draft complete. A later tick returned `already_recorded` without another model request.

The draft identifies Helix Health as the largest position and Meridian Payments as the position needing current research. It reports both scenario values correctly and asks who will obtain the research and when. Acceptance remains unavailable until the source issue is resolved. Human approval remains pending.

The proxy's corrective branch was present but did not trigger. All three model responses followed the ordinary path, so the experiment verifies successful retry and persistence, not live recovery from a reasoning-only response. The corrective branch remains covered by CPU regression tests only. Usage includes 14,960 input tokens and 1,103 output tokens, with 8,691 cached input tokens. Corrective usage was zero.

The invocation used `scheduler.tick` and an explicit historical date matching the sample prices. It does not establish wall-clock unattended inference. Both owned services were stopped and the shared Mac queue was released after the experiment. The previous failed queue and its evidence were left intact.
