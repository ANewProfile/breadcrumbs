from datetime import date
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from routers.school_schedule import (
    BellTime,
    WaveTimes,
    BellTimes,
    DaySchedule,
    ScheduleConfigUpdate,
    GenerateIn,
    SnowDayIn,
    generate_school_schedule,
    delete_future_school_events,
    add_snow_day,
)

USER = {"_id": "user-1"}


def make_full_schedule():
    return {
        "bell_times": {
            "z": None,
            "p1": {"start": "08:00", "end": "08:45"},
            "p2": {"start": "08:50", "end": "09:35"},
            "wave1": {"lunch": {"start": "10:49", "end": "11:19"}, "period3": {"start": "11:21", "end": "12:31"}},
            "wave2": {"period3": {"start": "10:54", "end": "12:04"}, "lunch": {"start": "12:06", "end": "12:36"}},
            "p4": {"start": "11:20", "end": "12:05"},
            "p5": {"start": "12:10", "end": "12:55"},
        },
        "courses": {"A": "Chemistry"},
        "day_schedules": {
            str(n): {"z": None, "periods": ["A", None, None, None, None], "lunch_wave": 1}
            for n in range(1, 7)
        },
    }


def test_valid_bell_time():
    bt = BellTime(start="08:00", end="08:45")
    assert bt.start == "08:00"


@pytest.mark.parametrize("bad_time", ["8:00", "25:00", "08:60", "morning", ""])
def test_invalid_bell_time_rejected(bad_time):
    with pytest.raises(ValidationError):
        BellTime(start=bad_time, end="08:45")


def test_valid_day_schedule():
    ds = DaySchedule(z="A", periods=["B", "C", None, "D", "T"], lunch_wave=2)
    assert ds.periods[2] is None
    assert ds.lunch_wave == 2


def test_day_schedule_wrong_period_count_rejected():
    with pytest.raises(ValidationError):
        DaySchedule(periods=["A", "B"], lunch_wave=1)


def test_day_schedule_invalid_block_letter_rejected():
    with pytest.raises(ValidationError):
        DaySchedule(periods=["A", "B", "Z", "D", "T"], lunch_wave=1)  # type: ignore[arg-type]


def test_day_schedule_invalid_lunch_wave_rejected():
    with pytest.raises(ValidationError):
        DaySchedule(periods=[None] * 5, lunch_wave=3)  # type: ignore[arg-type]


def test_day_schedule_period5_end_defaults_to_none():
    ds = DaySchedule(periods=[None] * 5, lunch_wave=1)
    assert ds.period5_end is None


def test_day_schedule_valid_period5_end_accepted():
    ds = DaySchedule(periods=[None] * 5, lunch_wave=1, period5_end="12:30")
    assert ds.period5_end == "12:30"


@pytest.mark.parametrize("bad_time", ["12:5", "24:10", "12:75", "noon"])
def test_day_schedule_invalid_period5_end_rejected(bad_time):
    with pytest.raises(ValidationError):
        DaySchedule(periods=[None] * 5, lunch_wave=1, period5_end=bad_time)


def test_schedule_config_update_partial():
    body = ScheduleConfigUpdate(courses={"A": "Chemistry"})
    assert body.courses == {"A": "Chemistry"}
    assert body.bell_times is None
    assert body.day_schedules is None


def test_generate_in_rejects_end_before_start():
    with pytest.raises(ValidationError):
        GenerateIn(start_date=date(2024, 9, 5), end_date=date(2024, 9, 1))


def test_generate_in_rejects_excessive_range():
    with pytest.raises(ValidationError):
        GenerateIn(start_date=date(2024, 1, 1), end_date=date(2026, 1, 1))


def test_generate_in_defaults_start_day_and_off_dates():
    body = GenerateIn(start_date=date(2024, 9, 3), end_date=date(2024, 9, 6))
    assert body.start_day_number == "1"
    assert body.off_dates == []


