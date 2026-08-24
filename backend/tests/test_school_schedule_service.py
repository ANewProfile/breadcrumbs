from datetime import date
from services.school_schedule_service import (
    get_school_schedule,
    update_school_schedule,
    compute_school_events,
    get_last_event_watermark,
    record_last_event_watermark,
    clear_last_event_watermark,
    get_last_generation,
    record_last_generation,
    clear_last_generation,
    rotation_day_number_on,
    DEFAULT_BELL_TIMES,
)


def make_schedule(**day_overrides):
    day_schedules = {
        str(n): {"z": None, "periods": [None] * 5, "lunch_wave": 1}
        for n in range(1, 7)
    }
    for day_num, override in day_overrides.items():
        day_schedules[day_num].update(override)
    return {
        "bell_times": dict(DEFAULT_BELL_TIMES),
        "courses": {"A": "Chemistry", "B": "Algebra II"},
        "day_schedules": day_schedules,
    }


def test_rotation_wraps_after_six_school_days():
    schedule = make_schedule(**{
        "1": {"periods": ["A", None, None, None, None]},
        "2": {"periods": ["A", None, None, None, None]},
        "3": {"periods": ["A", None, None, None, None]},
        "4": {"periods": ["A", None, None, None, None]},
        "5": {"periods": ["A", None, None, None, None]},
        "6": {"periods": ["B", None, None, None, None]},
    })
    # Mon 2024-06-10 through Mon 2024-06-17 = 6 consecutive weekdays (skips the weekend)
    events = compute_school_events(
        schedule, date(2024, 6, 10), date(2024, 6, 17), set(), "1", "America/New_York"
    )
    titles = [e["title"] for e in events if e["label"] == "Period 1"]
    assert titles == ["Chemistry", "Chemistry", "Chemistry", "Chemistry", "Chemistry", "Algebra II"]


def test_weekends_and_off_dates_are_skipped_and_dont_consume_rotation():
    schedule = make_schedule(**{
        "1": {"periods": ["A", None, None, None, None]},
        "2": {"periods": ["B", None, None, None, None]},
    })
    # Fri 2024-06-14 (Day 1), weekend skipped, Mon 2024-06-17 marked off, Tue 2024-06-18 (Day 2)
    events = compute_school_events(
        schedule,
        date(2024, 6, 14),
        date(2024, 6, 18),
        {"2024-06-17"},
        "1",
        "America/New_York",
    )
    period_1_events = [e for e in events if e["label"] == "Period 1"]
    assert [e["date"] for e in period_1_events] == ["2024-06-14", "2024-06-18"]
    assert [e["title"] for e in period_1_events] == ["Chemistry", "Algebra II"]


def test_lunch_wave_1_sits_before_period_3_with_its_own_times():
    schedule = make_schedule(**{"1": {"periods": [None, None, "A", None, None], "lunch_wave": 1}})
    events = compute_school_events(schedule, date(2024, 6, 10), date(2024, 6, 10), set(), "1", "America/New_York")
    labels_titles = [(e["label"], e["title"]) for e in events]
    assert labels_titles == [("Lunch", "Lunch"), ("Period 3", "Chemistry")]
    assert events[0]["start"].startswith("2024-06-10T10:49")
    assert events[0]["end"].startswith("2024-06-10T11:19")
    assert events[1]["start"].startswith("2024-06-10T11:21")
    assert events[1]["end"].startswith("2024-06-10T12:31")


def test_lunch_wave_2_sits_after_period_3_with_its_own_times():
    schedule = make_schedule(**{"1": {"periods": [None, None, "A", None, None], "lunch_wave": 2}})
    events = compute_school_events(schedule, date(2024, 6, 10), date(2024, 6, 10), set(), "1", "America/New_York")
    labels_titles = [(e["label"], e["title"]) for e in events]
    assert labels_titles == [("Period 3", "Chemistry"), ("Lunch", "Lunch")]
    assert events[0]["start"].startswith("2024-06-10T10:54")
    assert events[0]["end"].startswith("2024-06-10T12:04")
    assert events[1]["start"].startswith("2024-06-10T12:06")
    assert events[1]["end"].startswith("2024-06-10T12:36")


