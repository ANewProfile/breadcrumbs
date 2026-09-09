from datetime import date, datetime, time, timedelta

DEFAULT_MAX_CONTINUOUS_MINUTES = 90
DEFAULT_MAX_SUBJECTS_PER_DAY = 3
# A task this short barely dents a day's capacity, so it's not worth spreading
# out or holding back for a day closer to its deadline the way longer tasks
# are — just drop it into the earliest day that has room for it.
SHORT_TASK_MAX_MINUTES = 10

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


def _apply_time_of_day_preference(day_blocks: dict, preferred_time_of_day: str | None) -> dict:
    window = TIME_OF_DAY_WINDOWS.get(preferred_time_of_day or "")
    if not window:
        return day_blocks
    window_start, window_end = window

    reordered: dict[date, list] = {}
    for day, blocks_for_day in day_blocks.items():
        preferred_parts, other_parts = [], []
        for block in blocks_for_day:
            pref, other = _split_for_window(block, window_start, window_end)
            preferred_parts.extend(pref)
            other_parts.extend(other)
        preferred_parts.sort(key=lambda b: b["start"])
        other_parts.sort(key=lambda b: b["start"])
        # Try the preferred window first; only spill into the rest of the day
        # once it's full.
        reordered[day] = preferred_parts + other_parts
    return reordered


def _urgency_bucket(task: dict, today: date) -> int:
    """
    Lower = more urgent. Due date drives this, not priority — a deadline is a
    hard constraint, priority is only a tiebreaker among similarly-urgent tasks.
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
    # Due date first, then priority, then how short the task is — each only a
    # tiebreaker among tasks tied on everything before it, never overriding
    # it. Shorter tasks go next so they claim small leftover gaps before a
    # longer task in the same urgency/priority tier can crowd them out or
    # force them onto a different day. Subject comes after that, so
    # same-subject tasks at the same urgency, priority, and length land next
    # to each other in processing order — since assignment below is a
    # forward-filling first-fit, adjacent-in-order tasks naturally end up
    # packed into the same contiguous block (cognitive-load batching),
    # without needing a separate grouping pass.
    return (
        _urgency_bucket(task, today),
        PRIORITY_RANK.get(task.get("priority", "medium"), 1),
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
        if needed <= SHORT_TASK_MAX_MINUTES:
            return sorted(days)
        if due_date is None:
            # No deadline pressure: do it as soon as reasonably possible, tied
            # days broken by earliest date first.
            return sorted(days, key=lambda d: (day_minutes.get(d, 0), d))
        # A real deadline: among equally-loaded days, prefer the one closer to
        # the due date. That leaves the nearest days (today, tomorrow, ...)
        # open for tasks with tighter deadlines instead of reflexively using
        # them just because they sort first.
        return sorted(days, key=lambda d: (day_minutes.get(d, 0), -d.toordinal()))

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
            # Soft constraints (subject-switch cap, continuous-work cap) are cognitive-load
            # preferences, not hard requirements — fall back to plain duration-fit so a task
            # never goes unschedulable just because the ideal slot was already claimed.
            or try_days(days, task, subject, needed, False)
        )
        if not placed:
            unfit_ids.append(task["id"])

    return assignments, unfit_ids