def test_wave_times_requires_both_lunch_and_period3():
    with pytest.raises(ValidationError):
        WaveTimes(lunch={"start": "10:49", "end": "11:19"})  # type: ignore[call-arg]


def test_bell_times_wave1_and_wave2_independent():
    bt = BellTimes(
        p1={"start": "08:00", "end": "08:45"},
        p2={"start": "08:50", "end": "09:35"},
        wave1={"lunch": {"start": "10:49", "end": "11:19"}, "period3": {"start": "11:21", "end": "12:31"}},
        wave2={"period3": {"start": "10:54", "end": "12:04"}, "lunch": {"start": "12:06", "end": "12:36"}},
        p4={"start": "11:20", "end": "12:05"},
        p5={"start": "12:10", "end": "12:55"},
    )
    assert bt.wave1.lunch.start == "10:49"
    assert bt.wave2.period3.start == "10:54"


@patch("routers.school_schedule.record_last_generation")
@patch("routers.school_schedule.record_last_event_watermark")
@patch("routers.school_schedule.create_school_gcal_events_bulk")
@patch("routers.school_schedule.get_credentials_for_user")
@patch("routers.school_schedule.get_settings")
@patch("routers.school_schedule.get_school_schedule")
def test_generate_creates_events_with_school_suffixed_creator(
    mock_get_schedule, mock_get_settings, mock_creds, mock_create_bulk, mock_record_watermark, mock_record_generation
):
    mock_get_schedule.return_value = make_full_schedule()
    mock_get_settings.return_value = {"timezone": "America/New_York"}
    mock_create_bulk.side_effect = lambda creds, events: ["evt-1"] * len(events)

    body = GenerateIn(start_date=date(2024, 9, 3), end_date=date(2024, 9, 3))  # a Tuesday
    result = generate_school_schedule(body, USER)

    assert result["created_count"] > 0
    mock_create_bulk.assert_called_once()
    assert all(ev["gcal_event_id"] == "evt-1" for ev in result["events"])
    mock_record_watermark.assert_called_once()


@patch("routers.school_schedule.record_last_generation")
@patch("routers.school_schedule.record_last_event_watermark")
@patch("routers.school_schedule.create_school_gcal_events_bulk")
@patch("routers.school_schedule.get_credentials_for_user")
@patch("routers.school_schedule.get_settings")
@patch("routers.school_schedule.get_school_schedule")
def test_generate_applies_early_dismissal_override_for_that_date_only(
    mock_get_schedule, mock_get_settings, mock_creds, mock_create_bulk, mock_record_watermark, mock_record_generation
):
    schedule = make_full_schedule()
    for day_sched in schedule["day_schedules"].values():
        day_sched["periods"] = [None, None, None, None, "A"]  # give every day a Period 5 block
    mock_get_schedule.return_value = schedule
    mock_get_settings.return_value = {"timezone": "America/New_York"}
    mock_create_bulk.side_effect = lambda creds, events: [f"evt-{i}" for i in range(len(events))]

    body = GenerateIn(
        start_date=date(2024, 9, 3),
        end_date=date(2024, 9, 4),
        early_dismissals=[{"date": "2024-09-03", "period5_end": "12:30"}],
    )
    result = generate_school_schedule(body, USER)

    p5_events = {ev["date"]: ev for ev in result["events"] if ev["label"] == "Period 5"}
    assert p5_events["2024-09-03"]["end"].startswith("2024-09-03T12:30")
    assert p5_events["2024-09-04"]["end"].startswith("2024-09-04T12:55")  # unaffected


def test_generate_rejects_date_thats_both_off_and_early_dismissal():
    with pytest.raises(ValidationError):
        GenerateIn(
            start_date=date(2024, 9, 3),
            end_date=date(2024, 9, 4),
            off_dates=[date(2024, 9, 3)],
            early_dismissals=[{"date": "2024-09-03", "period5_end": "12:30"}],
        )


