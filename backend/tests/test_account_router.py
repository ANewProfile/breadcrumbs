from unittest.mock import patch
from bson import ObjectId
from routers.account import disconnect_google_route, delete_data_route, delete_account_route
from auth.session import SESSION_COOKIE_NAME

USER = {"_id": ObjectId()}


@patch("routers.account.disconnect_google")
def test_disconnect_google_route_calls_service(mock_disconnect):
    result = disconnect_google_route(USER)

    mock_disconnect.assert_called_once()
    assert mock_disconnect.call_args[0][1] == USER
    assert result == {"ok": True}


@patch("routers.account.delete_all_task_data")
@patch("routers.account.cleanup_future_gcal_events")
def test_delete_data_route_cleans_up_and_wipes_tasks(mock_cleanup, mock_delete_all):
    result = delete_data_route(USER)

    mock_cleanup.assert_called_once()
    mock_delete_all.assert_called_once()
    assert mock_delete_all.call_args[0][2] == USER["_id"]
    assert result == {"ok": True}


@patch("routers.account.delete_account")
@patch("routers.account.revoke_google_grant")
@patch("routers.account.cleanup_future_gcal_events")
def test_delete_account_route_wipes_everything_and_clears_cookie(
    mock_cleanup, mock_revoke, mock_delete_account
):
    response = delete_account_route(USER)

    mock_cleanup.assert_called_once()
    mock_revoke.assert_called_once()
    mock_delete_account.assert_called_once()
    assert mock_delete_account.call_args[0][4] == USER["_id"]
    set_cookie_headers = response.headers.getlist("set-cookie")
    assert any(SESSION_COOKIE_NAME in h for h in set_cookie_headers)
