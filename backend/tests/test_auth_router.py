from unittest.mock import patch, MagicMock
import pytest
from fastapi import HTTPException
from bson import ObjectId
from routers.auth import google_login, google_callback, logout, me, STATE_COOKIE_NAME, VERIFIER_COOKIE_NAME
from auth.session import SESSION_COOKIE_NAME


def fake_request(cookies: dict):
    return MagicMock(cookies=cookies)


@patch("routers.auth.build_authorization_url")
def test_google_login_redirects_and_sets_state_and_verifier_cookies(mock_build_url):
    mock_build_url.return_value = ("https://accounts.google.com/o/oauth2/auth?client_id=...", "verifier123")

    response = google_login()

    assert response.status_code in (302, 307)
    assert response.headers["location"] == mock_build_url.return_value[0]
    set_cookie_headers = response.headers.getlist("set-cookie")
    assert any(STATE_COOKIE_NAME in h for h in set_cookie_headers)
    assert any(VERIFIER_COOKIE_NAME in h and "verifier123" in h for h in set_cookie_headers)


def test_google_callback_rejects_missing_state_cookie():
    request = fake_request({})
    with pytest.raises(HTTPException) as exc_info:
        google_callback(request, code="authcode", state="mystate")
    assert exc_info.value.status_code == 400


def test_google_callback_rejects_state_mismatch():
    request = fake_request({STATE_COOKIE_NAME: "expected", VERIFIER_COOKIE_NAME: "v"})
    with pytest.raises(HTTPException) as exc_info:
        google_callback(request, code="authcode", state="different")
    assert exc_info.value.status_code == 400


def test_google_callback_rejects_missing_verifier_cookie():
    request = fake_request({STATE_COOKIE_NAME: "matching-state"})
    with pytest.raises(HTTPException) as exc_info:
        google_callback(request, code="authcode", state="matching-state")
    assert exc_info.value.status_code == 400


@patch("routers.auth.create_session")
@patch("routers.auth.store_google_credentials")
@patch("routers.auth.credentials_to_dict")
@patch("routers.auth.upsert_user")
@patch("routers.auth.decode_identity")
@patch("routers.auth.exchange_code_for_credentials")
def test_google_callback_success_creates_session_and_redirects(
    mock_exchange, mock_decode, mock_upsert, mock_to_dict, mock_store_creds, mock_create_session
):
    request = fake_request({STATE_COOKIE_NAME: "matching-state", VERIFIER_COOKIE_NAME: "verifier123"})
    mock_exchange.return_value = "creds-object"
    mock_to_dict.return_value = {"token": "abc"}
    mock_decode.return_value = {"sub": "g123", "email": "a@b.com", "name": "A", "picture": None}
    user_id = ObjectId()
    mock_upsert.return_value = {"_id": user_id}
    mock_create_session.return_value = "session-token-abc"

    response = google_callback(request, code="authcode", state="matching-state")

    mock_exchange.assert_called_once_with("authcode", "verifier123")
    _, upsert_kwargs = mock_upsert.call_args
    assert upsert_kwargs == {"google_sub": "g123", "email": "a@b.com", "name": "A", "picture": None}
    mock_create_session.assert_called_once()
    assert response.status_code in (302, 307)
    set_cookie_headers = response.headers.getlist("set-cookie")
    assert any(SESSION_COOKIE_NAME in h and "session-token-abc" in h for h in set_cookie_headers)


@patch("routers.auth.delete_session")
def test_logout_deletes_session_and_clears_cookie(mock_delete_session):
    request = fake_request({SESSION_COOKIE_NAME: "tok123"})

    response = logout(request)

    mock_delete_session.assert_called_once()
    assert mock_delete_session.call_args[0][1] == "tok123"
    set_cookie_headers = response.headers.getlist("set-cookie")
    assert any(SESSION_COOKIE_NAME in h for h in set_cookie_headers)


def test_me_returns_none_when_not_authenticated():
    result = me(None)
    assert result == {"user": None}


def test_me_returns_user_shape_when_authenticated():
    user_id = ObjectId()
    result = me({
        "_id": user_id,
        "email": "a@b.com",
        "name": "A",
        "picture": "http://pic",
        "google_credentials": {"token": "abc"},
    })
    assert result == {
        "user": {
            "id": str(user_id),
            "email": "a@b.com",
            "name": "A",
            "picture": "http://pic",
            "google_connected": True,
        }
    }


def test_me_reports_google_connected_false_when_not_connected():
    user_id = ObjectId()
    result = me({"_id": user_id, "email": "a@b.com", "name": "A", "picture": None})
    assert result["user"]["google_connected"] is False
