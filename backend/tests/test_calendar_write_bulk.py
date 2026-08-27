from unittest.mock import patch
from googleapiclient.errors import HttpError
from services.calendar_write import create_school_gcal_events_bulk, delete_gcal_events_bulk

CREDS = object()


class FakeHttpError(HttpError):
    """googleapiclient's HttpError needs a real response object; this fakes
    just enough of one (status + a body the rate-limit check can string-match)
    for the batch callback logic to exercise its retry branches."""

    def __init__(self, status: int, reason: str = ""):
        resp = type("Resp", (), {"status": status, "reason": reason})()
        super().__init__(resp, reason.encode())


class FakeBatch:
    """Stands in for googleapiclient's BatchHttpRequest: collects (request,
    callback) pairs via add(), then fires every callback on execute() —
    synchronously, so tests don't need a real event loop or network."""

    def __init__(self):
        self.items = []

    def add(self, request, callback=None):
        self.items.append((request, callback))

    def execute(self):
        for request, callback in self.items:
            request(callback)


class FakeService:
    """request-builder methods hand back a closure that FakeBatch.execute()
    calls with the callback, so each fake "request" decides its own outcome."""

    def __init__(self, outcomes):
        self.outcomes = outcomes  # dict keyed by id (event id or body-derived key) -> result or exception
        self.batch = FakeBatch()

    def events(self):
        return self

    def insert(self, calendarId, body):
        title = body["summary"]

        def _request(callback):
            outcome = self.outcomes[title]
            if isinstance(outcome, Exception):
                callback(None, None, outcome)
            else:
                callback(None, {"id": outcome}, None)

        return _request

    def delete(self, calendarId, eventId):
        def _request(callback):
            outcome = self.outcomes.get(eventId)
            if isinstance(outcome, Exception):
                callback(None, None, outcome)
            else:
                callback(None, None, None)

        return _request

    def new_batch_http_request(self):
        return self.batch


@patch("services.calendar_write.build")
def test_create_bulk_batches_requests_and_preserves_order(mock_build):
    events = [
        {"title": "Chemistry", "start": "2024-09-03T08:00:00", "end": "2024-09-03T08:45:00"},
        {"title": "Algebra II", "start": "2024-09-03T08:50:00", "end": "2024-09-03T09:35:00"},
        {"title": "Lunch", "start": "2024-09-03T10:49:00", "end": "2024-09-03T11:19:00"},
    ]
    mock_build.side_effect = lambda *a, **kw: FakeService({
        "Chemistry [SCHOOL]": "evt-1",
        "Algebra II [SCHOOL]": "evt-2",
        "Lunch [SCHOOL]": "evt-3",
    })

    ids = create_school_gcal_events_bulk(CREDS, events, chunk_size=50, max_workers=1)

    assert ids == ["evt-1", "evt-2", "evt-3"]


@patch("services.calendar_write.build")
def test_create_bulk_splits_into_multiple_chunks(mock_build):
    events = [{"title": str(i), "start": "s", "end": "e"} for i in range(5)]
    mock_build.side_effect = lambda *a, **kw: FakeService({f"{i} [SCHOOL]": f"evt-{i}" for i in range(5)})

    ids = create_school_gcal_events_bulk(CREDS, events, chunk_size=2, max_workers=2)

    assert ids == [f"evt-{i}" for i in range(5)]
    assert mock_build.call_count == 3  # 5 events / chunk_size 2 -> 3 batches


@patch("services.calendar_write.create_school_gcal_event")
@patch("services.calendar_write.build")
def test_create_bulk_retries_rate_limited_items_individually(mock_build, mock_create_single):
    events = [
        {"title": "Chemistry", "start": "2024-09-03T08:00:00", "end": "2024-09-03T08:45:00"},
        {"title": "Algebra II", "start": "2024-09-03T08:50:00", "end": "2024-09-03T09:35:00"},
    ]
    mock_build.side_effect = lambda *a, **kw: FakeService({
        "Chemistry [SCHOOL]": "evt-1",
        "Algebra II [SCHOOL]": FakeHttpError(429),
    })
    mock_create_single.return_value = "evt-retried"

    ids = create_school_gcal_events_bulk(CREDS, events, chunk_size=50, max_workers=1)

    assert ids == ["evt-1", "evt-retried"]
    mock_create_single.assert_called_once_with(
        CREDS, title="Algebra II", start_iso="2024-09-03T08:50:00", end_iso="2024-09-03T09:35:00"
    )


@patch("services.calendar_write.build")
def test_delete_bulk_calls_every_id(mock_build):
    event_ids = ["1", "2", "3", "4", "5"]
    mock_build.side_effect = lambda *a, **kw: FakeService({eid: None for eid in event_ids})

    delete_gcal_events_bulk(CREDS, event_ids, chunk_size=2, max_workers=2)

    assert mock_build.call_count == 3  # 5 ids / chunk_size 2 -> 3 batches


@patch("services.calendar_write.build")
def test_delete_bulk_swallows_already_gone_events(mock_build):
    mock_build.side_effect = lambda *a, **kw: FakeService({"1": FakeHttpError(404), "2": None})

    delete_gcal_events_bulk(CREDS, ["1", "2"], chunk_size=50, max_workers=1)  # should not raise


@patch("services.calendar_write.delete_gcal_event")
@patch("services.calendar_write.build")
def test_delete_bulk_retries_rate_limited_items_individually(mock_build, mock_delete_single):
    mock_build.side_effect = lambda *a, **kw: FakeService({"1": FakeHttpError(429), "2": None})

    delete_gcal_events_bulk(CREDS, ["1", "2"], chunk_size=50, max_workers=1)

    mock_delete_single.assert_called_once_with(CREDS, "1")