@patch("routers.school_schedule.clear_last_generation")
@patch("routers.school_schedule.clear_last_event_watermark")
@patch("routers.school_schedule.get_last_event_watermark")
@patch("routers.school_schedule.delete_gcal_events_bulk")
@patch("routers.school_schedule.search_events")
@patch("routers.school_schedule.get_credentials_for_user")
def test_delete_future_school_events_filters_to_exact_suffix(
    mock_creds, mock_search, mock_delete_bulk, mock_get_watermark, mock_clear_watermark, mock_clear_generation
):
    mock_get_watermark.return_value = None
    mock_search.return_value = [
        {"id": "1", "summary": "Chemistry [SCHOOL]"},
        {"id": "2", "summary": "Unrelated event that happens to mention [SCHOOL] mid-description"},
        {"id": "3", "summary": "Algebra II [SCHOOL]"},
    ]

    result = delete_future_school_events(USER)

    assert result["deleted_count"] == 2
    mock_delete_bulk.assert_called_once()
    _, deleted_ids = mock_delete_bulk.call_args.args
    assert set(deleted_ids) == {"1", "3"}
    mock_clear_watermark.assert_called_once()


@patch("routers.school_schedule.clear_last_generation")
@patch("routers.school_schedule.clear_last_event_watermark")
@patch("routers.school_schedule.get_last_event_watermark")
@patch("routers.school_schedule.delete_gcal_events_bulk")
@patch("routers.school_schedule.search_events")
@patch("routers.school_schedule.get_credentials_for_user")
def test_delete_future_school_events_bounds_search_with_watermark(
    mock_creds, mock_search, mock_delete_bulk, mock_get_watermark, mock_clear_watermark, mock_clear_generation
):
    mock_get_watermark.return_value = "2099-09-03T12:55:00-04:00"
    mock_search.return_value = []

    delete_future_school_events(USER)

    _, kwargs = mock_search.call_args
    assert kwargs["time_max_iso"] == "2099-09-03T12:56:00-04:00"


@patch("routers.school_schedule.clear_last_generation")
@patch("routers.school_schedule.clear_last_event_watermark")
@patch("routers.school_schedule.get_last_event_watermark")
@patch("routers.school_schedule.delete_gcal_events_bulk")
@patch("routers.school_schedule.search_events")
@patch("routers.school_schedule.get_credentials_for_user")
def test_delete_future_school_events_skips_search_when_watermark_already_past(
    mock_creds, mock_search, mock_delete_bulk, mock_get_watermark, mock_clear_watermark, mock_clear_generation
):
    mock_get_watermark.return_value = "2000-01-01T00:00:00-04:00"

    result = delete_future_school_events(USER)

    assert result["deleted_count"] == 0
    mock_search.assert_not_called()
    mock_delete_bulk.assert_not_called()
    mock_clear_watermark.assert_called_once()
    mock_clear_generation.assert_called_once()


def make_rotation_schedule():
    """Each rotation day has a distinct Period 1 letter (A..F) so tests can read
    the day number for a date straight off the generated event's title."""
    letters = ["A", "B", "C", "D", "E", "F"]
    return {
        "bell_times": {
            "z": None,
            "p1": {"start": "08:00", "end": "08:45"},
            "p2": {"start": "08:50", "end": "09:35"},
            "wave1": {"lunch": {"start": "10:49", "end": "11:19"}, "period3": {"start": "11:21", "end": "12:31"}},
            "wave2": {"period3": {"start": "10:54", "end": "12:04"}, "lunch": {"start": "12:06", "end": "12:36"}},
            "p4": {"start": "11:20", "end": "12:05"},
            "p5": {"start": "12:10", "end": "12:55"},
        },
        "courses": {letter: letter for letter in letters},
        "day_schedules": {
            str(n): {"z": None, "periods": [letters[n - 1], None, None, None, None], "lunch_wave": 1}
            for n in range(1, 7)
        },
    }


