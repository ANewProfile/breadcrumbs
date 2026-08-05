from unittest.mock import patch, MagicMock
import pytest
from bson import ObjectId
from google.oauth2.credentials import Credentials
from auth.google_auth import (
    build_authorization_url,
    exchange_code_for_credentials,
    decode_identity,
    credentials_to_dict,
    get_credentials_for_user,
)


@patch("auth.google_auth.Flow")
def test_build_authorization_url_requests_offline_access_and_consent(mock_flow_cls):
    mock_flow = MagicMock()
    mock_flow.authorization_url.return_value = ("https://accounts.google.com/o/oauth2/auth?...", "state123")
    mock_flow.code_verifier = "generated-verifier"
    mock_flow_cls.from_client_config.return_value = mock_flow

    url, code_verifier = build_authorization_url("mystate")

    assert url == "https://accounts.google.com/o/oauth2/auth?..."
    assert code_verifier == "generated-verifier"
    mock_flow.authorization_url.assert_called_once_with(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
        state="mystate",
    )


@patch("auth.google_auth.Flow")
def test_exchange_code_for_credentials_fetches_token_with_verifier(mock_flow_cls):
    mock_flow = MagicMock()
    mock_flow.credentials = "the-credentials"
    mock_flow_cls.from_client_config.return_value = mock_flow

    result = exchange_code_for_credentials("authcode", "the-verifier")

    mock_flow_cls.from_client_config.assert_called_once()
    _, kwargs = mock_flow_cls.from_client_config.call_args
    assert kwargs["code_verifier"] == "the-verifier"
    mock_flow.fetch_token.assert_called_once_with(code="authcode")
    assert result == "the-credentials"


@patch("auth.google_auth.google_id_token")
def test_decode_identity_extracts_claims(mock_id_token_module):
    mock_id_token_module.verify_oauth2_token.return_value = {
        "sub": "12345",
        "email": "a@b.com",
        "name": "A B",
        "picture": "http://pic",
    }
    mock_creds = MagicMock(id_token="sometoken")

    result = decode_identity(mock_creds)

    assert result == {"sub": "12345", "email": "a@b.com", "name": "A B", "picture": "http://pic"}


def test_credentials_to_dict_round_trips_via_to_json():
    creds = Credentials(
        token="abc",
        refresh_token="def",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="cid",
        client_secret="secret",
        scopes=["a"],
    )

    result = credentials_to_dict(creds)

    assert result["token"] == "abc"
    assert result["refresh_token"] == "def"


def test_get_credentials_for_user_raises_without_stored_credentials():
    with pytest.raises(ValueError):
        get_credentials_for_user({"_id": ObjectId()}, MagicMock())


@patch("auth.google_auth.Credentials")
def test_get_credentials_for_user_returns_valid_credentials_without_refresh(mock_creds_cls):
    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds_cls.from_authorized_user_info.return_value = mock_creds
    mock_users = MagicMock()
    user_doc = {"_id": ObjectId(), "google_credentials": {"token": "abc"}}

    result = get_credentials_for_user(user_doc, mock_users)

    assert result is mock_creds
    mock_creds.refresh.assert_not_called()
    mock_users.update_one.assert_not_called()


@patch("auth.google_auth.credentials_to_dict")
@patch("auth.google_auth.Credentials")
def test_get_credentials_for_user_refreshes_and_persists_when_expired(mock_creds_cls, mock_to_dict):
    mock_creds = MagicMock()
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "refresh-token"
    mock_creds_cls.from_authorized_user_info.return_value = mock_creds
    mock_to_dict.return_value = {"token": "refreshed"}
    mock_users = MagicMock()
    user_id = ObjectId()
    user_doc = {"_id": user_id, "google_credentials": {"token": "stale"}}

    result = get_credentials_for_user(user_doc, mock_users)

    mock_creds.refresh.assert_called_once()
    mock_users.update_one.assert_called_once_with(
        {"_id": user_id}, {"$set": {"google_credentials": {"token": "refreshed"}}}
    )
    assert result is mock_creds


@patch("auth.google_auth.Credentials")
def test_get_credentials_for_user_raises_when_expired_without_refresh_token(mock_creds_cls):
    mock_creds = MagicMock()
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = None
    mock_creds_cls.from_authorized_user_info.return_value = mock_creds
    mock_users = MagicMock()

    with pytest.raises(ValueError):
        get_credentials_for_user({"_id": ObjectId(), "google_credentials": {}}, mock_users)
