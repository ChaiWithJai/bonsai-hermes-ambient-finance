# Review instruction changes

A scheduled request now names its work item explicitly, so a newer run cannot redirect a read that supplies the original ID. The model receives portfolio facts and unresolved source requirements without seeing its own changing generation status. The review command uses the same source rules and separately requires a completed draft.

The [first revised draft](../evidence/acceptance-v2-result.json) corrected the issuer-limit wording but copied an in-progress status into its conclusion. It omitted total portfolio value and exceeded the requested length. The [next draft](../evidence/acceptance-v3-result.json) restored the total, required updated research and avoided that obsolete status. Its 14 mechanical checks passed, while repetition and presentation still need editorial review.

Both were manual runs of the September 25 sample work item through local Bonsai and Hermes. The saved records include source hashes, output and elapsed time. They do not establish unattended operation, investment quality or a speedup. The original drafts are preserved for comparison, including the failed result.

Run `python3 -m unittest discover -s tests -v` for the deterministic checks. Twenty-one tests cover the existing calculations and scheduling behavior, explicit work-item selection, source review requirements and the review command. The model outputs remain development examples rather than held-out validation.

The September 26 persisted-final run verified that the scheduled worker saved the exact final answer from Hermes session `20260926_181011_a2eb5f`. That answer still offered to mark a position acceptable while R-MER was stale. The acceptance command already rejects that action. The tool now supplies explicit source-blocking state, the named research update and the available reviewer decision, and the scheduled prompt asks about obtaining those updates. The 21 deterministic checks pass; a live model replay of this intervention remains pending. The earlier output is preserved under `evidence/persisted-final-20260926/`.
