from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from bson import ObjectId
from services.account_service import (
    cleanup_future_gcal_events,
    disconnect_google,
    revoke_google_grant,
    delete_all_task_data,
    delete_account,
)

USER = {"_id": ObjectId()}


def make_task(gcal_event_id, block_end):
    return {"gcal_event_id": gcal_event_id, "scheduled_blocks": [{"start": block_end.isoformat(), "end": block_end.isoformat()}]}


@patch("services.account_service.get_credentials_for_user")
@patch("services.account_service.delete_gcal_event")
def test_cleanup_skips_when_no_gcal_tasks(mock_delete_gcal, mock_get_creds):
    mock_tasks = MagicMock()
    mock_tasks.find.return_value = []

    cleanup_future_gcal_events(mock_tasks, MagicMock(), USER)

    mock_get_creds.assert_not_called()
    mock_delete_gcal.assert_not_called()


@patch("services.account_service.get_credentials_for_user")
@patch("services.account_service.delete_gcal_event")
def test_cleanup_noop_when_credentials_unavailable(mock_delete_gcal, mock_get_creds):
    mock_tasks = MagicMock()
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    mock_tasks.find.return_value = [make_task("evt1", future)]
    mock_get_creds.side_effect = ValueError("no creds")

    cleanup_future_gcal_events(mock_tasks, MagicMock(), USER)

    mock_delete_gcal.assert_not_called()


@patch("services.account_service.get_credentials_for_user")
@patch("services.account_service.delete_gcal_event")
def test_cleanup_deletes_only_future_events(mock_delete_gcal, mock_get_creds):
    mock_tasks = MagicMock()
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    mock_tasks.find.return_value = [make_task("future_evt", future), make_task("past_evt", past)]
    mock_get_creds.return_value = "creds"

    cleanup_future_gcal_events(mock_tasks, MagicMock(), USER)

    mock_delete_gcal.assert_called_once_with("creds", "future_evt")


@patch("services.account_service.get_credentials_for_user")
@patch("services.account_service.revoke_credentials")
def test_disconnect_google_revokes_and_unsets_credentials(mock_revoke, mock_get_creds):
    mock_users = MagicMock()
    mock_get_creds.return_value = "creds"

    disconnect_google(mock_users, USER)

    mock_revoke.assert_called_once_with("creds")
    mock_users.update_one.assert_called_once_with(
        {"_id": USER["_id"]}, {"$unset": {"google_credentials": ""}}
    )


@patch("services.account_service.get_credentials_for_user")
@patch("services.account_service.revoke_credentials")
def test_disconnect_google_still_unsets_when_already_disconnected(mock_revoke, mock_get_creds):
    mock_users = MagicMock()
    mock_get_creds.side_effect = ValueError("no creds")

    disconnect_google(mock_users, USER)

    mock_revoke.assert_not_called()
    mock_users.update_one.assert_called_once_with(
        {"_id": USER["_id"]}, {"$unset": {"google_credentials": ""}}
    )


@patch("services.account_service.get_credentials_for_user")
@patch("services.account_service.revoke_credentials")
def test_revoke_google_grant_revokes_without_writing_to_user_doc(mock_revoke, mock_get_creds):
    # Used right before the user doc is deleted (account deletion) — it must not
    # write a field to a document that's about to be erased anyway.
    mock_users = MagicMock()
    mock_get_creds.return_value = "creds"

    revoke_google_grant(mock_users, USER)

    mock_revoke.assert_called_once_with("creds")
    mock_users.update_one.assert_not_called()


@patch("services.account_service.get_credentials_for_user")
@patch("services.account_service.revoke_credentials")
def test_revoke_google_grant_noop_when_already_disconnected(mock_revoke, mock_get_creds):
    mock_users = MagicMock()
    mock_get_creds.side_effect = ValueError("no creds")

    revoke_google_grant(mock_users, USER)

    mock_revoke.assert_not_called()
    mock_users.update_one.assert_not_called()


def test_delete_all_task_data_wipes_tasks_and_settings_only():
    mock_tasks = MagicMock()
    mock_settings = MagicMock()
    user_id = ObjectId()

    delete_all_task_data(mock_tasks, mock_settings, user_id)

    mock_tasks.delete_many.assert_called_once_with({"user_id": user_id})
    mock_settings.delete_one.assert_called_once_with({"_id": user_id})


def test_delete_account_wipes_everything_including_user():
    mock_users = MagicMock()
    mock_tasks = MagicMock()
    mock_settings = MagicMock()
    mock_sessions = MagicMock()
    user_id = ObjectId()

    delete_account(mock_users, mock_tasks, mock_settings, mock_sessions, user_id)

    mock_tasks.delete_many.assert_called_once_with({"user_id": user_id})
    mock_settings.delete_one.assert_called_once_with({"_id": user_id})
    mock_sessions.delete_many.assert_called_once_with({"user_id": user_id})
    mock_users.delete_one.assert_called_once_with({"_id": user_id})
