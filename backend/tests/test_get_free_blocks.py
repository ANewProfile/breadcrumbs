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


def test_start_floor_is_ten_minutes_out_rounded_up_to_five():
    today = datetime.now(TZ).date()
    now = dt(today, 14, 3)  # 14:03 -> +10 = 14:13 -> rounds up to 14:15

    with patch("services.get_free_blocks.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        blocks = compute_free_blocks([])

    todays_blocks = [b for b in blocks if b["start"].date() == today]
    assert todays_blocks[0]["start"] == dt(today, 14, 15)


def test_start_floor_exact_five_minute_now_needs_no_rounding():
    today = datetime.now(TZ).date()
    now = dt(today, 14, 0)  # 14:00 -> +10 = 14:10, already a multiple of 5

    with patch("services.get_free_blocks.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        blocks = compute_free_blocks([])

    todays_blocks = [b for b in blocks if b["start"].date() == today]
    assert todays_blocks[0]["start"] == dt(today, 14, 10)


def test_recurring_no_go_zone_removes_window_every_day():
    today = datetime.now(TZ).date()
    now = dt(today, 8)
    zone = {"label": "Lunch", "start_time": "12:00", "end_time": "13:00", "days_of_week": None, "date": None}

    with patch("services.get_free_blocks.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        blocks = compute_free_blocks([], no_go_zones=[zone], lookahead_days=2)

    for offset in range(3):
        day = today + timedelta(days=offset)
        day_blocks = [b for b in blocks if b["start"].date() == day]
        for b in day_blocks:
            assert not (b["start"] < dt(day, 13) and b["end"] > dt(day, 12)), f"{b} overlaps lunch"


def test_one_off_no_go_zone_only_applies_to_its_date():
    today = datetime.now(TZ).date()
    tomorrow = today + timedelta(days=1)
    now = dt(today, 8)
    zone = {"label": "Dentist", "start_time": "14:00", "end_time": "15:00", "date": tomorrow.isoformat(), "days_of_week": None}

    with patch("services.get_free_blocks.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        blocks = compute_free_blocks([], no_go_zones=[zone], lookahead_days=2)

    tomorrow_blocks = [b for b in blocks if b["start"].date() == tomorrow]
    for b in tomorrow_blocks:
        assert not (b["start"] < dt(tomorrow, 15) and b["end"] > dt(tomorrow, 14))

    today_blocks = [b for b in blocks if b["start"].date() == today]
    assert any(b["start"] <= dt(today, 14) and b["end"] >= dt(today, 15) for b in today_blocks)


def test_days_of_week_no_go_zone_only_applies_on_matching_weekdays():
    today = datetime.now(TZ).date()
    now = dt(today, 8)
    # Pick a weekday that's definitely not "today" so we can assert it's untouched.
    other_weekday = (today.weekday() + 1) % 7
    zone = {"label": "Gym", "start_time": "17:00", "end_time": "18:00", "days_of_week": [other_weekday], "date": None}

    with patch("services.get_free_blocks.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        blocks = compute_free_blocks([], no_go_zones=[zone], lookahead_days=1)

    today_blocks = [b for b in blocks if b["start"].date() == today]
    assert any(b["start"] <= dt(today, 17) and b["end"] >= dt(today, 18) for b in today_blocks)


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
