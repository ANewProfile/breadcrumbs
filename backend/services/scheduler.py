from datetime import date, datetime, time, timedelta

DEFAULT_MAX_CONTINUOUS_MINUTES = 90
DEFAULT_MAX_SUBJECTS_PER_DAY = 3
# How much total task time the scheduler will try to pack into a single day
# before spilling to the next one. This is the lever for "get things done as
# soon as possible without overloading the day" — days fill up toward this
# limit before a later day is touched at all.
DEFAULT_MAX_DAILY_MINUTES = 240

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}

# Being willing to work at 6:30am doesn't mean that's preferred over 3:30pm —
# these are soft windows within a day: tasks are tried here first and only
# spill outside the window when it doesn't have room.
TIME_OF_DAY_WINDOWS: dict[str, tuple[time, time]] = {
    "morning": (time(0, 0), time(12, 0)),
    "afternoon": (time(12, 0), time(17, 0)),
    "evening": (time(17, 0), time(23, 59, 59)),
}


def _sub_block(block: dict, start: datetime, end: datetime) -> dict:
    return {
        "start": start,
        "end": end,
        "duration_min": int((end - start).total_seconds() / 60),
        "streak_subject": None,
        "streak_minutes": 0,
    }


def _split_for_window(block: dict, window_start: time, window_end: time) -> tuple[list, list]:
    """
    Splits one free block around a preferred time-of-day window into
    (preferred_parts, other_parts). A block outside the window entirely comes
    back unchanged as the sole "other" part.
    """
    day = block["start"].date()
    tz = block["start"].tzinfo
    window_lo = max(block["start"], datetime.combine(day, window_start, tzinfo=tz))
    window_hi = min(block["end"], datetime.combine(day, window_end, tzinfo=tz))
    if window_lo >= window_hi:
        return [], [block]

    other = []
    if block["start"] < window_lo:
        other.append(_sub_block(block, block["start"], window_lo))
    preferred = [_sub_block(block, window_lo, window_hi)]
    if window_hi < block["end"]:
        other.append(_sub_block(block, window_hi, block["end"]))
    return preferred, other


def _distance_to_window(block: dict, window_lo: datetime, window_hi: datetime) -> timedelta:
    """
    How far a spillover block sits from the preferred window — zero if
    (somehow) overlapping, otherwise the gap to whichever edge it's on.
    Ordering spillover by this instead of raw start time means a slot right
    next to the preferred window (e.g. the evening, right after an afternoon
    preference) gets tried before a slot that's merely earlier in the day
    (e.g. before dawn) but much further from what the user actually asked for.
    """
    if block["end"] <= window_lo:
        return window_lo - block["end"]
    if block["start"] >= window_hi:
        return block["start"] - window_hi
    return timedelta(0)


def _apply_time_of_day_preference(day_blocks: dict, preferred_time_of_day: str | None) -> dict:
    window = TIME_OF_DAY_WINDOWS.get(preferred_time_of_day or "")
    if not window:
        return day_blocks
    window_start, window_end = window

    reordered: dict[date, list] = {}
    for day, blocks_for_day in day_blocks.items():
        tz = blocks_for_day[0]["start"].tzinfo
        window_lo = datetime.combine(day, window_start, tzinfo=tz)
        window_hi = datetime.combine(day, window_end, tzinfo=tz)

        preferred_parts, other_parts = [], []
        for block in blocks_for_day:
            pref, other = _split_for_window(block, window_start, window_end)
            preferred_parts.extend(pref)
            other_parts.extend(other)
        preferred_parts.sort(key=lambda b: b["start"])
        # Try the preferred window first; only spill into the rest of the day
        # once it's full — and when it does spill, try the slot closest to
        # the window first rather than whichever happens to be earliest.
        other_parts.sort(key=lambda b: (_distance_to_window(b, window_lo, window_hi), b["start"]))
        reordered[day] = preferred_parts + other_parts
    return reordered


def _urgency_bucket(task: dict, today: date) -> int:
    """
    Lower = more urgent. This only breaks ties among tasks of the same
    priority (see _sort_key) — it does not override priority. The due date's
    real teeth are elsewhere: candidate_days() refuses to place a task on or
    after its own due day no matter how it's sorted here.
    """
    due = task.get("due_date")
    if not due:
        return 4
    due_date = due if isinstance(due, date) else date.fromisoformat(due)
    days = (due_date - today).days
    if days <= 0:
        return 0
    if days == 1:
        return 1
    if days <= 7:
        return 2
    return 3


