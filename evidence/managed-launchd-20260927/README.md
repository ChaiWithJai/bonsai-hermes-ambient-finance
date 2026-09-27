# Scheduled daily review with owned model startup

The launchd job started the model and proxy, ran the September 26 daily review, and saved a 197-word final answer in Hermes and the work item. The answer fits the requested 250-word limit. It identifies the largest exposure and stale research, reports both scenarios, and asks who will obtain updated Meridian research and when. Human review remains pending.

The job used the actual local date without a historical clock override. Its input directory contains explicitly mocked September 26 prices, with provenance recorded separately. The original repository inputs were unchanged. The mocked prices do not refresh automatically, and the September 27 data check is blocked.

The first RunAtLoad attempt stopped before inference because the lab queue scanner mistook the wrapper's runtime argument for a running model. The adapter was corrected to exclude only its own PID. A launchd kickstart then completed the review. The preserved lifecycle logs retain both attempts.

Hermes took 160.2 seconds in this run. Five upstream requests consumed 28,696 input tokens and 3,192 output tokens, including an output-limit continuation. Cached input accounted for 20,338 tokens. The corrective reasoning-only branch was not invoked, and the timing is not an isolated model performance comparison.

The job stopped both owned services and released the Mac queue. The temporary LaunchAgent was unloaded, and the canonical five-minute LaunchAgent was replaced with the tested managed configuration after its previous plist was backed up. Canonical startup preserved the completed work item without another inference request. Source inputs and work items from the earlier service were retained.

The installed service requires a logged-in user and an awake Mac. Reboot recovery was not tested. The source-data integration remains a demo input provider, not a live market feed or automatically updated analyst repository.
