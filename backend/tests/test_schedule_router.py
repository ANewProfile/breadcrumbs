from unittest.mock import patch
from bson import ObjectId
import pytest
from fastapi import HTTPException
from routers.schedule import run_schedule

USER = {"_id": ObjectId()}


@patch("routers.schedule.get_credentials_for_user")
@patch("routers.schedule.get_settings")
def test_run_schedule_returns_400_when_google_disconnected(mock_get_settings, mock_get_creds):
    mock_get_settings.return_value = {"lookahead_days": 7}
    mock_get_creds.side_effect = ValueError("User has not connected a Google account")

    with pytest.raises(HTTPException) as exc_info:
        run_schedule(USER)

    assert exc_info.value.status_code == 400
    assert "reconnect" in exc_info.value.detail.lower()
