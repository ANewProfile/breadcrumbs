from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from auth.session import get_current_user, SESSION_COOKIE_NAME
from database import users_collection, tasks_collection, settings_collection, sessions_collection
from services.account_service import (
    cleanup_future_gcal_events,
    disconnect_google,
    delete_all_task_data,
    delete_account,
)

router = APIRouter()


@router.post("/disconnect-google")
def disconnect_google_route(user: dict = Depends(get_current_user)):
    disconnect_google(users_collection, user)
    return {"ok": True}


@router.post("/delete-data")
def delete_data_route(user: dict = Depends(get_current_user)):
    cleanup_future_gcal_events(tasks_collection, users_collection, user)
    delete_all_task_data(tasks_collection, settings_collection, user["_id"])
    return {"ok": True}


@router.delete("")
def delete_account_route(user: dict = Depends(get_current_user)):
    cleanup_future_gcal_events(tasks_collection, users_collection, user)
    disconnect_google(users_collection, user)
    delete_account(users_collection, tasks_collection, settings_collection, sessions_collection, user["_id"])
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response
