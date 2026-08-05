from unittest.mock import patch
from datetime import datetime, timedelta, timezone
import pytest
from bson import ObjectId
from fastapi import HTTPException
from routers.tasks import delete_task

TASK_ID = "507f1f77bcf86cd799439011"
USER = {"_id": ObjectId()}


def make_task(gcal_event_id=None, block_end=None):
    doc = {"_id": TASK_ID, "user_id": USER["_id"], "gcal_event_id": gcal_event_id, "scheduled_blocks": []}
    if block_end:
        doc["scheduled_blocks"] = [{"start": block_end.isoformat(), "end": block_end.isoformat()}]
    return doc


@patch("routers.tasks.get_credentials_for_user")
@patch("routers.tasks.delete_gcal_event")
@patch("routers.tasks.tasks_collection")
def test_delete_future_task_deletes_gcal_event(mock_collection, mock_delete_gcal, mock_creds):
    future_end = datetime.now(timezone.utc) + timedelta(hours=1)
    mock_collection.find_one.return_value = make_task(gcal_event_id="evt1", block_end=future_end)

    delete_task(TASK_ID, USER)

    mock_delete_gcal.assert_called_once()
    mock_collection.delete_one.assert_called_once()


@patch("routers.tasks.get_credentials_for_user")
@patch("routers.tasks.delete_gcal_event")
@patch("routers.tasks.tasks_collection")
def test_delete_past_task_keeps_gcal_event(mock_collection, mock_delete_gcal, mock_creds):
    past_end = datetime.now(timezone.utc) - timedelta(hours=1)
    mock_collection.find_one.return_value = make_task(gcal_event_id="evt1", block_end=past_end)

    delete_task(TASK_ID, USER)

    mock_delete_gcal.assert_not_called()
    mock_collection.delete_one.assert_called_once()


@patch("routers.tasks.delete_gcal_event")
@patch("routers.tasks.tasks_collection")
def test_delete_task_without_gcal_event_skips_calendar_call(mock_collection, mock_delete_gcal):
    mock_collection.find_one.return_value = make_task(gcal_event_id=None, block_end=None)

    delete_task(TASK_ID, USER)

    mock_delete_gcal.assert_not_called()
    mock_collection.delete_one.assert_called_once()


@patch("routers.tasks.tasks_collection")
def test_delete_nonexistent_task_raises_404(mock_collection):
    mock_collection.find_one.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        delete_task(TASK_ID, USER)

    assert exc_info.value.status_code == 404


@patch("routers.tasks.get_credentials_for_user")
@patch("routers.tasks.delete_gcal_event")
@patch("routers.tasks.tasks_collection")
def test_delete_future_task_proceeds_when_google_disconnected(mock_collection, mock_delete_gcal, mock_creds):
    # Google disconnected shouldn't block deleting the task itself — just skip the calendar cleanup.
    future_end = datetime.now(timezone.utc) + timedelta(hours=1)
    mock_collection.find_one.return_value = make_task(gcal_event_id="evt1", block_end=future_end)
    mock_creds.side_effect = ValueError("User has not connected a Google account")

    delete_task(TASK_ID, USER)

    mock_delete_gcal.assert_not_called()
    mock_collection.delete_one.assert_called_once()
