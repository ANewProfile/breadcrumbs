from datetime import datetime, timezone

MIN_SAMPLES_FOR_HISTORY = 5
HISTORICAL_WEIGHT = 0.6
USER_ESTIMATE_WEIGHT = 0.4
RECENCY_DECAY = 0.85

# Sentinel for completions recorded before completed_at existed — sorts last
# (lowest recency weight) rather than crashing on a missing timestamp.
_MISSING_COMPLETED_AT = datetime.min.replace(tzinfo=timezone.utc)


def compute_subject_history(tasks_collection, user_id, subject: str) -> list[dict]:
    """
    One entry per completed task *of this user* in this subject, capturing how
    its actual duration compared to what the user predicted for it specifically
    (actual_minutes / estimated_minutes), plus when it was completed.

    This is deliberately relative, not absolute: a subject where tasks "just
    run long" produces ratios > 1 regardless of whether individual tasks are
    5 minutes or 5 hours, so the correction transfers across task sizes within
    the subject instead of anchoring to one historical average duration.
    """
    cursor = tasks_collection.find(
        {"user_id": user_id, "subject": subject, "status": "done"},
        {"estimated_minutes": 1, "actual_minutes": 1, "completed_at": 1},
    )
    history: list[dict] = []
    for doc in cursor:
        estimated = doc.get("estimated_minutes")
        if not estimated:
            continue
        completed_at = doc.get("completed_at") or _MISSING_COMPLETED_AT
        for actual in doc.get("actual_minutes", []):
            history.append({"ratio": actual / estimated, "completed_at": completed_at})
    return history


def weighted_estimate(user_estimate: int, history: list[dict]) -> tuple[float, bool]:
    """
    Scales the user's estimate for this task by a recency-weighted average of
    how far off their past estimates in this subject have run — rather than
    blending toward this subject's average absolute duration. More recent
    completions count more (exponential decay by recency rank), so a recent
    shift in pace outweighs an old one. Blends the correction factor toward
    1.0 (no adjustment) rather than fully trusting it, and only applies once
    there's enough history to trust.
    """
    if len(history) < MIN_SAMPLES_FOR_HISTORY:
        return float(user_estimate), False

    ordered = sorted(history, key=lambda h: h["completed_at"], reverse=True)
    weights = [RECENCY_DECAY**i for i in range(len(ordered))]
    weighted_ratio = sum(w * h["ratio"] for w, h in zip(weights, ordered)) / sum(weights)

    blended_ratio = HISTORICAL_WEIGHT * weighted_ratio + USER_ESTIMATE_WEIGHT * 1.0
    return user_estimate * blended_ratio, True
