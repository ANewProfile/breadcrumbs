from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from services.scheduler import assign_tasks

TZ = ZoneInfo("America/New_York")


def dt(hour: int, minute: int = 0, day_offset: int = 0) -> datetime:
    base = datetime(2024, 6, 12, hour, minute, tzinfo=TZ)
    return base + timedelta(days=day_offset)


def make_block(start_hour, end_hour, day_offset: int = 0):
    s, e = dt(start_hour, day_offset=day_offset), dt(end_hour, day_offset=day_offset)
    return {"start": s, "end": e, "duration_min": int((e - s).total_seconds() / 60)}


def make_task(id_, subject, estimated_minutes, due_date=None, priority=None):
    task = {"id": id_, "subject": subject, "estimated_minutes": estimated_minutes}
    if due_date is not None:
        task["due_date"] = due_date
    if priority is not None:
        task["priority"] = priority
    return task


def test_single_task_fits():
    tasks = [make_task("abc", "Math", 30)]
    blocks = [make_block(9, 11)]
    assignments, unfit = assign_tasks(tasks, blocks)
    assert "abc" in assignments
    assert assignments["abc"]["start"] == dt(9).isoformat()
    assert assignments["abc"]["end"] == dt(9, 30).isoformat()
    assert unfit == []


def test_task_too_large_skipped():
    tasks = [make_task("abc", "Math", 120)]
    blocks = [make_block(9, 10)]  # only 60 min
    assignments, unfit = assign_tasks(tasks, blocks)
    assert assignments == {}
    assert unfit == ["abc"]


def test_block_shrinks_after_assignment():
    tasks = [
        make_task("a", "Math", 30),
        make_task("b", "Math", 30),
    ]
    blocks = [make_block(9, 11)]  # 120 min
    assignments, unfit = assign_tasks(tasks, blocks)
    assert "a" in assignments
    assert "b" in assignments
    # tasks sorted by subject (both "Math"), both fit in the single block
    assert assignments["a"]["end"] == assignments["b"]["start"]
    assert unfit == []


def test_tasks_sorted_by_subject():
    tasks = [
        make_task("z", "Physics", 30),
        make_task("a", "Biology", 30),
    ]
    blocks = [make_block(9, 10)]  # 60 min, fits both
    assignments, unfit = assign_tasks(tasks, blocks)
    # Biology comes first alphabetically, so "a" gets the earlier slot
    assert assignments["a"]["start"] == dt(9).isoformat()
    assert assignments["z"]["start"] == dt(9, 30).isoformat()
    assert unfit == []


def test_empty_tasks():
    assignments, unfit = assign_tasks([], [make_block(9, 11)])
    assert assignments == {}
    assert unfit == []


def test_empty_blocks():
    tasks = [make_task("a", "Math", 30)]
    assignments, unfit = assign_tasks(tasks, [])
    assert assignments == {}
    assert unfit == ["a"]


def test_adjusted_minutes_overrides_estimated_minutes():
    task = make_task("a", "Math", 30)
    task["adjusted_minutes"] = 50
    blocks = [make_block(9, 11)]  # 120 min
    assignments, unfit = assign_tasks([task], blocks)
    # block should be sized to the adjusted (historically-informed) estimate, not the raw one
    assert assignments["a"]["end"] == dt(9, 50).isoformat()
    assert unfit == []


def test_spills_to_next_block():
    tasks = [
        make_task("a", "Math", 60),
        make_task("b", "Math", 60),
    ]
    blocks = [make_block(9, 10), make_block(14, 16)]  # 60 min, then 120 min
    assignments, unfit = assign_tasks(tasks, blocks)
    assert "a" in assignments
    assert "b" in assignments
    assert assignments["a"]["start"] == dt(9).isoformat()
    assert assignments["b"]["start"] == dt(14).isoformat()
    assert unfit == []


