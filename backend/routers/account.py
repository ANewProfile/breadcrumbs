from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from auth.session import get_current_user, SESSION_COOKIE_NAME
from database import users_collection, tasks_collection, settings_collection, sessions_collection
from rate_limit import rate_limit
from services.account_service import (
    cleanup_future_gcal_events,
    disconnect_google,
    revoke_google_grant,
    delete_all_task_data,
    delete_account,
)

router = APIRouter()


@router.post("/disconnect-google", dependencies=[Depends(rate_limit("10/minute"))])
def disconnect_google_route(user: dict = Depends(get_current_user)):
    disconnect_google(users_collection, user)
    return {"ok": True}


@router.post("/delete-data", dependencies=[Depends(rate_limit("5/minute"))])
def delete_data_route(user: dict = Depends(get_current_user)):
    cleanup_future_gcal_events(tasks_collection, users_collection, user)
    delete_all_task_data(tasks_collection, settings_collection, user["_id"])
    return {"ok": True}


@router.delete("", dependencies=[Depends(rate_limit("5/minute"))])
def delete_account_route(user: dict = Depends(get_current_user)):
    cleanup_future_gcal_events(tasks_collection, users_collection, user)
    revoke_google_grant(users_collection, user)
    delete_account(users_collection, tasks_collection, settings_collection, sessions_collection, user["_id"])
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response
