import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator, model_validator
from database import school_schedule_collection, settings_collection, users_collection
from auth.session import get_current_user
from auth.google_auth import get_credentials_for_user
from services.calendar_write import create_school_gcal_events_bulk, delete_gcal_events_bulk
from services.calendar_service import search_events
from services.settings_service import get_settings
from services.school_schedule_service import (
    get_school_schedule,
    update_school_schedule,
    compute_school_events,
    get_last_event_watermark,
    record_last_event_watermark,
    clear_last_event_watermark,
    record_last_generation,
    clear_last_generation,
    resolve_day_number_from_events,
    SCHOOL_EVENT_SUFFIX,
)

router = APIRouter()

TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
BlockLetter = Literal["A", "B", "C", "D", "E", "F", "G", "T"]
DayNumber = Literal["1", "2", "3", "4", "5", "6"]
MAX_GENERATE_DAYS = 366


class BellTime(BaseModel):
    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def validate_time(cls, v):
        if not TIME_RE.match(v):
            raise ValueError("must be in 24-hour HH:MM format")
        return v


class WaveTimes(BaseModel):
    lunch: BellTime
    period3: BellTime


class BellTimes(BaseModel):
    z: BellTime | None = None
    p1: BellTime
    p2: BellTime
    wave1: WaveTimes
    wave2: WaveTimes
    p4: BellTime
    p5: BellTime


class DaySchedule(BaseModel):
    z: BlockLetter | None = None
    periods: list[BlockLetter | None]
    lunch_wave: Literal[1, 2]
    # Early-dismissal override — e.g. Day 6 lets out sooner, so period 5 ends at
    # a different clock time on that day only. Leaves the normal p5 start alone.
    period5_end: str | None = None

    @field_validator("periods")
    @classmethod
    def validate_period_count(cls, v):
        if len(v) != 5:
            raise ValueError("periods must have exactly 5 entries (periods 1-5)")
        return v

    @field_validator("period5_end")
    @classmethod
    def validate_period5_end(cls, v):
        if v is not None and not TIME_RE.match(v):
            raise ValueError("must be in 24-hour HH:MM format")
        return v


class ScheduleConfigUpdate(BaseModel):
    bell_times: BellTimes | None = None
    courses: dict[BlockLetter, str] | None = None
    day_schedules: dict[DayNumber, DaySchedule] | None = None


class EarlyDismissal(BaseModel):
    date: date
    period5_end: str

    @field_validator("period5_end")
    @classmethod
    def validate_period5_end(cls, v):
        if not TIME_RE.match(v):
            raise ValueError("must be in 24-hour HH:MM format")
        return v


class GenerateIn(BaseModel):
    start_date: date
    end_date: date
    start_day_number: DayNumber = "1"
    off_dates: list[date] = []
    early_dismissals: list[EarlyDismissal] = []

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if (self.end_date - self.start_date).days > MAX_GENERATE_DAYS:
            raise ValueError(f"range cannot exceed {MAX_GENERATE_DAYS} days")
        overlap = {d.isoformat() for d in self.off_dates} & {e.date.isoformat() for e in self.early_dismissals}
        if overlap:
            raise ValueError(f"dates can't be both a day off and an early dismissal: {', '.join(sorted(overlap))}")
        return self


class SnowDayIn(BaseModel):
    date: date


@router.get("")
def read_school_schedule(user: dict = Depends(get_current_user)):
    return get_school_schedule(school_schedule_collection, user["_id"])


@router.patch("")
def patch_school_schedule(body: ScheduleConfigUpdate, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    return update_school_schedule(school_schedule_collection, user["_id"], updates)


@router.post("/generate")
def generate_school_schedule(body: GenerateIn, user: dict = Depends(get_current_user)):
    schedule = get_school_schedule(school_schedule_collection, user["_id"])
    settings = get_settings(settings_collection, user["_id"])
    try:
        creds = get_credentials_for_user(user, users_collection)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Please connect your Google Calendar in Settings before adding your schedule.",
        )

    off_dates = {d.isoformat() for d in body.off_dates}
    early_dismissals = {e.date.isoformat(): e.period5_end for e in body.early_dismissals}
    events = compute_school_events(
        schedule,
        body.start_date,
        body.end_date,
        off_dates,
        body.start_day_number,
        settings["timezone"],
        early_dismissals,
    )
    if not events:
        raise HTTPException(status_code=400, detail="No school days found in that date range")

    gcal_ids = create_school_gcal_events_bulk(creds, events)
    created = [{**ev, "gcal_event_id": gid} for ev, gid in zip(events, gcal_ids)]
    record_last_event_watermark(school_schedule_collection, user["_id"], events)
    record_last_generation(
        school_schedule_collection,
        user["_id"],
        start_date=body.start_date.isoformat(),
        end_date=body.end_date.isoformat(),
        start_day_number=body.start_day_number,
        off_dates=sorted(off_dates),
        early_dismissals=[e.model_dump(mode="json") for e in body.early_dismissals],
    )

    return {"created_count": len(created), "events": created}


