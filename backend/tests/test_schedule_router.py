from unittest.mock import patch
from bson import ObjectId
import pytest
from fastapi import HTTPException
from routers.schedule import run_schedule, reschedule_missed

USER = {"_id": ObjectId()}

BASE_SETTINGS = {
    "lookahead_days": 7, "day_start": "08:00", "day_end": "22:00", "timezone": "UTC",
    "max_continuous_minutes": 90, "max_subjects_per_day": 3,
    "break_between_tasks_minutes": 0, "break_between_subjects_minutes": 0,
    "preferred_time_of_day": "no_preference",
}


@patch("routers.schedule.get_credentials_for_user")
@patch("routers.schedule.get_settings")
def test_run_schedule_returns_400_when_google_disconnected(mock_get_settings, mock_get_creds):
    mock_get_settings.return_value = {"lookahead_days": 7}
    mock_get_creds.side_effect = ValueError("User has not connected a Google account")

    with pytest.raises(HTTPException) as exc_info:
        run_schedule(USER)

    assert exc_info.value.status_code == 400
    assert "reconnect" in exc_info.value.detail.lower()


@patch("routers.schedule.get_events")
@patch("routers.schedule.get_credentials_for_user")
@patch("routers.schedule.no_go_zones_collection")
@patch("routers.schedule.tasks_collection")
@patch("routers.schedule.get_settings")
def test_run_schedule_dev_user_skips_google_entirely(
    mock_get_settings, mock_tasks_collection, mock_no_go_zones_collection, mock_get_creds, mock_get_events
):
    mock_get_settings.return_value = {
        "lookahead_days": 7, "day_start": "08:00", "day_end": "22:00", "timezone": "UTC",
    }
    mock_no_go_zones_collection.find.return_value = []
    mock_tasks_collection.find.return_value = []
    dev_user = {"_id": ObjectId(), "is_dev_user": True}

    with pytest.raises(HTTPException) as exc_info:
        run_schedule(dev_user)

    assert exc_info.value.status_code == 400
    assert "no pending tasks" in exc_info.value.detail.lower()
    mock_get_creds.assert_not_called()
    mock_get_events.assert_not_called()


@patch("routers.schedule.assign_tasks")
@patch("routers.schedule.compute_free_blocks")
@patch("routers.schedule.weighted_estimate")
@patch("routers.schedule.compute_subject_history")
@patch("routers.schedule.update_gcal_event")
@patch("routers.schedule.create_gcal_event")
@patch("routers.schedule.get_events")
@patch("routers.schedule.get_credentials_for_user")
@patch("routers.schedule.no_go_zones_collection")
@patch("routers.schedule.tasks_collection")
@patch("routers.schedule.get_settings")
def test_run_schedule_includes_and_moves_already_scheduled_tasks(
    mock_get_settings,
    mock_tasks_collection,
    mock_no_go_zones_collection,
    mock_get_creds,
    mock_get_events,
    mock_create_event,
    mock_update_event,
    mock_compute_history,
    mock_weighted_estimate,
    mock_compute_free_blocks,
    mock_assign_tasks,
):
    mock_get_settings.return_value = BASE_SETTINGS
    mock_get_creds.return_value = "creds"
    mock_get_events.return_value = [
        {"id": "existing-gcal-id", "start": {"dateTime": "2026-01-01T09:00:00-05:00"}, "end": {"dateTime": "2026-01-01T10:00:00-05:00"}},
        {"id": "unrelated-event", "start": {"dateTime": "2026-01-01T11:00:00-05:00"}, "end": {"dateTime": "2026-01-01T12:00:00-05:00"}},
    ]
    mock_no_go_zones_collection.find.return_value = []
    scheduled_task_id = str(ObjectId())
    mock_tasks_collection.find.return_value = [
        {
            "_id": ObjectId(scheduled_task_id), "user_id": USER["_id"], "title": "Existing", "subject": "Math",
            "estimated_minutes": 60, "status": "scheduled", "gcal_event_id": "existing-gcal-id",
            "scheduled_blocks": [{"start": "2026-01-01T09:00:00-05:00", "end": "2026-01-01T10:00:00-05:00"}],
        },
    ]
    mock_compute_history.return_value = []
    mock_weighted_estimate.return_value = (60.0, False)
    mock_compute_free_blocks.return_value = []
    mock_assign_tasks.return_value = (
        {scheduled_task_id: {"start": "2026-01-01T13:00:00-05:00", "end": "2026-01-01T14:00:00-05:00"}},
        [],
    )

    run_schedule(USER)

    # "scheduled" tasks are included in the re-run, not just pending/unschedulable ones.
    find_query = mock_tasks_collection.find.call_args[0][0]
    assert set(find_query["status"]["$in"]) == {"pending", "unschedulable", "scheduled"}

    # The task's own existing event is excluded from the busy-time calculation
    # so it doesn't block itself from being moved.
    events_passed_to_free_blocks = mock_compute_free_blocks.call_args[0][0]
    assert [e["id"] for e in events_passed_to_free_blocks] == ["unrelated-event"]

    # Moving it updates the existing event rather than creating a duplicate.
    mock_update_event.assert_called_once_with(
        "creds", "existing-gcal-id",
        start_iso="2026-01-01T13:00:00-05:00", end_iso="2026-01-01T14:00:00-05:00",
    )
    mock_create_event.assert_not_called()


