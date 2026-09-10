# backend/routers/calendars.py
from fastapi import APIRouter, HTTPException, Depends
from googleapiclient.errors import HttpError
from auth.session import get_current_user
from auth.google_auth import get_credentials_for_user
from services.calendar_service import list_calendars
from database import users_collection

router = APIRouter()


@router.get("")
def read_calendars(user: dict = Depends(get_current_user)):
    """
    Every calendar on the user's Google account they could choose to include
    as busy time — their own, ones shared with them, and ones they've
    subscribed to. Dev users have no real Google account, so they just get
    the one fake "primary" calendar that _dev_fake_busy_events synthesizes.
    """
    if user.get("is_dev_user"):
        return [{"id": "primary", "summary": "Dev calendar (simulated)", "primary": True}]

    try:
        creds = get_credentials_for_user(user, users_collection)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Please reconnect your Google Calendar in Settings to see your calendars.",
        )

    try:
        return list_calendars(creds)
    except HttpError as e:
        if e.resp.status == 403:
            raise HTTPException(
                status_code=400,
                detail="Please reconnect your Google Calendar in Settings to grant calendar list access.",
            )
        raise
