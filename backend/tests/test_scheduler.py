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
    # leaving 70 free. Tomorrow stays completely empty. A task due later
    # should still just drop into today's leftover room. the scheduler
    # always front-loads onto the earliest day with space, never holding a
    # day back for a later deadline.
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


def test_later_due_task_still_lands_on_today_when_today_has_room():
    due_tomorrow = dt(0, day_offset=1).date().isoformat()
    due_in_two_days = dt(0, day_offset=2).date().isoformat()
    tasks = [
        make_task("soon", "Math", 30, due_date=due_tomorrow),
        make_task("later", "Physics", 30, due_date=due_in_two_days),
    ]
    blocks = [make_block(9, 11, day_offset=0), make_block(9, 11, day_offset=1)]
    assignments, unfit = assign_tasks(tasks, blocks)
    today = dt(9, day_offset=0).date()
    starts = {k: datetime.fromisoformat(v["start"]) for k, v in assignments.items()}
    assert starts["soon"].date() == today
    assert starts["later"].date() == today
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


def test_high_priority_task_claims_the_slot_before_a_more_urgent_low_priority_one():
    # "urgent_low" is due today (the most urgent a task can be) while
    # "distant_high" isn't due for a week, but it's high-priority — priority
    # comes first in processing order, so it claims the only slot regardless
    # of which task's deadline is closer.
    due_today = dt(0).date().isoformat()
    due_in_a_week = dt(0, day_offset=7).date().isoformat()
    tasks = [
        make_task("urgent_low", "Reading", 30, due_date=due_today, priority="low"),
        make_task("distant_high", "Math", 30, due_date=due_in_a_week, priority="high"),
    ]
    blocks = [make_block(9, 10)]  # only 60 min, room for one 30-min task with none to spare
    assignments, unfit = assign_tasks(tasks, blocks)
    assert assignments["distant_high"]["start"] == dt(9).isoformat()
    assert assignments["urgent_low"]["start"] == dt(9, 30).isoformat()
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
    # The scheduler front-loads onto day 0 first: "a" and "b" both fit there
    # (40 + 40 = 80 minutes of uninterrupted Math, still within the 90-min
    # continuous-work cap). Only "c" overflows once a third 40-minute helping
    # would push that streak to 120 minutes, so it spills to day 1; day 0 is
    # never left idle just to spread work out preemptively.
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


def test_no_due_dates_still_pack_into_earliest_day_within_the_cap():
    tasks = [make_task(f"t{i}", "Math", 30) for i in range(3)]
    blocks = [make_block(9, 11, day_offset=i) for i in range(3)]
    assignments, unfit = assign_tasks(tasks, blocks)
    day0 = dt(9, day_offset=0).date()
    days = {datetime.fromisoformat(v["start"]).date() for v in assignments.values()}
    assert days == {day0}
    assert unfit == []


def test_daily_minutes_cap_spills_extra_tasks_to_the_next_day():
    # Same setup, but a daily cap tight enough that only two of the three
    # 30-minute tasks fit on day 0. the scheduler should hit that cap as
    # closely as possible before spilling the rest onto day 1, rather than
    # leaving day 0 under-used.
    tasks = [make_task(f"t{i}", "Math", 30) for i in range(3)]
    blocks = [make_block(9, 11, day_offset=i) for i in range(3)]
    assignments, unfit = assign_tasks(tasks, blocks, max_daily_minutes=60)
    day0 = dt(9, day_offset=0).date()
    day1 = dt(9, day_offset=1).date()
    days = sorted(datetime.fromisoformat(v["start"]).date() for v in assignments.values())
    assert days == [day0, day0, day1]
    assert unfit == []


def test_hard_due_date_cutoff_marks_task_unfit_past_due():
    # Only a block after the due date exists. The scheduler must not push
    # the task past its deadline just because a later block would fit.
    today_str = dt(0).date().isoformat()
    tasks = [make_task("late", "Math", 30, due_date=today_str)]
    blocks = [make_block(9, 10, day_offset=1)]
    assignments, unfit = assign_tasks(tasks, blocks)
    assert assignments == {}
    assert unfit == ["late"]


def test_task_never_scheduled_on_its_own_due_date():
    # A task is due the instant its due day starts, so it can't be completed
    # that day - only day+2 (before the day+3 due date) is a valid target,
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
    # Being willing to work at 8am doesn't mean it's preferred over 12pm -
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


def test_preferred_time_of_day_spillover_prefers_slot_nearest_window_over_earliest():
    # The afternoon window (12:00-17:00) has no room at all today. Only a
    # pre-dawn block and a late-evening block remain. The evening block is
    # only an hour past the window; the early block is hours before it. A
    # plain "earliest first" spillover would wrongly pick the early block
    # just because it comes first in the day.
    tasks = [make_task("t", "Math", 30)]
    blocks = [make_block(6, 7), make_block(18, 19)]
    assignments, unfit = assign_tasks(tasks, blocks, preferred_time_of_day="afternoon")
    assert assignments["t"]["start"] == dt(18).isoformat()
    assert unfit == []


def test_no_time_of_day_preference_keeps_default_earliest_first_behavior():
    tasks = [make_task("t", "Math", 30)]
    blocks = [make_block(8, 22)]
    assignments, unfit = assign_tasks(tasks, blocks)
    assert assignments["t"]["start"] == dt(8).isoformat()
    assert unfit == []


def test_due_dated_tasks_use_the_earliest_available_day_not_the_one_nearest_the_deadline():
    # Due in 4 days: day+2 and day+3 are both valid (neither is the due date
    # itself). The scheduler should grab the earliest one (day+2) and get the
    # task done as soon as possible, rather than holding it back for the day
    # closer to the deadline just because the deadline is still a few days out.
    due_str = dt(0, day_offset=4).date().isoformat()
    tasks = [make_task("t", "Math", 30, due_date=due_str)]
    blocks = [make_block(9, 11, day_offset=2), make_block(9, 11, day_offset=3)]
    assignments, unfit = assign_tasks(tasks, blocks)
    assert assignments["t"]["start"] == dt(9, day_offset=2).isoformat()
    assert unfit == []


def test_due_dated_tasks_still_spread_across_available_days_before_due():
    # Same due date, two same-subject tasks: the first takes the earliest
    # available day (day+2), and rather than exceeding the continuous-work
    # cap there, the second spills to the other available day (day+3)
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
    # Only the day right before the due date has any free block at all
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
