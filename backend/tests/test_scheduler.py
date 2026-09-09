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


def test_priority_beats_subject_within_same_urgency():
    # "Art" would win over "Zoology" alphabetically, but "Zoology" is
    # high-priority and "Art" is low — priority is the tiebreaker ahead of
    # subject, not after it.
    tasks = [
        make_task("art_task", "Art", 30, priority="low"),
        make_task("zoology_task", "Zoology", 30, priority="high"),
    ]
    blocks = [make_block(9, 10)]  # 60 min, fits both
    assignments, unfit = assign_tasks(tasks, blocks)
    assert assignments["zoology_task"]["start"] == dt(9).isoformat()
    assert assignments["art_task"]["start"] == dt(9, 30).isoformat()
    assert unfit == []


def test_shorter_task_beats_subject_within_same_urgency_and_priority():
    # "Art" would win over "Zoology" alphabetically, and both are the same
    # priority, but "Zoology" is the shorter task — length is the tiebreaker
    # ahead of subject, right after priority.
    tasks = [
        make_task("art_task", "Art", 30),
        make_task("zoology_task", "Zoology", 10),
    ]
    blocks = [make_block(9, 10)]  # 60 min, fits both
    assignments, unfit = assign_tasks(tasks, blocks)
    assert assignments["zoology_task"]["start"] == dt(9).isoformat()
    assert assignments["art_task"]["start"] == dt(9, 10).isoformat()
    assert unfit == []


def test_short_task_fills_todays_leftover_room_instead_of_an_emptier_day():
    # "filler" is due tomorrow, so it's processed first and forced onto today
    # (see the due-date exclusion tests), using 50 of today's 120 minutes and
    # leaving 70 free. Tomorrow stays completely empty. A quick 10-minute
    # task due later should still just drop into today's leftover room
    # rather than jumping to the emptier day the way a longer task would.
    due_tomorrow = dt(0, day_offset=1).date().isoformat()
    due_later = dt(0, day_offset=4).date().isoformat()
    tasks = [
        make_task("filler", "Math", 50, due_date=due_tomorrow),
        make_task("quick", "Reading", 10, due_date=due_later),
    ]
    blocks = [make_block(9, 11, day_offset=0), make_block(9, 11, day_offset=1)]
    assignments, unfit = assign_tasks(tasks, blocks)
    today = dt(9, day_offset=0).date()
    starts = {k: datetime.fromisoformat(v["start"]) for k, v in assignments.items()}
    assert starts["filler"].date() == today
    assert starts["quick"].date() == today
    assert unfit == []


def test_nearer_due_task_keeps_today_while_later_due_task_uses_tomorrow():
    # One task due tomorrow (must be done today — see the due-date exclusion
    # tests) and one due in two days, competing for the same two days of
    # room. The due-tomorrow task can only use today; the due-in-two-days
    # task should be pushed to tomorrow rather than also grabbing today, even
    # though today technically has room for both.
    due_tomorrow = dt(0, day_offset=1).date().isoformat()
    due_in_two_days = dt(0, day_offset=2).date().isoformat()
    tasks = [
        make_task("soon", "Math", 30, due_date=due_tomorrow),
        make_task("later", "Physics", 30, due_date=due_in_two_days),
    ]
    blocks = [make_block(9, 11, day_offset=0), make_block(9, 11, day_offset=1)]
    assignments, unfit = assign_tasks(tasks, blocks)
    today = dt(9, day_offset=0).date()
    tomorrow = dt(9, day_offset=1).date()
    starts = {k: datetime.fromisoformat(v["start"]) for k, v in assignments.items()}
    assert starts["soon"].date() == today
    assert starts["later"].date() == tomorrow
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
    # With no due dates, the scheduler actively load-balances across both
    # available days rather than packing everything into day 0: "a" lands on
    # the (tied, earliest) day 0, "b" then prefers the still-empty day 1, and
    # "c" comes back to day 0 since 40+40=80 is still within the 90-min cap.
    day0 = dt(9, day_offset=0).date()
    day1 = dt(9, day_offset=1).date()
    starts = {k: datetime.fromisoformat(v["start"]) for k, v in assignments.items()}
    assert starts["a"].date() == day0
    assert starts["b"].date() == day1
    assert starts["c"].date() == day0
    # The continuous-work cap is still respected: day 0 never accrues more
    # than 90 minutes of uninterrupted Math (40 + 40 = 80 here).
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


