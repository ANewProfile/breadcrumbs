# backend/services/calendar_service.py
from googleapiclient.discovery import build
from datetime import datetime, timezone, timedelta

def get_events(creds, lookahead_days=7):
    service = build("calendar", "v3", credentials=creds)
    now = datetime.now(timezone.utc)
    time_max = now.replace(hour=23, minute=59) + timedelta(days=lookahead_days)

    events = service.events().list(
        calendarId="primary",
        timeMin=now.isoformat(),
        timeMax=time_max.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute().get("items", [])

    return events
