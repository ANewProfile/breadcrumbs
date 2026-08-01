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
    # Subject is the secondary key (after urgency) so same-subject tasks within
    # the same urgency tier land next to each other in processing order — since
    # assignment below is a forward-filling first-fit, adjacent-in-order tasks
    # naturally end up packed into the same contiguous block (cognitive-load
    # batching), without needing a separate grouping pass.
    return (
        _urgency_bucket(task, today),
        task["subject"],
        PRIORITY_RANK.get(task.get("priority", "medium"), 1),
        task["id"],
    )


def assign_tasks(
    tasks: list,
    free_blocks: list,
    max_continuous_minutes: int = DEFAULT_MAX_CONTINUOUS_MINUTES,
    max_subjects_per_day: int = DEFAULT_MAX_SUBJECTS_PER_DAY,
) -> tuple[dict, list]:
    today = free_blocks[0]["start"].date() if free_blocks else date.today()
    tasks_sorted = sorted(tasks, key=lambda t: _sort_key(t, today))

    blocks = [dict(b, streak_subject=None, streak_minutes=0) for b in free_blocks]
    day_subjects: dict[date, set] = {}
    assignments: dict[str, dict] = {}
    unfit_ids: list[str] = []

    def can_place(block, subject, needed, enforce_soft_constraints):
        if block["duration_min"] < needed:
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
        end_dt = block["start"] + timedelta(minutes=needed)
        assignments[task["id"]] = {
            "start": block["start"].isoformat(),
            "end": end_dt.isoformat(),
        }
        day = block["start"].date()
        day_subjects.setdefault(day, set()).add(subject)
        if block["streak_subject"] == subject:
            block["streak_minutes"] += needed
        else:
            block["streak_subject"] = subject
            block["streak_minutes"] = needed
        block["start"] = end_dt
        block["duration_min"] -= needed

    for task in tasks_sorted:
        subject = task["subject"]
        needed = round(task.get("adjusted_minutes", task["estimated_minutes"]))

        block = next((b for b in blocks if can_place(b, subject, needed, True)), None)
        if block is None:
            # Soft constraints (subject-switch cap, continuous-work cap) are cognitive-load
            # preferences, not hard requirements — fall back to plain duration-fit so a task
            # never goes unschedulable just because the ideal slot was already claimed.
            block = next((b for b in blocks if can_place(b, subject, needed, False)), None)

        if block is not None:
            place(block, task, subject, needed)
        else:
            unfit_ids.append(task["id"])

    return assignments, unfit_ids
