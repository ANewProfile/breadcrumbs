from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

BLOCK_LETTERS = ["A", "B", "C", "D", "E", "F", "G", "T"]
DAY_NUMBERS = ["1", "2", "3", "4", "5", "6"]

# Events from the school-schedule tool are suffixed rather than prefixed, so
# they read as "Chemistry [SCHOOL]" instead of "[Breadcrumbs] Chemistry".
SCHOOL_EVENT_SUFFIX = " [SCHOOL]"

# Lunch wave 1 and wave 2 run on fully independent clock times around 3rd period
# (not just the same two slots swapped) — e.g. wave 1's lunch+class block can
# start and end at different times than wave 2's class+lunch block.
DEFAULT_BELL_TIMES = {
    "z": None,
    "p1": {"start": "08:00", "end": "08:45"},
    "p2": {"start": "08:50", "end": "09:35"},
    "wave1": {"lunch": {"start": "10:49", "end": "11:19"}, "period3": {"start": "11:21", "end": "12:31"}},
    "wave2": {"period3": {"start": "10:54", "end": "12:04"}, "lunch": {"start": "12:06", "end": "12:36"}},
    "p4": {"start": "11:20", "end": "12:05"},
    "p5": {"start": "12:10", "end": "12:55"},
}


def _default_day_schedule() -> dict:
    return {"z": None, "periods": [None] * 5, "lunch_wave": 1, "period5_end": None}


def _default_schedule() -> dict:
    return {
        "bell_times": dict(DEFAULT_BELL_TIMES),
        "courses": {},
        "day_schedules": {d: _default_day_schedule() for d in DAY_NUMBERS},
    }


def get_school_schedule(collection, user_id) -> dict:
    """Each user has their own school-schedule document, keyed by their own _id."""
    doc = collection.find_one({"_id": user_id})
    merged = _default_schedule()
    if not doc:
        return merged

    if doc.get("bell_times"):
        merged["bell_times"].update(doc["bell_times"])
    if doc.get("courses"):
        merged["courses"].update(doc["courses"])
    if doc.get("day_schedules"):
        for day_num, day_sched in doc["day_schedules"].items():
            if day_num in merged["day_schedules"] and day_sched:
                merged["day_schedules"][day_num].update(day_sched)
    return merged


def update_school_schedule(collection, user_id, updates: dict) -> dict:
    if updates:
        collection.update_one({"_id": user_id}, {"$set": updates}, upsert=True)
    return get_school_schedule(collection, user_id)


def get_last_event_watermark(collection, user_id) -> str | None:
    """The end time (ISO 8601) of the furthest-in-the-future event this tool has
    created for the user. Lets delete-future-events bound its calendar search to
    that point instead of searching with no upper bound, which is what made it slow."""
    doc = collection.find_one({"_id": user_id})
    return doc.get("last_event_end") if doc else None


def record_last_event_watermark(collection, user_id, events: list[dict]) -> None:
    """Advances the watermark to the latest `end` among `events`, never moving it
    backwards — a /generate call for an earlier date range shouldn't erase a
    further-out watermark left by an earlier call whose events haven't been
    deleted yet."""
    if not events:
        return
    newest_end = max(events, key=lambda ev: datetime.fromisoformat(ev["end"]))["end"]
    current = get_last_event_watermark(collection, user_id)
    if current is None or datetime.fromisoformat(newest_end) > datetime.fromisoformat(current):
        collection.update_one({"_id": user_id}, {"$set": {"last_event_end": newest_end}}, upsert=True)


def clear_last_event_watermark(collection, user_id) -> None:
    collection.update_one({"_id": user_id}, {"$set": {"last_event_end": None}}, upsert=True)


def get_last_generation(collection, user_id) -> dict | None:
    """The params of the most recent /generate call — lets a later snow-day
    request figure out what rotation day a given date already holds, and how
    far out the previously-created events run, without the caller having to
    resend the whole range."""
    doc = collection.find_one({"_id": user_id})
    return doc.get("last_generation") if doc else None


