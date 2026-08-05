from unittest.mock import patch
from datetime import datetime, timedelta, timezone
import pytest
from bson import ObjectId
from pydantic import ValidationError
from fastapi import HTTPException
from routers.tasks import reschedule_task, RescheduleIn

TASK_ID = "507f1f77bcf86cd799439011"
NEW_START = datetime.now(timezone.utc) + timedelta(days=1)
USER = {"_id": ObjectId()}


def make_task(gcal_event_id=None, scheduled_blocks=None, estimated_minutes=30, estimated_minutes_used=None):
    doc = {
        "_id": TASK_ID,
        "user_id": USER["_id"],
        "title": "Some task",
        "gcal_event_id": gcal_event_id,
        "scheduled_blocks": scheduled_blocks or [],
        "estimated_minutes": estimated_minutes,
    }
    if estimated_minutes_used is not None:
        doc["estimated_minutes_used"] = estimated_minutes_used
    return doc


def test_reschedule_naive_datetime_rejected():
    with pytest.raises(ValidationError):
        RescheduleIn(start=datetime(2026, 8, 5, 9, 0))  # no tzinfo


@patch("routers.tasks.get_settings")
@patch("routers.tasks.get_events")
@patch("routers.tasks.find_conflicting_gcal_event")
@patch("routers.tasks.find_conflicting_task")
@patch("routers.tasks.update_gcal_event")
@patch("routers.tasks.create_gcal_event")
@patch("routers.tasks.get_credentials_for_user")
@patch("routers.tasks.tasks_collection")
def test_reschedule_existing_scheduled_task_moves_gcal_event(
    mock_collection, mock_creds, mock_create_gcal, mock_update_gcal,
    mock_find_task_conflict, mock_find_gcal_conflict, mock_get_events, mock_get_settings,
):
    old_start = datetime.now(timezone.utc) + timedelta(hours=2)
    old_end = old_start + timedelta(minutes=30)
    mock_collection.find_one.return_value = make_task(
        gcal_event_id="evt1",
        scheduled_blocks=[{"start": old_start.isoformat(), "end": old_end.isoformat()}],
    )
    mock_collection.find_one_and_update.return_value = make_task(gcal_event_id="evt1")
    mock_find_task_conflict.return_value = None
    mock_find_gcal_conflict.return_value = None
    mock_get_events.return_value = []
    mock_get_settings.return_value = {"lookahead_days": 7}

    reschedule_task(TASK_ID, RescheduleIn(start=NEW_START), USER)

    mock_update_gcal.assert_called_once()
    mock_create_gcal.assert_not_called()
    args, _ = mock_collection.find_one_and_update.call_args
    assert args[1]["$set"]["status"] == "scheduled"


@patch("routers.tasks.get_settings")
@patch("routers.tasks.get_events")
@patch("routers.tasks.find_conflicting_gcal_event")
@patch("routers.tasks.find_conflicting_task")
@patch("routers.tasks.update_gcal_event")
@patch("routers.tasks.create_gcal_event")
@patch("routers.tasks.get_credentials_for_user")
@patch("routers.tasks.tasks_collection")
def test_reschedule_pending_task_creates_new_gcal_event(
    mock_collection, mock_creds, mock_create_gcal, mock_update_gcal,
    mock_find_task_conflict, mock_find_gcal_conflict, mock_get_events, mock_get_settings,
):
    mock_collection.find_one.return_value = make_task(gcal_event_id=None, scheduled_blocks=[])
    mock_collection.find_one_and_update.return_value = make_task(gcal_event_id="new_evt")
    mock_find_task_conflict.return_value = None
    mock_find_gcal_conflict.return_value = None
    mock_get_events.return_value = []
    mock_get_settings.return_value = {"lookahead_days": 7}
    mock_create_gcal.return_value = "new_evt"

    reschedule_task(TASK_ID, RescheduleIn(start=NEW_START), USER)

    mock_create_gcal.assert_called_once()
    mock_update_gcal.assert_not_called()


@patch("routers.tasks.find_conflicting_task")
@patch("routers.tasks.tasks_collection")
def test_reschedule_rejects_conflict_with_another_task(mock_collection, mock_find_task_conflict):
    mock_collection.find_one.return_value = make_task()
    mock_find_task_conflict.return_value = {"title": "Other task"}

    with pytest.raises(HTTPException) as exc_info:
        reschedule_task(TASK_ID, RescheduleIn(start=NEW_START), USER)

    assert exc_info.value.status_code == 409
    assert "Other task" in exc_info.value.detail


@patch("routers.tasks.get_settings")
@patch("routers.tasks.get_events")
@patch("routers.tasks.find_conflicting_gcal_event")
@patch("routers.tasks.find_conflicting_task")
@patch("routers.tasks.get_credentials_for_user")
@patch("routers.tasks.tasks_collection")
def test_reschedule_rejects_conflict_with_gcal_event(
    mock_collection, mock_creds, mock_find_task_conflict, mock_find_gcal_conflict, mock_get_events, mock_get_settings
):
    mock_collection.find_one.return_value = make_task()
    mock_find_task_conflict.return_value = None
    mock_find_gcal_conflict.return_value = {"summary": "Doctor appointment"}
    mock_get_events.return_value = []
    mock_get_settings.return_value = {"lookahead_days": 7}

    with pytest.raises(HTTPException) as exc_info:
        reschedule_task(TASK_ID, RescheduleIn(start=NEW_START), USER)

    assert exc_info.value.status_code == 409
    assert "Doctor appointment" in exc_info.value.detail


@patch("routers.tasks.tasks_collection")
def test_reschedule_nonexistent_task_raises_404(mock_collection):
    mock_collection.find_one.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        reschedule_task(TASK_ID, RescheduleIn(start=NEW_START), USER)

    assert exc_info.value.status_code == 404


@patch("routers.tasks.get_credentials_for_user")
@patch("routers.tasks.find_conflicting_task")
@patch("routers.tasks.tasks_collection")
def test_reschedule_returns_400_when_google_disconnected(mock_collection, mock_find_task_conflict, mock_get_creds):
    mock_collection.find_one.return_value = make_task()
    mock_find_task_conflict.return_value = None
    mock_get_creds.side_effect = ValueError("User has not connected a Google account")

    with pytest.raises(HTTPException) as exc_info:
        reschedule_task(TASK_ID, RescheduleIn(start=NEW_START), USER)

    assert exc_info.value.status_code == 400
    assert "reconnect" in exc_info.value.detail.lower()
