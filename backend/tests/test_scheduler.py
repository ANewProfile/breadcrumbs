from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from services.scheduler import assign_tasks

TZ = ZoneInfo("America/New_York")


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2024, 6, 12, hour, minute, tzinfo=TZ)


def make_block(start_hour, end_hour):
    s, e = dt(start_hour), dt(end_hour)
    return {"start": s, "end": e, "duration_min": int((e - s).total_seconds() / 60)}


def make_task(id_, subject, estimated_minutes):
    return {"id": id_, "subject": subject, "estimated_minutes": estimated_minutes}


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
