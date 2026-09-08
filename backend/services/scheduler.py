from datetime import date, timedelta

DEFAULT_MAX_CONTINUOUS_MINUTES = 90
DEFAULT_MAX_SUBJECTS_PER_DAY = 3

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


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
    # Due date first, then priority — priority is the tiebreaker among
    # similarly-urgent tasks, ahead of subject. Subject still comes after, so
    # same-subject tasks at the same urgency *and* priority land next to each
    # other in processing order — since assignment below is a forward-filling
    # first-fit, adjacent-in-order tasks naturally end up packed into the same
    # contiguous block (cognitive-load batching), without needing a separate
    # grouping pass.
    return (
        _urgency_bucket(task, today),
        PRIORITY_RANK.get(task.get("priority", "medium"), 1),
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
) -> tuple[dict, list]:
    today = free_blocks[0]["start"].date() if free_blocks else date.today()
    tasks_sorted = sorted(tasks, key=lambda t: _sort_key(t, today))

    blocks = [dict(b, streak_subject=None, streak_minutes=0) for b in free_blocks]
    day_blocks: dict[date, list] = {}
    for b in blocks:
        day_blocks.setdefault(b["start"].date(), []).append(b)

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

    def candidate_days(task):
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
        days = candidate_days(task)

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
