from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch
from services.get_free_blocks import compute_free_blocks

TZ = ZoneInfo("America/New_York")


def gcal_event(start: datetime, end: datetime) -> dict:
    return {
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
    }


def dt(date, hour, minute=0):
    return datetime(date.year, date.month, date.day, hour, minute, tzinfo=TZ)


def test_past_blocks_excluded():
    today = datetime.now(TZ).date()
    # Single event earlier today that already passed; free block before it is in the past.
    event_start = dt(today, 9)
    event_end = dt(today, 10)
    now = dt(today, 14)  # simulate "it is now 14:00"

    with patch("services.get_free_blocks.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        blocks = compute_free_blocks([gcal_event(event_start, event_end)])

    for b in blocks:
        assert b["start"] >= now, f"Block {b} starts before now"


def test_future_blocks_included():
    today = datetime.now(TZ).date()
    tomorrow = today + timedelta(days=1)
    # Event tomorrow morning; free block after it should be included.
    event_start = dt(tomorrow, 9)
    event_end = dt(tomorrow, 10)
    now = dt(today, 14)

    with patch("services.get_free_blocks.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        blocks = compute_free_blocks([gcal_event(event_start, event_end)])

    tomorrow_blocks = [b for b in blocks if b["start"].date() == tomorrow]
    assert len(tomorrow_blocks) > 0


def test_empty_calendar_still_yields_free_blocks():
    today = datetime.now(TZ).date()
    now = dt(today, 14)

    with patch("services.get_free_blocks.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        blocks = compute_free_blocks([])

    assert len(blocks) > 0
    covered_dates = {b["start"].date() for b in blocks}
    assert today in covered_dates
    assert (today + timedelta(days=6)) in covered_dates


def test_sparse_events_do_not_truncate_lookahead_window():
    # A single event on day 1 should not cut off free blocks on later days —
    # the window always spans the full lookahead, not just dates with events.
    today = datetime.now(TZ).date()
    event_start = dt(today, 9)
    event_end = dt(today, 10)
    now = dt(today, 8)

    with patch("services.get_free_blocks.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        blocks = compute_free_blocks([gcal_event(event_start, event_end)], lookahead_days=7)

    covered_dates = {b["start"].date() for b in blocks}
    assert (today + timedelta(days=6)) in covered_dates