def test_break_between_tasks_inserts_gap_for_same_subject():
    tasks = [
        make_task("a", "Math", 30),
        make_task("b", "Math", 30),
    ]
    blocks = [make_block(9, 11)]  # 120 min
    assignments, unfit = assign_tasks(tasks, blocks, break_between_tasks_minutes=10)
    assert assignments["a"]["end"] == dt(9, 30).isoformat()
    # 10-minute gap after "a" ends, not immediately back-to-back
    assert assignments["b"]["start"] == dt(9, 40).isoformat()
    assert unfit == []


def test_break_between_subjects_only_applies_on_subject_switch():
    tasks = [
        make_task("m", "Math", 30),
        make_task("p", "Physics", 30),
    ]
    blocks = [make_block(9, 11)]  # 120 min
    assignments, unfit = assign_tasks(tasks, blocks, break_between_subjects_minutes=15)
    assert assignments["m"]["end"] == dt(9, 30).isoformat()
    # 15-minute gap since the subject changed from Math to Physics
    assert assignments["p"]["start"] == dt(9, 45).isoformat()
    assert unfit == []


def test_no_due_dates_actively_spread_across_available_days():
    # Three same-subject tasks, three days each with plenty of room and no
    # due-date pressure — the scheduler should load-balance one per day
    # rather than packing all three into day 0.
    tasks = [make_task(f"t{i}", "Math", 30) for i in range(3)]
    blocks = [make_block(9, 11, day_offset=i) for i in range(3)]
    assignments, unfit = assign_tasks(tasks, blocks)
    days = sorted(datetime.fromisoformat(v["start"]).date() for v in assignments.values())
    assert days == [dt(9, day_offset=i).date() for i in range(3)]
    assert unfit == []


def test_hard_due_date_cutoff_marks_task_unfit_past_due():
    # Only a block after the due date exists — the scheduler must not push
    # the task past its deadline just because a later block would fit.
    today_str = dt(0).date().isoformat()
    tasks = [make_task("late", "Math", 30, due_date=today_str)]
    blocks = [make_block(9, 10, day_offset=1)]
    assignments, unfit = assign_tasks(tasks, blocks)
    assert assignments == {}
    assert unfit == ["late"]


def test_task_never_scheduled_on_its_own_due_date():
    # A task is due the instant its due day starts, so it can't be completed
    # that day — only day+2 (before the day+3 due date) is a valid target,
    # even though day+3 also has an empty block.
    due_str = dt(0, day_offset=3).date().isoformat()
    tasks = [make_task("t", "Math", 30, due_date=due_str)]
    blocks = [make_block(9, 11, day_offset=2), make_block(9, 11, day_offset=3)]
    assignments, unfit = assign_tasks(tasks, blocks)
    assert assignments["t"]["start"] == dt(9, day_offset=2).isoformat()
    assert unfit == []


def test_task_due_today_can_still_be_scheduled_today():
    # Exception to the rule above: if the due date IS today, today is already
    # underway and still the only chance to get it done.
    today_str = dt(0).date().isoformat()
    tasks = [make_task("t", "Math", 30, due_date=today_str)]
    blocks = [make_block(9, 11, day_offset=0)]
    assignments, unfit = assign_tasks(tasks, blocks)
    assert assignments["t"]["start"] == dt(9, day_offset=0).isoformat()
    assert unfit == []


