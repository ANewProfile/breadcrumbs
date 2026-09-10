# backend/services/calendar_service.py
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timezone, timedelta

DEFAULT_CALENDAR_IDS = ["primary"]


def list_calendars(creds) -> list[dict]:
    """
    Every calendar on this Google account: the user's own primary calendar,
    secondary calendars they created, ones shared with them, and ones they've
    subscribed to (e.g. a holidays feed) — anything showing up in their
    Google Calendar UI. Lets the user pick which of these should count as
    busy time for scheduling.
    """
    service = build("calendar", "v3", credentials=creds)
    calendars = []
    page_token = None
    while True:
        response = service.calendarList().list(pageToken=page_token).execute()
        for item in response.get("items", []):
            calendars.append({
                "id": item["id"],
                "summary": item.get("summary", item["id"]),
                "primary": bool(item.get("primary")),
            })
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return calendars


def get_events(creds, lookahead_days=7, calendar_ids: list[str] | None = None):
    service = build("calendar", "v3", credentials=creds)
    now = datetime.now(timezone.utc)
    time_max = now.replace(hour=23, minute=59) + timedelta(days=lookahead_days)

    events = []
    for calendar_id in calendar_ids or DEFAULT_CALENDAR_IDS:
        try:
            items = service.events().list(
                calendarId=calendar_id,
                timeMin=now.isoformat(),
                timeMax=time_max.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            ).execute().get("items", [])
        except HttpError as e:
            # A previously-selected calendar can disappear (unshared,
            # unsubscribed, deleted) — skip it rather than failing the whole
            # scheduling run over one stale calendar.
            if e.resp.status in (403, 404):
                continue
            raise
        events.extend(items)

    return events


def search_events(creds, query: str, time_min_iso: str, time_max_iso: str | None = None) -> list:
    """
    Full-text searches the primary calendar (Google's q= param matches summary,
    description, location, attendees — not just the title) for events starting
    at or after time_min_iso. Paginates through every page since a school year's
    worth of events can exceed a single response.

    Pass time_max_iso when the caller knows how far into the future matching
    events can possibly go — an unbounded search makes Google scan arbitrarily
    far ahead just to confirm there's nothing left, which is slow.
    """
    service = build("calendar", "v3", credentials=creds)
    list_kwargs = {
        "calendarId": "primary",
        "q": query,
        "timeMin": time_min_iso,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if time_max_iso:
        list_kwargs["timeMax"] = time_max_iso

    events = []
    page_token = None
    while True:
        response = service.events().list(pageToken=page_token, **list_kwargs).execute()
        events.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return events