@router.post("/snow-day")
def add_snow_day(body: SnowDayIn, user: dict = Depends(get_current_user)):
    """
    Removes a single school day (e.g. a snow closure) from an already-generated
    calendar and shifts the rotation for every day after it back one school
    day — Day 2 becomes whatever Day 3 would've been, etc. — rather than
    skipping the rotation number that date would've had.

    Reads everything it needs straight from Google Calendar (the actual source
    of truth) instead of a remembered /generate call: which rotation day the
    snow date itself currently holds (inferred from its events' titles and
    slot times), how far out the schedule already runs, and which weekdays in
    between are already-declared days off. That keeps this working even if a
    /generate record was never made for this account, is stale, or got cleared
    by a since-run "delete school events" whose calendar deletes didn't fully
    land — snow days are unplanned by nature, so this shouldn't depend on
    Breadcrumbs' own memory of a prior action being intact.

    One tradeoff: a one-off early-dismissal date within the shifted range
    (declared via /generate's early_dismissals, not a day's own recurring
    period5_end) can't be recovered from calendar-event content alone, so it's
    not preserved by a snow day that shifts past it.
    """
    snow_date = body.date
    if snow_date.weekday() >= 5:
        raise HTTPException(status_code=400, detail="That date is a weekend — there's no school day to remove.")

    schedule = get_school_schedule(school_schedule_collection, user["_id"])
    settings = get_settings(settings_collection, user["_id"])
    try:
        creds = get_credentials_for_user(user, users_collection)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Please connect your Google Calendar in Settings before adding a snow day.",
        )

    tz = ZoneInfo(settings["timezone"])
    snow_day_start = datetime.combine(snow_date, time.min, tzinfo=tz)
    scan_end = datetime.combine(snow_date + timedelta(days=MAX_GENERATE_DAYS), time.min, tzinfo=tz)

    future_candidates = search_events(
        creds, "[SCHOOL]", time_min_iso=snow_day_start.isoformat(), time_max_iso=scan_end.isoformat()
    )
    future_events = [ev for ev in future_candidates if ev.get("summary", "").endswith(SCHOOL_EVENT_SUFFIX)]

    todays_events = [
        ev for ev in future_events
        if ev.get("start", {}).get("dateTime", "")[:10] == snow_date.isoformat()
    ]
    if not todays_events:
        raise HTTPException(
            status_code=400,
            detail="No school events found on that date — add your schedule to Google Calendar first, or double-check the date.",
        )

    resume_day_number = resolve_day_number_from_events(schedule, todays_events)
    if resume_day_number is None:
        raise HTTPException(
            status_code=400,
            detail="Couldn't match that date's calendar events to your current schedule configuration — has the schedule changed since these events were added?",
        )

    dates_with_events = {ev["start"]["dateTime"][:10] for ev in future_events if ev.get("start", {}).get("dateTime")}
    end_date = max(date.fromisoformat(d) for d in dates_with_events)

    off_dates: set[str] = set()
    d = snow_date
    while d <= end_date:
        if d.weekday() < 5 and d.isoformat() not in dates_with_events:
            off_dates.add(d.isoformat())
        d += timedelta(days=1)
    off_dates.add(snow_date.isoformat())

    delete_gcal_events_bulk(creds, [ev["id"] for ev in future_events])

    new_events = compute_school_events(
        schedule, snow_date, end_date, off_dates, resume_day_number, settings["timezone"], early_dismissals={},
    )
    gcal_ids = create_school_gcal_events_bulk(creds, new_events)
    created = [{**ev, "gcal_event_id": gid} for ev, gid in zip(new_events, gcal_ids)]

    record_last_event_watermark(school_schedule_collection, user["_id"], new_events)

    return {"removed_date": snow_date.isoformat(), "deleted_count": len(future_events), "created_count": len(created), "events": created}


@router.post("/delete-future-events")
def delete_future_school_events(user: dict = Depends(get_current_user)):
    """
    Deletes every future calendar event this tool created — anything whose title
    ends in " [SCHOOL]" — regardless of when it was generated or from which
    date range. Google's q= search is fuzzy (matches anywhere in the event, not
    just the title), so results are re-filtered on the exact suffix before deleting.

    Bounds the search with a stored watermark (the end time of the furthest-out
    event /generate has created) instead of searching with no upper bound —
    unbounded search was slow, since Google has to scan arbitrarily far into the
    future to know it's done. Falls back to unbounded if no watermark is on
    record (e.g. events created before this watermark existed).
    """
    try:
        creds = get_credentials_for_user(user, users_collection)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Please connect your Google Calendar in Settings first.",
        )

    now = datetime.now(timezone.utc)
    watermark = get_last_event_watermark(school_schedule_collection, user["_id"])
    if watermark and datetime.fromisoformat(watermark) <= now:
        # Everything on record has already passed — nothing future to delete.
        clear_last_event_watermark(school_schedule_collection, user["_id"])
        clear_last_generation(school_schedule_collection, user["_id"])
        return {"deleted_count": 0}

    time_max_iso = (datetime.fromisoformat(watermark) + timedelta(minutes=1)).isoformat() if watermark else None
    candidates = search_events(creds, "[SCHOOL]", time_min_iso=now.isoformat(), time_max_iso=time_max_iso)
    to_delete = [e for e in candidates if e.get("summary", "").endswith(SCHOOL_EVENT_SUFFIX)]

    delete_gcal_events_bulk(creds, [ev["id"] for ev in to_delete])
    clear_last_event_watermark(school_schedule_collection, user["_id"])
    # Also clears the /generate params a snow day would resume from — otherwise
    # a later snow-day call would recreate events this call just deleted.
    clear_last_generation(school_schedule_collection, user["_id"])

    return {"deleted_count": len(to_delete)}