def make_event(event_id: str, date_str: str, title: str, start_time: str = "08:00", end_time: str = "08:45") -> dict:
    """A minimal Google Calendar event resource for a school-schedule event, as
    add_snow_day reads it: summary, start.dateTime, and end.dateTime."""
    return {
        "id": event_id,
        "summary": f"{title} [SCHOOL]",
        "start": {"dateTime": f"{date_str}T{start_time}:00-04:00"},
        "end": {"dateTime": f"{date_str}T{end_time}:00-04:00"},
    }


@patch("routers.school_schedule.search_events")
@patch("routers.school_schedule.get_credentials_for_user")
@patch("routers.school_schedule.get_settings")
@patch("routers.school_schedule.get_school_schedule")
def test_snow_day_requires_school_events_on_that_date(mock_get_schedule, mock_get_settings, mock_creds, mock_search):
    mock_get_schedule.return_value = make_rotation_schedule()
    mock_get_settings.return_value = {"timezone": "America/New_York"}
    mock_search.return_value = []
    with pytest.raises(HTTPException) as exc:
        add_snow_day(SnowDayIn(date=date(2024, 9, 5)), USER)
    assert exc.value.status_code == 400


@patch("routers.school_schedule.search_events")
@patch("routers.school_schedule.get_credentials_for_user")
@patch("routers.school_schedule.get_settings")
@patch("routers.school_schedule.get_school_schedule")
def test_snow_day_rejects_date_with_no_events_even_if_other_dates_have_them(
    mock_get_schedule, mock_get_settings, mock_creds, mock_search
):
    mock_get_schedule.return_value = make_rotation_schedule()
    mock_get_settings.return_value = {"timezone": "America/New_York"}
    mock_search.return_value = [make_event("evt-1", "2024-09-06", "D")]
    with pytest.raises(HTTPException) as exc:
        add_snow_day(SnowDayIn(date=date(2024, 9, 5)), USER)
    assert exc.value.status_code == 400


def test_snow_day_rejects_weekend_date():
    with pytest.raises(HTTPException) as exc:
        add_snow_day(SnowDayIn(date=date(2024, 9, 7)), USER)  # Saturday
    assert exc.value.status_code == 400


@patch("routers.school_schedule.record_last_event_watermark")
@patch("routers.school_schedule.create_school_gcal_events_bulk")
@patch("routers.school_schedule.delete_gcal_events_bulk")
@patch("routers.school_schedule.search_events")
@patch("routers.school_schedule.get_credentials_for_user")
@patch("routers.school_schedule.get_settings")
@patch("routers.school_schedule.get_school_schedule")
def test_snow_day_shifts_content_one_school_day_later_and_appends_a_new_last_day(
    mock_get_schedule, mock_get_settings, mock_creds,
    mock_search, mock_delete_bulk, mock_create_bulk, mock_record_watermark,
):
    # These are the events already sitting on the calendar (this tool's prior
    # output) from the snow date (Thu 2024-09-05) through the previous last
    # school day (Thu 2024-09-12) — read back directly instead of a stored
    # /generate record. Each date's own content (here, just its Period 1
    # title) should reappear verbatim one already-scheduled date later, with
    # a brand new date appended past 09-12 to host what was on 09-12.
    mock_get_schedule.return_value = make_rotation_schedule()
    mock_get_settings.return_value = {"timezone": "America/New_York"}
    mock_search.return_value = [
        make_event("old-1", "2024-09-05", "C"),
        make_event("old-2", "2024-09-06", "D"),
        make_event("old-3", "2024-09-09", "E"),
        make_event("old-4", "2024-09-10", "F"),
        make_event("old-5", "2024-09-11", "A"),
        make_event("old-6", "2024-09-12", "B"),
    ]
    mock_create_bulk.side_effect = lambda creds, events: [f"evt-{i}" for i in range(len(events))]

    result = add_snow_day(SnowDayIn(date=date(2024, 9, 5)), USER)

    period1_days = {ev["date"]: ev["title"] for ev in result["events"] if ev["label"] == "Period 1"}
    assert period1_days == {
        "2024-09-06": "C",  # 09-05's own content, pushed to the next school day
        "2024-09-09": "D",
        "2024-09-10": "E",
        "2024-09-11": "F",
        "2024-09-12": "A",
        "2024-09-13": "B",  # new day appended past the old last day (09-12) for its content
    }
    assert "2024-09-05" not in period1_days
    assert result["removed_date"] == "2024-09-05"
    assert result["deleted_count"] == 6
    assert result["created_count"] == 6
    mock_delete_bulk.assert_called_once()


