from datetime import datetime, timezone
from unittest.mock import MagicMock
from bson import ObjectId
from services.reschedule import overlaps, find_conflicting_task, find_conflicting_gcal_event


def dt(hour, minute=0):
    return datetime(2026, 8, 5, hour, minute, tzinfo=timezone.utc)


def test_overlaps_true_for_intersecting_ranges():
    assert overlaps(dt(9), dt(10), dt(9, 30), dt(10, 30)) is True


def test_overlaps_false_for_adjacent_ranges():
    # back-to-back, touching but not overlapping
    assert overlaps(dt(9), dt(10), dt(10), dt(11)) is False


def test_overlaps_false_for_disjoint_ranges():
    assert overlaps(dt(9), dt(10), dt(11), dt(12)) is False


def test_find_conflicting_task_detects_overlap_and_excludes_self():
    other_id = ObjectId()
    self_id = ObjectId()
    user_id = ObjectId()
    mock_collection = MagicMock()
    mock_collection.find.return_value = [
        {
            "_id": other_id,
            "title": "Other task",
            "scheduled_blocks": [{"start": dt(9).isoformat(), "end": dt(10).isoformat()}],
        }
    ]

    conflict = find_conflicting_task(mock_collection, user_id, str(self_id), dt(9, 30), dt(10, 30))

    mock_collection.find.assert_called_once_with(
        {"status": "scheduled", "user_id": user_id, "_id": {"$ne": self_id}}
    )
    assert conflict is not None
    assert conflict["title"] == "Other task"


def test_find_conflicting_task_returns_none_when_no_overlap():
    mock_collection = MagicMock()
    mock_collection.find.return_value = [
        {
            "_id": ObjectId(),
            "title": "Other task",
            "scheduled_blocks": [{"start": dt(9).isoformat(), "end": dt(10).isoformat()}],
        }
    ]

    conflict = find_conflicting_task(mock_collection, ObjectId(), str(ObjectId()), dt(11), dt(12))
    assert conflict is None


def gcal_event(event_id, start, end):
    return {
        "id": event_id,
        "summary": "Existing event",
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
    }


def test_find_conflicting_gcal_event_detects_overlap():
    events = [gcal_event("evt1", dt(9), dt(10))]
    conflict = find_conflicting_gcal_event(events, exclude_event_id=None, new_start=dt(9, 30), new_end=dt(10, 30))
    assert conflict is not None
    assert conflict["id"] == "evt1"


def test_find_conflicting_gcal_event_excludes_own_event():
    events = [gcal_event("own_event", dt(9), dt(10))]
    conflict = find_conflicting_gcal_event(events, exclude_event_id="own_event", new_start=dt(9, 30), new_end=dt(10, 30))
    assert conflict is None


def test_find_conflicting_gcal_event_skips_all_day_events():
    all_day_event = {"id": "allday", "summary": "Holiday", "start": {"date": "2026-08-05"}, "end": {"date": "2026-08-06"}}
    conflict = find_conflicting_gcal_event([all_day_event], exclude_event_id=None, new_start=dt(9), new_end=dt(10))
    assert conflict is None
