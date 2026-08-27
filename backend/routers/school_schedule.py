import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator, model_validator
from database import school_schedule_collection, settings_collection, users_collection
from auth.session import get_current_user
from auth.google_auth import get_credentials_for_user
from rate_limit import rate_limit
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
    label_for_start_time,
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


@router.post("/generate", dependencies=[Depends(rate_limit("10/minute"))])
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


@router.post("/snow-day", dependencies=[Depends(rate_limit("10/minute"))])
def add_snow_day(body: SnowDayIn, user: dict = Depends(get_current_user)):
    """
    Removes a single school day (e.g. a snow closure) from an already-generated
    calendar and shifts every already-scheduled day after it one day later to
    absorb the gap — Day 3 (which was going to happen on the snow date)
    instead happens on the next school day, Day 4 moves to the day after that,
    and so on — with one new school day appended past whatever was previously
    the last one, so nothing at the end gets silently dropped.

    This works purely off the actual calendar content already sitting on each
    of those already-scheduled dates — pairing "date N" with "whatever's
    already on date N+1" and reusing it verbatim (same title, same clock
    time, just moved to a new date) — instead of recomputing anything from the
    bell_times/courses config or a remembered /generate call. That means it
    keeps working even if a /generate record was never made for this account,
    is stale, or got cleared by a since-run "delete school events" whose
    calendar deletes didn't fully land, and it never needs to guess which of
    the 6 rotation days a date "should" be — so a schedule edited since these
    events were created can't make it misfire. It also means a one-off early
    dismissal already baked into an event's end time rides along with it
    automatically when that event's day shifts.
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

    candidates = search_events(
        creds, "[SCHOOL]", time_min_iso=snow_day_start.isoformat(), time_max_iso=scan_end.isoformat()
    )
    future_events = [ev for ev in candidates if ev.get("summary", "").endswith(SCHOOL_EVENT_SUFFIX)]

    events_by_date: dict[str, list[dict]] = {}
    for ev in future_events:
        start_iso = ev.get("start", {}).get("dateTime")
        if not start_iso:
            continue
        events_by_date.setdefault(start_iso[:10], []).append(ev)

    if snow_date.isoformat() not in events_by_date:
        raise HTTPException(
            status_code=400,
            detail="No school events found on that date — add your schedule to Google Calendar first, or double-check the date.",
        )

    # Every date that currently has events, chronological — old_dates[0] is
    # snow_date itself (guaranteed: the search starts at snow_date, and we've
    # just confirmed it has events). Dates with no events in between (existing
    # holidays) are simply absent, so they're untouched by the shift.
    old_dates = sorted(date.fromisoformat(d) for d in events_by_date)

    extra_date = old_dates[-1] + timedelta(days=1)
    while extra_date.weekday() >= 5:
        extra_date += timedelta(days=1)
    # new_target_dates[i] is where old_dates[i]'s content moves to: the next
    # already-scheduled date for every date but the last, and this freshly
    # appended one for the last date's content.
    new_target_dates = old_dates[1:] + [extra_date]

    new_events = []
    for old_d, target_d in zip(old_dates, new_target_dates):
        for ev in events_by_date[old_d.isoformat()]:
            summary = ev.get("summary", "")
            title = summary[: -len(SCHOOL_EVENT_SUFFIX)] if summary.endswith(SCHOOL_EVENT_SUFFIX) else summary
            start_iso = ev["start"]["dateTime"]
            end_iso = ev.get("end", {}).get("dateTime", start_iso)
            new_start = datetime.combine(target_d, datetime.fromisoformat(start_iso).time(), tzinfo=tz)
            new_end = datetime.combine(target_d, datetime.fromisoformat(end_iso).time(), tzinfo=tz)
            new_events.append({
                "title": title,
                "label": label_for_start_time(schedule["bell_times"], start_iso) or "",
                "date": target_d.isoformat(),
                "start": new_start.isoformat(),
                "end": new_end.isoformat(),
            })

    delete_gcal_events_bulk(creds, [ev["id"] for ev in future_events])

    gcal_ids = create_school_gcal_events_bulk(creds, new_events)
    created = [{**ev, "gcal_event_id": gid} for ev, gid in zip(new_events, gcal_ids)]

    record_last_event_watermark(school_schedule_collection, user["_id"], new_events)

    return {"removed_date": snow_date.isoformat(), "deleted_count": len(future_events), "created_count": len(created), "events": created}


@router.post("/delete-future-events", dependencies=[Depends(rate_limit("10/minute"))])
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