def test_due_date_urgency_beats_subject_alphabetical_order():
    # "Zoology" would lose to "Art" alphabetically, but it's due today —
    # a hard deadline outranks alphabetical/subject grouping.
    today_str = dt(0).date().isoformat()
    tasks = [
        make_task("art_task", "Art", 30, due_date=None),
        make_task("zoology_task", "Zoology", 30, due_date=today_str),
    ]
    blocks = [make_block(9, 10)]  # 60 min, fits both
    assignments, unfit = assign_tasks(tasks, blocks)
    assert assignments["zoology_task"]["start"] == dt(9).isoformat()
    assert assignments["art_task"]["start"] == dt(9, 30).isoformat()
    assert unfit == []


def test_priority_breaks_ties_within_same_urgency():
    tasks = [
        make_task("low", "Biology", 30, priority="low"),
        make_task("high", "Biology", 30, priority="high"),
    ]
    blocks = [make_block(9, 10)]
    assignments, unfit = assign_tasks(tasks, blocks)
    assert assignments["high"]["start"] == dt(9).isoformat()
    assert assignments["low"]["start"] == dt(9, 30).isoformat()
    assert unfit == []


def test_same_subject_tasks_batch_contiguously_even_when_interleaved():
    # Submitted interleaved (Math, Physics, Math) — the scheduler should still
    # cluster same-subject tasks together rather than round-robining them.
    tasks = [
        make_task("m1", "Math", 20),
        make_task("p1", "Physics", 20),
        make_task("m2", "Math", 20),
    ]
    blocks = [make_block(9, 10)]  # 60 min
    assignments, unfit = assign_tasks(tasks, blocks)
    math_starts = sorted([assignments["m1"]["start"], assignments["m2"]["start"]])
    assert math_starts == [dt(9).isoformat(), dt(9, 20).isoformat()]
    assert assignments["p1"]["start"] == dt(9, 40).isoformat()
    assert unfit == []


def test_continuous_work_cap_pushes_overflow_to_another_block():
    tasks = [
        make_task("a", "Math", 40),
        make_task("b", "Math", 40),
        make_task("c", "Math", 40),
    ]
    # Two same-day-capacity blocks on different days, each with plenty of room.
    blocks = [make_block(9, 11, day_offset=0), make_block(9, 11, day_offset=1)]
    assignments, unfit = assign_tasks(tasks, blocks, max_continuous_minutes=90)
    # First two (80 min) fit within the cap on day 0; the third would push the
    # streak to 120 > 90, so it should be pushed onto day 1 instead.
    day0 = dt(9, day_offset=0).date()
    day1 = dt(9, day_offset=1).date()
    starts = {k: datetime.fromisoformat(v["start"]) for k, v in assignments.items()}
    assert starts["a"].date() == day0
    assert starts["b"].date() == day0
    assert starts["c"].date() == day1
    assert unfit == []


def test_subject_switch_cap_pushes_new_subject_to_another_day():
    tasks = [
        make_task("math_task", "Math", 60),
        make_task("physics_task", "Physics", 60),
    ]
    blocks = [make_block(9, 11, day_offset=0), make_block(9, 11, day_offset=1)]
    assignments, unfit = assign_tasks(tasks, blocks, max_subjects_per_day=1)
    day0 = dt(9, day_offset=0).date()
    day1 = dt(9, day_offset=1).date()
    starts = {k: datetime.fromisoformat(v["start"]) for k, v in assignments.items()}
    assert starts["math_task"].date() == day0
    assert starts["physics_task"].date() == day1
    assert unfit == []


def test_soft_constraints_fall_back_when_no_alternative_block_exists():
    # Only one block exists, so exceeding the continuous-work cap is better
    # than marking the task unschedulable.
    tasks = [
        make_task("a", "Math", 40),
        make_task("b", "Math", 40),
        make_task("c", "Math", 40),
    ]
    blocks = [make_block(9, 11)]  # single 120-min block, no alternative day
    assignments, unfit = assign_tasks(tasks, blocks, max_continuous_minutes=90)
    assert set(assignments.keys()) == {"a", "b", "c"}
    assert unfit == []