def record_last_generation(
    collection, user_id, *, start_date: str, end_date: str, start_day_number: str,
    off_dates: list[str], early_dismissals: list[dict],
) -> None:
    collection.update_one(
        {"_id": user_id},
        {"$set": {"last_generation": {
            "start_date": start_date,
            "end_date": end_date,
            "start_day_number": start_day_number,
            "off_dates": sorted(off_dates),
            "early_dismissals": early_dismissals,
        }}},
        upsert=True,
    )


def clear_last_generation(collection, user_id) -> None:
    collection.update_one({"_id": user_id}, {"$set": {"last_generation": None}}, upsert=True)


def rotation_day_number_on(start_date: date, start_day_number: str, off_dates: set[str], target_date: date) -> str:
    """Walks the same weekday/off-date rotation as compute_school_events, up to
    (not including) target_date, and returns the day number target_date would
    be assigned. Used so a snow day added after the fact can hand that same
    number to the next real school day — the rotation just picks up there
    instead of being consumed by the now-cancelled date."""
    current_day_num = int(start_day_number)
    d = start_date
    while d < target_date:
        if d.weekday() < 5 and d.isoformat() not in off_dates:
            current_day_num = current_day_num % 6 + 1
        d += timedelta(days=1)
    return str(current_day_num)


def _day_schedule_signature(schedule: dict, day_num: str) -> dict[str, str]:
    """Maps period label -> the event title this day number currently produces
    for that slot (e.g. "Period 1" -> "Chemistry"), per this schedule's live
    bell_times/courses config. Used to recognize, from calendar events alone,
    which of the 6 rotation days already-created events represent."""
    day_sched = schedule["day_schedules"][day_num]
    courses = schedule.get("courses", {})
    periods = day_sched.get("periods") or [None] * 5
    slots = [
        ("Z Block", day_sched.get("z")),
        ("Period 1", periods[0]),
        ("Period 2", periods[1]),
        ("Period 3", periods[2]),
        ("Period 4", periods[3]),
        ("Period 5", periods[4]),
    ]
    return {label: courses.get(block, f"{block} Block") for label, block in slots if block is not None}


def _label_for_start_time(bell_times: dict, start_iso: str) -> str | None:
    """Identifies which slot (Z Block, Period 1..5) a calendar event belongs to
    purely from its own start clock time — those are fixed per slot regardless
    of which rotation day it is, except Period 3 which has two possible start
    times (one per lunch wave)."""
    start_hhmm = datetime.fromisoformat(start_iso).strftime("%H:%M")
    for wave in ("wave1", "wave2"):
        if start_hhmm == bell_times[wave]["period3"]["start"]:
            return "Period 3"
    fixed = {
        "Z Block": (bell_times.get("z") or {}).get("start"),
        "Period 1": bell_times["p1"]["start"],
        "Period 2": bell_times["p2"]["start"],
        "Period 4": bell_times["p4"]["start"],
        "Period 5": bell_times["p5"]["start"],
    }
    for label, bell_start in fixed.items():
        if bell_start and start_hhmm == bell_start:
            return label
    return None


def resolve_day_number_from_events(schedule: dict, events: list[dict]) -> str | None:
    """Given the raw Google Calendar event objects (already filtered to this
    tool's " [SCHOOL]"-suffixed events) that fall on one date, figures out which
    of the 6 rotation days produced them — by identifying each event's slot from
    its start time, then finding the day number whose current course
    assignments match every observed (slot, title) pair. Returns None if no
    events are usable, or if more than one day number is equally consistent
    with what's observed (schedule changed since these events were created).
    """
    observed: dict[str, str] = {}
    for ev in events:
        summary = ev.get("summary", "")
        if not summary.endswith(SCHOOL_EVENT_SUFFIX):
            continue
        title = summary[: -len(SCHOOL_EVENT_SUFFIX)]
        if title == "Lunch":
            continue
        start_iso = ev.get("start", {}).get("dateTime")
        if not start_iso:
            continue
        label = _label_for_start_time(schedule["bell_times"], start_iso)
        if label:
            observed[label] = title

    if not observed:
        return None

    matches = [
        day_num
        for day_num in DAY_NUMBERS
        if all(_day_schedule_signature(schedule, day_num).get(label) == title for label, title in observed.items())
    ]
    return matches[0] if len(matches) == 1 else None


