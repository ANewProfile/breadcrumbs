import random
import time
from concurrent.futures import ThreadPoolExecutor
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

RATE_LIMIT_MAX_RETRIES = 5
RATE_LIMIT_BASE_DELAY_SECONDS = 1.0

# Calendar's batch endpoint lets one HTTP request carry many operations (Google
# caps a single batch at 1000, but a few hundred events sharing one connection
# already risks a slow/oversized response, so chunk well under that). Chunks
# still run concurrently against each other, same as the old one-request-per-
# event approach did per event.
#
# Each sub-request inside a batch counts against Calendar's per-user quota
# (500 queries/100s by default) individually, so BATCH_CHUNK_SIZE * BATCH_MAX_WORKERS
# is roughly the size of the burst fired at once. 50 * 4 = 200 was tripping that
# quota for larger schedules even with the retry/backoff below absorbing some of
# it — halving both keeps a burst at 25 * 2 = 50, comfortably under the limit.
BATCH_CHUNK_SIZE = 25
BATCH_MAX_WORKERS = 2


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


def create_school_gcal_event(creds, title: str, start_iso: str, end_iso: str) -> str:
    """Events from the school-schedule tool are suffixed rather than prefixed,
    so they read as "Chemistry [SCHOOL]" instead of "[Breadcrumbs] Chemistry"."""
    service = build("calendar", "v3", credentials=creds)
    event = {
        "summary": f"{title} [SCHOOL]",
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
    }
    result = _execute_with_rate_limit_retry(service.events().insert(calendarId="primary", body=event))
    return result["id"]


def _chunked(items: list, chunk_size: int) -> list[list]:
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def create_school_gcal_events_bulk(
    creds, events: list[dict], chunk_size: int = BATCH_CHUNK_SIZE, max_workers: int = BATCH_MAX_WORKERS
) -> list[str]:
    """
    Creates many events via Calendar's batch endpoint — one HTTP request bundles
    up to `chunk_size` inserts instead of one request per event, and the chunks
    themselves run concurrently. A semester's worth of blocks (100+ events) done
    one request at a time could take minutes; batching cuts that to a handful of
    round trips. Resource objects from build() aren't thread-safe, so each chunk
    builds its own service, same as the old per-event approach did.

    Quota is still enforced per item inside a batch, so an individual insert can
    still come back rate-limited even though the request as a whole succeeded —
    those are retried one at a time through create_school_gcal_event, which
    already has backoff for exactly this.
    """
    results: list[str | None] = [None] * len(events)
    rate_limited: list[int] = []

    def _run_chunk(base_index: int, chunk: list[dict]) -> None:
        service = build("calendar", "v3", credentials=creds)
        batch = service.new_batch_http_request()
        for offset, ev in enumerate(chunk):
            i = base_index + offset

            def _callback(request_id, response, exception, i=i):
                if exception is not None:
                    if isinstance(exception, HttpError) and _is_rate_limit_error(exception):
                        rate_limited.append(i)
                    else:
                        raise exception
                else:
                    results[i] = response["id"]

            body = {
                "summary": f"{ev['title']} [SCHOOL]",
                "start": {"dateTime": ev["start"]},
                "end": {"dateTime": ev["end"]},
            }
            batch.add(service.events().insert(calendarId="primary", body=body), callback=_callback)
        batch.execute()

    chunks = [(i, chunk) for i, chunk in zip(range(0, len(events), chunk_size), _chunked(events, chunk_size))]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(lambda c: _run_chunk(*c), chunks))

    for i in rate_limited:
        results[i] = create_school_gcal_event(
            creds, title=events[i]["title"], start_iso=events[i]["start"], end_iso=events[i]["end"]
        )

    return results


def delete_gcal_event(creds, event_id: str) -> None:
    service = build("calendar", "v3", credentials=creds)
    try:
        _execute_with_rate_limit_retry(service.events().delete(calendarId="primary", eventId=event_id))
    except HttpError as e:
        if e.resp.status not in (404, 410):
            raise


def delete_gcal_events_bulk(
    creds, event_ids: list[str], chunk_size: int = BATCH_CHUNK_SIZE, max_workers: int = BATCH_MAX_WORKERS
) -> None:
    """Deletes many events via Calendar's batch endpoint — see
    create_school_gcal_events_bulk for why, and for the per-item rate-limit
    fallback. A 404/410 (already gone) is swallowed per item, same as the
    single-event delete_gcal_event does."""
    def _run_chunk(chunk: list[str]) -> None:
        service = build("calendar", "v3", credentials=creds)
        batch = service.new_batch_http_request()
        for event_id in chunk:
            def _callback(request_id, response, exception, event_id=event_id):
                if exception is None:
                    return
                if isinstance(exception, HttpError) and exception.resp.status in (404, 410):
                    return
                if isinstance(exception, HttpError) and _is_rate_limit_error(exception):
                    delete_gcal_event(creds, event_id)
                else:
                    raise exception

            batch.add(service.events().delete(calendarId="primary", eventId=event_id), callback=_callback)
        batch.execute()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(_run_chunk, _chunked(event_ids, chunk_size)))


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