@patch("routers.schedule.assign_tasks")
@patch("routers.schedule.compute_free_blocks")
@patch("routers.schedule.weighted_estimate")
@patch("routers.schedule.compute_subject_history")
@patch("routers.schedule.delete_gcal_event")
@patch("routers.schedule.get_events")
@patch("routers.schedule.get_credentials_for_user")
@patch("routers.schedule.no_go_zones_collection")
@patch("routers.schedule.tasks_collection")
@patch("routers.schedule.get_settings")
def test_run_schedule_deletes_event_for_task_bumped_out_of_schedule(
    mock_get_settings,
    mock_tasks_collection,
    mock_no_go_zones_collection,
    mock_get_creds,
    mock_get_events,
    mock_delete_event,
    mock_compute_history,
    mock_weighted_estimate,
    mock_compute_free_blocks,
    mock_assign_tasks,
):
    mock_get_settings.return_value = BASE_SETTINGS
    mock_get_creds.return_value = "creds"
    mock_get_events.return_value = []
    mock_no_go_zones_collection.find.return_value = []
    bumped_task_id = str(ObjectId())
    mock_tasks_collection.find.return_value = [
        {
            "_id": ObjectId(bumped_task_id), "user_id": USER["_id"], "title": "Bumped", "subject": "Math",
            "estimated_minutes": 60, "status": "scheduled", "gcal_event_id": "stale-gcal-id",
            "scheduled_blocks": [{"start": "2026-01-01T09:00:00-05:00", "end": "2026-01-01T10:00:00-05:00"}],
        },
    ]
    mock_compute_history.return_value = []
    mock_weighted_estimate.return_value = (60.0, False)
    mock_compute_free_blocks.return_value = []
    mock_assign_tasks.return_value = ({}, [bumped_task_id])

    run_schedule(USER)

    mock_delete_event.assert_called_once_with("creds", "stale-gcal-id")
    update_args = mock_tasks_collection.update_one.call_args
    assert update_args[0][1]["$set"] == {"status": "unschedulable", "scheduled_blocks": []}
    assert update_args[0][1]["$unset"] == {"gcal_event_id": ""}


@patch("routers.schedule.get_events")
@patch("routers.schedule.get_credentials_for_user")
@patch("routers.schedule.no_go_zones_collection")
@patch("routers.schedule.tasks_collection")
@patch("routers.schedule.get_settings")
def test_reschedule_missed_returns_400_when_nothing_missed(
    mock_get_settings, mock_tasks_collection, mock_no_go_zones_collection, mock_get_creds, mock_get_events
):
    mock_get_settings.return_value = BASE_SETTINGS
    mock_get_creds.return_value = "creds"
    mock_get_events.return_value = []
    mock_no_go_zones_collection.find.return_value = []
    mock_tasks_collection.find.return_value = [
        {
            "_id": ObjectId(), "user_id": USER["_id"], "title": "Future", "subject": "Math",
            "estimated_minutes": 60, "status": "scheduled",
            "scheduled_blocks": [{"start": "2099-01-01T09:00:00-05:00", "end": "2099-01-01T10:00:00-05:00"}],
        },
    ]

    with pytest.raises(HTTPException) as exc_info:
        reschedule_missed(USER)

    assert exc_info.value.status_code == 400
    assert "missed" in exc_info.value.detail.lower()