def _daily_slots(bell_times: dict, day_sched: dict) -> list[tuple[str, str | None, dict | None]]:
    """
    Returns (label, block_letter_or_None_for_lunch_or_free, bell_time) for every
    slot in a school day, in chronological order. A slot is omitted from the
    calendar downstream if its bell_time is missing (e.g. no Z block that day)
    or its block is None (a free/unscheduled period).
    """
    periods = day_sched.get("periods") or [None] * 5
    lunch_wave = day_sched.get("lunch_wave", 1)
    wave_times = bell_times.get(f"wave{lunch_wave}") or {}
    period_3 = ("Period 3", periods[2], wave_times.get("period3"))
    lunch = ("Lunch", "LUNCH", wave_times.get("lunch"))
    slots = [
        ("Z Block", day_sched.get("z"), bell_times.get("z")),
        ("Period 1", periods[0], bell_times.get("p1")),
        ("Period 2", periods[1], bell_times.get("p2")),
    ]
    # wave 1 -> lunch comes before 3rd period; wave 2 -> lunch comes after.
    slots += [lunch, period_3] if lunch_wave == 1 else [period_3, lunch]

    p5_bell_time = bell_times.get("p5")
    period5_end = day_sched.get("period5_end")
    if p5_bell_time and period5_end:
        p5_bell_time = {"start": p5_bell_time["start"], "end": period5_end}

    slots += [
        ("Period 4", periods[3], bell_times.get("p4")),
        ("Period 5", periods[4], p5_bell_time),
    ]
    return slots


def compute_school_events(
    schedule: dict,
    start_date: date,
    end_date: date,
    off_dates: set[str],
    start_day_number: str,
    tz_str: str,
    early_dismissals: dict[str, str] | None = None,
) -> list[dict]:
    """
    Walks each calendar day from start_date to end_date, skipping weekends and
    any date in off_dates, and assigns the 6-day rotation only to the days that
    remain — so a school holiday doesn't consume a rotation slot the way a
    weekend doesn't. Returns one dict per calendar event to create.

    early_dismissals maps an ISO date to a period-5-end override for that
    specific calendar date — unlike a day-schedule's own period5_end (which
    recurs every time that rotation day comes around, e.g. Day 6 always lets
    out early), this applies once regardless of which rotation day it lands on.
    """
    tz = ZoneInfo(tz_str)
    bell_times = schedule["bell_times"]
    courses = schedule.get("courses", {})
    early_dismissals = early_dismissals or {}

    events = []
    current_day_num = int(start_day_number)
    d = start_date
    while d <= end_date:
        is_school_day = d.weekday() < 5 and d.isoformat() not in off_dates
        if is_school_day:
            day_sched = schedule["day_schedules"][str(current_day_num)]
            dismissal_override = early_dismissals.get(d.isoformat())
            if dismissal_override:
                day_sched = {**day_sched, "period5_end": dismissal_override}
            for label, block, bell_time in _daily_slots(bell_times, day_sched):
                if block is None or bell_time is None:
                    continue
                title = "Lunch" if block == "LUNCH" else courses.get(block, f"{block} Block")
                start_dt = datetime.combine(d, _parse_time(bell_time["start"]), tzinfo=tz)
                end_dt = datetime.combine(d, _parse_time(bell_time["end"]), tzinfo=tz)
                events.append({
                    "title": title,
                    "label": label,
                    "date": d.isoformat(),
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat(),
                })
            current_day_num = current_day_num % 6 + 1
        d += timedelta(days=1)
    return events


def _parse_time(hhmm: str) -> time:
    hour, minute = hhmm.split(":")
    return time(int(hour), int(minute))
