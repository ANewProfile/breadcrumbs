from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def create_gcal_event(creds, title: str, start_iso: str, end_iso: str) -> str:
    service = build("calendar", "v3", credentials=creds)
    event = {
        "summary": f"[Breadcrumbs] {title}",
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
    }
    result = service.events().insert(calendarId="primary", body=event).execute()
    return result["id"]


def delete_gcal_event(creds, event_id: str) -> None:
    service = build("calendar", "v3", credentials=creds)
    try:
        service.events().delete(calendarId="primary", eventId=event_id).execute()
    except HttpError as e:
        if e.resp.status not in (404, 410):
            raise
