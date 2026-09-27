"""Decide whether refreshed sources can reopen an unreviewed blocked item."""


def can_refresh(saved, current):
    return (
        saved.get("status") == "blocked"
        and saved.get("model_status") in ("skipped_data_gate", "not_requested")
        and saved.get("review_decision", "pending") == "pending"
        and current.get("status") == "review_required"
        and bool(saved.get("source_sha256"))
        and saved.get("source_sha256") != current.get("source_sha256")
    )