def _sort_key(task: dict, today: date):
    # Priority first: a high-priority task claims slots ahead of a
    # lower-priority one even if the lower-priority task's due date is
    # sooner. Due date only breaks ties within the same priority tier — it
    # never overrides priority, though it still hard-blocks a task from
    # landing on or after its own due day (see candidate_days) regardless of
    # this ordering. How short the task is comes next, so shorter tasks claim
    # small leftover gaps before a longer task in the same priority/urgency
    # tier can crowd them out or force them onto a different day. Subject
    # comes after that, so same-subject tasks at the same priority, urgency,
    # and length land next to each other in processing order — since
    # assignment below is a forward-filling first-fit, adjacent-in-order
    # tasks naturally end up packed into the same contiguous block
    # (cognitive-load batching), without needing a separate grouping pass.
    return (
        PRIORITY_RANK.get(task.get("priority", "medium"), 1),
        _urgency_bucket(task, today),
        round(task.get("adjusted_minutes", task["estimated_minutes"])),
        task["subject"],
        task["id"],
    )


def _task_due_date(task: dict) -> date | None:
    due = task.get("due_date")
    if not due:
        return None
    return due if isinstance(due, date) else date.fromisoformat(due)


def assign_tasks(
    tasks: list,
    free_blocks: list,
    max_continuous_minutes: int = DEFAULT_MAX_CONTINUOUS_MINUTES,
    max_subjects_per_day: int = DEFAULT_MAX_SUBJECTS_PER_DAY,
    max_daily_minutes: int = DEFAULT_MAX_DAILY_MINUTES,
    break_between_tasks_minutes: int = 0,
    break_between_subjects_minutes: int = 0,
    preferred_time_of_day: str | None = None,
) -> tuple[dict, list]:
    today = free_blocks[0]["start"].date() if free_blocks else date.today()
    tasks_sorted = sorted(tasks, key=lambda t: _sort_key(t, today))

    blocks = [dict(b, streak_subject=None, streak_minutes=0) for b in free_blocks]
    day_blocks: dict[date, list] = {}
    for b in blocks:
        day_blocks.setdefault(b["start"].date(), []).append(b)
    day_blocks = _apply_time_of_day_preference(day_blocks, preferred_time_of_day)

    day_subjects: dict[date, set] = {}
    day_minutes: dict[date, int] = {}
    assignments: dict[str, dict] = {}
    unfit_ids: list[str] = []

    def gap_for(block, subject):
        if block["streak_subject"] is None:
            return 0
        if block["streak_subject"] == subject:
            return break_between_tasks_minutes
        return break_between_subjects_minutes

    def can_place(block, subject, needed, enforce_soft_constraints):
        gap = gap_for(block, subject)
        if block["duration_min"] < needed + gap:
            return False
        if not enforce_soft_constraints:
            return True
        day = block["start"].date()
        used_today = day_subjects.get(day, set())
        if subject not in used_today and len(used_today) >= max_subjects_per_day:
            return False
        if day_minutes.get(day, 0) + needed > max_daily_minutes:
            return False
        if block["streak_subject"] == subject and block["streak_minutes"] + needed > max_continuous_minutes:
            return False
        return True

    def place(block, task, subject, needed):
        gap = gap_for(block, subject)
        if gap:
            block["start"] += timedelta(minutes=gap)
            block["duration_min"] -= gap

        end_dt = block["start"] + timedelta(minutes=needed)
        assignments[task["id"]] = {
            "start": block["start"].isoformat(),
            "end": end_dt.isoformat(),
        }
        day = block["start"].date()
        day_subjects.setdefault(day, set()).add(subject)
        day_minutes[day] = day_minutes.get(day, 0) + needed
        if block["streak_subject"] == subject:
            block["streak_minutes"] += needed
        else:
            block["streak_subject"] = subject
            block["streak_minutes"] = needed
        block["start"] = end_dt
        block["duration_min"] -= needed

    def candidate_days(task, needed):
        due_date = _task_due_date(task)
        # Hard constraint: a task is due the instant its due day starts, so it
        # must be completed on some earlier day — never on the due date itself,
        # unless the due date is today (already underway, so still fair game).
        days = [
            d for d in day_blocks
            if due_date is None
            or d < due_date
            or (due_date == today and d == due_date)
        ]
        # Always prefer the earliest eligible day: get things done as soon as
        # possible rather than holding a day back for a task whose deadline
        # happens to be further out. A day isn't skipped just because a later
        # due date exists — it's skipped only once max_daily_minutes (a soft
        # constraint enforced in can_place) says it's full, at which point
        # this ordering naturally spills onto the next earliest day.
        return sorted(days)

    def try_days(days, task, subject, needed, enforce_soft_constraints):
        for d in days:
            for block in day_blocks[d]:
                if can_place(block, subject, needed, enforce_soft_constraints):
                    place(block, task, subject, needed)
                    return True
        return False

    for task in tasks_sorted:
        subject = task["subject"]
        needed = round(task.get("adjusted_minutes", task["estimated_minutes"]))
        days = candidate_days(task, needed)

        placed = (
            try_days(days, task, subject, needed, True)
            # Soft constraints (subject-switch cap, daily-minutes cap, continuous-work cap)
            # are cognitive-load/workload preferences, not hard requirements — fall back to
            # plain duration-fit so a task never goes unschedulable just because the ideal
            # slot was already claimed.
            or try_days(days, task, subject, needed, False)
        )
        if not placed:
            unfit_ids.append(task["id"])

    return assignments, unfit_ids
