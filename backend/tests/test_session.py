from unittest.mock import patch, MagicMock
import pytest
from fastapi import HTTPException
from auth.session import get_current_user, get_current_user_optional, SESSION_COOKIE_NAME


def fake_request(cookies: dict):
    return MagicMock(cookies=cookies)


@patch("auth.session.get_user_for_session")
def test_get_current_user_raises_401_when_no_session(mock_get_user):
    mock_get_user.return_value = None
    request = fake_request({})

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(request)

    assert exc_info.value.status_code == 401


@patch("auth.session.get_user_for_session")
def test_get_current_user_returns_user_for_valid_session(mock_get_user):
    mock_get_user.return_value = {"_id": "u1", "email": "a@b.com"}
    request = fake_request({SESSION_COOKIE_NAME: "tok"})

    result = get_current_user(request)

    assert result["email"] == "a@b.com"
    mock_get_user.assert_called_once()
    assert mock_get_user.call_args[0][2] == "tok"


@patch("auth.session.get_user_for_session")
def test_get_current_user_optional_returns_none_without_raising(mock_get_user):
    mock_get_user.return_value = None
    request = fake_request({})

    assert get_current_user_optional(request) is None


@patch("auth.session.get_user_for_session")
def test_get_current_user_optional_returns_user_when_present(mock_get_user):
    mock_get_user.return_value = {"_id": "u1"}
    request = fake_request({SESSION_COOKIE_NAME: "tok"})

    assert get_current_user_optional(request) == {"_id": "u1"}