@patch("routers.schedule.assign_tasks")
@patch("routers.schedule.compute_free_blocks")
@patch("routers.schedule.weighted_estimate")
@patch("routers.schedule.compute_subject_history")
@patch("routers.schedule.update_gcal_event")
@patch("routers.schedule.create_gcal_event")
@patch("routers.schedule.get_events")
@patch("routers.schedule.get_credentials_for_user")
@patch("routers.schedule.no_go_zones_collection")
@patch("routers.schedule.tasks_collection")
@patch("routers.schedule.get_settings")
def test_reschedule_missed_only_reassigns_past_tasks(
    mock_get_settings,
    mock_tasks_collection,
    mock_no_go_zones_collection,
    mock_get_creds,
    mock_get_events,
    mock_create_event,
    mock_update_event,
    mock_compute_history,
    mock_weighted_estimate,
    mock_compute_free_blocks,
    mock_assign_tasks,
):
    mock_get_settings.return_value = BASE_SETTINGS
    mock_get_creds.return_value = "creds"
    mock_get_events.return_value = []
    mock_no_go_zones_collection.find.return_value = []
    missed_id = str(ObjectId())
    future_id = str(ObjectId())
    mock_tasks_collection.find.return_value = [
        {
            "_id": ObjectId(missed_id), "user_id": USER["_id"], "title": "Missed", "subject": "Math",
            "estimated_minutes": 60, "status": "scheduled", "gcal_event_id": "missed-gcal-id",
            "scheduled_blocks": [{"start": "2020-01-01T09:00:00-05:00", "end": "2020-01-01T10:00:00-05:00"}],
        },
        {
            "_id": ObjectId(future_id), "user_id": USER["_id"], "title": "Future", "subject": "Math",
            "estimated_minutes": 60, "status": "scheduled", "gcal_event_id": "future-gcal-id",
            "scheduled_blocks": [{"start": "2099-01-01T09:00:00-05:00", "end": "2099-01-01T10:00:00-05:00"}],
        },
    ]
    mock_compute_history.return_value = []
    mock_weighted_estimate.return_value = (60.0, False)
    mock_compute_free_blocks.return_value = []
    mock_assign_tasks.return_value = (
        {missed_id: {"start": "2026-06-01T09:00:00-05:00", "end": "2026-06-01T10:00:00-05:00"}},
        [],
    )

    reschedule_missed(USER)

    # Only the missed task is handed to the assigner — the still-future
    # scheduled task is left completely untouched.
    tasks_passed = mock_assign_tasks.call_args[0][0]
    assert [t["id"] for t in tasks_passed] == [missed_id]

    # Its existing event gets moved, not duplicated.
    mock_update_event.assert_called_once_with(
        "creds", "missed-gcal-id",
        start_iso="2026-06-01T09:00:00-05:00", end_iso="2026-06-01T10:00:00-05:00",
    )
    mock_create_event.assert_not_called()


@patch("routers.schedule.assign_tasks")
@patch("routers.schedule.compute_free_blocks")
@patch("routers.schedule.weighted_estimate")
@patch("routers.schedule.compute_subject_history")
@patch("routers.schedule.no_go_zones_collection")
@patch("routers.schedule.tasks_collection")
@patch("routers.schedule.get_settings")
def test_reschedule_missed_dev_mode_treats_other_scheduled_dev_tasks_as_busy(
    mock_get_settings,
    mock_tasks_collection,
    mock_no_go_zones_collection,
    mock_compute_history,
    mock_weighted_estimate,
    mock_compute_free_blocks,
    mock_assign_tasks,
):
    # Regression test: dev mode has no real Google Calendar to read busy time
    # from, so it used to always report an empty calendar, meaning a
    # reschedule-missed run had no way to see that another dev task already
    # occupied a slot and would happily double-book it.
    mock_get_settings.return_value = BASE_SETTINGS
    mock_no_go_zones_collection.find.return_value = []

    other_task_id = str(ObjectId())
    missed_task_id = str(ObjectId())
    other_task = {
        "_id": ObjectId(other_task_id), "user_id": USER["_id"], "title": "Other", "subject": "Math",
        "estimated_minutes": 60, "status": "scheduled", "gcal_event_id": "dev-fake-other",
        "scheduled_blocks": [{"start": "2099-01-01T08:00:00+00:00", "end": "2099-01-01T09:00:00+00:00"}],
    }
    missed_task = {
        "_id": ObjectId(missed_task_id), "user_id": USER["_id"], "title": "Missed", "subject": "Math",
        "estimated_minutes": 60, "status": "scheduled", "gcal_event_id": "dev-fake-missed",
        "scheduled_blocks": [{"start": "2020-01-01T08:00:00+00:00", "end": "2020-01-01T09:00:00+00:00"}],
    }
    mock_tasks_collection.find.return_value = [other_task, missed_task]
    mock_compute_history.return_value = []
    mock_weighted_estimate.return_value = (60.0, False)
    mock_compute_free_blocks.return_value = []
    mock_assign_tasks.return_value = ({}, [missed_task_id])

    dev_user = {"_id": USER["_id"], "is_dev_user": True}
    reschedule_missed(dev_user)

    events_passed = mock_compute_free_blocks.call_args[0][0]
    assert any(e["id"] == "dev-fake-other" for e in events_passed)