@patch("routers.school_schedule.record_last_event_watermark")
@patch("routers.school_schedule.create_school_gcal_events_bulk")
@patch("routers.school_schedule.delete_gcal_events_bulk")
@patch("routers.school_schedule.search_events")
@patch("routers.school_schedule.get_credentials_for_user")
@patch("routers.school_schedule.get_settings")
@patch("routers.school_schedule.get_school_schedule")
def test_snow_day_appended_day_skips_the_weekend(
    mock_get_schedule, mock_get_settings, mock_creds,
    mock_search, mock_delete_bulk, mock_create_bulk, mock_record_watermark,
):
    # Only the snow date itself (Fri 2024-09-06) has events, so its content
    # moves to a brand new appended date — which must skip Sat/Sun.
    mock_get_schedule.return_value = make_rotation_schedule()
    mock_get_settings.return_value = {"timezone": "America/New_York"}
    mock_search.return_value = [make_event("old-1", "2024-09-06", "D")]
    mock_create_bulk.side_effect = lambda creds, events: [f"evt-{i}" for i in range(len(events))]

    result = add_snow_day(SnowDayIn(date=date(2024, 9, 6)), USER)

    assert [ev["date"] for ev in result["events"]] == ["2024-09-09"]  # Monday, not 09-07/08
    assert result["events"][0]["title"] == "D"
    assert result["deleted_count"] == 1
    assert result["created_count"] == 1


@patch("routers.school_schedule.search_events")
@patch("routers.school_schedule.get_credentials_for_user")
@patch("routers.school_schedule.get_settings")
@patch("routers.school_schedule.get_school_schedule")
def test_snow_day_preserves_an_early_dismissals_end_time_when_it_shifts(
    mock_get_schedule, mock_get_settings, mock_creds, mock_search
):
    # A one-off early dismissal is just whatever end time actually landed on
    # the calendar event — carrying the raw event forward to its new date
    # preserves that automatically, with no separate tracking needed.
    mock_get_schedule.return_value = make_rotation_schedule()
    mock_get_settings.return_value = {"timezone": "America/New_York"}
    mock_search.return_value = [
        make_event("old-1", "2024-09-05", "C"),
        make_event("old-2", "2024-09-06", "D", end_time="11:15"),  # early dismissal
    ]
    with patch("routers.school_schedule.delete_gcal_events_bulk"), \
         patch("routers.school_schedule.create_school_gcal_events_bulk") as mock_create_bulk, \
         patch("routers.school_schedule.record_last_event_watermark"):
        mock_create_bulk.side_effect = lambda creds, events: [f"evt-{i}" for i in range(len(events))]
        result = add_snow_day(SnowDayIn(date=date(2024, 9, 5)), USER)

    # 09-06's own content (the early-dismissal event) moves to the next
    # already-scheduled date, 09-09 (09-05's Thu->Fri gap has no weekend to
    # skip, but 09-06 is a Friday so its successor is Monday 09-09).
    shifted = next(ev for ev in result["events"] if ev["date"] == "2024-09-09")
    assert shifted["end"].startswith("2024-09-09T11:15:00")
    assert shifted["title"] == "D"
