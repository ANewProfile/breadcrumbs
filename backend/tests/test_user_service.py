from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from bson import ObjectId
from services.user_service import (
    upsert_user,
    store_google_credentials,
    create_session,
    get_user_for_session,
    delete_session,
)


def test_upsert_user_upserts_by_google_sub():
    mock_users = MagicMock()
    mock_users.find_one_and_update.return_value = {"_id": ObjectId(), "email": "a@b.com"}

    upsert_user(mock_users, google_sub="sub123", email="a@b.com", name="A", picture=None)

    args, kwargs = mock_users.find_one_and_update.call_args
    assert args[0] == {"google_sub": "sub123"}
    assert kwargs["upsert"] is True
    assert args[1]["$setOnInsert"]["google_sub"] == "sub123"
    assert args[1]["$set"]["email"] == "a@b.com"


def test_store_google_credentials_sets_on_user_doc():
    mock_users = MagicMock()
    user_id = ObjectId()
    creds = {"token": "abc", "refresh_token": "def"}

    store_google_credentials(mock_users, user_id, creds)

    mock_users.update_one.assert_called_once_with(
        {"_id": user_id}, {"$set": {"google_credentials": creds}}
    )


def test_create_session_inserts_and_returns_token():
    mock_sessions = MagicMock()
    user_id = ObjectId()

    token = create_session(mock_sessions, user_id)

    assert isinstance(token, str) and len(token) > 20
    mock_sessions.insert_one.assert_called_once()
    inserted = mock_sessions.insert_one.call_args[0][0]
    assert inserted["_id"] == token
    assert inserted["user_id"] == user_id


def test_get_user_for_session_returns_none_for_missing_token():
    mock_sessions = MagicMock()
    mock_users = MagicMock()
    assert get_user_for_session(mock_sessions, mock_users, None) is None
    mock_sessions.find_one.assert_not_called()


def test_get_user_for_session_returns_none_when_session_not_found():
    mock_sessions = MagicMock()
    mock_users = MagicMock()
    mock_sessions.find_one.return_value = None

    assert get_user_for_session(mock_sessions, mock_users, "sometoken") is None


def test_get_user_for_session_returns_user_for_valid_session():
    mock_sessions = MagicMock()
    mock_users = MagicMock()
    user_id = ObjectId()
    mock_sessions.find_one.return_value = {
        "_id": "tok",
        "user_id": user_id,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
    }
    mock_users.find_one.return_value = {"_id": user_id, "email": "a@b.com"}

    result = get_user_for_session(mock_sessions, mock_users, "tok")

    assert result["email"] == "a@b.com"
    mock_users.find_one.assert_called_once_with({"_id": user_id})


def test_get_user_for_session_handles_naive_datetime_from_mongo():
    # pymongo returns naive datetimes by default even for UTC-stored values —
    # this must not raise a naive/aware comparison error.
    mock_sessions = MagicMock()
    mock_users = MagicMock()
    naive_future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
    mock_sessions.find_one.return_value = {
        "_id": "tok",
        "user_id": ObjectId(),
        "expires_at": naive_future,
    }
    mock_users.find_one.return_value = {"email": "a@b.com"}

    result = get_user_for_session(mock_sessions, mock_users, "tok")
    assert result is not None


def test_get_user_for_session_expires_and_deletes_stale_session():
    mock_sessions = MagicMock()
    mock_users = MagicMock()
    mock_sessions.find_one.return_value = {
        "_id": "tok",
        "user_id": ObjectId(),
        "expires_at": datetime.now(timezone.utc) - timedelta(days=1),
    }

    result = get_user_for_session(mock_sessions, mock_users, "tok")

    assert result is None
    mock_sessions.delete_one.assert_called_once_with({"_id": "tok"})
    mock_users.find_one.assert_not_called()


def test_delete_session_removes_token():
    mock_sessions = MagicMock()
    delete_session(mock_sessions, "tok")
    mock_sessions.delete_one.assert_called_once_with({"_id": "tok"})


def test_delete_session_noop_for_none():
    mock_sessions = MagicMock()
    delete_session(mock_sessions, None)
    mock_sessions.delete_one.assert_not_called()