def test_free_periods_and_missing_z_block_produce_no_events():
    schedule = make_schedule(**{"1": {"periods": [None, None, None, None, None], "z": None}})
    events = compute_school_events(schedule, date(2024, 6, 10), date(2024, 6, 10), set(), "1", "America/New_York")
    assert events == [{
        "title": "Lunch", "label": "Lunch", "date": "2024-06-10",
        "start": "2024-06-10T10:49:00-04:00", "end": "2024-06-10T11:19:00-04:00",
    }]


def test_period5_end_override_shortens_only_that_day():
    schedule = make_schedule(**{
        "5": {"periods": [None, None, None, None, "A"]},
        "6": {"periods": [None, None, None, None, "A"], "period5_end": "12:30"},
    })
    day5_events = compute_school_events(schedule, date(2024, 6, 14), date(2024, 6, 14), set(), "5", "America/New_York")
    day6_events = compute_school_events(schedule, date(2024, 6, 14), date(2024, 6, 14), set(), "6", "America/New_York")

    p5_day5 = next(e for e in day5_events if e["label"] == "Period 5")
    p5_day6 = next(e for e in day6_events if e["label"] == "Period 5")

    assert p5_day5["start"].startswith("2024-06-14T12:10") and p5_day5["end"].startswith("2024-06-14T12:55")
    assert p5_day6["start"].startswith("2024-06-14T12:10") and p5_day6["end"].startswith("2024-06-14T12:30")


def test_early_dismissal_overrides_period5_end_for_that_date_only():
    schedule = make_schedule(**{
        "1": {"periods": [None, None, None, None, "A"]},
        "2": {"periods": [None, None, None, None, "A"]},
    })
    # Fri 2024-06-14 = Day 1, Mon 2024-06-17 = Day 2 (weekend skipped)
    events = compute_school_events(
        schedule,
        date(2024, 6, 14),
        date(2024, 6, 17),
        set(),
        "1",
        "America/New_York",
        {"2024-06-14": "12:30"},
    )
    p5_events = {e["date"]: e for e in events if e["label"] == "Period 5"}
    assert p5_events["2024-06-14"]["end"].startswith("2024-06-14T12:30")  # overridden
    assert p5_events["2024-06-17"]["end"].startswith("2024-06-17T12:55")  # unaffected, normal default


def test_unlabeled_block_falls_back_to_letter_name():
    schedule = make_schedule(**{"1": {"periods": ["G", None, None, None, None]}})
    events = compute_school_events(schedule, date(2024, 6, 10), date(2024, 6, 10), set(), "1", "America/New_York")
    assert events[0]["title"] == "G Block"


class FakeCollection:
    def __init__(self):
        self.doc = None

    def find_one(self, _query):
        return self.doc

    def update_one(self, query, update, upsert=False):
        del upsert
        self.doc = {**(self.doc or {"_id": query["_id"]}), **update["$set"]}


def test_get_school_schedule_fills_defaults_for_missing_user():
    collection = FakeCollection()
    result = get_school_schedule(collection, "user-1")
    assert result["bell_times"] == DEFAULT_BELL_TIMES
    assert result["courses"] == {}
    assert set(result["day_schedules"].keys()) == {"1", "2", "3", "4", "5", "6"}


def test_update_school_schedule_merges_partial_day_update():
    collection = FakeCollection()
    update_school_schedule(collection, "user-1", {
        "day_schedules": {"3": {"z": "A", "periods": ["B", "C", "D", "E", "F"], "lunch_wave": 2}}
    })
    result = get_school_schedule(collection, "user-1")
    assert result["day_schedules"]["3"]["z"] == "A"
    assert result["day_schedules"]["1"]["z"] is None  # untouched days keep defaults


def test_get_last_event_watermark_is_none_for_user_with_no_record():
    collection = FakeCollection()
    assert get_last_event_watermark(collection, "user-1") is None