def test_preferred_time_of_day_places_task_within_that_window():
    # Being willing to work at 8am doesn't mean it's preferred over 12pm —
    # with the whole day free, an "afternoon" preference should land the
    # task at the start of the afternoon window, not the start of the day.
    tasks = [make_task("t", "Math", 30)]
    blocks = [make_block(8, 22)]
    assignments, unfit = assign_tasks(tasks, blocks, preferred_time_of_day="afternoon")
    assert assignments["t"]["start"] == dt(12).isoformat()
    assert unfit == []


def test_preferred_time_of_day_spills_into_rest_of_day_once_window_is_full():
    # Afternoon (12:00-17:00) only has 300 minutes of room. The first
    # same-sized task fills most of it; the second can't fit what's left of
    # the window, so it should spill into the morning (the next-earliest
    # remaining time) rather than going unfit or jumping to another day.
    tasks = [
        make_task("a", "Math", 200),
        make_task("b", "Math", 200),
    ]
    blocks = [make_block(8, 22)]
    assignments, unfit = assign_tasks(
        tasks, blocks, preferred_time_of_day="afternoon", max_continuous_minutes=999
    )
    assert assignments["a"]["start"] == dt(12).isoformat()
    assert assignments["b"]["start"] == dt(8).isoformat()
    assert unfit == []


def test_no_time_of_day_preference_keeps_default_earliest_first_behavior():
    tasks = [make_task("t", "Math", 30)]
    blocks = [make_block(8, 22)]
    assignments, unfit = assign_tasks(tasks, blocks)
    assert assignments["t"]["start"] == dt(8).isoformat()
    assert unfit == []


def test_due_dated_tasks_prefer_the_day_closer_to_the_deadline_when_tied():
    # Due in 4 days: day+2 and day+3 are both valid (neither is the due date
    # itself) and tied on load, so the scheduler should use the day closer to
    # the deadline (day+3) first — leaving day+2 (nearer to now) open for
    # whatever might need it more urgently — rather than reflexively filling
    # the earlier day just because it sorts first.
    due_str = dt(0, day_offset=4).date().isoformat()
    tasks = [make_task("t", "Math", 30, due_date=due_str)]
    blocks = [make_block(9, 11, day_offset=2), make_block(9, 11, day_offset=3)]
    assignments, unfit = assign_tasks(tasks, blocks)
    assert assignments["t"]["start"] == dt(9, day_offset=3).isoformat()
    assert unfit == []


def test_due_dated_tasks_still_spread_across_available_days_before_due():
    # Same due date, two same-subject tasks: the first takes the day closer
    # to the deadline (day+3), and rather than exceeding the continuous-work
    # cap there, the second spreads to the other available day (day+2) —
    # no soft-constraint relaxation needed since a whole other day is free.
    due_str = dt(0, day_offset=4).date().isoformat()
    tasks = [
        make_task("a", "Math", 30, due_date=due_str),
        make_task("b", "Math", 30, due_date=due_str),
    ]
    blocks = [make_block(9, 11, day_offset=2), make_block(9, 11, day_offset=3)]
    assignments, unfit = assign_tasks(tasks, blocks, max_continuous_minutes=30)
    starts = {k: datetime.fromisoformat(v["start"]) for k, v in assignments.items()}
    days_used = {starts["a"].date(), starts["b"].date()}
    assert days_used == {dt(9, day_offset=2).date(), dt(9, day_offset=3).date()}
    assert unfit == []


def test_only_day_before_due_date_available_is_still_used():
    # Only the day right before the due date has any free block at all —
    # better to use it than to leave the task unschedulable.
    due_str = dt(0, day_offset=3).date().isoformat()
    tasks = [make_task("t", "Math", 30, due_date=due_str)]
    blocks = [make_block(9, 10, day_offset=2)]
    assignments, unfit = assign_tasks(tasks, blocks)
    assert assignments["t"]["start"] == dt(9, day_offset=2).isoformat()
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
