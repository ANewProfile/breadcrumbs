import random
import time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

RATE_LIMIT_MAX_RETRIES = 5
RATE_LIMIT_BASE_DELAY_SECONDS = 1.0


def _is_rate_limit_error(e: HttpError) -> bool:
    status = e.resp.status
    if status == 429:
        return True
    if status == 403:
        # Google returns 403 (not 429) for Calendar API quota hits, distinguished
        # only by the reason string in the body — usageLimits/rateLimitExceeded
        # or userRateLimitExceeded. Other 403s (e.g. permission denied) must not
        # be retried.
        message = str(e)
        return "rateLimitExceeded" in message or "userRateLimitExceeded" in message
    return False


def _execute_with_rate_limit_retry(request):
    """Runs a googleapiclient request, retrying with exponential backoff + jitter
    on Calendar API rate-limit errors. Bulk calls fire several of these per
    worker thread in quick succession, so a single burst can trip Google's
    per-user quota even though it clears again within ~100 seconds."""
    attempt = 0
    while True:
        try:
            return request.execute()
        except HttpError as e:
            if not _is_rate_limit_error(e) or attempt >= RATE_LIMIT_MAX_RETRIES - 1:
                raise
            delay = RATE_LIMIT_BASE_DELAY_SECONDS * (2**attempt) + random.uniform(0, 1)
            time.sleep(delay)
            attempt += 1


def create_gcal_event(creds, title: str, start_iso: str, end_iso: str) -> str:
    service = build("calendar", "v3", credentials=creds)
    event = {
        "summary": f"[Breadcrumbs] {title}",
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
    }
    result = _execute_with_rate_limit_retry(service.events().insert(calendarId="primary", body=event))
    return result["id"]


def delete_gcal_event(creds, event_id: str) -> None:
    service = build("calendar", "v3", credentials=creds)
    try:
        _execute_with_rate_limit_retry(service.events().delete(calendarId="primary", eventId=event_id))
    except HttpError as e:
        if e.resp.status not in (404, 410):
            raise


def update_gcal_event(creds, event_id: str, start_iso: str, end_iso: str) -> None:
    service = build("calendar", "v3", credentials=creds)
    _execute_with_rate_limit_retry(
        service.events().patch(
            calendarId="primary",
            eventId=event_id,
            body={
                "start": {"dateTime": start_iso},
                "end": {"dateTime": end_iso},
            },
        )
    )
