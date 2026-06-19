from googleapiclient.discovery import build


def create_gcal_event(creds, title: str, start_iso: str, end_iso: str) -> str:
    service = build("calendar", "v3", credentials=creds)
    event = {
        "summary": f"[Breadcrumbs] {title}",
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
    }
    result = service.events().insert(calendarId="primary", body=event).execute()
    return result["id"]