def test_record_last_event_watermark_stores_latest_end():
    collection = FakeCollection()
    events = [
        {"end": "2024-09-03T09:35:00-04:00"},
        {"end": "2024-09-05T12:55:00-04:00"},
        {"end": "2024-09-04T08:45:00-04:00"},
    ]
    record_last_event_watermark(collection, "user-1", events)
    assert get_last_event_watermark(collection, "user-1") == "2024-09-05T12:55:00-04:00"


def test_record_last_event_watermark_never_moves_backwards():
    collection = FakeCollection()
    record_last_event_watermark(collection, "user-1", [{"end": "2024-09-05T12:55:00-04:00"}])
    record_last_event_watermark(collection, "user-1", [{"end": "2024-09-04T08:45:00-04:00"}])
    assert get_last_event_watermark(collection, "user-1") == "2024-09-05T12:55:00-04:00"


def test_record_last_event_watermark_does_nothing_for_empty_events():
    collection = FakeCollection()
    record_last_event_watermark(collection, "user-1", [])
    assert get_last_event_watermark(collection, "user-1") is None


def test_clear_last_event_watermark_resets_to_none():
    collection = FakeCollection()
    record_last_event_watermark(collection, "user-1", [{"end": "2024-09-05T12:55:00-04:00"}])
    clear_last_event_watermark(collection, "user-1")
    assert get_last_event_watermark(collection, "user-1") is None


def test_get_last_generation_is_none_for_user_with_no_record():
    collection = FakeCollection()
    assert get_last_generation(collection, "user-1") is None


def test_record_and_get_last_generation_round_trips():
    collection = FakeCollection()
    record_last_generation(
        collection, "user-1",
        start_date="2024-09-03", end_date="2024-09-12", start_day_number="1",
        off_dates=["2024-09-05"], early_dismissals=[{"date": "2024-09-06", "period5_end": "12:30"}],
    )
    result = get_last_generation(collection, "user-1")
    assert result == {
        "start_date": "2024-09-03",
        "end_date": "2024-09-12",
        "start_day_number": "1",
        "off_dates": ["2024-09-05"],
        "early_dismissals": [{"date": "2024-09-06", "period5_end": "12:30"}],
    }


def test_record_last_generation_sorts_off_dates():
    collection = FakeCollection()
    record_last_generation(
        collection, "user-1",
        start_date="2024-09-03", end_date="2024-09-12", start_day_number="1",
        off_dates=["2024-09-10", "2024-09-05"], early_dismissals=[],
    )
    assert get_last_generation(collection, "user-1")["off_dates"] == ["2024-09-05", "2024-09-10"]


def test_clear_last_generation_resets_to_none():
    collection = FakeCollection()
    record_last_generation(
        collection, "user-1",
        start_date="2024-09-03", end_date="2024-09-12", start_day_number="1",
        off_dates=[], early_dismissals=[],
    )
    clear_last_generation(collection, "user-1")
    assert get_last_generation(collection, "user-1") is None


def test_rotation_day_number_on_start_date_returns_start_day_number():
    assert rotation_day_number_on(date(2024, 9, 3), "1", set(), date(2024, 9, 3)) == "1"


def test_rotation_day_number_on_advances_over_weekdays_and_skips_weekends():
    # Tue 9/3=Day1, Wed 9/4=Day2, Thu 9/5=Day3, Fri 9/6=Day4, weekend skipped, Mon 9/9=Day5
    assert rotation_day_number_on(date(2024, 9, 3), "1", set(), date(2024, 9, 5)) == "3"
    assert rotation_day_number_on(date(2024, 9, 3), "1", set(), date(2024, 9, 9)) == "5"


def test_rotation_day_number_on_wraps_after_six():
    # Tue 9/3 through Wed 9/11 = 7 weekdays -> wraps 1..6 then back to 1
    assert rotation_day_number_on(date(2024, 9, 3), "1", set(), date(2024, 9, 11)) == "1"


def test_rotation_day_number_on_skips_off_dates_without_consuming_a_number():
    # Off date 9/4 doesn't consume Day2 — 9/5 still gets Day2, not Day3
    assert rotation_day_number_on(date(2024, 9, 3), "1", {"2024-09-04"}, date(2024, 9, 5)) == "2"
