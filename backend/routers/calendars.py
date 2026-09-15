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
    Get calendars on the user's GCal that they might want to use to put "busy" events on
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
